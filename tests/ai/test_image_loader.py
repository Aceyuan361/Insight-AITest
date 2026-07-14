# -*- coding: utf-8 -*-
"""ImageLoader 测试（VLM OCR 路径，全 mock，不真实调 vision）。"""
from unittest.mock import MagicMock

import pytest


def test_image_loader_extracts_text(tmp_path):
    """图片 loader：读字节 → base64 → VLM OCR → 纯文本。"""
    img_path = tmp_path / "scan.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\n fake png bytes")

    from insight_aitest.platform.services.kb.loader.image import ImageLoader

    fake_llm = MagicMock()
    fake_llm.chat_with_image.return_value = "图片中的文字内容"
    loader = ImageLoader(llm=fake_llm)
    doc = loader.load(img_path)

    assert doc.content == "图片中的文字内容"
    assert doc.meta["ocr"] is True
    assert doc.meta["mime_type"] == "image/png"
    # 确认 base64 编码传入（image.py 调用：prompt, b64 位置 + mime= 关键字）
    import base64

    call = fake_llm.chat_with_image.call_args
    assert "提取" in call.args[0]  # prompt 是 OCR 提取提示词
    assert base64.b64decode(call.args[1]) == b"\x89PNG\r\n\x1a\n fake png bytes"  # image_base64
    assert call.kwargs["mime"] == "image/png"


def test_image_loader_unsupported_ext(tmp_path):
    """非注册扩展名报错（走 _IMG_MIME 校验）。"""
    img_path = tmp_path / "a.bmp"
    img_path.write_bytes(b"x")
    from insight_aitest.platform.services.kb.loader.image import ImageLoader
    from insight_aitest.platform.services.kb.loader.base import DocumentLoadError

    loader = ImageLoader(llm=MagicMock())
    with pytest.raises(DocumentLoadError, match="不支持"):
        loader.load(img_path)


def test_image_loader_empty_ocr_raises(tmp_path):
    """OCR 返回空：报错。"""
    img_path = tmp_path / "blank.jpg"
    img_path.write_bytes(b"jpg bytes")
    from insight_aitest.platform.services.kb.loader.image import ImageLoader
    from insight_aitest.platform.services.kb.loader.base import DocumentLoadError

    fake_llm = MagicMock()
    fake_llm.chat_with_image.return_value = ""
    loader = ImageLoader(llm=fake_llm)
    with pytest.raises(DocumentLoadError, match="未识别到文字"):
        loader.load(img_path)


def test_image_loader_jpeg_mime(tmp_path):
    """jpg 扩展名映射 image/jpeg。"""
    img_path = tmp_path / "photo.jpeg"
    img_path.write_bytes(b"jpeg data")
    from insight_aitest.platform.services.kb.loader.image import ImageLoader

    fake_llm = MagicMock()
    fake_llm.chat_with_image.return_value = "JPEG 文字"
    loader = ImageLoader(llm=fake_llm)
    doc = loader.load(img_path)
    assert doc.content == "JPEG 文字"
    assert doc.meta["mime_type"] == "image/jpeg"


def test_image_loader_via_factory(tmp_path):
    """get_loader 无参实例化图片 loader（默认从 deps 取 llm，此处 mock deps）。"""
    img_path = tmp_path / "f.png"
    img_path.write_bytes(b"png")
    fake_llm = MagicMock()
    fake_llm.chat_with_image.return_value = "factory text"

    import insight_aitest.platform.services.kb.loader.image as image_mod

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(image_mod.ImageLoader, "__init__", lambda self: setattr(self, "_llm", fake_llm))
        from insight_aitest.platform.services.kb.loader import get_loader

        doc = get_loader("f.png").load(img_path)
    assert doc.content == "factory text"
