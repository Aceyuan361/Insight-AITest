# -*- coding: utf-8 -*-
"""用例 content schema 校验（spec D §3.4）。

functional 严格校验；API/UI 对齐各自 executor 的 _validate_content（base_url 必填）；
performance 执行器未就绪，保持宽松校验。
"""

from __future__ import annotations


def validate_content(case_type: str, content: dict) -> bool:
    """按类型校验 content 结构。对齐各 executor 的 _validate_content。"""
    if not isinstance(content, dict):
        return False
    if case_type == "functional":
        # 必须有 steps（list）和 expected（非空 str）
        if "steps" not in content or not isinstance(content["steps"], list):
            return False
        if not content.get("expected"):
            return False
        return True
    if case_type == "api":
        # 对齐 api/engine/executor.py::_validate_content：base_url 必填 + steps 为 list
        if not content.get("base_url"):
            return False
        steps = content.get("steps")
        if not isinstance(steps, list):
            return False
        # 每步至少要有 method（executor 默认 GET，但生成时应有明确方法）
        return all(isinstance(s, dict) and s.get("method") for s in steps) if steps else True
    if case_type == "performance":
        # 宽松：有 scenario 或 steps 即可（执行器未就绪）
        return bool(content.get("scenario") or content.get("steps"))
    if case_type == "ui":
        # 对齐 ui/engine/executor.py::_validate_content：base_url 必填 + steps 为 list
        if not content.get("base_url"):
            return False
        return isinstance(content.get("steps"), list)
    return False
