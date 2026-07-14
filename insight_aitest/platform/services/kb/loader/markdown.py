# -*- coding: utf-8 -*-
"""Markdown Loader：直接读文本（RAG 不渲染）。"""

from __future__ import annotations

from pathlib import Path

from insight_aitest.platform.services.kb.loader import register_loader
from insight_aitest.platform.services.kb.loader.base import DocumentLoadError, DocumentLoader
from insight_aitest.platform.services.kb.models import ParsedDocument


@register_loader(".md")
@register_loader(".markdown")
class MarkdownLoader(DocumentLoader):
    def load(self, path: Path) -> ParsedDocument:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            raise DocumentLoadError(f"读取 Markdown 失败: {e}") from e
        return ParsedDocument(
            filename=path.name,
            content=content,
            meta={"mime_type": "text/markdown", "char_count": len(content)},
        )
