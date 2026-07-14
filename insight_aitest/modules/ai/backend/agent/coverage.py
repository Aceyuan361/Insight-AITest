# -*- coding: utf-8 -*-
"""需求覆盖度分析逻辑。

流程：
1. 从需求文档提取需求点（复用 Analyzer RAG + LLM）
2. 加载 batch 内所有用例
3. LLM 语义匹配：需求点 × 用例，输出覆盖矩阵
4. 标记遗漏（无用例覆盖）和冗余（多对一）
5. 可选：对遗漏需求点调用 generator.generate 补生成
"""

from __future__ import annotations

from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json


_COVERAGE_PROMPT = """你是测试覆盖度分析专家。请分析以下需求点与测试用例的覆盖关系。

需求点列表：
{requirements}

测试用例列表：
{cases}

请输出严格 JSON 数组，每个元素表示一个需求点的覆盖情况：
[{{"requirement_id": "需求点ID", "requirement_summary": "需求点摘要", "case_ids": [匹配的用例ID列表], "match_reason": "匹配理由"}}]

规则：
1. case_ids 为空表示该需求点未被覆盖（遗漏）
2. 一个用例可匹配多个需求点
3. 匹配依据：用例的 title/description/steps 与需求点的 summary 语义相关
4. 不要输出 JSON 以外的内容。"""


def _format_requirements(points) -> str:
    parts = []
    for p in points:
        parts.append(f"- ID: {p.id}, 摘要: {p.summary}, 类型: {p.suggested_type.value}")
    return "\n".join(parts)


def _format_cases(cases) -> str:
    parts = []
    for c in cases:
        desc = (c.description or "")[:100]
        parts.append(f"- ID: {c.id}, 标题: {c.title}, 描述: {desc}")
    return "\n".join(parts)


def analyze_coverage(
    batch_id: str,
    document_ids: list[int] | None,
    ctx,  # SkillContext
    supplement: bool = True,
) -> dict:
    """分析需求覆盖度。

    返回 {coverage_matrix, missing_points, redundant_cases, supplemented_case_ids, coverage_rate}
    """
    from insight_aitest.modules.testcase.backend.deps import get_analyzer

    # 1. 提取需求点
    analyzer = get_analyzer()
    query = "提取所有可测试需求点"
    requirement_points = analyzer.analyze(query, document_ids=document_ids, project_id=ctx.project_id)

    # 2. 加载用例
    cases = ctx.case_db.list_cases_by_batch(batch_id)
    if not cases:
        return {
            "coverage_matrix": [],
            "missing_points": [p.summary for p in requirement_points],
            "redundant_cases": [],
            "supplemented_case_ids": [],
            "coverage_rate": 0.0,
        }

    # 3. LLM 语义匹配
    prompt = _COVERAGE_PROMPT.format(
        requirements=_format_requirements(requirement_points),
        cases=_format_cases(cases),
    )
    raw = ctx.llm.chat([{"role": "user", "content": prompt}])
    data = _extract_json(raw)

    coverage_matrix = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                coverage_matrix.append({
                    "requirement_id": item.get("requirement_id", ""),
                    "requirement_summary": item.get("requirement_summary", ""),
                    "case_ids": item.get("case_ids", []),
                    "match_reason": item.get("match_reason", ""),
                })

    # 4. 分析遗漏和冗余
    covered_ids = {m["requirement_id"] for m in coverage_matrix if m.get("case_ids")}
    missing = [p for p in requirement_points if p.id not in covered_ids]

    # 冗余：多个需求点映射到同一用例
    case_to_reqs: dict[int, list[str]] = {}
    for m in coverage_matrix:
        for cid in m.get("case_ids", []):
            case_to_reqs.setdefault(cid, []).append(m["requirement_id"])
    redundant = [{"case_id": cid, "requirements": reqs} for cid, reqs in case_to_reqs.items() if len(reqs) > 1]

    # 5. 补充遗漏用例
    supplemented = []
    if supplement and missing:
        for rp in missing:
            try:
                case = ctx.generator.generate(
                    rp, document_ids=document_ids, project_id=ctx.project_id
                )
                case.source = f"ai:coverage:{ctx.config.chat_model}"
                case.batch_id = batch_id
                case.project_id = ctx.project_id
                case_id = ctx.case_db.create_case(case)
                supplemented.append(case_id)
            except Exception:
                pass

    total = max(len(requirement_points), 1)
    coverage_rate = round(len(covered_ids) / total, 2)
    return {
        "coverage_matrix": coverage_matrix,
        "missing_points": [p.summary for p in missing],
        "redundant_cases": redundant,
        "supplemented_case_ids": supplemented,
        "coverage_rate": coverage_rate,
    }
