# -*- coding: utf-8 -*-
"""截图→UI 用例生成测试。"""
from unittest.mock import MagicMock

import pytest

from insight_aitest.modules.testcase.backend.generator.generator import Generator

# ===== Task 2: build_generate_from_image_prompt =====


def test_generate_from_image_prompt_contains_base_url():
    """prompt 包含 base_url。"""
    from insight_aitest.modules.testcase.backend.generator.prompts import build_generate_from_image_prompt

    prompt = build_generate_from_image_prompt(base_url="https://example.com/login")
    assert "https://example.com/login" in prompt


def test_generate_from_image_prompt_contains_ui_schema():
    """prompt 包含 UI 用例 schema（kind=action/assert/extract）。"""
    from insight_aitest.modules.testcase.backend.generator.prompts import build_generate_from_image_prompt

    prompt = build_generate_from_image_prompt(base_url="https://example.com")
    assert "kind" in prompt
    assert "action" in prompt
    assert "assert" in prompt
    assert "extract" in prompt


def test_generate_from_image_prompt_contains_point_summary():
    """prompt 包含可选的测试重点。"""
    from insight_aitest.modules.testcase.backend.generator.prompts import build_generate_from_image_prompt

    prompt = build_generate_from_image_prompt(
        base_url="https://example.com",
        point_summary="重点验证登录失败场景",
    )
    assert "重点验证登录失败场景" in prompt


def test_generate_from_image_prompt_omits_empty_summary():
    """point_summary 为空时不出现测试重点行。"""
    from insight_aitest.modules.testcase.backend.generator.prompts import build_generate_from_image_prompt

    prompt = build_generate_from_image_prompt(base_url="https://example.com")
    assert "测试重点" not in prompt


# ===== Task 1: chat_with_images 多图 vision =====


def test_chat_with_images_constructs_multi_image_content():
    """chat_with_images 构造的 content 数组包含 text + N 个 image_url。"""
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig
    from unittest.mock import patch

    cfg = LLMConfig(llm_api_key="test-key")
    client = LLMClient(cfg)

    images = [("base64data1", "image/png"), ("base64data2", "image/jpeg")]

    with patch.object(client._client.chat.completions, "create") as mock_create:
        mock_create.return_value.choices = [MagicMock(message=MagicMock(content="ok"))]
        result = client.chat_with_images("describe these", images)

    assert result == "ok"
    call_kwargs = mock_create.call_args.kwargs
    messages = call_kwargs["messages"]
    content = messages[0]["content"]
    # content 应该是 list：1 个 text + 2 个 image_url = 3 个元素
    assert len(content) == 3
    assert content[0]["type"] == "text"
    assert content[0]["text"] == "describe these"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == "data:image/png;base64,base64data1"
    assert content[2]["type"] == "image_url"
    assert content[2]["image_url"]["url"] == "data:image/jpeg;base64,base64data2"


def test_chat_with_images_empty_list_raises():
    """chat_with_images 空图列表应报错（调用方应保证至少 1 张）。"""
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig

    cfg = LLMConfig(llm_api_key="test-key")
    client = LLMClient(cfg)
    with pytest.raises((ValueError, AssertionError)):
        client.chat_with_images("prompt", [])


# ===== Task 3: Generator.generate_from_image =====



def _fake_llm_with_json_response(json_str: str):
    """返回固定 JSON 的假 LLM。"""
    llm = MagicMock()
    llm.chat_with_images.return_value = json_str
    return llm


_VALID_UI_JSON = """{
    "title": "登录流程测试",
    "description": "验证用户能通过截图所示的界面完成登录",
    "preconditions": "用户已注册",
    "content": {
        "base_url": "https://wrong-from-llm.com",
        "steps": [
            {"kind": "action", "action": "在登录页输入用户名和密码"},
            {"kind": "assert", "assert": "页面显示用户头像"}
        ]
    }
}"""


