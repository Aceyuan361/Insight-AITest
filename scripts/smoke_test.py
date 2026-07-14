# -*- coding: utf-8 -*-
"""子系统 A 冒烟测试：启动后端 → 调关键 API → 断言 → 关闭。

用法：先手动启动后端 (python -m insight_aitest)，再运行本脚本。
默认连 http://localhost:8001，可用环境变量 BASE_URL 覆盖。
"""
import json
import os
import sys
import urllib.request

BASE = os.getenv("BASE_URL", "http://localhost:8001")


def get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as r:
        return json.loads(r.read().decode())


def main() -> int:
    failures = []

    # 1. 平台健康
    try:
        assert get("/api/platform/health")["status"] == "healthy"
        print("OK /api/platform/health")
    except Exception as e:
        failures.append(f"/api/platform/health: {e}")

    # 2. 模块清单
    try:
        modules = get("/api/platform/modules")
        ids = {m["id"] for m in modules}
        assert "performance" in ids, f"performance 不在清单: {ids}"
        assert "example" in ids, f"example 不在清单: {ids}"
        assert "ai" in ids, f"ai 不在清单: {ids}"
        print(f"OK /api/platform/modules 含 {ids}")
    except Exception as e:
        failures.append(f"/api/platform/modules: {e}")

    # 3. 性能模块设备 API
    try:
        devices = get("/api/modules/performance/devices")
        assert isinstance(devices, list)
        print(f"OK /api/modules/performance/devices 返回 {len(devices)} 个设备")
    except Exception as e:
        failures.append(f"/api/modules/performance/devices: {e}")

    # 4. AI 模块健康 + 文档 API
    try:
        ai_health = get("/api/modules/ai/health")
        assert ai_health["status"] == "healthy"
        print("OK /api/modules/ai/health")
    except Exception as e:
        failures.append(f"/api/modules/ai/health: {e}")

    try:
        ai_docs = get("/api/modules/ai/documents")
        assert isinstance(ai_docs, list)
        print(f"OK /api/modules/ai/documents 返回 {len(ai_docs)} 个文档")
    except Exception as e:
        failures.append(f"/api/modules/ai/documents: {e}")

    if failures:
        print("\nFAIL 冒烟测试失败:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nPASS 冒烟测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
