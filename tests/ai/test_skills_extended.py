# -*- coding: utf-8 -*-
"""扩展 skill 测试：write_ui_case_from_image + 数据驱动 skill（mock + live）。

mock 测试：FakeLLM + MockTransport + MagicMock case_db，验证 skill 行为和返回结构。
live 测试：真实 LLMClient（agnes key），验证 vision + 数据驱动生成质量。
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from insight_aitest.modules.ai.backend.agent.skills import (
    SKILLS,
    SkillContext,
    _write_ui_case_from_image,
    _generate_data_driven_api_case,
    _execute_data_driven_api_case,
)
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseStatus,
    CaseType,
    TestCase,
    TestType,
)

live = pytest.mark.live

# ===== 公共夹具 =====

BASE = "https://test.local"


def _handler(request: httpx.Request) -> httpx.Response:
    """模拟被测 API：/register 根据 body 返回不同状态。"""
    p = request.url.path
    if request.method == "POST" and p == "/register":
        try:
            body = json.loads(request.content) if request.content else {}
        except Exception:
            body = {}
        # 非法用户名（含特殊字符）→ 400
        if "<" in str(body.get("username", "")):
            return httpx.Response(400, json={"err": "invalid username"})
        return httpx.Response(200, json={"code": 0, "data": {"id": 1}})
    return httpx.Response(404, text="not found")


def _transport():
    return httpx.MockTransport(_handler)


class FakeLLM:
    """假 LLM：chat 返回可控 JSON。"""

    def __init__(self, response: str = ""):
        self._response = response
        self.calls = []

    def chat(self, messages, **kwargs):
        self.calls.append(messages)
        return self._response


def _mock_ctx(llm_response: str = "", case: TestCase | None = None) -> tuple[SkillContext, MagicMock, MagicMock]:
    """构造 mock SkillContext（FakeLLM + MagicMock case_db + run_db）。"""
    case_db = MagicMock()
    if case is not None:
        case_db.get_case.return_value = case
    case_db.update_result = MagicMock()
    case_db.create_case.return_value = 1

    run_db = MagicMock()
    run_db.create_run.side_effect = lambda run: getattr(run, "id", None) or 1

    ctx = SkillContext(
        llm=FakeLLM(llm_response),
        config=MagicMock(chat_model="fake-model"),
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
        api_run_db=run_db,
        http_transport=_transport(),
    )
    return ctx, case_db, run_db


# ===== 注册断言 =====


def test_new_skills_registered():
    """3 个新 skill 注册进 SKILLS + catalog。"""
    for sid in ("write_ui_case_from_image", "generate_data_driven_api_case", "execute_data_driven_api_case"):
        assert sid in SKILLS, f"{sid} 未注册"
    from insight_aitest.modules.ai.backend.agent.skills import get_skill_catalog
    catalog = get_skill_catalog()
    for sid in ("write_ui_case_from_image", "generate_data_driven_api_case", "execute_data_driven_api_case"):
        assert sid in catalog, f"{sid} 不在 catalog"


def test_data_driven_prompt_renders_valid_json():
    """_DATA_DRIVEN_PROMPT 渲染后的 JSON 示例必须合法（防 .format() 花括号转义 bug）。"""
    import json
    from insight_aitest.modules.ai.backend.agent.skills import _DATA_DRIVEN_PROMPT, get_skill_catalog

    rendered = _DATA_DRIVEN_PROMPT.format(
        catalog=get_skill_catalog(), query="test", refs_section="",
    )
    # 抽取 JSON 示例（从 "{\n  \"title\"" 开始到最后一个 "}"）
    start = rendered.find('{\n  "title"')
    assert start != -1, "prompt 里找不到 JSON 示例起始"
    candidate = rendered[start:rendered.rfind("}") + 1]
    data = json.loads(candidate)  # 必须解析成功
    assert "content" in data
    assert "datasets" in data["content"]
    assert len(data["content"]["datasets"]) == 3
    # datasets 每项不能是双花括号（转义 bug 的特征）
    for ds in data["content"]["datasets"]:
        assert "name" in ds and "vars" in ds


def test_generate_data_driven_rejects_empty_query():
    """空 query → ValueError（与其他 skill 的参数校验一致）。"""
    ctx, _, _ = _mock_ctx()
    for bad in [{"query": ""}, {"query": "   "}, {}]:
        try:
            _generate_data_driven_api_case(bad, ctx)
            assert False, f"应抛 ValueError: {bad}"
        except ValueError as e:
            assert "query" in str(e)


# ===== write_ui_case_from_image =====


def test_write_ui_case_from_image_success():
    """正常截图 → generator 生成 UI 用例 → 落库 → 返回 case_id。"""
    fake_case = TestCase(
        title="登录页用例",
        type=CaseType.UI,
        status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE,
        content={"base_url": BASE, "steps": [{"kind": "action", "action": "点击登录"}]},
        source="ai:vision",
    )
    ctx, case_db, _ = _mock_ctx()
    ctx.generator.generate_from_image = MagicMock(return_value=fake_case)

    result = _write_ui_case_from_image(
        {"images": [{"data": "iVBOR...", "mime": "image/png"}], "base_url": BASE},
        ctx,
    )

    assert result["case_id"] == 1
    assert result["type"] == "ui"
    assert "vision" in result["source"]
    ctx.generator.generate_from_image.assert_called_once()
    args = ctx.generator.generate_from_image.call_args.args
    assert args[0] == [("iVBOR...", "image/png")]  # images 元组列表
    assert args[1] == BASE  # base_url
    case_db.create_case.assert_called_once()


def test_write_ui_case_from_image_missing_images():
    """缺 images → 抛 ValueError。"""
    ctx, _, _ = _mock_ctx()
    try:
        _write_ui_case_from_image({"base_url": BASE}, ctx)
        assert False, "应抛 ValueError"
    except ValueError as e:
        assert "images" in str(e)


def test_write_ui_case_from_image_missing_base_url():
    """缺 base_url → 抛 ValueError。"""
    ctx, _, _ = _mock_ctx()
    try:
        _write_ui_case_from_image({"images": [{"data": "x"}]}, ctx)
        assert False, "应抛 ValueError"
    except ValueError as e:
        assert "base_url" in str(e)


def test_write_ui_case_from_image_default_mime():
    """mime 缺省 → 默认 image/png。"""
    fake_case = TestCase(title="x", type=CaseType.UI, content={"base_url": BASE, "steps": []})
    ctx, _, _ = _mock_ctx()
    ctx.generator.generate_from_image = MagicMock(return_value=fake_case)

    _write_ui_case_from_image({"images": [{"data": "abc"}], "base_url": BASE}, ctx)

    args = ctx.generator.generate_from_image.call_args.args
    assert args[0] == [("abc", "image/png")]


# ===== generate_data_driven_api_case =====


def test_generate_data_driven_api_case_success():
    """FakeLLM 返回含 datasets 的 content → 校验 + 落库。"""
    llm_resp = json.dumps({
        "title": "注册接口数据驱动",
        "description": "覆盖多组注册数据",
        "content": {
            "base_url": BASE,
            "steps": [{
                "method": "POST",
                "path": "/register",
                "headers": {"Content-Type": "application/json"},
                "body": {"username": "{{username}}", "age": "{{age}}"},
                "assertions": [{"type": "status_code", "expected": 200}],
            }],
            "datasets": [
                {"name": "正向", "vars": {"username": "alice", "age": 25}},
                {"name": "边界-最小", "vars": {"username": "a", "age": 0}},
                {"name": "非法", "vars": {"username": "<script>", "age": -1}},
            ],
        },
    })
    ctx, case_db, _ = _mock_ctx(llm_resp)

    result = _generate_data_driven_api_case({"query": "注册接口"}, ctx)

    assert result["case_id"] == 1
    assert result["type"] == "api"
    assert result["datasets_count"] == 3
    assert result["valid"] is True
    assert "data-driven" in (ctx.case_db.create_case.call_args.args[0].tags or [])
    case_db.create_case.assert_called_once()


def test_generate_data_driven_api_case_missing_datasets_fallback():
    """LLM 没返回 datasets → 降级为单组空 vars。"""
    llm_resp = json.dumps({
        "title": "无数据组",
        "content": {"base_url": BASE, "steps": [{"method": "GET", "path": "/ok"}]},
    })
    ctx, case_db, _ = _mock_ctx(llm_resp)

    result = _generate_data_driven_api_case({"query": "test"}, ctx)

    assert result["datasets_count"] == 1  # 降级默认
    saved_case = case_db.create_case.call_args.args[0]
    assert saved_case.content["datasets"] == [{"name": "默认", "vars": {}}]


def test_generate_data_driven_api_case_bad_llm():
    """LLM 返回非 JSON → 抛 ValueError。"""
    ctx, _, _ = _mock_ctx("不是 JSON")
    try:
        _generate_data_driven_api_case({"query": "test"}, ctx)
        assert False, "应抛 ValueError"
    except ValueError:
        pass


# ===== execute_data_driven_api_case =====


def _make_datadriven_case() -> TestCase:
    """构造一条数据驱动用例：3 组数据，其中 1 组非法（400）。"""
    return TestCase(
        title="注册接口数据驱动",
        type=CaseType.API,
        status=CaseStatus.DRAFT,
        content={
            "base_url": BASE,
            "steps": [{
                "method": "POST",
                "path": "/register",
                "headers": {"Content-Type": "application/json"},
                "body": {"username": "{{username}}", "age": "{{age}}"},
                "assertions": [{"type": "status_code", "expected": 200}],
            }],
            "datasets": [
                {"name": "正向", "vars": {"username": "alice", "age": 25}},
                {"name": "非法-特殊字符", "vars": {"username": "<script>", "age": -1}},
            ],
        },
    )


def test_execute_data_driven_api_case_multi_datasets():
    """2 组数据：正向 passed + 非法 failed → 聚合 passed=1, failed=1。"""
    case = _make_datadriven_case()
    ctx, case_db, run_db = _mock_ctx(case=case)

    result = _execute_data_driven_api_case({"case_id": 1}, ctx)

    assert result["case_id"] == 1
    assert result["total_datasets"] == 2
    assert result["passed"] == 1
    assert result["failed"] == 1
    # partial 映射为 failed（last_result 域只认 passed/failed/error）
    assert result["overall_status"] == "failed"
    assert len(result["per_dataset"]) == 2
    # 正向组 passed
    assert result["per_dataset"][0]["name"] == "正向"
    assert result["per_dataset"][0]["status"] == "passed"
    # 非法组 failed（400 断言 200 失败）
    assert result["per_dataset"][1]["name"] == "非法-特殊字符"
    assert result["per_dataset"][1]["status"] == "failed"
    # 2 组各落 1 条 run
    assert run_db.create_run.call_count == 2


def test_execute_data_driven_api_case_no_run_db():
    """api_run_db 未注入 → 抛 RuntimeError。"""
    case = _make_datadriven_case()
    ctx, _, _ = _mock_ctx(case=case)
    ctx.api_run_db = None
    try:
        _execute_data_driven_api_case({"case_id": 1}, ctx)
        assert False, "应抛 RuntimeError"
    except RuntimeError:
        pass


def test_execute_data_driven_api_case_missing_case():
    """用例不存在 → 抛 ValueError。"""
    ctx, case_db, _ = _mock_ctx()
    case_db.get_case.return_value = None
    try:
        _execute_data_driven_api_case({"case_id": 999}, ctx)
        assert False, "应抛 ValueError"
    except ValueError:
        pass


def test_execute_data_driven_api_case_no_datasets_fallback():
    """content 无 datasets → 降级为单组空 vars 执行（等价普通用例）。"""
    case = TestCase(
        title="普通用例",
        type=CaseType.API,
        content={"base_url": BASE, "steps": [{"method": "GET", "path": "/register"}]},
    )
    ctx, _, run_db = _mock_ctx(case=case)

    result = _execute_data_driven_api_case({"case_id": 1}, ctx)

    assert result["total_datasets"] == 1
    assert run_db.create_run.call_count == 1


def test_execute_data_driven_api_case_missing_var_records_error():
    """dataset 缺占位符的值 → executor 内部记 StepResult.error → 该组 status=error（不抛异常）。

    executor._run_step catch UndefinedVariableError 记成 step error，RunRecord.status=error。
    _execute_data_driven_api_case 把它作为 failed 计数（status != passed）。
    """
    case = TestCase(
        title="缺值用例",
        type=CaseType.API,
        content={
            "base_url": BASE,
            "steps": [{
                "method": "POST",
                "path": "/register",
                "body": {"username": "{{username}}"},
                "assertions": [{"type": "status_code", "expected": 200}],
            }],
            "datasets": [
                {"name": "缺值组", "vars": {}},  # 没给 username
            ],
        },
    )
    ctx, _, _ = _mock_ctx(case=case)

    result = _execute_data_driven_api_case({"case_id": 1}, ctx)

    assert result["total_datasets"] == 1
    # executor 把 UndefinedVariableError 记成 step error → RunRecord.status="error"
    assert result["per_dataset"][0]["status"] == "error"
    assert result["passed"] == 0
    # 失败明细应含变量相关错误
    failures = result["per_dataset"][0].get("failures", [])
    assert len(failures) >= 1
    assert any("username" in str(f.get("error", "")) for f in failures)


# ===== live 测试（真实 LLM key，默认跳过）=====


@live
def test_live_write_ui_case_from_image(tmp_path):
    """真实 vision key：截图 → UI 用例 skill 端到端。"""
    import base64
    import struct
    import zlib
    from insight_aitest.modules.testcase.backend.generator.generator import Generator
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import load_config

    cfg = load_config()
    if not cfg.api_key_set:
        pytest.skip("LLM API key 未配置")

    # 生成一张测试 PNG
    width, height = 400, 300
    raw = b"\x00" + bytes((220, 50, 50)) * width
    for _ in range(height - 1):
        raw += b"\x00" + bytes((50, 50, 220)) * width
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw)

    def _chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    screenshot_b64 = base64.b64encode(png).decode()

    real_generator = Generator(retriever=MagicMock(), llm=LLMClient(cfg), config=cfg)
    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))

    ctx = SkillContext(
        llm=LLMClient(cfg),
        config=cfg,
        retriever=MagicMock(),
        generator=real_generator,
        case_db=case_db,
        project_id=None,
        version_id=None,
    )

    result = _write_ui_case_from_image(
        {"images": [{"data": screenshot_b64, "mime": "image/png"}], "base_url": "https://demo.example.com/app"},
        ctx,
    )
    print(f"\n[live] case_id={result['case_id']}, title={result['title']!r}, source={result['source']}")
    assert result["case_id"] > 0
    assert result["type"] == "ui"
    saved = case_db.get_case(result["case_id"])
    assert saved.content.get("base_url") == "https://demo.example.com/app"


@live
def test_live_generate_and_execute_data_driven(tmp_path):
    """真实 LLM：生成数据驱动用例 + MockTransport 执行多组。"""
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import load_config

    cfg = load_config()
    if not cfg.api_key_set:
        pytest.skip("LLM API key 未配置")

    case_db = TestCaseDatabase(str(tmp_path / "tc.db"))

    # 共用 MockTransport（/register 端点）
    def live_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/register"):
            try:
                body = json.loads(request.content) if request.content else {}
            except Exception:
                body = {}
            # 非法用户名（特殊字符/空）→ 400
            uname = str(body.get("username", ""))
            if "<" in uname or not uname:
                return httpx.Response(400, json={"err": "invalid username"})
            # 正向：返回丰富字段（兼容 LLM 可能加的 json_schema 断言）
            return httpx.Response(200, json={
                "code": 0,
                "data": {"id": 1, "message": "ok"},
                "id": 1,
                "message": "registered",
            })
        return httpx.Response(404)

    # 阶段 1：真实 LLM 生成数据驱动用例
    gen_ctx = SkillContext(
        llm=LLMClient(cfg),
        config=cfg,
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
    )
    gen_result = _generate_data_driven_api_case(
        {"query": "用户注册接口 POST /api/register，username 和 age 字段"},
        gen_ctx,
    )
    print(f"\n[live] 生成: case_id={gen_result['case_id']}, datasets={gen_result['datasets_count']}")
    assert gen_result["case_id"] > 0
    assert gen_result["datasets_count"] >= 2

    # 阶段 2：执行
    case = case_db.get_case(gen_result["case_id"])
    # 把 base_url 改成 mock 域名（LLM 生成的 base_url 不可达）
    case.content["base_url"] = BASE
    # 确保 path 以 /register 结尾（MockTransport 只认这个）
    for s in case.content.get("steps", []):
        if "register" not in s.get("path", ""):
            s["path"] = "/register"
    case_db.update_case(gen_result["case_id"], content=case.content)

    run_db = MagicMock()
    run_db.create_run.side_effect = lambda run: 1
    exec_ctx = SkillContext(
        llm=LLMClient(cfg),
        config=cfg,
        retriever=MagicMock(),
        generator=MagicMock(),
        case_db=case_db,
        project_id=None,
        version_id=None,
        api_run_db=run_db,
        http_transport=httpx.MockTransport(live_handler),
    )
    exec_result = _execute_data_driven_api_case({"case_id": gen_result["case_id"]}, exec_ctx)
    print(f"[live] 执行: total={exec_result['total_datasets']}, passed={exec_result['passed']}, failed={exec_result['failed']}")
    for pd in exec_result["per_dataset"]:
        print(f"  - {pd['name']}: {pd['status']}")
    # 验证 skill 机制：每组都执行了，结果集齐全（passed/failed 具体数取决于 LLM 生成的断言）
    assert exec_result["total_datasets"] >= 2
    assert len(exec_result["per_dataset"]) == exec_result["total_datasets"]
    assert exec_result["passed"] + exec_result["failed"] == exec_result["total_datasets"]
    # 至少有 1 组有 run_id（执行引擎真正跑了）
    assert any(pd.get("run_id") for pd in exec_result["per_dataset"])
