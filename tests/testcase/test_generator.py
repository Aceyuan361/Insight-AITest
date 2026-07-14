# -*- coding: utf-8 -*-
"""生成器测试（mock LLM）。"""
from unittest.mock import MagicMock

from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
from insight_aitest.modules.testcase.backend.generator.generator import Generator
from insight_aitest.modules.testcase.backend.persistence.models import (
    CaseStatus, CaseType, TestType,
)


def _cfg():
    from insight_aitest.platform.services.llm.config import LLMConfig
    return LLMConfig(llm_api_key="k", embed_dim=4, chat_model="glm-4-flash")


def _point(design=TestType.POSITIVE):
    return TestPoint(id="tp-1", summary="登录", suggested_type=CaseType.FUNCTIONAL,
                     suggested_design=design, rationale="r")


def test_generate_functional():
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = (
        '{"title":"登录正向测试","description":"验证正常登录","preconditions":"已开登录页",'
        '"content":{"steps":[{"no":1,"action":"输入手机号","data":"13800"}],"expected":"登录成功"}}')
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None)
    assert case.title == "登录正向测试"
    assert case.type == CaseType.FUNCTIONAL
    assert case.test_design == TestType.POSITIVE
    assert case.status == CaseStatus.DRAFT
    assert case.content["expected"] == "登录成功"
    assert case.source == "ai:glm-4-flash"
    assert case.preconditions == "已开登录页"


def test_generate_negative_design():
    """test_design=异常 时 prompt 应含异常约束。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = '{"title":"x","content":{"steps":[],"expected":"x"}}'
    gen = Generator(retriever, llm, _cfg())
    gen.generate(_point(design=TestType.NEGATIVE), document_ids=None)
    prompt = llm.chat.call_args[0][0][0]["content"]
    assert "异常" in prompt or "反向" in prompt


def test_generate_parse_fail():
    """LLM 输出非法 JSON：返回空 content + source 标记失败。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = "乱七八糟不是json"
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None)
    assert case.content == {}
    assert case.source == "ai:failed"
    assert case.status == CaseStatus.DRAFT


def test_generate_override_type_and_design():
    """override_type/override_design 覆盖建议值。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = '{"title":"x","content":{"base_url":"http://a","steps":[]}}'
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None,
                        override_type="api", override_design="boundary")
    assert case.type == CaseType.API
    assert case.test_design == TestType.BOUNDARY


def test_generate_retriever_error_degrades():
    """retriever 异常时降级为空检索，仍能生成。"""
    retriever = MagicMock()
    retriever.retrieve.side_effect = RuntimeError("down")
    llm = MagicMock()
    llm.chat.return_value = '{"title":"x","content":{"steps":[],"expected":"y"}}'
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None)
    assert case.title == "x"  # 仍生成了


def test_generate_invalid_content_marked():
    """LLM 输出能解析 JSON 但 content 不符 schema（如 ui 缺 base_url）：标记 ai:invalid。
    仍保留 content 供用户手动修，不谎称成功。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    # ui content 缺 base_url（validate_content("ui", ...) 返回 False）
    llm.chat.return_value = '{"title":"x","content":{"steps":[{"kind":"action","action":"点击"}]}}'
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None, override_type="ui")
    assert case.type == CaseType.UI
    assert case.source == "ai:invalid"
    assert case.content.get("steps")  # content 仍保留


def test_generate_valid_content_not_marked_invalid():
    """valid content（functional 有 steps+expected）不应标记 invalid。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = (
        '{"title":"x","content":{"steps":[{"no":1,"action":"点击"}],"expected":"成功"}}')
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None)
    assert case.source == "ai:glm-4-flash"


# ---- P1-D：激活 api/ui 用例生成 ----


def test_generate_api_full_fields():
    """api 用例生成：content 含 executor 消费的全字段（base_url/steps/assertions/extract）。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = (
        '{"title":"登录接口测试","description":"验证登录API","preconditions":"服务可用",'
        '"content":{"base_url":"https://api.example.com","steps":['
        '{"method":"POST","path":"/v1/login","headers":{"Content-Type":"application/json"},'
        '"body":{"username":"admin","password":"123456"},'
        '"assertions":[{"type":"status_code","expected":200},{"type":"jsonpath","path":"$.code","expected":0}],'
        '"extract":{"token":"$.data.token"}}]}}')
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None, override_type="api")
    assert case.type == CaseType.API
    content = case.content
    assert content["base_url"] == "https://api.example.com"
    step = content["steps"][0]
    assert step["method"] == "POST"
    assert step["path"] == "/v1/login"
    assert step["body"]["username"] == "admin"
    assert any(a["type"] == "status_code" for a in step["assertions"])
    assert any(a["type"] == "jsonpath" for a in step["assertions"])
    assert step["extract"]["token"] == "$.data.token"


def test_generate_ui_full_fields():
    """ui 用例生成：content 含 base_url + kind=action/assert/extract 三类步骤。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = (
        '{"title":"登录页UI测试","description":"验证登录流程","preconditions":"浏览器就绪",'
        '"content":{"base_url":"https://example.com","steps":['
        '{"kind":"action","action":"在登录页输入用户名admin和密码123456，点击登录"},'
        '{"kind":"assert","assert":"页面显示用户头像"},'
        '{"kind":"extract","extract":{"userName":"页面右上角用户名"}}]}}')
    gen = Generator(retriever, llm, _cfg())
    case = gen.generate(_point(), document_ids=None, override_type="ui")
    assert case.type == CaseType.UI
    content = case.content
    assert content["base_url"] == "https://example.com"
    kinds = [s.get("kind") for s in content["steps"]]
    assert "action" in kinds
    assert "assert" in kinds
    assert "extract" in kinds


def test_generate_api_prompt_has_type_instruction():
    """api 类型 prompt 应含 base_url 必填 + assertions/extract 指导。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = '{"title":"x","content":{"base_url":"http://a","steps":[]}}'
    gen = Generator(retriever, llm, _cfg())
    gen.generate(_point(), document_ids=None, override_type="api")
    prompt = llm.chat.call_args[0][0][0]["content"]
    assert "base_url 必填" in prompt
    assert "jsonpath" in prompt
    assert "extract" in prompt


def test_generate_ui_prompt_has_type_instruction():
    """ui 类型 prompt 应含 base_url 必填 + kind 三类指导。"""
    retriever = MagicMock()
    retriever.retrieve.return_value = []
    llm = MagicMock()
    llm.chat.return_value = '{"title":"x","content":{"base_url":"http://a","steps":[]}}'
    gen = Generator(retriever, llm, _cfg())
    gen.generate(_point(), document_ids=None, override_type="ui")
    prompt = llm.chat.call_args[0][0][0]["content"]
    assert "base_url 必填" in prompt
    assert "kind=action" in prompt
    assert "kind=assert" in prompt
    assert "kind=extract" in prompt
