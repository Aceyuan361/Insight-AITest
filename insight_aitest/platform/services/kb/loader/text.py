# -*- coding: utf-8 -*-
"""Text Loader：自动探测编码（Windows 中文环境重要）。"""

from __future__ import annotations

from pathlib import Path

from insight_aitest.platform.services.kb.loader import register_loader
from insight_aitest.platform.services.kb.loader.base import DocumentLoadError, DocumentLoader
from insight_aitest.platform.services.kb.models import ParsedDocument


@register_loader(".txt")
class TextLoader(DocumentLoader):
    def load(self, path: Path) -> ParsedDocument:
        raw = path.read_bytes()
        content = self._decode(raw)
        return ParsedDocument(
            filename=path.name,
            content=content,
            meta={"mime_type": "text/plain", "char_count": len(content)},
        )

    @staticmethod
    def _decode(raw: bytes) -> str:
        # 优先 utf-8，失败则 chardet 探测，再失败 gbk fallback
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
        try:
            import chardet

            guess = chardet.detect(raw)
            if guess and guess.get("encoding"):
                try:
                    return raw.decode(guess["encoding"])
                except (UnicodeDecodeError, LookupError):
                    pass
        except ImportError:
            pass
        try:
            return raw.decode("gbk", errors="replace")
        except Exception as e:
            raise DocumentLoadError(f"无法解码文本: {e}") from e
