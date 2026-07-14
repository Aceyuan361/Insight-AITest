# -*- coding: utf-8 -*-
"""Agent Plan 生成器（子项目2 + 全自主增强）。

三阶段规划：
1. understand：阅读用户意图 + 上传文件 → 需求摘要
2. propose_strategies：基于摘要 → 测试策略选项
3. generate_plan：兼容旧流程，意图 → plan（用于无文件场景或降级）

复用 testcase/analyzer 的 _extract_json 容错解析器。
"""

from __future__ import annotations

from typing import Iterator, TYPE_CHECKING

from insight_aitest.modules.ai.backend.agent.skills import SKILLS, get_skill_catalog
from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig


# ===== Prompts =====

_PLAN_PROMPT = """你是一个资深测试 Agent 的规划器。用户给了你一个测试任务，请制定一个工作计划。

可用能力（skill）：
{catalog}

规则：
1. 只能使用上面列出的 skill，不要编造不存在的 skill
2. 一般先用 rag_search 检索知识库获取上下文，再生成用例
3. 生成用例后，建议用 execute_api_case（接口）/ execute_ui_case（UI）执行验证，形成闭环
4. 引用上一步生成的用例时，case_id 用 "$prev"（executor 自动解析为上一步的 case_id）
5. 想让执行失败时自动修复，在该 step 加 "loop": {{"enabled": true, "max_fixes": 2}}（仅 API 用例可自动修复，UI 用例失败只分析不修复）
6. 需要批量执行/回归验证时，用 run_api_suite 把多条用例打包成套件执行（自动检测回归）
7. 接口需要多组数据测试（边界值/等价类）时，用 generate_data_driven_api_case 生成 + execute_data_driven_api_case 执行（一条用例覆盖多组数据）
8. 有 UI 截图时可用 write_ui_case_from_image 生成 UI 用例（params 需带 images base64 数组 + base_url）
9. 输出一个 JSON 数组，每个元素代表一个步骤
10. 每个 step 的 params 根据用户意图填充合理值

用户任务：{intent}

请直接输出 JSON 数组（不要额外解释）：
[{{"skill": "skill_id", "desc": "步骤描述", "params": {{...}}}}]"""


_UNDERSTAND_PROMPT = """你是一个资深测试 Agent。用户给了你一个测试任务，并上传了相关文档。请阅读以下材料，理解测试范围。

用户意图：{intent}

上传的文档内容：
{documents}

请分析并输出一个 JSON 对象（不要额外解释）：
{{
  "summary": "用2-3句话总结你理解的测试范围",
  "scope": ["测试范围1", "测试范围2", "测试范围3"],
  "doc_types": {{
    "has_prd": true或false,
    "has_api_doc": true或false,
    "has_ui_image": true或false,
    "detail": "简要说明：有哪些文档，分别是什么类型（PRD需求文档/API接口文档/UI截图/其他）"
  }},
  "missing_for": {{
    "api_test": "若缺少接口文档，说明'需要接口文档（如Swagger/OpenAPI）才能生成可执行的接口用例'；若不缺则填''",
    "ui_test": "若缺少UI截图/设计稿，说明'需要UI截图或设计稿才能生成UI测试用例'；若不缺则填''"
  }}
}}"""