def test_generate_from_image_returns_valid_case():
    """截图 → 生成合法 UI 用例。"""
    from insight_aitest.modules.testcase.backend.persistence.models import CaseStatus, CaseType
    from insight_aitest.platform.services.llm.config import LLMConfig

    llm = _fake_llm_with_json_response(_VALID_UI_JSON)
    cfg = LLMConfig()
    gen = Generator(retriever=MagicMock(), llm=llm, config=cfg)

    case = gen.generate_from_image(
        images=[("base64data", "image/png")],
        base_url="https://example.com/login",
    )
    assert case.type == CaseType.UI
    assert case.status == CaseStatus.DRAFT
    assert case.source == "ai:vision"
    assert case.title == "登录流程测试"
    assert len(case.content["steps"]) == 2


def test_generate_from_image_forces_base_url():
    """返回的 content.base_url 强制覆盖为请求参数（防 LLM 编造）。"""
    from insight_aitest.platform.services.llm.config import LLMConfig

    llm = _fake_llm_with_json_response(_VALID_UI_JSON)
    gen = Generator(retriever=MagicMock(), llm=llm, config=LLMConfig())

    case = gen.generate_from_image(
        images=[("base64data", "image/png")],
        base_url="https://correct-url.example.com",
    )
    assert case.content["base_url"] == "https://correct-url.example.com"


def test_generate_from_image_invalid_json_returns_failed():
    """LLM 返回非 JSON → source=ai:failed。"""
    from insight_aitest.modules.testcase.backend.persistence.models import CaseStatus
    from insight_aitest.platform.services.llm.config import LLMConfig

    llm = _fake_llm_with_json_response("这不是 JSON")
    gen = Generator(retriever=MagicMock(), llm=llm, config=LLMConfig())

    case = gen.generate_from_image(
        images=[("base64data", "image/png")],
        base_url="https://example.com",
    )
    assert case.source == "ai:failed"
    assert case.status == CaseStatus.DRAFT
    assert case.content == {}


def test_generate_from_image_passes_all_images_to_llm():
    """多张截图都传给 chat_with_images。"""
    from insight_aitest.platform.services.llm.config import LLMConfig

    llm = _fake_llm_with_json_response(_VALID_UI_JSON)
    gen = Generator(retriever=MagicMock(), llm=llm, config=LLMConfig())

    images = [("img1", "image/png"), ("img2", "image/png"), ("img3", "image/jpeg")]
    gen.generate_from_image(images=images, base_url="https://example.com")

    llm.chat_with_images.assert_called_once()
    call_args = llm.chat_with_images.call_args
    assert call_args[0][1] == images or call_args.kwargs["images"] == images


# ===== Task 4: POST /testcases/generate-from-image 路由 =====


