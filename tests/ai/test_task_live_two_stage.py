# -*- coding: utf-8 -*-
"""两阶段用例生成 · 真实 LLM 链路测试（@pytest.mark.live）。

用真实 LLM 验证 LLM 输出契约——这些是 FakeLLM 抓不到的：
- LLM 是否真的按 prompt 产出含 extract_test_points 的策略
- extract_test_points 返回的 test_points 是否结构合法
- write_cases_batch 逐条生成是否真的产出可用的 TestCase

默认 CI 跳过（addopts = "-m 'not live'"），本地手跑：
    pytest -m live tests/ai/test_task_live_two_stage.py

LLM 厂商可通过环境变量切换（覆盖配置文件），例如用 DeepSeek：
    INSIGHT_EYE_AI_LLM_BASE_URL=https://api.deepseek.com/v1 \\
    INSIGHT_EYE_AI_LLM_API_KEY=sk-xxx \\
    INSIGHT_EYE_AI_CHAT_MODEL=deepseek-v4-flash \\
    pytest -m live tests/ai/test_task_live_two_stage.py
"""
from __future__ import annotations

import asyncio
import json
import os

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport

pytestmark = pytest.mark.live

BASE = "/api/modules/ai/tasks"

_REQUIREMENTS_DOC = """# 登录功能需求
## 功能描述
用户可以通过账号密码或手机验证码登录系统。

## 测试场景
1. 正确的账号和密码登录成功
2. 密码错误时提示"密码不正确"
3. 连续输错密码 5 次锁定账号 30 分钟
4. 手机验证码登录：发送验证码、验证码校验
5. 空密码、空账号的输入校验
"""

# 真实 LLM 各阶段耗时实测基线（DeepSeek v4-flash ~2s/调用；agnes-2.0-flash ~25s/调用）。
# 超时取 2 倍余量，覆盖厂商切换与网络波动。
_EXTRACT_TIMEOUT = 180   # 阶段1：提取测试点（1 次 LLM 调用，输出 20-50 点）
_GENERATE_TIMEOUT = 120  # 阶段2：批量生成（3 点，每点 1 次 LLM + 1 次 embed）
_CLIENT_TIMEOUT = 480    # httpx 整体超时（覆盖两阶段 + 轮询）


def _build_app(tmp_path, monkeypatch):
    """构造 app，用真实 LLM（不注入 FakeLLM）。

    LLM 厂商/模型/key 由环境变量 INSIGHT_EYE_AI_* 覆盖配置文件；
    不设这些变量时回退到 ~/.insight_eye/llm_config.json。
    """
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")

    import insight_aitest.modules.ai.backend.deps as deps
    import insight_aitest.platform.services.kb.deps as kb_deps
    import insight_aitest.modules.ai.backend.persistence.database as ai_db_mod
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    import insight_aitest.modules.testcase.backend.persistence.database as tc_db_mod

    deps._db = None
    deps._agent = None
    deps._planner = None
    kb_deps._llm_config = None
    kb_deps._kb_db = None
    kb_deps._llm = None
    kb_deps._vector_store = None
    kb_deps._retriever = None
    kb_deps._config_file = None
    tc_deps._tc_db = None
    tc_deps._generator = None

    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    deps._db = ai_db_mod.AIDatabase(str(tmp_path / "ai.db"))
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "testcase.db"))

    # 不注入 FakeLLM —— 用真实 LLM
    from insight_aitest.modules.ai.backend.routes import router as ai_router
    from insight_aitest.modules.testcase.backend.routes import router as tc_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    app.include_router(tc_router, prefix="/api/modules/testcase")
    return app


def _skip_if_no_llm_key():
    from insight_aitest.platform.services.llm.config import load_config
    cfg = load_config()
    if not cfg.api_key_set:
        pytest.skip("LLM API key 未配置（环境变量或 ~/.insight_eye/llm_config.json）")


def _model_tag():
    """当前使用的 chat_model 标签（用于日志可读性）。"""
    return os.getenv("INSIGHT_EYE_AI_CHAT_MODEL", "config-default")


async def _read_sse(response):
    events = []
    buffer = ""
    async for chunk in response.aiter_text():
        buffer += chunk
        while "\n\n" in buffer:
            block, buffer = buffer.split("\n\n", 1)
            evt_type = None
            evt_data = {}
            for line in block.split("\n"):
                if line.startswith("event: "):
                    evt_type = line[7:].strip()
                elif line.startswith("data: "):
                    try:
                        evt_data = json.loads(line[6:])
                    except Exception:
                        evt_data = {"raw": line[6:]}
            if evt_type:
                events.append((evt_type, evt_data))
    return events


async def _poll(client, task_id, timeout=60):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        r = await client.get(f"{BASE}/{task_id}")
        task = r.json()
        if task["status"] in ("done", "failed", "cancelled"):
            return task
        await asyncio.sleep(0.5)
    return (await client.get(f"{BASE}/{task_id}")).json()


