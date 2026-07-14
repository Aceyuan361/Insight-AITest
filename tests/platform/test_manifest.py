# -*- coding: utf-8 -*-
import pytest
from pydantic import ValidationError
from insight_aitest.modules._registry.manifest import (
    ModuleManifest,
    FrontendSpec,
    NavSpec,
)


def test_minimal_valid_manifest():
    m = ModuleManifest(
        id="performance",
        name={"zh": "性能监控", "en": "Performance"},
        version="2.0.0",
        category="testing",
        icon="Gauge",
        order=1,
        frontend=FrontendSpec(
            route="/performance",
            entry="performance:PerformanceApp",
            nav=NavSpec(label={"zh": "性能", "en": "Perf"}, icon="Gauge"),
        ),
    )
    assert m.id == "performance"
    assert m.default_enabled is True


def test_invalid_id_rejected():
    with pytest.raises(ValidationError):
        ModuleManifest(
            id="Bad ID!",
            name={"zh": "x"},
            version="1.0.0",
            category="testing",
            icon="Gauge",
            order=1,
        )


def test_invalid_category_rejected():
    with pytest.raises(ValidationError):
        ModuleManifest(
            id="ok",
            name={"zh": "x"},
            version="1.0.0",
            category="bogus",
            icon="Gauge",
            order=1,
        )


def test_name_requires_at_least_one_lang():
    with pytest.raises(ValidationError):
        ModuleManifest(
            id="ok",
            name={},
            version="1.0.0",
            category="testing",
            icon="Gauge",
            order=1,
        )


def test_route_must_start_with_slash():
    with pytest.raises(ValidationError):
        ModuleManifest(
            id="ok",
            name={"zh": "x"},
            version="1.0.0",
            category="testing",
            icon="Gauge",
            order=1,
            frontend=FrontendSpec(
                route="noleadingslash",
                entry="ok:Ok",
                nav=NavSpec(label={"zh": "x"}, icon="Gauge"),
            ),
        )
