# -*- coding: utf-8 -*-
"""content schema 校验测试。"""
from insight_aitest.modules.testcase.backend.generator.schemas import validate_content


def test_functional_valid():
    assert validate_content("functional", {
        "steps": [{"no": 1, "action": "点击登录"}], "expected": "成功"}) is True


def test_functional_missing_expected():
    assert validate_content("functional", {"steps": []}) is False


def test_functional_empty_expected():
    assert validate_content("functional", {"steps": [], "expected": ""}) is False


def test_functional_missing_steps():
    assert validate_content("functional", {"expected": "ok"}) is False


def test_api_valid():
    assert validate_content("api", {
        "base_url": "http://x", "steps": [{"method": "POST", "path": "/login"}]}) is True


def test_api_missing_base_url():
    assert validate_content("api", {"steps": []}) is False


def test_api_step_missing_method():
    # 每步应有明确 method（executor 默认 GET，但生成时应明确）
    assert validate_content("api", {
        "base_url": "http://x", "steps": [{"path": "/login"}]}) is False


def test_api_empty_steps():
    # 空 steps 仍合法（边界用例可以 0 步）
    assert validate_content("api", {"base_url": "http://x", "steps": []}) is True


def test_performance_valid():
    assert validate_content("performance", {"scenario": "滑动30秒"}) is True


def test_performance_missing():
    assert validate_content("performance", {"foo": "bar"}) is False


def test_ui_valid():
    assert validate_content("ui", {
        "base_url": "http://x", "steps": [{"kind": "action", "action": "点击登录"}]}) is True


def test_ui_missing_base_url():
    # 对齐 executor：base_url 必填
    assert validate_content("ui", {"steps": [{"action": "click"}]}) is False


def test_ui_missing_steps():
    assert validate_content("ui", {"base_url": "http://x", "foo": "bar"}) is False


def test_unknown_type():
    assert validate_content("unknown", {"steps": []}) is False
