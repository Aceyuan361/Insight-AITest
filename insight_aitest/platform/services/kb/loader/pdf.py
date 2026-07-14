# -*- coding: utf-8 -*-
"""PDF Loader：优先抽文本层；扫描件（无文本）走 VLM OCR。

策略（按依赖可用性优雅降级）：
1) pymupdf（fitz）可用 → 抽文本层；扫描件则逐页 rasterize 成图片 → VLM OCR 拼纯文本。
2) pymupdf 不可用 → 回退 pypdf 抽文本层；扫描件报错引导（保持旧行为）。

OCR 开关由 LLMConfig.ocr_enabled 控制（默认开，需 vision_model 配置）。
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

# 扫描件判定：每页平均字符数低于此阈值视为无文本层
_MIN_CHARS_PER_PAGE = 10


def _ocr_enabled() -> bool:
    """从平台配置取 ocr_enabled（测试可 monkeypatch）。"""
    try:
        from insight_aitest.platform.services.kb.deps import get_llm_config

        return get_llm_config().ocr_enabled
    except Exception:
        return True


def _get_llm() -> "LLMClient":
    from insight_aitest.platform.services.kb.deps import get_llm

    return get_llm()


def _pdf_ocr_with_fitz(doc) -> str:
    """用 pymupdf 逐页 rasterize → VLM OCR → 拼纯文本。"""
    llm = _get_llm()
    pages = []
    for page in doc:
        # 渲染成图片（150dpi 兼顾清晰度与 token 成本）
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("ascii")
        try:
            text = llm.chat_with_image(OCR_PROMPT, b64, mime="image/png").strip()
        except Exception as e:
            raise DocumentLoadError(f"PDF 扫描件 OCR 失败（第 {len(pages) + 1} 页）: {e}") from e
        if text:
            pages.append(text)
    return "\n\n".join(pages)


@register_loader(".pdf")
class PdfLoader(DocumentLoader):
    def load(self, path: Path) -> ParsedDocument:
        try:
            import fitz  # pymupdf

            has_fitz = True
        except ImportError:
            fitz = None
            has_fitz = False

        # ---- pymupdf 路径（优先，支持扫描件 OCR）----
        if has_fitz:
            try:
                doc = fitz.open(str(path))
            except Exception as e:
                raise DocumentLoadError(f"PDF 解析失败: {e}") from e

            page_count = doc.page_count
            # 抽文本层
            text_pages = [page.get_text() or "" for page in doc]
            content = "\n\n".join(text_pages)
            is_scanned = page_count > 0 and len(content.strip()) < page_count * _MIN_CHARS_PER_PAGE

            if is_scanned:
                # 扫描件 → OCR 分支
                if not _ocr_enabled():
                    doc.close()
                    raise DocumentLoadError(
                        "该 PDF 似为扫描件（无可提取文本），OCR 已禁用。请在设置中开启 OCR 或提供带文本层的 PDF。"
                    )
                try:
                    content = _pdf_ocr_with_fitz(doc)
                finally:
                    doc.close()
                if not content.strip():
                    raise DocumentLoadError("扫描件 OCR 未识别到文字内容。")
                return ParsedDocument(
                    filename=path.name,
                    content=content,
                    meta={
                        "mime_type": "application/pdf",
                        "page_count": page_count,
                        "char_count": len(content),
                        "scanned": True,
                        "ocr": True,
                    },
                )

            doc.close()
            return ParsedDocument(
                filename=path.name,
                content=content,
                meta={
                    "mime_type": "application/pdf",
                    "page_count": page_count,
                    "char_count": len(content),
                    "scanned": False,
                },
            )

        # ---- pypdf 回退路径（无 OCR 能力，保持旧行为）----
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise DocumentLoadError(f"pypdf/pymupdf 均未安装: {e}") from e
        try:
            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            content = "\n\n".join(pages)
        except Exception as e:
            raise DocumentLoadError(f"PDF 解析失败: {e}") from e

        page_count = len(reader.pages)
        if page_count > 0 and len(content.strip()) < page_count * _MIN_CHARS_PER_PAGE:
            raise DocumentLoadError(
                "该 PDF 似为扫描件（无可提取文本），未安装 pymupdf 无法 OCR。"
                "请安装 pymupdf 或提供带文本层的 PDF。"
            )
        return ParsedDocument(
            filename=path.name,
            content=content,
            meta={
                "mime_type": "application/pdf",
                "page_count": page_count,
                "char_count": len(content),
                "scanned": False,
            },
        )
