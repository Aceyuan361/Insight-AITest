# -*- coding: utf-8 -*-
"""变量解析测试：{{var}} 替换 + JSONPath 提取。"""
import pytest
from insight_aitest.modules.api.backend.engine.variables import (
    inject_variables, extract_variables, UndefinedVariableError,
)


def test_inject_replaces_placeholder():
    out = inject_variables("Bearer {{token}}", {"token": "abc"})
    assert out == "Bearer abc"


def test_inject_in_dict_values():
    out = inject_variables({"h": "x-{{id}}", "url": "/u/{{id}}"}, {"id": "7"})
    assert out == {"h": "x-7", "url": "/u/7"}


def test_inject_nested_dict_and_list():
    out = inject_variables({"a": [{"b": "{{k}}"}]}, {"k": "v"})
    assert out == {"a": [{"b": "v"}]}


def test_inject_undefined_raises():
    with pytest.raises(UndefinedVariableError):
        inject_variables("{{nope}}", {})


def test_inject_partial_value_undefined_raises():
    # 变量名是扁平 key，{{a.b}} 视为名为 "a.b" 的变量
    with pytest.raises(UndefinedVariableError):
        inject_variables("{{a.b}}", {"a": {"b": "x"}})


def test_inject_no_placeholder_passes_through():
    assert inject_variables("plain", {}) == "plain"
    assert inject_variables({"k": 123}, {}) == {"k": 123}


def test_extract_simple_jsonpath():
    data = {"data": {"token": "abc"}}
    out = extract_variables({"token": "$.data.token"}, data)
    assert out == {"token": "abc"}


def test_extract_array_index():
    data = {"items": [{"id": 1}, {"id": 2}]}
    out = extract_variables({"second": "$.items[1].id"}, data)
    assert out == {"second": 2}


def test_extract_multiple():
    data = {"a": {"b": 1, "c": 2}}
    out = extract_variables({"x": "$.a.b", "y": "$.a.c"}, data)
    assert out == {"x": 1, "y": 2}
