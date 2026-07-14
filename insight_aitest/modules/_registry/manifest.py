# -*- coding: utf-8 -*-
"""模块清单 (manifest) 的 Pydantic schema。"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


class NavSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: dict[str, str]
    icon: str
    show_in_dashboard: bool = True


class FrontendSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route: str
    entry: str
    nav: NavSpec

    @field_validator("route")
    @classmethod
    def route_must_start_with_slash(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("frontend.route must start with '/'")
        return v


class BackendSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    router: str
    websocket: Optional[str] = None
    dependencies: list[str] = Field(default_factory=list)


class ModuleManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: dict[str, str]
    version: str
    category: Literal["testing", "ai", "infra", "agent", "assets"]
    icon: str
    order: int
    description: dict[str, str] = Field(default_factory=dict)
    backend: Optional[BackendSpec] = None
    frontend: Optional[FrontendSpec] = None
    default_enabled: bool = True

    @field_validator("id")
    @classmethod
    def id_format(cls, v: str) -> str:
        if not ID_PATTERN.match(v):
            raise ValueError("id must match ^[a-z][a-z0-9-]*$")
        return v

    @field_validator("name")
    @classmethod
    def name_at_least_one_lang(cls, v: dict[str, str]) -> dict[str, str]:
        if not v or not any(v.values()):
            raise ValueError("name must contain at least one language")
        return v