def _setup_app(tmp_path, monkeypatch):
    """构造一个最小 app（仅挂 testcase router），与 test_generate_api.py 同模式。"""
    monkeypatch.setenv("INSIGHT_EYE_AI_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("INSIGHT_EYE_AI_EMBED_DIM", "4")
    import insight_aitest.modules.testcase.backend.deps as tc_deps
    tc_deps._tc_db = None
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    tc_deps._tc_db = TestCaseDatabase(str(tmp_path / "testcase.db"))
    from insight_aitest.modules.testcase.backend.routes import router as tc_router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(tc_router, prefix="/api/modules/testcase")
    from fastapi.testclient import TestClient
    return app, TestClient(app)


def test_generate_from_image_route_creates_case(tmp_path, monkeypatch):
    """路由调用 generate_from_image 并落库。"""
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CasePriority,
        CaseStatus,
        CaseType,
        TestCase,
        TestType,
    )

    # 构造一个 fake TestCase
    fake_case = TestCase(
        title="路由测试用例",
        type=CaseType.UI,
        description="from route test",
        priority=CasePriority.P2,
        status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE,
        content={"base_url": "https://example.com", "steps": [{"kind": "action", "action": "点击"}]},
        source="ai:vision",
    )

    app, client = _setup_app(tmp_path, monkeypatch)

    # 用 FastAPI 官方 dependency_overrides 覆盖 generator 和 db（monkeypatch 模块属性对 Depends 无效）
    from insight_aitest.modules.testcase.backend.deps import get_generator, get_tc_db
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    db = TestCaseDatabase(str(tmp_path / "tc_route.db"))
    mock_gen = MagicMock()
    mock_gen.generate_from_image.return_value = fake_case
    app.dependency_overrides[get_generator] = lambda: mock_gen
    app.dependency_overrides[get_tc_db] = lambda: db

    try:
        resp = client.post(
            "/api/modules/testcase/testcases/generate-from-image",
            json={
                "images": [{"data": "base64img", "mime": "image/png"}],
                "base_url": "https://example.com",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["title"] == "路由测试用例"
    assert body["type"] == "ui"
    assert body["source"] == "ai:vision"

    # 验证 generator 被正确调用
    mock_gen.generate_from_image.assert_called_once()
    call = mock_gen.generate_from_image.call_args
    # 第一个位置参数应是 images list of (data, mime) tuples
    images_arg = call[0][0] if call[0] else call.kwargs.get("images")
    assert images_arg == [("base64img", "image/png")]


# ===== Task 5: 真实 vision key 测试 =====

import base64  # noqa: E402
import struct  # noqa: E402
import zlib  # noqa: E402

live = pytest.mark.live


def _make_screenshot_png(width: int = 400, height: int = 300, top_color=(220, 50, 50), bottom_color=(50, 50, 220)) -> str:
    """生成一张有辨识度的 PNG（上半一色、下半另一色），供 vision model 识别。"""
    raw_rows = []
    for y in range(height):
        row = b"\x00"  # filter byte
        for x in range(width):
            row += bytes(top_color if y < height // 2 else bottom_color)
        raw_rows.append(row)
    raw = b"".join(raw_rows)

    def _chunk(typ: bytes, data: bytes) -> bytes:
        c = typ + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


@live
def test_real_single_screenshot_generates_ui_case():
    """真实 key：单张截图 → 生成 UI 用例，验证 vision 管线端到端通。"""
    from insight_aitest.modules.testcase.backend.generator.generator import Generator
    from insight_aitest.modules.testcase.backend.generator.schemas import validate_content
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import load_config

    cfg = load_config()
    if not cfg.api_key_set:
        pytest.skip("LLM API key 未配置")

    llm = LLMClient(cfg)
    gen = Generator(retriever=MagicMock(), llm=llm, config=cfg)

    screenshot = _make_screenshot_png()
    case = gen.generate_from_image(
        images=[(screenshot, "image/png")],
        base_url="https://demo.example.com/app",
    )
    print(f"\n[live] source={case.source} title={case.title!r}")
    print(f"[live] content={case.content}")

    assert case.type.value == "ui"
    assert case.source in ("ai:vision", "ai:invalid")
    # base_url 一定被强制覆盖
    assert case.content.get("base_url") == "https://demo.example.com/app"
    if case.source == "ai:vision":
        assert validate_content("ui", case.content), f"content 无效: {case.content}"
        assert len(case.content.get("steps", [])) >= 1


@live
def test_real_multi_screenshot_generates_multi_step_case():
    """真实 key：多张截图 → 生成多步 UI 用例。"""
    from insight_aitest.modules.testcase.backend.generator.generator import Generator
    from insight_aitest.modules.testcase.backend.generator.schemas import validate_content
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import load_config

    cfg = load_config()
    if not cfg.api_key_set:
        pytest.skip("LLM API key 未配置")

    llm = LLMClient(cfg)
    gen = Generator(retriever=MagicMock(), llm=llm, config=cfg)

    img1 = _make_screenshot_png(400, 300, top_color=(220, 50, 50), bottom_color=(50, 50, 220))
    img2 = _make_screenshot_png(400, 300, top_color=(50, 220, 50), bottom_color=(220, 220, 50))

    case = gen.generate_from_image(
        images=[(img1, "image/png"), (img2, "image/png")],
        base_url="https://demo.example.com/flow",
        point_summary="验证两个页面的操作流程",
    )
    print(f"\n[live] source={case.source} title={case.title!r}")
    print(f"[live] content={case.content}")

    assert case.type.value == "ui"
    if case.source == "ai:vision":
        assert validate_content("ui", case.content)
        assert len(case.content.get("steps", [])) >= 2, f"多图应生成多步，实际 {len(case.content.get('steps', []))} 步"
