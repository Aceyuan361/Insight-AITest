# -*- coding: utf-8 -*-
"""分析器（Phase A）：检索 → LLM 分析 → 可测点清单（spec D §3.5.1）。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from insight_aitest.modules.testcase.backend.generator.prompts import build_analyze_prompt

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.config import LLMConfig
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.kb.retriever import Retriever
    from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType


@dataclass
class TestPoint:
    __test__ = False  # 避免 pytest 误收集
    id: str
    summary: str
    suggested_type: "CaseType"
    suggested_design: "TestType"
    rationale: str
    chunk_refs: list[int] = field(default_factory=list)


def _extract_json(text: str) -> list | dict | None:
    """容错解析 LLM 输出为 JSON。

    1. 先找 ```json ... ``` 代码块
    2. 退化为找首个 [ 或 { 到末个 ] 或 } 的子串
    3. 全失败返回 None
    """
    m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    candidate = m.group(1) if m else text
    try:
        return json.loads(candidate)
    except Exception:
        pass
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = candidate.find(open_ch)
        end = candidate.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except Exception:
                continue
    return None


class Analyzer:
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

    def analyze(
        self,
        query: str,
        document_ids: list[int] | None = None,
        project_id: int | None = None,
    ) -> list[TestPoint]:
        """检索 → LLM 分析 → 可测点清单。

        project_id 非 None 时按项目隔离 RAG 检索（KB 升级，杜绝跨项目污染）。
        """
        from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType

        scored = self._retrieve(query, document_ids, project_id=project_id)
        chunks = [(s.document.filename, s.chunk.text) for s in scored]
        prompt = build_analyze_prompt(query, chunks)
        raw = self.llm.chat([{"role": "user", "content": prompt}])
        data = _extract_json(raw)
        if not data or not isinstance(data, list):
            return []
        points = []
        for d in data:
            if not isinstance(d, dict) or "summary" not in d:
                continue
            try:
                points.append(
                    TestPoint(
                        id=d.get("id", f"tp-{len(points) + 1}"),
                        summary=d["summary"],
                        suggested_type=CaseType(d.get("suggested_type", "functional")),
                        suggested_design=TestType(d.get("suggested_design", "positive")),
                        rationale=d.get("rationale", ""),
                        chunk_refs=d.get("chunk_refs", []),
                    )
                )
            except (ValueError, KeyError):
                continue
        return points
