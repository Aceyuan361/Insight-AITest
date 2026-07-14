# -*- coding: utf-8 -*-
"""Task 生命周期 HTTP 全链路测试。

用 httpx.AsyncClient + ASGITransport 在持久事件循环里测 SSE stream / select /
generate-batch 端点。这是之前 TestClient 下的结构性盲区——后台线程的
run_coroutine_threadsafe 在请求级事件循环关闭后失败，导致 stream 回填 bug 等
问题不可见。

覆盖矩阵：
  T1 stream 创建 → DB 有 context + strategies（stream 回填回归）
  T2 stream 事件序列完整（phase/understand_done/strategies_done/done）
  T3 stream LLM 异常 → error + FAILED
  T4 select → 后台执行 → task 终态
  T5 generate-batch 全链路 → batch_id 写入 DB
  T6 generate-batch 空测试点 → 400
  T7 select 不存在的策略 → 400
  T8 GET /tasks/{id}/stream 消费队列事件
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import httpx
from fastapi import FastAPI
from httpx import ASGITransport

BASE = "/api/modules/ai/tasks"


# ===== 可控 FakeLLM =====


class _ScriptedLLM:
    """可控假 LLM：understand/strategize 返回预设 JSON。

    chat() 用于同步路径；stream_chat() 用于 thinking_level=off 的 stream 路径，
    把预设 JSON 整块 yield（planner 拼接后 _extract_json 解析）。
    """

    def __init__(self, understand_json: str, strategies_json: str):
        self._understand = understand_json
        self._strategies = strategies_json
        self._call_idx = 0

    def chat(self, messages, **kwargs):
        # planner 先调 understand 再调 strategies
        self._call_idx += 1
        return self._understand if self._call_idx % 2 == 1 else self._strategies

    def stream_chat(self, messages, **kwargs):
        # 同 chat 的顺序
        self._call_idx += 1
        raw = self._understand if self._call_idx % 2 == 1 else self._strategies
        yield raw

    def stream_chat_raw(self, messages, thinking_level="off", **kwargs):
        self._call_idx += 1
        raw = self._understand if self._call_idx % 2 == 1 else self._strategies
        yield ("content", raw)

    def embed(self, texts):
        return [[0.1] * 4 for _ in texts]

    def embed_query(self, text):
        return [0.1] * 4


_UNDERSTAND_JSON = '{"summary": "登录功能含账密和验证码登录", "scope": ["账密登录", "验证码登录"]}'

_STRATEGIES_JSON = json.dumps([
    {
        "id": "A",
        "label": "批量生成用例",
        "description": "从需求文档提取测试点",
        "plan": [
            {"skill": "extract_test_points", "desc": "提取测试点",
             "params": {"query": "登录功能", "documents_text": "需求"}},
        ],
    },
    {
        "id": "B",
        "label": "功能用例",
        "description": "生成功能用例",
        "plan": [
            {"skill": "rag_search", "desc": "检索", "params": {"query": "登录"}},
            {"skill": "write_functional_case", "desc": "生成", "params": {"query": "登录", "design": "positive"}},
        ],
    },
])


# ===== 异步夹具 =====


def _build_async_app(tmp_path, monkeypatch, llm=None):
    """构造用 tmp 目录的 app，返回 (app, ai_db_path)。

    与 test_agent_tasks._setup_app 同构，但不返回 TestClient——调用方用
    httpx.AsyncClient + ASGITransport 自己管理事件循环。
    """
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
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
    # 重置 generator 单例（generate-batch 需要）
    tc_deps._generator = None

    cfg = deps.get_config()
    cfg.db_path = str(tmp_path / "kb.db")
    cfg.docs_dir = str(tmp_path / "docs")
    ai_db_path = str(tmp_path / "ai.db")
    deps._db = ai_db_mod.AIDatabase(ai_db_path)
    tc_deps._tc_db = tc_db_mod.TestCaseDatabase(str(tmp_path / "testcase.db"))

    fake = llm or _ScriptedLLM(_UNDERSTAND_JSON, _STRATEGIES_JSON)
    kb_deps._llm = fake
    kb_deps._llm_config = cfg

    from insight_aitest.modules.ai.backend.routes import router as ai_router
    app = FastAPI()
    app.include_router(ai_router, prefix="/api/modules/ai")
    return app, ai_db_path


def _inject_mock_generator(monkeypatch):
    """注入 mock generator（generate-batch 的 write_cases_batch 用，不调真实 LLM）。"""
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CaseType, CaseStatus, CasePriority, TestType, TestCase,
    )

    def _fake_generate(point, **kwargs):
        return TestCase(
            title=f"用例-{getattr(point, 'summary', '')}",
            type=CaseType.FUNCTIONAL, description="",
            priority=CasePriority.P2, status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE, preconditions="",
            content={"steps": []}, tags=[],
        )

    import insight_aitest.modules.testcase.backend.deps as tc_deps_mod
    mock_gen = MagicMock()
    mock_gen.generate = _fake_generate
    monkeypatch.setattr(tc_deps_mod, "get_generator", lambda: mock_gen)


async def _read_sse_events(response) -> list[tuple[str, dict]]:
    """从 httpx streaming response 读全部 SSE 事件，返回 [(type, data), ...]。"""
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


# ===== T1: stream 创建 → DB 有 context + strategies（stream 回填回归）=====


async def test_t1_stream_writes_context_and_strategies_to_db(tmp_path, monkeypatch):
    """stream 创建 task 后，DB 里的 context / strategies 必须非空。

    回归测试：create_task_stream 的 _produce 曾只转发 SSE 不回填 DB，
    导致 task 卡在 pending_select 但 strategies 为空。
    """
    app, _ = _build_async_app(tmp_path, monkeypatch)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 读完整 stream
        async with client.stream("POST", f"{BASE}/stream",
                                  json={"intent": "帮我批量生成登录用例"}) as resp:
            assert resp.status_code == 200
            events = await _read_sse_events(resp)

    # 最后一个 done 事件里有 task
    done_events = [d for t, d in events if t == "done"]
    assert done_events, "stream 必须以 done 事件结束"
    task_id = done_events[0]["task"]["id"]

    # 关键断言：DB 里的 context / strategies 被正确回填
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/{task_id}")
        task = r.json()

    assert task["status"] == "pending_select"
    # context.summary 应是 LLM 返回的（非原始 intent）
    assert "登录功能" in task["context"]["summary"]
    assert len(task["context"]["scope"]) >= 1
    # strategies 非空（回填修复的核心）
    assert len(task["strategies"]) >= 1
    assert task["strategies"][0]["id"] in ("A", "B")


# ===== T2: stream 事件序列完整 =====


async def test_t2_stream_event_sequence_complete(tmp_path, monkeypatch):
    """stream 必须产出完整事件序列：phase×2 + understand_done + strategies_done + done。"""
    app, _ = _build_async_app(tmp_path, monkeypatch)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", f"{BASE}/stream",
                                  json={"intent": "测试登录"}) as resp:
            events = await _read_sse_events(resp)

    evt_types = [t for t, _ in events]
    assert "phase" in evt_types
    assert "understand_done" in evt_types
    assert "strategies_done" in evt_types
    assert "done" in evt_types
    # done 是最后一个
    assert evt_types[-1] == "done"


# ===== T3: stream LLM 异常 → error + 失败任务被删除（不残留 FAILED）=====


async def test_t3_stream_llm_error_emits_error_and_deletes_task(tmp_path, monkeypatch):
    """LLM 抛异常 → stream 产 error 事件，失败任务直接删除（不残留 FAILED 行）。

    设计变更（会话管理修复）：理解/策略阶段失败的任务直接删除，
    避免切换 tab 后出现重复会话（FAILED 残留 + 新任务）。
    """
    class _ExplodingLLM(_ScriptedLLM):
        def chat(self, messages, **kwargs):
            raise RuntimeError("LLM 服务不可用")
        def stream_chat(self, messages, **kwargs):
            raise RuntimeError("LLM 服务不可用")

    app, _ = _build_async_app(tmp_path, monkeypatch, llm=_ExplodingLLM("", ""))

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", f"{BASE}/stream",
                                  json={"intent": "测试"}) as resp:
            events = await _read_sse_events(resp)

    evt_types = [t for t, _ in events]
    assert "error" in evt_types
    # 失败任务应被删除——查 tasks 列表应为空（无 FAILED 残留）
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(BASE)
        tasks = r.json()
    failed = [t for t in tasks if t["status"] == "failed"]
    assert len(failed) == 0
    assert len(tasks) == 0


# ===== T4: select → 后台执行 → task 终态 =====


async def test_t4_select_executes_and_reaches_terminal_state(tmp_path, monkeypatch):
    """select 策略 → 后台执行 → task 到达 done/failed 终态。

    select 端点之前从未 HTTP 测过（TestClient 事件循环问题）。
    """
    _inject_mock_generator(monkeypatch)
    app, _ = _build_async_app(tmp_path, monkeypatch)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1) 先 stream 创建 task + 拿策略
        async with client.stream("POST", f"{BASE}/stream",
                                  json={"intent": "测试登录"}) as resp:
            events = await _read_sse_events(resp)
        task_id = [d for t, d in events if t == "done"][0]["task"]["id"]
        task = (await client.get(f"{BASE}/{task_id}")).json()
        strategy_id = task["strategies"][0]["id"]

        # 2) select 策略
        r = await client.post(f"{BASE}/{task_id}/select",
                              json={"strategy_id": strategy_id})
        assert r.status_code == 200

        # 3) 轮询等待后台执行完成
        final = await _poll_until_terminal(client, task_id, timeout=8)
        assert final["status"] in ("done", "failed"), \
            f"select 后应到终态，实际 {final['status']}"
        # result 有 steps
        assert "steps" in (final["result"] or {})


async def _poll_until_terminal(client, task_id, timeout=8) -> dict:
    """轮询 task 直到 done/failed/cancelled。"""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        r = await client.get(f"{BASE}/{task_id}")
        task = r.json()
        if task["status"] in ("done", "failed", "cancelled"):
            return task
        await asyncio.sleep(0.15)
    # 超时返回最后状态
    return (await client.get(f"{BASE}/{task_id}")).json()


# ===== T5: generate-batch 全链路 → batch_id 写入 DB =====


async def test_t5_generate_batch_full_pipeline_writes_batch_id(tmp_path, monkeypatch):
    """generate-batch 端点 → 后台执行 write_cases_batch → result.batch_id 写入 DB。

    之前只测了同步返回（plan 构造），后台执行 + batch_id 汇总从未测过。
    """
    _inject_mock_generator(monkeypatch)
    app, _ = _build_async_app(tmp_path, monkeypatch)

    # 先创建一个 task（同步 create，不走 stream）
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(BASE, json={"intent": "批量生成用例"})
        task_id = r.json()["id"]

        test_points = [
            {"id": "tp1", "description": "正确登录", "type_hint": "functional", "design_hint": "positive"},
            {"id": "tp2", "description": "空密码", "type_hint": "functional", "design_hint": "negative"},
        ]
        r = await client.post(f"{BASE}/{task_id}/generate-batch",
                              json={"test_points": test_points, "project_id": 1, "version_id": 2})
        assert r.status_code == 200

        final = await _poll_until_terminal(client, task_id, timeout=10)
        assert final["status"] == "done", f"期望 done，实际 {final['status']}，error={final.get('error')}"
        # batch_id 汇总到 result 顶层
        assert final["result"].get("batch_id"), "result.batch_id 必须非空"
        assert final["result"]["batch_id"].startswith(f"batch-{task_id}-")


# ===== T6: generate-batch 空测试点 → 400 =====


async def test_t6_generate_batch_empty_points_returns_400(tmp_path, monkeypatch):
    app, _ = _build_async_app(tmp_path, monkeypatch)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(BASE, json={"intent": "x"})
        task_id = r.json()["id"]
        r = await client.post(f"{BASE}/{task_id}/generate-batch", json={"test_points": []})
        assert r.status_code == 400


# ===== T7: select 不存在的策略 → 400 =====


async def test_t7_select_nonexistent_strategy_returns_400(tmp_path, monkeypatch):
    app, _ = _build_async_app(tmp_path, monkeypatch)
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with client.stream("POST", f"{BASE}/stream", json={"intent": "x"}) as resp:
            events = await _read_sse_events(resp)
        task_id = [d for t, d in events if t == "done"][0]["task"]["id"]
        r = await client.post(f"{BASE}/{task_id}/select",
                              json={"strategy_id": "NONEXISTENT"})
        assert r.status_code == 400


# ===== T8: GET /tasks/{id}/stream 消费队列事件 =====


async def test_t8_stream_task_consumes_queue_events(tmp_path, monkeypatch):
    """GET /tasks/{id}/stream 在 select 后能消费 executor 推送的细粒度事件。"""
    _inject_mock_generator(monkeypatch)
    app, _ = _build_async_app(tmp_path, monkeypatch)

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 创建 + select
        async with client.stream("POST", f"{BASE}/stream", json={"intent": "测试"}) as resp:
            events = await _read_sse_events(resp)
        task_id = [d for t, d in events if t == "done"][0]["task"]["id"]
        task = (await client.get(f"{BASE}/{task_id}")).json()
        strategy_id = task["strategies"][0]["id"]

        # select 后立刻开 stream 消费（并发：select 触发后台线程，stream 读队列）
        await client.post(f"{BASE}/{task_id}/select", json={"strategy_id": strategy_id})

        async with client.stream("GET", f"{BASE}/{task_id}/stream") as resp:
            sse_events = await _read_sse_events(resp)

    evt_types = [t for t, _ in sse_events]
    # 应该至少有 done 或 error 终态事件（队列模式或 DB 轮询模式都行）
    assert any(t in ("done", "error", "cancelled") for t in evt_types), \
        f"stream_task 应推终态事件，实际事件类型：{evt_types}"
