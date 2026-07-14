# -*- coding: utf-8 -*-
"""生成器（Phase B）：为单个可测点生成一条用例（spec D §3.5.2）。

检索相关片段 → LLM 结构化生成 → 解析校验 → 返回 TestCase(status=draft)。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json
from insight_aitest.modules.testcase.backend.generator.prompts import build_generate_prompt
from insight_aitest.modules.testcase.backend.generator.schemas import validate_content

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.config import LLMConfig
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.kb.retriever import Retriever
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    from insight_aitest.modules.testcase.backend.persistence.models import TestCase


class Generator:
    def __init__(self, retriever: "Retriever", llm: "LLMClient", config: "LLMConfig") -> None:
        self.retriever = retriever
        self.llm = llm
        self.config = config

    def _retrieve(self, query: str, document_ids, project_id: int | None = None):
        try:
            return self.retriever.retrieve(
                query, document_ids=document_ids, project_id=project_id
            )
        except Exception:
            return []

    def generate(
        self,
        point: "TestPoint",
        document_ids: list[int] | None = None,
        override_type: str | None = None,
        override_design: str | None = None,
        project_id: int | None = None,
    ) -> "TestCase":
        """为单个可测点生成一条用例。

        project_id 非 None 时按项目隔离 RAG 检索（KB 升级，杜绝跨项目污染）。
        """
        from insight_aitest.modules.testcase.backend.persistence.models import (
            CasePriority,
            CaseStatus,
            CaseType,
            TestCase,
            TestType,
        )

        case_type = CaseType(override_type) if override_type else point.suggested_type
        design = TestType(override_design) if override_design else point.suggested_design

        scored = self._retrieve(point.summary, document_ids, project_id=project_id)
        chunks = [(s.document.filename, s.chunk.text) for s in scored]
        prompt = build_generate_prompt(case_type.value, design.value, point.summary, chunks)
        raw = self.llm.chat([{"role": "user", "content": prompt}])
        data = _extract_json(raw)

        if not data or not isinstance(data, dict):
            # 解析失败：返回空 content + 标记失败来源，让用户手动编辑
            return TestCase(
                title=point.summary,
                type=case_type,
                test_design=design,
                status=CaseStatus.DRAFT,
                source="ai:failed",
                content={},
            )

        content = data.get("content", {})
        if not isinstance(content, dict):
            content = {}
        # schema 校验：content 不符结构时标记 source（仍保留 content 供用户手动修，不谎称成功）
        is_valid = validate_content(case_type.value, content)
        # 防御：description 空串回退到 point.summary，preconditions 空串回退到"无"
        description = data.get("description", "")
        if not description or not description.strip():
            description = point.summary
        preconditions = data.get("preconditions", "")
        if not preconditions or not preconditions.strip():
            preconditions = "无"
        return TestCase(
            title=data.get("title", point.summary),
            type=case_type,
            description=description,
            priority=CasePriority.P2,
            status=CaseStatus.DRAFT,
            test_design=design,
            preconditions=preconditions,
            content=content,
            source=f"ai:{self.config.chat_model}" if is_valid else "ai:invalid",
        )

    def generate_from_image(
        self,
        images: list[tuple[str, str]],
        base_url: str,
        point_summary: str = "",
    ) -> "TestCase":
        """从截图生成一条 UI 用例（与 generate 平行，不走 RAG 检索）。

        images: [(base64, mime), ...] 截图列表，按顺序表示操作流程。
        base_url: 目标 URL（强制覆盖 LLM 输出，防编造）。
        """
        from insight_aitest.modules.testcase.backend.generator.prompts import (
            build_generate_from_image_prompt,
        )
        from insight_aitest.modules.testcase.backend.persistence.models import (
            CasePriority,
            CaseStatus,
            CaseType,
            TestCase,
            TestType,
        )

        prompt = build_generate_from_image_prompt(base_url, point_summary)
        raw = self.llm.chat_with_images(prompt, images)
        data = _extract_json(raw)

        if not data or not isinstance(data, dict):
            return TestCase(
                title=f"截图用例 ({base_url})",
                type=CaseType.UI,
                test_design=TestType.POSITIVE,
                status=CaseStatus.DRAFT,
                source="ai:failed",
                content={},
            )

        content = data.get("content", {})
        if not isinstance(content, dict):
            content = {}
        # 强制覆盖 base_url（防 LLM 漏填/改写/编造）
        content["base_url"] = base_url

        is_valid = validate_content("ui", content)
        return TestCase(
            title=data.get("title", f"截图用例 ({base_url})"),
            type=CaseType.UI,
            description=data.get("description", ""),
            priority=CasePriority.P2,
            status=CaseStatus.DRAFT,
            test_design=TestType.POSITIVE,
            preconditions=data.get("preconditions", ""),
            content=content,
            source="ai:vision" if is_valid else "ai:invalid",
        )
