# -*- coding: utf-8 -*-
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _make_text_pdf(path: Path):
    """用 reportlab 生成一个带文本层的最小 PDF。"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawString(100, 700, "Hello PDF test content")
    c.drawString(100, 680, "Second line of text")
    c.save()


def _make_blank_pdf(path: Path):
    """生成无文本层的 PDF（模拟扫描件）。"""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)


def test_pdf_loader_extracts_text(tmp_path):
    pdf_path = tmp_path / "test.pdf"
    _make_text_pdf(pdf_path)
    from insight_aitest.platform.services.kb.loader import get_loader
    doc = get_loader("test.pdf").load(pdf_path)
    assert "Hello PDF test content" in doc.content
    assert doc.meta.get("page_count", 0) >= 1
    assert doc.meta.get("scanned") is False


def test_pdf_loader_scanned_ocr_disabled_raises(tmp_path):
    """扫描件 + OCR 禁用：报错引导。"""
    pdf_path = tmp_path / "blank.pdf"
    _make_blank_pdf(pdf_path)
    from insight_aitest.platform.services.kb.loader import get_loader
    from insight_aitest.platform.services.kb.loader.base import DocumentLoadError
    with patch(
        "insight_aitest.platform.services.kb.loader.pdf._ocr_enabled", return_value=False
    ):
        with pytest.raises(DocumentLoadError, match="扫描件"):
            get_loader("blank.pdf").load(pdf_path)


def test_pdf_loader_scanned_ocr_calls_vision(tmp_path):
    """扫描件 + OCR 开启：走 vision model 逐页 OCR，拼纯文本。"""
    pdf_path = tmp_path / "blank.pdf"
    _make_blank_pdf(pdf_path)
    fake_llm = MagicMock()
    fake_llm.chat_with_image.return_value = "OCR 识别的扫描件文字"
    with patch(
        "insight_aitest.platform.services.kb.loader.pdf._ocr_enabled", return_value=True
    ), patch(
        "insight_aitest.platform.services.kb.loader.pdf._get_llm", return_value=fake_llm
    ):
        from insight_aitest.platform.services.kb.loader import get_loader
        doc = get_loader("blank.pdf").load(pdf_path)
    assert "OCR 识别的扫描件文字" in doc.content
    assert doc.meta.get("scanned") is True
    assert doc.meta.get("ocr") is True
    fake_llm.chat_with_image.assert_called_once()


def test_pdf_loader_scanned_ocr_empty_raises(tmp_path):
    """扫描件 OCR 返回空：报错。"""
    pdf_path = tmp_path / "blank.pdf"
    _make_blank_pdf(pdf_path)
    fake_llm = MagicMock()
    fake_llm.chat_with_image.return_value = ""
    with patch(
        "insight_aitest.platform.services.kb.loader.pdf._ocr_enabled", return_value=True
    ), patch(
        "insight_aitest.platform.services.kb.loader.pdf._get_llm", return_value=fake_llm
    ):
        from insight_aitest.platform.services.kb.loader import get_loader
        from insight_aitest.platform.services.kb.loader.base import DocumentLoadError
        with pytest.raises(DocumentLoadError, match="未识别到文字"):
            get_loader("blank.pdf").load(pdf_path)
