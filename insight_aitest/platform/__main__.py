# -*- coding: utf-8 -*-
"""平台命令行工具。

用法：
    python -m insight_aitest.platform validate-modules
"""

import argparse
import os
import sys

from insight_aitest.platform.module_registry import (
    ManifestError,
    ModuleLoadError,
    ModuleRegistry,
)


def main() -> int:
    parser = argparse.ArgumentParser(prog="insight-eyes-platform")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate-modules", help="校验所有模块 manifest 是否合法")

    args = parser.parse_args()

    if args.cmd == "validate-modules":
        modules_dir = os.path.join(os.path.dirname(__file__), "..", "modules")
        # 让 manifest 里的短路径 import（如 performance.backend.routes）可用
        modules_abs = os.path.abspath(modules_dir)
        if modules_abs not in sys.path:
            sys.path.insert(0, modules_abs)
        registry = ModuleRegistry()
        try:
            registry.scan(modules_dir)
            registry.resolve_backends()
        except (ManifestError, ModuleLoadError) as e:
            print(f"❌ 校验失败: {e}", file=sys.stderr)
            return 1
        print(f"✓ 校验通过，共 {len(registry.modules)} 个模块:")
        for lm in registry.modules:
            print(f"  - {lm.manifest.id} ({lm.manifest.version})")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
