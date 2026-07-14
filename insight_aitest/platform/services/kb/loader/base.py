# -*- coding: utf-8 -*-
"""DocumentLoader 接口（平台共享服务）。加新格式 = 加一个 Loader 子类 + 注册表加一行。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from insight_aitest.platform.services.kb.models import ParsedDocument


class UnsupportedFormatError(Exception):
    """不支持的文件格式。"""


class DocumentLoadError(Exception):
    """文档解析失败。"""


# OCR 共享提示词（VLM 读图抽取纯文本，供 ImageLoader / PDF 扫描件复用）
OCR_PROMPT = (
    "请提取这张图片中的所有可见文字，按从上到下、从左到右的阅读顺序输出为纯文本。"
    "要求：1) 只输出文字内容，不要输出任何解释、标注或格式标记；"
    "2) 保留原文的段落分隔（用空行表示）；3) 表格内容逐行输出；"
    "4) 如图片为纯图形无文字，输出空字符串。"
)


class DocumentLoader(ABC):
    @abstractmethod
    def load(self, path: Path) -> ParsedDocument:
        """读取文件，返回纯文本 + 元信息。失败抛 DocumentLoadError。"""
