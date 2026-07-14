# -*- coding: utf-8 -*-
"""Image Loader：用 vision model（VLM 读图）抽取图片中的文字。

走 OpenAI 兼容多模态协议（LLMClient.chat_with_image），不引入 tesseract/paddle
（Windows 部署负担）。扫描件截图、纯图片文档、截图凭证等均可处理。

OCR 输出必须是连续纯文本（满足 Chunker 的文本可定位不变量）。
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING

from insight_aitest.platform.services.kb.loader import register_loader
from insight_aitest.platform.services.kb.loader.base import (
    DocumentLoadError,
    DocumentLoader,
    OCR_PROMPT,
)
from insight_aitest.platform.services.kb.models import ParsedDocument

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.client import LLMClient

# 支持的图片扩展名 → mime
_IMG_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


@register_loader(".png")
@register_loader(".jpg")
@register_loader(".jpeg")
@register_loader(".gif")
@register_loader(".webp")
class ImageLoader(DocumentLoader):
    """图片文档 loader：VLM OCR 抽取文字。"""

    def __init__(self, llm: "LLMClient | None" = None) -> None:
        # 默认从平台单例取 LLM（get_loader() 无参实例化时走此路径）；
        # 测试可显式注入 mock。
        self._llm = llm

    def _get_llm(self) -> "LLMClient":
        if self._llm is not None:
            return self._llm
        from insight_aitest.platform.services.kb.deps import get_llm

        return get_llm()

    def load(self, path: Path) -> ParsedDocument:
        ext = path.suffix.lower()
        mime = _IMG_MIME.get(ext)
        if mime is None:
            raise DocumentLoadError(f"不支持的图片格式: {ext}")

        try:
            raw = path.read_bytes()
        except OSError as e:
            raise DocumentLoadError(f"图片读取失败: {e}") from e

        b64 = base64.b64encode(raw).decode("ascii")

        try:
            llm = self._get_llm()
        except Exception as e:
            raise DocumentLoadError(f"OCR 服务不可用: {e}") from e

        try:
            content = llm.chat_with_image(OCR_PROMPT, b64, mime=mime).strip()
        except Exception as e:
            raise DocumentLoadError(f"图片 OCR 失败: {e}") from e

        if not content:
            raise DocumentLoadError("图片未识别到文字内容（可能为纯图形）。")

        return ParsedDocument(
            filename=path.name,
            content=content,
            meta={
                "mime_type": mime,
                "ocr": True,
                "byte_count": len(raw),
                "char_count": len(content),
            },
        )
