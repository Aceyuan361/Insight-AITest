# -*- coding: utf-8 -*-
import pytest
from insight_aitest.platform.module_registry import (
    ModuleRegistry,
    ManifestError,
)


def _write_manifest(tmp_path, mod_id, content):
    d = tmp_path / mod_id
    d.mkdir(parents=True)
    (d / "manifest.yaml").write_text(content, encoding="utf-8")
    return d


def test_scan_empty_dir_returns_no_modules(tmp_path):
    reg = ModuleRegistry()
    reg.scan(str(tmp_path))
    assert reg.modules == []


def test_scan_valid_manifest(tmp_path):
    _write_manifest(
        tmp_path,
        "perf",
        "id: perf\n"
        "name: {zh: 性能, en: Perf}\n"
        "version: 1.0.0\n"
        "category: testing\n"
        "icon: Gauge\n"
        "order: 1\n"
        "frontend:\n"
        "  route: /perf\n"
        "  entry: perf:PerfApp\n"
        "  nav: {label: {zh: 性能}, icon: Gauge}\n",
    )
    reg = ModuleRegistry()
    reg.scan(str(tmp_path))
    assert len(reg.modules) == 1
    assert reg.modules[0].manifest.id == "perf"


def test_scan_skips_underscore_directories(tmp_path):
    _write_manifest(
        tmp_path,
        "_registry",
        "id: registry\nname: {zh: x}\nversion: '1'\ncategory: testing\nicon: Gauge\norder: 1\n",
    )
    reg = ModuleRegistry()
    reg.scan(str(tmp_path))
    assert reg.modules == []  # _ 开头目录被跳过


def test_scan_duplicate_id_raises(tmp_path):
    _write_manifest(
        tmp_path, "perf", "id: perf\nname: {zh: x}\nversion: '1'\ncategory: testing\nicon: Gauge\norder: 1\n"
    )
    _write_manifest(
        tmp_path, "perf2", "id: perf\nname: {zh: y}\nversion: '1'\ncategory: testing\nicon: Gauge\norder: 2\n"
    )
    reg = ModuleRegistry()
    with pytest.raises(ManifestError):
        reg.scan(str(tmp_path))


def test_dependency_cycle_detected(tmp_path):
    _write_manifest(
        tmp_path,
        "a",
        "id: a\nname: {zh: a}\nversion: '1'\ncategory: testing\nicon: Gauge\norder: 1\n"
        "backend: {router: x:y, dependencies: [b]}\n",
    )
    _write_manifest(
        tmp_path,
        "b",
        "id: b\nname: {zh: b}\nversion: '1'\ncategory: testing\nicon: Gauge\norder: 2\n"
        "backend: {router: x:z, dependencies: [a]}\n",
    )
    reg = ModuleRegistry()
    with pytest.raises(ManifestError):
        reg.scan(str(tmp_path))


def test_topo_sort_resolves_dependencies(tmp_path):
    # a 依赖 b，所以 b 应该排在 a 前面
    _write_manifest(
        tmp_path,
        "a",
        "id: a\nname: {zh: a}\nversion: '1'\ncategory: testing\nicon: Gauge\norder: 1\n"
        "backend: {router: x:y, dependencies: [b]}\n",
    )
    _write_manifest(
        tmp_path,
        "b",
        "id: b\nname: {zh: b}\nversion: '1'\ncategory: testing\nicon: Gauge\norder: 2\n"
        "backend: {router: x:z, dependencies: []}\n",
    )
    reg = ModuleRegistry()
    reg.scan(str(tmp_path))
    ids = [lm.manifest.id for lm in reg.modules]
    assert ids.index("b") < ids.index("a")
