# -*- coding: utf-8 -*-
"""
模块清单注册中心：扫描 modules/ 目录，解析每个 manifest.yaml，
校验唯一性/格式，拓扑排序依赖，暴露模块列表。
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from fastapi import APIRouter

from insight_aitest.modules._registry.manifest import ModuleManifest


class ManifestError(Exception):
    """manifest 解析/校验失败。"""


class ModuleLoadError(Exception):
    """manifest 合法但运行时加载失败（router import 失败等）。"""


@dataclass
class LoadedModule:
    manifest: ModuleManifest
    router: Optional[APIRouter] = None
    websocket: Optional[Any] = None


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: list[LoadedModule] = []

    def scan(self, modules_dir: str) -> None:
        base = Path(modules_dir)
        if not base.exists():
            self._modules = []
            return

        seen_ids: set[str] = set()
        seen_routes: set[str] = set()
        loaded: dict[str, LoadedModule] = {}

        for child in sorted(base.iterdir()):
            if not child.is_dir() or child.name.startswith("_") or child.name.startswith("."):
                continue
            manifest_path = child / "manifest.yaml"
            if not manifest_path.exists():
                continue
            try:
                raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
                m = ModuleManifest(**raw)
            except Exception as e:  # Pydantic/YAML 错误
                raise ManifestError(f"[{child.name}] manifest 无效: {e}") from e

            if m.id in seen_ids:
                raise ManifestError(f"重复的模块 id: {m.id}")
            seen_ids.add(m.id)
            if m.frontend and m.frontend.route in seen_routes:
                raise ManifestError(f"重复的 frontend.route: {m.frontend.route}")
            if m.frontend:
                seen_routes.add(m.frontend.route)

            loaded[m.id] = LoadedModule(manifest=m)

        # 依赖拓扑排序 + 环检测
        ordered_ids = self._topo_sort(loaded)
        self._modules = [loaded[i] for i in ordered_ids]

    @staticmethod
    def _topo_sort(loaded: dict[str, LoadedModule]) -> list[str]:
        # 构建依赖图（仅考虑已加载模块内的依赖）
        graph: dict[str, list[str]] = {
            mid: (
                [d for d in lm.manifest.backend.dependencies if d in loaded]
                if lm.manifest.backend
                else []
            )
            for mid, lm in loaded.items()
        }
        visited: dict[str, int] = {}  # 0=visiting, 1=done
        order: list[str] = []

        def visit(node: str, stack: list[str]) -> None:
            state = visited.get(node)
            if state == 1:
                return
            if state == 0:
                cycle = " -> ".join(stack + [node])
                raise ManifestError(f"模块依赖存在环: {cycle}")
            visited[node] = 0
            for dep in graph[node]:
                visit(dep, stack + [node])
            visited[node] = 1
            order.append(node)

        for mid in loaded:
            visit(mid, [])
        return order

    @property
    def modules(self) -> list[LoadedModule]:
        return list(self._modules)

    def resolve_backends(self) -> None:
        """import 每个模块的 backend.router / websocket。失败抛 ModuleLoadError。"""
        for lm in self._modules:
            be = lm.manifest.backend
            if not be:
                continue
            lm.router = self._import_attr(
                be.router, expect_type=APIRouter, owner=lm.manifest.id, kind="router"
            )
            if be.websocket:
                lm.websocket = self._import_attr(
                    be.websocket, owner=lm.manifest.id, kind="websocket"
                )

    @staticmethod
    def _import_attr(spec: str, owner: str, kind: str, expect_type: Optional[type] = None) -> Any:
        if ":" not in spec:
            raise ModuleLoadError(
                f"[{owner}] backend.{kind} 必须形如 'module.path:attr'，实际: {spec}"
            )
        module_path, attr = spec.split(":", 1)
        try:
            mod = importlib.import_module(module_path)
            obj = getattr(mod, attr)
        except Exception as e:
            raise ModuleLoadError(f"[{owner}] 无法加载 backend.{kind} '{spec}': {e}") from e
        if expect_type and not isinstance(obj, expect_type):
            raise ModuleLoadError(f"[{owner}] backend.{kind} '{spec}' 不是 {expect_type.__name__}")
        return obj

    def to_public_list(self) -> list[dict[str, Any]]:
        out = []
        for lm in self._modules:
            m = lm.manifest
            out.append(
                {
                    "id": m.id,
                    "name": m.name,
                    "version": m.version,
                    "category": m.category,
                    "icon": m.icon,
                    "order": m.order,
                    "description": m.description,
                    "frontend": m.frontend.model_dump() if m.frontend else None,
                    "default_enabled": m.default_enabled,
                }
            )
        out.sort(key=lambda x: x["order"])
        return out
