# -*- coding: utf-8 -*-
"""Loader 工厂 + 注册表（平台共享服务）。"""

from __future__ import annotations

from pathlib import Path

from insight_aitest.platform.services.kb.loader.base import (
    DocumentLoader,
    UnsupportedFormatError,
)

_LOADERS: dict[str, type[DocumentLoader]] = {}


def register_loader(ext: str):
    """装饰器：注册某扩展名对应的 Loader 类。"""

    def wrapper(cls: type[DocumentLoader]) -> type[DocumentLoader]:
        _LOADERS[ext.lower()] = cls
        return cls

    return wrapper


def get_loader(filename: str) -> DocumentLoader:
    ext = Path(filename).suffix.lower()
    cls = _LOADERS.get(ext)
    if cls is None:
        raise UnsupportedFormatError(f"不支持的格式: {ext}")
    return cls()


# 导入子模块触发 @register_loader 装饰器注册
from . import markdown  # noqa: F401, E402
from . import text  # noqa: F401, E402
from . import pdf  # noqa: F401, E402
from . import docx  # noqa: F401, E402
from . import image  # noqa: F401, E402
from . import xlsx  # noqa: F401, E402
from . import pptx  # noqa: F401, E402
from . import html  # noqa: F401, E402