_STRATEGY_PROMPT = """你是一个资深测试 Agent。基于以下测试需求理解，提出 3-4 个测试策略选项让用户选择。

需求理解：
- 摘要：{summary}
- 测试范围：{scope}
- 可用文档类型：{doc_types_info}
- 能力限制：{capability_mask}

可用 skill：
{catalog}

闭环说明：
- 生成接口用例（write_api_case）后，可用 execute_api_case 执行验证
- 引用上一步生成的用例时，case_id 用 "$prev"（自动解析为上一步的 case_id）
- 想让执行失败后自动分析+修复，在该 step 加 "loop": {{"enabled": true, "max_fixes": 2}}
- 执行→（失败）→analyze_failure→fix_api_case→重新执行，自动闭环
- 接口需多组数据（边界/等价类）时：generate_data_driven_api_case → execute_data_driven_api_case
- 有 UI 截图时：write_ui_case_from_image（params 带 images base64 + base_url）
- 需要从需求文档批量生成用例时是两阶段流程：阶段1 用 extract_test_points（params.documents_text 传需求原文）提取测试点，**策略的 plan 只放 extract_test_points 这一步**（不要把 write_cases_batch 也放进 plan，否则会跳过人工确认环节）。用户在审阅面板确认/删减测试点后，前端自动触发阶段2 的 write_cases_batch 批量生成。AI 生成准确率约 80%，人工确认范围是不可省的环节。

**关键规则：当用户上传了需求文档（scope 或 summary 涉及"需求文档"/"批量"/"从文档生成"）时，必须把 E 型策略（批量生成用例）作为第一个策略选项。** 这是最适合该场景的策略——逐条手写 write_functional_case 在批量场景下效率极低且容易遗漏。

请提出策略选项，每个策略包含不同范围的测试计划。输出 JSON 数组：
[{{"id": "A", "label": "策略简称", "description": "这个策略覆盖什么", "plan": [{{"skill": "skill_id", "desc": "步骤描述", "params": {{...}}}}]}}]

策略应从窄到宽递进，例如：
- A: 批量生成用例（plan 仅含 extract_test_points 一步），从需求文档提取测试点供人工确认范围，确认后由前端触发批量生成。**上传了需求文档时此项必须为 A（首选）**
- B: 仅功能用例
- C: 仅接口用例
- D: 接口生成 + 执行验证闭环（write_api_case → execute_api_case 带 loop）

注意：E 型（extract_test_points）策略的 plan 里不能出现 write_cases_batch、write_functional_case、write_api_case 等生成 skill——它们属于阶段2，由前端在用户确认测试点后自动触发。

请直接输出 JSON 数组（不要额外解释）。"""


