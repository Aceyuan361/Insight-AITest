# -*- coding: utf-8 -*-
"""HTML 文档 Loader（.html / .htm）。用 beautifulsoup4 提取可见纯文本。"""

from __future__ import annotations

from pathlib import Path

from insight_aitest.platform.services.kb.loader import register_loader
from insight_aitest.platform.services.kb.loader.base import DocumentLoader
from insight_aitest.platform.services.kb.models import ParsedDocument


@register_loader(".htm")
@register_loader(".html")
class HtmlLoader(DocumentLoader):
    """HTML 文档 Loader。移除 script/style，保留块级结构以空行分隔。"""

    def load(self, path: Path) -> ParsedDocument:
        from bs4 import BeautifulSoup

        raw = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(raw, "html.parser")

        # 移除无关标签
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()

        # 块级元素间用空行分隔，保留可读结构
        content = soup.get_text(separator="\n", strip=True)
        # 合并连续空行
        lines = [ln.strip() for ln in content.splitlines()]
        content = "\n".join(ln for ln in lines if ln)

        return ParsedDocument(filename=path.name, content=content, meta={"format": "html"})
