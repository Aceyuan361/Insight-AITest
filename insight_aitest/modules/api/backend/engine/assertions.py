# -*- coding: utf-8 -*-
"""断言校验：status_code / header / jsonpath / response_time / json_schema / contains（spec E §4.3 + P1-E 扩展）。

D 原版 assertion: {"type":"status_code","expected":200}（无 path）
E 扩展:           {"type":"header","path":"...","expected":...}
                  {"type":"jsonpath","path":"...","expected":...}
P1-E 扩展:        {"type":"response_time","expected":<ms>}      响应耗时 ≤ expected
                  {"type":"json_schema","expected":{<json schema 子集>}}  结构校验
                  {"type":"contains","path":"<jsonpath|''>","expected":<子串或列表>}  包含

返回 dict: {type, target, expected, actual, passed}
"""

from __future__ import annotations

from typing import Any

from jsonpath_ng.ext import parse as jsonpath_parse

_JSONSCHEMA_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _eq(expected: Any, actual: Any) -> bool:
    """严格相等比较。

    优先用类型感知的 == 比较（bool 不会被 int 混淆）；
    类型不同但都是 scalar 时做宽松比较（兼容 API 返回 "200" vs 200）。
    """
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False
    # bool 特殊处理：Python 里 True == 1，但断言语义上不应混淆
    if isinstance(expected, bool) or isinstance(actual, bool):
        if type(expected) is not type(actual):
            return False
        return expected == actual
    # 类型相同直接 ==
    if type(expected) is type(actual):
        return expected == actual
    # 数值之间可以互比（int vs float）
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return float(expected) == float(actual)
    # 类型不同 scalar 做宽松比较（兼容 "200" vs 200）
    return str(expected) == str(actual)


def check_assertion(
    assertion: dict,
    *,
    status_code: int | None,
    headers: dict,
    body: Any,
    elapsed_ms: int | None = None,
) -> dict:
    """校验单条断言。返回 {type, target, expected, actual, passed}。"""
    atype = assertion.get("type")
    expected = assertion.get("expected")
    path = assertion.get("path")

    if atype == "status_code":
        actual = status_code
        passed = _eq(expected, actual)
        target = "status_code"
    elif atype == "header":
        # 响应头大小写不敏感
        actual = _header_get(headers, path or "")
        passed = _eq(expected, actual)
        target = f"header:{path}"
    elif atype == "jsonpath":
        actual = _jsonpath_get(body, path or "")
        passed = _eq(expected, actual)
        target = f"jsonpath:{path}"
    elif atype == "response_time":
        # expected 是毫秒上限：实际耗时 ≤ expected 即通过
        actual = elapsed_ms
        passed = (
            isinstance(actual, (int, float))
            and isinstance(expected, (int, float))
            and actual <= expected
        )
        target = "response_time(ms)"
    elif atype == "json_schema":
        # 轻量校验 json schema 子集：type / required / enum / properties（递归）
        # 不引入 jsonschema 依赖；覆盖最常见用法。完整 schema 校验留后续。
        schema = expected if isinstance(expected, dict) else {}
        actual = _describe_body_shape(body)
        passed = _check_jsonschema(body, schema)
        target = "json_schema"
    elif atype == "contains":
        # body（或 path 指向的字段）的文本表示包含 expected（字符串或列表任一）
        if path:
            target_val: Any = _jsonpath_get(body, path) if isinstance(body, (dict, list)) else None
        else:
            target_val = body
        actual = _stringify(target_val)
        needles = expected if isinstance(expected, list) else [expected]
        passed = any(str(n) in actual for n in needles if n is not None)
        target = f"contains:{path or 'body'}"
    else:
        actual = None
        passed = False
        target = f"unknown:{atype}"

    return {
        "type": atype,
        "target": target,
        "expected": expected,
        "actual": actual,
        "passed": passed,
    }


def _header_get(headers: dict, name: str) -> Any:
    lower = {k.lower(): v for k, v in headers.items()}
    return lower.get(name.lower())


def _jsonpath_get(body: Any, path: str) -> Any:
    if not isinstance(body, (dict, list)):
        return None  # 非 JSON 结构，jsonpath 断言取不到
    try:
        expr = jsonpath_parse(path)
        matches = [m.value for m in expr.find(body)]
        return matches[0] if matches else None
    except Exception:
        return None


def _stringify(val: Any) -> str:
    """把任意值转成可做子串匹配的文本（dict/list 走 JSON）。"""
    if val is None:
        return ""
    if isinstance(val, (dict, list)):
        try:
            return str(val) if len(str(val)) <= 200 else str(val)[:200]
        except Exception:
            return ""
    return str(val)


def _describe_body_shape(body: Any) -> str:
    """给 json_schema 断言的 actual 字段一个可读描述（非校验逻辑）。"""
    if isinstance(body, dict):
        keys = ",".join(sorted(body.keys())[:10])
        return f"object{{{keys}}}"
    if isinstance(body, list):
        return f"array[{len(body)}]"
    return type(body).__name__


def _check_jsonschema(body: Any, schema: dict) -> bool:
    """轻量 JSON Schema 子集校验：type / required / enum / properties（递归）。
    不引入 jsonschema 依赖；覆盖最常见用法，完整校验留后续。"""
    if not isinstance(schema, dict):
        return False

    # type
    stype = schema.get("type")
    if stype is not None:
        # bool 是 int 子类，需特殊处理：integer/number 不应匹配 True/False
        if stype == "integer" and isinstance(body, bool):
            return False
        if stype == "number" and isinstance(body, bool):
            return False
        py_type = _JSONSCHEMA_TYPES.get(stype)
        if py_type is None or not isinstance(body, py_type):
            return False

    # enum
    senum = schema.get("enum")
    if senum is not None and body not in senum:
        return False

    # required + properties（仅 object）
    if isinstance(body, dict):
        for key in schema.get("required", []) or []:
            if key not in body:
                return False
        props = schema.get("properties") or {}
        for key, subschema in props.items():
            if key in body and not _check_jsonschema(body[key], subschema):
                return False

    # items（仅 array，所有元素同 schema）
    if isinstance(body, list):
        items_schema = schema.get("items")
        if items_schema is not None:
            if not all(_check_jsonschema(item, items_schema) for item in body):
                return False

    return True
