# -*- coding: utf-8 -*-
"""变量解析：{{var}} 占位符替换 + JSONPath 提取（spec E §4）。

变量名是扁平 key（如 token），不支持 {{a.b}} 嵌套点（点是 JSONPath 语法）。
未定义变量抛 UndefinedVariableError（严格模式，不静默留空）。
"""

from __future__ import annotations

import re
from typing import Any

from jsonpath_ng.ext import parse as jsonpath_parse

_VAR_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


class UndefinedVariableError(Exception):
    """占位符引用了未定义的变量。"""


def inject_variables(value: Any, variables: dict[str, Any]) -> Any:
    """递归把 {{var}} 替换进 str / dict / list / 其他。

    - str: 替换占位符；未定义抛 UndefinedVariableError
    - dict/list: 递归处理
    - 其他（int/bool/None）: 原样返回
    """
    if isinstance(value, str):
        return _inject_str(value, variables)
    if isinstance(value, dict):
        return {k: inject_variables(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [inject_variables(v, variables) for v in value]
    return value


def _inject_str(s: str, variables: dict[str, Any]) -> str:
    def repl(m: re.Match) -> str:
        name = m.group(1)
        if name not in variables:
            raise UndefinedVariableError(f"未定义的变量: {{{{{name}}}}}")
        return str(variables[name])

    return _VAR_RE.sub(repl, s)


def extract_variables(spec: dict[str, str], data: Any) -> dict[str, Any]:
    """按 {var_name: jsonpath} 从 data 提取值。

    jsonpath 取不到（无匹配）抛 UndefinedVariableError。
    """
    out: dict[str, Any] = {}
    for var_name, path in spec.items():
        expr = jsonpath_parse(path)
        matches = [m.value for m in expr.find(data)]
        if not matches:
            raise UndefinedVariableError(f"提取失败，路径无匹配: {var_name} ← {path}")
        out[var_name] = matches[0]
    return out
