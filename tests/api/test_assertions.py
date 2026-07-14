# -*- coding: utf-8 -*-
"""断言校验测试：status_code / header / jsonpath 三类（spec E §4.3）。"""
from insight_aitest.modules.api.backend.engine.assertions import check_assertion


def test_status_code_pass():
    r = check_assertion({"type": "status_code", "expected": 200},
                        status_code=200, headers={}, body={})
    assert r["passed"] is True
    assert r["actual"] == 200


def test_status_code_fail():
    r = check_assertion({"type": "status_code", "expected": 200},
                        status_code=404, headers={}, body={})
    assert r["passed"] is False
    assert r["actual"] == 404


def test_header_pass():
    r = check_assertion({"type": "header", "path": "Content-Type", "expected": "application/json"},
                        status_code=200, headers={"Content-Type": "application/json"}, body={})
    assert r["passed"] is True


def test_header_case_insensitive():
    r = check_assertion({"type": "header", "path": "content-type", "expected": "application/json"},
                        status_code=200, headers={"Content-Type": "application/json"}, body={})
    assert r["passed"] is True


def test_jsonpath_pass():
    r = check_assertion({"type": "jsonpath", "path": "$.data.id", "expected": 42},
                        status_code=200, headers={}, body={"data": {"id": 42}})
    assert r["passed"] is True


def test_jsonpath_no_match_fails():
    r = check_assertion({"type": "jsonpath", "path": "$.data.missing", "expected": 1},
                        status_code=200, headers={}, body={"data": {}})
    assert r["passed"] is False
    assert r["actual"] is None


def test_expected_with_placeholder():
    # expected 支持 {{var}}（已在调用前注入，这里测值相等）
    r = check_assertion({"type": "jsonpath", "path": "$.id", "expected": "abc"},
                        status_code=200, headers={}, body={"id": "abc"})
    assert r["passed"] is True


def test_jsonpath_on_non_dict_body():
    # body 非 dict（如纯文本），jsonpath 断言自动 fail
    r = check_assertion({"type": "jsonpath", "path": "$.id", "expected": 1},
                        status_code=200, headers={}, body="plain text")
    assert r["passed"] is False


# ===== P1-E 新增断言类型：response_time / json_schema / contains =====


def test_response_time_pass():
    r = check_assertion({"type": "response_time", "expected": 500},
                        status_code=200, headers={}, body={}, elapsed_ms=120)
    assert r["passed"] is True
    assert r["actual"] == 120


def test_response_time_fail():
    r = check_assertion({"type": "response_time", "expected": 500},
                        status_code=200, headers={}, body={}, elapsed_ms=800)
    assert r["passed"] is False
    assert r["actual"] == 800


def test_response_time_boundary():
    # 等于阈值也算通过（≤）
    r = check_assertion({"type": "response_time", "expected": 500},
                        status_code=200, headers={}, body={}, elapsed_ms=500)
    assert r["passed"] is True


def test_json_schema_type_pass():
    r = check_assertion(
        {"type": "json_schema", "expected": {"type": "object", "required": ["id", "name"]}},
        status_code=200, headers={}, body={"id": 1, "name": "x"},
    )
    assert r["passed"] is True


def test_json_schema_missing_required_fail():
    r = check_assertion(
        {"type": "json_schema", "expected": {"type": "object", "required": ["id", "name"]}},
        status_code=200, headers={}, body={"id": 1},
    )
    assert r["passed"] is False


def test_json_schema_wrong_type_fail():
    r = check_assertion(
        {"type": "json_schema", "expected": {"type": "array"}},
        status_code=200, headers={}, body={"id": 1},
    )
    assert r["passed"] is False


def test_json_schema_nested_properties():
    r = check_assertion(
        {"type": "json_schema", "expected": {
            "type": "object",
            "properties": {"data": {"type": "object", "required": ["id"]}},
        }},
        status_code=200, headers={}, body={"data": {"id": 42}},
    )
    assert r["passed"] is True


def test_json_schema_array_items():
    r = check_assertion(
        {"type": "json_schema", "expected": {
            "type": "array", "items": {"type": "integer"},
        }},
        status_code=200, headers={}, body=[1, 2, 3],
    )
    assert r["passed"] is True


def test_json_schema_bool_not_integer():
    # bool 是 int 子类，但 integer 断言不应匹配 True/False
    r = check_assertion(
        {"type": "json_schema", "expected": {"type": "integer"}},
        status_code=200, headers={}, body=True,
    )
    assert r["passed"] is False


def test_contains_body_substring():
    r = check_assertion({"type": "contains", "expected": "success"},
                        status_code=200, headers={}, body={"msg": "operation success"})
    assert r["passed"] is True


def test_contains_path_field():
    r = check_assertion({"type": "contains", "path": "$.msg", "expected": "ok"},
                        status_code=200, headers={}, body={"msg": "all good ok!"})
    assert r["passed"] is True


def test_contains_fail():
    r = check_assertion({"type": "contains", "expected": "missing"},
                        status_code=200, headers={}, body={"msg": "hello"})
    assert r["passed"] is False


def test_contains_list_any():
    # expected 是列表时，任一命中即通过
    r = check_assertion({"type": "contains", "expected": ["error", "warning"]},
                        status_code=200, headers={}, body={"msg": "got a warning"})
    assert r["passed"] is True


def test_contains_plain_text_body():
    r = check_assertion({"type": "contains", "expected": "hello"},
                        status_code=200, headers={}, body="hello world")
    assert r["passed"] is True