async def test_live_llm_produces_strategies_with_extract_test_points(tmp_path, monkeypatch):
    """真实 LLM：上传需求文档 + 批量生成意图 → 策略列表含 extract_test_points。

    验证 prompt 引导对真实 LLM 有效。不强制 E 型（LLM 可能用不同 id/label），
    只要有任一策略的 plan 含 extract_test_points skill。
    """
    _skip_if_no_llm_key()
    app = _build_app(tmp_path, monkeypatch)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                                  timeout=httpx.Timeout(_CLIENT_TIMEOUT)) as client:
        async with client.stream("POST", f"{BASE}/stream", json={
            "intent": "帮我从这份需求文档批量生成测试用例",
            "files": [{"filename": "login_req.md", "content": _REQUIREMENTS_DOC}],
        }) as resp:
            events = await _read_sse(resp)

    done = [d for t, d in events if t == "done"]
    assert done, f"stream 未正常结束，事件：{[t for t, _ in events]}"
    task = done[0]["task"]

    # 核心断言：至少一个策略含 extract_test_points
    all_skills = []
    for s in task["strategies"]:
        all_skills.extend(step["skill"] for step in s["plan"])
    assert "extract_test_points" in all_skills, \
        f"真实 LLM({_model_tag()}) 应产出含 extract_test_points 的策略，实际 skills：{all_skills}"


async def test_live_full_two_stage_pipeline(tmp_path, monkeypatch):
    """真实 LLM 全链路：extract_test_points → 确认 → write_cases_batch → batch_id 有用例。

    阶段1：选含 extract_test_points 的策略 → 执行 → task.result 应含 test_points
    阶段2：取 test_points → generate-batch → result.batch_id 下有真实用例
    """
    _skip_if_no_llm_key()
    app = _build_app(tmp_path, monkeypatch)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                                  timeout=httpx.Timeout(_CLIENT_TIMEOUT)) as client:
        # 阶段1：创建 + 选 extract 策略
        async with client.stream("POST", f"{BASE}/stream", json={
            "intent": "帮我批量生成登录功能的测试用例",
            "files": [{"filename": "login.md", "content": _REQUIREMENTS_DOC}],
        }) as resp:
            events = await _read_sse(resp)
        task = [d for t, d in events if t == "done"][0]["task"]

        # 找含 extract_test_points 的策略
        extract_strategy = None
        for s in task["strategies"]:
            if any(step["skill"] == "extract_test_points" for step in s["plan"]):
                extract_strategy = s
                break
        if not extract_strategy:
            pytest.skip(f"真实 LLM({_model_tag()}) 未产出 extract_test_points 策略，实际：{[s['id'] for s in task['strategies']]}")

        # 执行 extract 策略
        await client.post(f"{BASE}/{task['id']}/select",
                          json={"strategy_id": extract_strategy["id"]})
        final = await _poll(client, task["id"], timeout=_EXTRACT_TIMEOUT)
        assert final["status"] == "done", f"extract 执行失败：{final.get('error')}"

        # 从 result.steps 提取 test_points（skill 返回字段展开到 step 顶层）
        steps = (final["result"] or {}).get("steps", [])
        tp_step = next((st for st in steps if st.get("skill") == "extract_test_points"), None)
        assert tp_step, "result.steps 里找不到 extract_test_points 步骤"
        test_points = tp_step.get("test_points", [])
        assert len(test_points) >= 2, f"应提取≥2 个测试点，实际 {len(test_points)}：{test_points}"

        # write_cases_batch 逐条调 LLM（O(N) 串行），真实 LLM 下每点耗时随厂商波动。
        # 为保证 live 测试在合理时间内完成，只取前 3 个测试点验证链路闭环。
        # （若需全量生成性能数据，单独跑性能测试，不混入链路验证）
        test_points_slice = test_points[:3]

        # 阶段2：generate-batch
        r = await client.post(f"{BASE}/{task['id']}/generate-batch",
                              json={"test_points": test_points_slice})
        assert r.status_code == 200
        gen_final = await _poll(client, task["id"], timeout=_GENERATE_TIMEOUT)
        assert gen_final["status"] == "done", f"generate-batch 失败：{gen_final.get('error')}"
        batch_id = (gen_final["result"] or {}).get("batch_id")
        assert batch_id, "result.batch_id 必须非空"

        # 验证 batch 下有真实用例（允许部分失败，但至少 1 条成功）
        r = await client.get(f"/api/modules/testcase/testcases/batch/{batch_id}")
        assert r.status_code == 200, f"查询 batch 用例失败：{r.status_code} {r.text}"
        cases = r.json()
        assert isinstance(cases, list), f"batch 查询应返回列表，实际：{type(cases)}"
        assert len(cases) >= 1, f"batch {batch_id} 下应有用例，实际 {len(cases)}"
        # 验证用例来源标记正确（ai:batch:<model>）
        for case in cases:
            assert case.get("source", "").startswith("ai:batch:"), \
                f"用例 source 应为 ai:batch:*，实际：{case.get('source')}"
