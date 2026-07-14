# -*- coding: utf-8 -*-
"""用例质量校验与自动修复逻辑。

校验规则：
- title 非空非空白
- description 非空非空白（至少一句话说明用例目的）
- preconditions 非空（可写"无"但不能为空串）
- content.steps 非空且每步有 action
- expected 不可为"系统正常"等不可验证描述

修复策略：
- 不合格用例携带需求点 summary + document_ids 重试生成（最多 1 次）
- 仍不合格则标记 source="ai:invalid"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from insight_aitest.modules.testcase.backend.persistence.models import TestCase


# 不可验证的 expected 描述（过于宽泛，无法据其判定通过/失败）。
# 注意："成功"/"正常" 类作为唯一预期过于宽泛，但若与具体行为组合（如"返回200且登录成功"）
# 仍可验证，故仅匹配 expected 整体等于这些词的用例。
_UNVERIFIABLE_EXPECTED = {"系统正常", "正常", "无异常", "系统正常运行"}


def validate_case(case: "TestCase") -> list[str]:
    """校验单条用例质量，返回问题列表（空列表=合格）。

    问题代码：
    - title_empty: 标题为空
    - description_empty: 描述为空
    - preconditions_empty: 前置条件为空串
    - steps_empty: content.steps 为空或非 list
    - expected_unverifiable: expected 不可验证
    """
    issues: list[str] = []

    if not case.title or not case.title.strip():
        issues.append("title_empty")

    if not case.description or not case.description.strip():
        issues.append("description_empty")

    if not case.preconditions or not case.preconditions.strip():
        issues.append("preconditions_empty")

    content = case.content if isinstance(case.content, dict) else {}
    steps = content.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        issues.append("steps_empty")
    else:
        for step in steps:
            if not isinstance(step, dict):
                issues.append("steps_empty")
                break
            action = step.get("action") or step.get("desc") or ""
            if not str(action).strip():
                issues.append("steps_empty")
                break

    expected = content.get("expected")
    if expected and isinstance(expected, str) and expected.strip() in _UNVERIFIABLE_EXPECTED:
        issues.append("expected_unverifiable")

    return issues


def validate_and_fix_cases(
    batch_id: str,
    document_ids: list[int] | None,
    ctx,  # SkillContext
) -> dict:
    """批量校验并修复用例。

    返回 {total, valid, fixed, invalid, quality_score, details}
    """
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint

    cases = ctx.case_db.list_cases_by_batch(batch_id)
    stats: dict = {"total": len(cases), "valid": 0, "fixed": 0, "invalid": 0, "details": []}

    for case in cases:
        issues = validate_case(case)
        if not issues:
            # 合格：标记 validated
            ctx.case_db.update_case(
                case.id, source=f"ai:validated:{ctx.config.chat_model}"
            )
            stats["valid"] += 1
            continue

        # 不合格：尝试重试生成（最多 1 次）
        point = TestPoint(
            id=f"fix-{case.id}",
            summary=case.title or case.description or "修复用例",
            suggested_type=case.type,
            suggested_design=case.test_design,
            rationale="质量自检修复",
        )
        try:
            fixed_case = ctx.generator.generate(
                point,
                document_ids=document_ids,
                project_id=ctx.project_id,
            )
            fixed_issues = validate_case(fixed_case)
            if not fixed_issues:
                # 修复成功：更新原用例
                ctx.case_db.update_case(
                    case.id,
                    title=fixed_case.title,
                    description=fixed_case.description,
                    preconditions=fixed_case.preconditions,
                    content=fixed_case.content,
                    source=f"ai:fixed:{ctx.config.chat_model}",
                )
                stats["fixed"] += 1
            else:
                # 修复后仍不合格：标记 invalid
                ctx.case_db.update_case(case.id, source="ai:invalid")
                stats["invalid"] += 1
                stats["details"].append(
                    {"case_id": case.id, "issues": issues + fixed_issues}
                )
        except Exception:
            ctx.case_db.update_case(case.id, source="ai:invalid")
            stats["invalid"] += 1
            stats["details"].append(
                {"case_id": case.id, "issues": issues + ["retry_failed"]}
            )

    total = max(stats["total"], 1)
    stats["quality_score"] = round((stats["valid"] + stats["fixed"]) / total, 2)
    return stats