class Planner:
    """Agent 规划器：理解 → 策略 → 计划。"""

    def __init__(self, llm: "LLMClient", config: "LLMConfig") -> None:
        self.llm = llm
        self.config = config

    # ===== 阶段 A：理解 =====

    def understand(self, intent: str, documents: list[dict]) -> dict:
        """阅读意图 + 文档 → 需求摘要。

        documents: [{filename, content}] — content 是已解析的纯文本。
        """
        doc_text = "\n\n".join(
            f"--- {d['filename']} ---\n{d['content'][:3000]}" for d in documents if d.get("content")
        )
        if not doc_text:
            doc_text = "（用户未上传文档）"

        prompt = _UNDERSTAND_PROMPT.format(intent=intent, documents=doc_text)
        raw = self.llm.chat([{"role": "user", "content": prompt}])
        data = _extract_json(raw)

        if not data or not isinstance(data, dict):
            # 降级：直接用 intent 作为摘要
            return {"summary": intent, "scope": [intent], "doc_types": {}, "missing_for": {}}

        return {
            "summary": data.get("summary", intent),
            "scope": data.get("scope", []) if isinstance(data.get("scope"), list) else [],
            "doc_types": data.get("doc_types", {}) if isinstance(data.get("doc_types"), dict) else {},
            "missing_for": data.get("missing_for", {}) if isinstance(data.get("missing_for"), dict) else {},
        }

    # ===== 阶段 B：策略生成 =====

    def propose_strategies(self, context: dict, document_ids: list[int] | None = None) -> list[dict]:
        """基于理解摘要 → 测试策略选项（现在注入文档类型和能力限制）。"""
        summary = context.get("summary", "")
        scope = context.get("scope", [])
        scope_text = "、".join(scope) if scope else "未明确"

        # 构建文档类型信息 + 能力掩码
        doc_types = context.get("doc_types", {})
        doc_types_info = doc_types.get("detail", "未检测到文档类型信息")
        missing = context.get("missing_for", {})

        capability_parts = []
        has_prd = doc_types.get("has_prd", False)
        has_api_doc = doc_types.get("has_api_doc", False)
        has_ui_image = doc_types.get("has_ui_image", False)

        if has_prd:
            capability_parts.append("✅ 功能用例：可生成（有PRD需求文档）")
        else:
            capability_parts.append("⚠️ 功能用例：缺少PRD，可能不准确")
        if has_api_doc:
            capability_parts.append("✅ 接口用例：可生成（有API文档）")
        else:
            capability_parts.append(
                f"🚫 接口用例：不可生成。{missing.get('api_test', '需要接口文档（Swagger/OpenAPI等）')}"
            )
        if has_ui_image:
            capability_parts.append("✅ UI用例：可生成（有截图/设计稿）")
        else:
            capability_parts.append(
                f"🚫 UI用例：不可生成。{missing.get('ui_test', '需要UI截图或设计稿')}"
            )
        capability_mask = "\n".join(capability_parts)

        prompt = _STRATEGY_PROMPT.format(
            summary=summary,
            scope=scope_text,
            doc_types_info=doc_types_info,
            capability_mask=capability_mask,
            catalog=get_skill_catalog(),
        )
        raw = self.llm.chat([{"role": "user", "content": prompt}])
        data = _extract_json(raw)

        if not data or not isinstance(data, list):
            # 降级：返回一个默认全量策略
            return [self._default_strategy()]

        # 校验每个策略的 plan 中的 skill id
        valid = []
        for strat in data:
            if not isinstance(strat, dict) or "plan" not in strat:
                continue
            plan = self._validate_plan(strat.get("plan", []), document_ids=document_ids)
            valid.append(
                {
                    "id": strat.get("id", chr(65 + len(valid))),  # A, B, C...
                    "label": strat.get("label", "测试策略"),
                    "description": strat.get("description", ""),
                    "plan": plan,
                }
            )

        return valid if valid else [self._default_strategy()]

    def _default_strategy(self) -> dict:
        """降级默认策略。"""
        return {
            "id": "A",
            "label": "标准测试",
            "description": "检索知识库并生成功能用例",
            "plan": [
                {
                    "skill": "rag_search",
                    "desc": "检索知识库",
                    "params": {"query": ""},
                },
                {
                    "skill": "write_functional_case",
                    "desc": "生成功能用例",
                    "params": {"query": "", "design": "positive"},
                },
            ],
        }

    def _validate_plan(
        self, plan: list, document_ids: list[int] | None = None
    ) -> list[dict]:
        """校验 plan 步骤的 skill id 有效性。保留 skill/desc/params/loop 字段。

        document_ids 非 None 时，注入到文档敏感型 skill（extract_test_points /
        write_cases_batch / write_case）的 params，供 RAG 检索限定文档范围。
        """
        _DOC_SENSITIVE_SKILLS = {
            "extract_test_points", "write_cases_batch",
            "write_functional_case", "write_api_case", "write_ui_case_from_image",
            "generate_data_driven_api_case",
        }
        valid = []
        for step in plan:
            if not isinstance(step, dict):
                continue
            skill_id = step.get("skill", "")
            if skill_id not in SKILLS:
                continue
            params = dict(step.get("params", {}))
            # 注入 document_ids：LLM 可能生成空 []，始终用真实值覆盖
            if skill_id in _DOC_SENSITIVE_SKILLS and document_ids:
                params["document_ids"] = document_ids
            entry = {
                "skill": skill_id,
                "desc": step.get("desc", SKILLS[skill_id].name),
                "params": params,
            }
            # 执行闭环：保留 loop 配置（仅执行类 skill 有意义）
            if isinstance(step.get("loop"), dict):
                entry["loop"] = step["loop"]
            valid.append(entry)
        return valid

    # ===== 流式版本（SSE 推送思考过程 + 结果）=====

    def understand_stream(
        self, intent: str, documents: list[dict], thinking_level: str = "off"
    ) -> Iterator[tuple[str, object]]:
        """流式理解：yield (kind, data)。

        kind="thinking" ← reasoning token（思考过程，实时推送给前端展示）。
        kind="content"  ← 正常输出 token（中间 JSON，累积不展示）。
        kind="result"   ← 解析完成的 {summary, scope}（最后一条）。
        kind="error"    ← 异常 message。

        thinking_level != "off" 时用 stream_chat_raw（带 reasoning），否则用 stream_chat（只 content）。
        """
        doc_text = "\n\n".join(
            f"--- {d['filename']} ---\n{d['content'][:3000]}" for d in documents if d.get("content")
        )
        if not doc_text:
            doc_text = "（用户未上传文档）"

        prompt = _UNDERSTAND_PROMPT.format(intent=intent, documents=doc_text)
        try:
            if thinking_level and thinking_level != "off":
                raw_iter = self.llm.stream_chat_raw(
                    [{"role": "user", "content": prompt}], thinking_level=thinking_level
                )
            else:
                raw_iter = (
                    ("content", tok)
                    for tok in self.llm.stream_chat([{"role": "user", "content": prompt}])
                )
            full = []
            for kind, text in raw_iter:
                if kind == "reasoning":
                    yield ("thinking", text)
                else:
                    full.append(text)
            raw = "".join(full)
            if not raw.strip():
                yield ("error", "模型返回空回复，请重试")
                return
            data = _extract_json(raw)
            if not data or not isinstance(data, dict):
                result = {"summary": intent, "scope": [intent], "doc_types": {}, "missing_for": {}}
            else:
                result = {
                    "summary": data.get("summary", intent),
                    "scope": data.get("scope", []) if isinstance(data.get("scope"), list) else [],
                    "doc_types": data.get("doc_types", {}) if isinstance(data.get("doc_types"), dict) else {},
                    "missing_for": data.get("missing_for", {}) if isinstance(data.get("missing_for"), dict) else {},
                }
            yield ("result", result)
        except Exception as e:
            yield ("error", str(e))

    def propose_strategies_stream(
        self, context: dict, thinking_level: str = "off", document_ids: list[int] | None = None
    ) -> Iterator[tuple[str, object]]:
        """流式策略生成：yield (kind, data)。同 understand_stream 结构。"""
        summary = context.get("summary", "")
        scope = context.get("scope", [])
        scope_text = "、".join(scope) if scope else "未明确"

        # 构建文档类型信息 + 能力掩码（同 propose_strategies）
        doc_types = context.get("doc_types", {})
        doc_types_info = doc_types.get("detail", "未检测到文档类型信息")
        missing = context.get("missing_for", {})
        has_prd = doc_types.get("has_prd", False)
        has_api_doc = doc_types.get("has_api_doc", False)
        has_ui_image = doc_types.get("has_ui_image", False)
        capability_parts = []
        if has_prd:
            capability_parts.append("✅ 功能用例：可生成（有PRD需求文档）")
        else:
            capability_parts.append("⚠️ 功能用例：缺少PRD，可能不准确")
        if has_api_doc:
            capability_parts.append("✅ 接口用例：可生成（有API文档）")
        else:
            capability_parts.append(f"🚫 接口用例：不可生成。{missing.get('api_test', '需要接口文档')}")
        if has_ui_image:
            capability_parts.append("✅ UI用例：可生成（有截图/设计稿）")
        else:
            capability_parts.append(f"🚫 UI用例：不可生成。{missing.get('ui_test', '需要UI截图或设计稿')}")
        capability_mask = "\n".join(capability_parts)

        prompt = _STRATEGY_PROMPT.format(
            summary=summary,
            scope=scope_text,
            doc_types_info=doc_types_info,
            capability_mask=capability_mask,
            catalog=get_skill_catalog(),
        )
        try:
            if thinking_level and thinking_level != "off":
                raw_iter = self.llm.stream_chat_raw(
                    [{"role": "user", "content": prompt}], thinking_level=thinking_level
                )
            else:
                raw_iter = (
                    ("content", tok)
                    for tok in self.llm.stream_chat([{"role": "user", "content": prompt}])
                )
            full = []
            for kind, text in raw_iter:
                if kind == "reasoning":
                    yield ("thinking", text)
                else:
                    full.append(text)
            raw = "".join(full)
            if not raw.strip():
                yield ("error", "模型返回空回复，请重试")
                return
            data = _extract_json(raw)
            if not data or not isinstance(data, list):
                strategies = [self._default_strategy()]
            else:
                valid = []
                for strat in data:
                    if not isinstance(strat, dict) or "plan" not in strat:
                        continue
                    plan = self._validate_plan(strat.get("plan", []), document_ids=document_ids)
                    valid.append(
                        {
                            "id": strat.get("id", chr(65 + len(valid))),
                            "label": strat.get("label", "测试策略"),
                            "description": strat.get("description", ""),
                            "plan": plan,
                        }
                    )
                strategies = valid if valid else [self._default_strategy()]
            yield ("result", strategies)
        except Exception as e:
            yield ("error", str(e))

    # ===== 兼容旧流程 =====

    def generate_plan(self, intent: str) -> list[dict]:
        """旧流程兼容：意图 → plan（无文档理解/策略选择）。"""
        prompt = _PLAN_PROMPT.format(catalog=get_skill_catalog(), intent=intent)
        raw = self.llm.chat([{"role": "user", "content": prompt}])
        data = _extract_json(raw)

        if not data or not isinstance(data, list):
            return [
                {
                    "skill": "rag_search",
                    "desc": f"检索知识库中与「{intent}」相关的内容",
                    "params": {"query": intent},
                }
            ]

        valid = self._validate_plan(data)
        return (
            valid
            if valid
            else [
                {
                    "skill": "rag_search",
                    "desc": f"检索知识库中与「{intent}」相关的内容",
                    "params": {"query": intent},
                }
            ]
        )
