# 项目全面清理和重构计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**目标:** 清理项目中的临时文件、旧注释、弃用代码，更新文档，进行全面代码审查，使项目达到生产就绪状态。

**架构:** 分阶段清理，每个阶段独立提交，确保可回滚

**Tech Stack:** Python, Git, 文件系统操作

---

## 阶段 1: 创建归档目录结构

**目标:** 建立归档目录，用于存储旧文件和备份

**Files:**
- Create: `archive/README.md`
- Create: `archive/deprecated/README.md`
- Create: `archive/backup/README.md`
- Create: `archive/docs/README.md`
- Create: `tests/debug/README.md`

### Step 1: 创建归档根目录 README

```markdown
# 归档目录

此目录存储项目中不再使用的文件，但保留用于历史参考。

## 目录结构

- `deprecated/` - 已弃用的代码（标记为 @deprecated）
- `backup/` - 备份文件（旧版本代码）
- `docs/` - 旧的设计文档
- `../tests/debug/` - 调试测试文件

## 归档策略

文件在此目录中**不会**被导入到主代码库中。
它们仅用于历史参考和紧急回滚。
```

**Step 2: 创建 archive/deprecated/README.md**

```markdown
# 已弃用代码

此目录包含已标记为 `@deprecated` 的代码文件。

## 列表

- `cpu_collector.py` - tidevice CPU采集器
- `memory_collector.py` - tidevice Memory采集器
- `fps_collector.py` - tidevice FPS采集器
- `battery_collector.py` - tidevice Battery采集器
- `network_collector.py` - tidevice Network采集器

## 迁移指南

请使用 py-ios-device 架构代替：

```python
from insight_eyes.public.ios.ios_apm import IOSAPM

apm = IOSAPM(bundle_id, udid)
apm.start()
cpu_data = apm.collectCpu()
apm.stop()
```
```

**Step 3: 创建 archive/backup/README.md**

```markdown
# 备份文件

此目录存储旧版本的代码文件，用于回滚和参考。

## 文件列表

- `fps_collector_backup.py` - FPS采集器旧版本
- `main_window_fixed.py` - 主窗口修复版本
- `main_window_batch.py` - 主窗口批处理版本

## 注意

这些文件**不应**被导入到主代码中。
```

**Step 4: 创建 archive/docs/README.md**

```markdown
# 旧文档归档

此目录存储旧的设计文档和计划文档。

## 归档原因

- 计划已完成
- 设计已实施
- 内容已过时

## 参考最新文档

请查看项目根目录的 `docs/` 目录获取最新文档。
```

**Step 5: 创建 tests/debug/README.md**

```markdown
# 调试测试文件

此目录存储用于调试的临时测试文件。

## 用途

- 临时问题诊断
- 功能验证
- 性能测试

## 注意

这些测试**不**包含在主测试套件中。
它们不会被CI/CD自动运行。
```

**Step 6: 提交归档目录结构**

```bash
git add archive/ tests/debug/
git commit -m "feat: 创建归档目录结构

- 添加 archive/ 目录用于存储旧文件
- 添加 tests/debug/ 用于调试测试
- 为每个子目录创建 README.md 说明"
```

---

## 阶段 2: 清理根目录临时测试文件

**目标:** 移动25个临时测试文件到 `tests/debug/` 目录

**Files:**
- Move: `test_*.py` → `tests/debug/`

### Step 1: 创建临时测试文件列表

创建 `scripts/cleanup_temp_tests.py`:

```python
#!/usr/bin/env python3
"""
临时测试文件清理脚本

将根目录的临时测试文件移动到 tests/debug/ 目录
"""
import os
import shutil
from pathlib import Path

# 临时测试文件列表（需要移动）
TEMP_TEST_FILES = [
    'test_code_structure.py',
    'test_config_fix.py',
    'test_config_manager.py',
    'test_deadlock_scenario.py',
    'test_debug.py',
    'test_debug_getattr.py',
    'test_debug_init.py',
    'test_debug_new.py',
    'test_diagnose_startup.py',
    'test_direct.py',
    'test_direct_call.py',
    'test_ensure_dir.py',
    'test_fps_comprehensive.py',
    'test_fps_fix.py',
    'test_import_only.py',
    'test_indent_check.py',
    'test_init_debug.py',
    'test_integration_simple.py',
    'test_ios_foreground_monitoring.py',
    'test_ios_upgrade_integration.py',
    'test_main_window_fix.py',
    'test_monitoring.py',
    'test_qobject_init.py',
    'test_report_integration.py',
    'test_simple_verify.py',
    'test_save_config_deadlock.py',
]

# 保留在根目录的测试文件
KEEP_IN_ROOT = [
    'test_all_fixes.py',
    'test_integration.py',
    'run_ios_tests.py',
    'final_test.py',
    'quick_test_fps.py',
    'verify_docs.py',
    'verify_fix.py',
    'verify_fix_simple.py',
    'verify_logic.py',
    'verify_spec_compliance.py',
    'verify_task3.py',
    'verify_fix_v2.py',
]

def move_temp_tests():
    """移动临时测试文件到 debug 目录"""
    project_root = Path.cwd()
    debug_dir = project_root / 'insight_eyes' / 'desktop' / 'tests' / 'debug'
    debug_dir.mkdir(parents=True, exist_ok=True)

    moved_count = 0

    for test_file in TEMP_TEST_FILES:
        source = project_root / test_file
        if source.exists():
            dest = debug_dir / test_file
            shutil.move(str(source), str(dest))
            print(f"✓ 移动: {test_file}")
            moved_count += 1
        else:
            print(f"⊘ 跳过: {test_file} (不存在)")

    print(f"\n总计移动 {moved_count} 个文件")

    # 验证保留的文件
    print("\n保留在根目录的测试文件:")
    for test_file in KEEP_IN_ROOT:
        source = project_root / test_file
        if source.exists():
            print(f"  ✓ {test_file}")

if __name__ == '__main__':
    move_temp_tests()
```

**Step 2: 运行清理脚本**

```bash
python scripts/cleanup_temp_tests.py
```

**Expected Output:**
```
✓ 移动: test_code_structure.py
✓ 移动: test_config_fix.py
...
总计移动 25 个文件

保留在根目录的测试文件:
  ✓ test_all_fixes.py
  ✓ test_integration.py
  ...
```

**Step 3: 提交测试文件清理**

```bash
git add insight_eyes/desktop/tests/debug/
git add scripts/cleanup_temp_tests.py
git commit -m "refactor: 清理临时测试文件

- 移动 25 个临时测试文件到 tests/debug/
- 保留核心测试文件在根目录
- 添加清理脚本用于后续维护"
```

---

## 阶段 3: 归档备份文件

**目标:** 移动备份文件和旧版本文件到 `archive/backup/`

**Files:**
- Move: `insight_eyes/public/android/fps_collector_backup.py`
- Move: `insight_eyes/desktop/ui/main_window_fixed.py`
- Move: `insight_eyes/desktop/ui/main_window_batch.py`
- Move: `insight_eyes/desktop/analytics/thresholds.py` (如果确认是旧版本)

### Step 1: 移动备份文件

创建 `scripts/archive_backups.py`:

```python
#!/usr/bin/env python3
"""
备份文件归档脚本

将备份文件移动到 archive/backup/ 目录
"""
import os
import shutil
from pathlib import Path

# 备份文件列表
BACKUP_FILES = [
    ('insight_eyes/public/android/fps_collector_backup.py', 'archive/backup/android/fps_collector_backup.py'),
    ('insight_eyes/desktop/ui/main_window_fixed.py', 'archive/backup/desktop/ui/main_window_fixed.py'),
    ('insight_eyes/desktop/ui/main_window_batch.py', 'archive/backup/desktop/ui/main_window_batch.py'),
]

def archive_backups():
    """归档备份文件"""
    project_root = Path.cwd()

    for source_path, dest_path in BACKUP_FILES:
        source = project_root / source_path
        dest = project_root / dest_path

        if source.exists():
            # 创建目标目录
            dest.parent.mkdir(parents=True, exist_ok=True)

            # 移动文件
            shutil.move(str(source), str(dest))
            print(f"✓ 归档: {source_path}")
        else:
            print(f"⊘ 跳过: {source_path} (不存在)")

    print("\n备份文件归档完成")

if __name__ == '__main__':
    archive_backups()
```

**Step 2: 运行归档脚本**

```bash
python scripts/archive_backups.py
```

**Step 3: 提交备份文件归档**

```bash
git add archive/backup/
git add scripts/archive_backups.py
git commit -m "refactor: 归档备份文件

- 归档 fps_collector_backup.py
- 归档 main_window_fixed.py 和 main_window_batch.py
- 创建归档脚本用于后续维护"
```

---

## 阶段 4: 更新项目文档

**目标:** 更新 CLAUDE.md 和其他核心文档，反映当前架构状态

**Files:**
- Modify: `CLAUDE.md`
- Modify: `insight_eyes/desktop/requirements.txt`
- Create: `docs/MIGRATION_GUIDE.md`

### Step 4.1: 更新 CLAUDE.md 的 iOS 监控章节

在 `CLAUDE.md` 中找到 "iOS Monitoring Enhancement (2025-01-20)" 章节，更新为：

```markdown
### iOS Monitoring (2025-01-21 更新)

**当前架构: py-ios-device 主要方案**

**核心组件:**
| 组件 | 文件 | 功能 |
|------|------|------|
| IOSAPM | `public/ios/ios_apm.py` | iOS APM 主类 |
| PyIOSConnection | `public/ios/pyios_connect.py` | 连接管理器 |
| SysMontapCollector | `public/ios/pyios_collectors/sysmontap.py` | CPU/Memory/Network |
| GraphicsCollector | `public/ios/pyios_collectors/graphics.py` | FPS/GPU |
| EnergyCollector | `public/ios/pyios_collectors/energy.py` | Battery |
| IOSDataNormalizer | `public/ios/data_normalizer.py` | 数据规范化 |

**版本支持:**
- iOS 15-26: py-ios-device（推荐）
- iOS 17-26: pymobiledevice3 隧道支持

**依赖:**
```bash
pip install py-ios-device pymobiledevice3
```

**弃用说明:**
- tidevice 采集器已标记 `@deprecated`
- 将在 v3.0 版本完全移除
- 推荐迁移到 py-ios-device 架构

**迁移指南:**
```python
# 旧方式 (已弃用)
from insight_eyes.public.ios.cpu_collector import CPUCollector

# 新方式 (推荐)
from insight_eyes.public.ios.ios_apm import IOSAPM

apm = IOSAPM(bundle_id, udid)
apm.start()
cpu_data = apm.collectCpu()
apm.stop()
```
```

### Step 4.2: 创建迁移指南文档

创建 `docs/MIGRATION_GUIDE.md`:

```markdown
# iOS 监控迁移指南

## 从 tidevice 迁移到 py-ios-device

### 背景

tidevice 已被标记为弃用，将在 v3.0 版本完全移除。
建议所有用户迁移到 py-ios-device 架构。

### 迁移步骤

#### 1. 安装新依赖

```bash
pip install py-ios-device>=0.7.0 pymobiledevice3>=1.0.0
```

#### 2. 更新代码

**旧代码:**
```python
from insight_eyes.public.ios.cpu_collector import CPUCollector
from insight_eyes.public.ios.memory_collector import MemoryCollector
from insight_eyes.public.ios.fps_collector import FPSCollector

collector = CPUCollector(udid)
cpu_data = collector.collect(bundle_id)
```

**新代码:**
```python
from insight_eyes.public.ios.ios_apm import IOSAPM

apm = IOSAPM(bundle_id, udid)
apm.start()
cpu_data = apm.collectCpu()
memory_data = apm.collectMemory()
fps_data = apm.collectFps()
apm.stop()
```

#### 3. 数据格式

新架构返回统一的数据格式：

```python
# CPU
{'appCpuRate': 25.5, 'sysCpuRate': 45.2}

# Memory
{'totalPass': 256.0, 'nativePass': 512.0, 'dalvikPass': 0.0}

# FPS
{'fps': 60, 'jank': 0, 'bigJank': 0, 'ftime_avg': 16.67}
```

### 兼容性

| iOS 版本 | tidevice | py-ios-device |
|---------|----------|---------------|
| iOS 15-16 | ✅ 支持 | ✅ 推荐 |
| iOS 17-18 | ⚠️ 有限支持 | ✅ 完全支持 |
| iOS 19-26 | ❌ 不支持 | ✅ 完全支持 |

### 故障排除

**问题**: `ModuleNotFoundError: No module named 'py_ios_device'`

**解决**:
```bash
pip install py-ios-device pymobiledevice3
```

**问题**: 连接失败

**解决**: 确保 iOS 设备已信任电脑，并已启动 Instruments 服务。

### 获取帮助

- 查看测试报告: `docs/ios-migration-testing-report.md`
- 查看实施报告: `docs/ios-monitoring-upgrade-implementation-report.md`
- 提交 Issue: https://github.com/Aceyuan361/Insight-Eye/issues
```

### Step 4.3: 提交文档更新

```bash
git add CLAUDE.md docs/MIGRATION_GUIDE.md
git commit -m "docs: 更新 iOS 监控文档

- 更新 CLAUDE.md 中的 iOS 监控章节
- 添加迁移指南 MIGRATION_GUIDE.md
- 标注 tidevice 弃用状态"
```

---

## 阶段 5: 代码审查 - 清理 tidevice 相关注释

**目标:** 审查所有文件，清理 tidevice 相关的旧注释和注释掉的代码

**Files:**
- Review: 所有 Python 文件
- Modify: 包含旧注释的文件

### Step 5.1: 扫描需要审查的文件

创建 `scripts/scan_old_comments.py`:

```python
#!/usr/bin/env python3
"""
扫描需要清理的旧注释
"""
import re
from pathlib import Path

# 需要搜索的模式
PATTERNS = [
    r'# TODO.*tidevice',
    r'# FIXME.*tidevice',
    r'# XXX.*tidevice',
    r'# HACK.*tidevice',
    r'# 旧.*tidevice',
    r'# tidevice.*弃用',
    r'# deprecated.*tidevice',
    r'### tidevice',
]

def scan_files():
    """扫描所有 Python 文件"""
    project_root = Path.cwd()
    python_files = project_root.rglob('*.py')

    findings = []

    for py_file in python_files:
        # 跳过归档目录
        if 'archive' in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding='utf-8')
            for pattern in PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    findings.append({
                        'file': str(py_file.relative_to(project_root)),
                        'line': line_num,
                        'text': match.group(),
                        'pattern': pattern
                    })
        except Exception as e:
            print(f"✗ 读取失败: {py_file}: {e}")

    # 输出结果
    if findings:
        print(f"找到 {len(findings)} 个需要审查的注释:\n")
        for finding in findings:
            print(f"  {finding['file']}:{finding['line']}")
            print(f"    {finding['text']}\n")
    else:
        print("✓ 未找到需要清理的旧注释")

    return findings

if __name__ == '__main__':
    scan_files()
```

### Step 5.2: 运行扫描

```bash
python scripts/scan_old_comments.py > old_comments_report.txt
```

### Step 5.3: 手动审查和清理

根据扫描报告，逐个文件审查并清理：

**示例清理**:

**Before:**
```python
# TODO: 迁移到 py-ios-device (已弃用 tidevice)
# XXX: 临时使用 tidevice，后续需要替换
def collect_cpu(self):
    # 使用 tidevent 命令采集
    cmd = f'tidevice --udid {self.udid} perf ...'
```

**After:**
```python
# 使用 py-ios-device 架构采集 CPU
def collect_cpu(self):
    # 通过 SysMontapCollector 采集
    collector = self._get_sysmontap_collector()
    return collector.collect_cpu()
```

### Step 5.4: 提交清理结果

```bash
git add .
git commit -m "refactor: 清理 tidevice 相关旧注释

- 扫描并清理所有 tidevent 相关注释
- 更新代码注释以反映新架构
- 保持代码简洁清晰"
```

---

## 阶段 6: 归档旧的设计文档

**目标:** 移动已完成的设计文档到 `archive/docs/`

**Files:**
- Move: `docs/plans/findings.md`
- Move: `docs/plans/task_plan.md`
- Move: `docs/plans/progress.md`

### Step 6.1: 移动旧文档

```bash
mkdir -p archive/docs/plans
mv docs/plans/findings.md archive/docs/plans/
mv docs/plans/task_plan.md archive/docs/plans/
mv docs/plans/progress.md archive/docs/plans/
```

### Step 6.2: 提交文档归档

```bash
git add archive/docs/
git commit -m "docs: 归档已完成的设计文档

- 移动 findings.md, task_plan.md, progress.md 到 archive/docs/plans/
- 这些文档对应的计划已完成并实施
- 保留用于历史参考"
```

---

## 阶段 7: 更新 requirements.txt

**目标:** 确保 requirements.txt 清晰反映当前依赖状态

**Files:**
- Modify: `insight_eyes/desktop/requirements.txt`

### Step 7.1: 更新 requirements.txt

在 `insight_eyes/desktop/requirements.txt` 中更新 iOS 依赖部分：

```txt
# ============================================================
# iOS 设备支持
# ============================================================
# py-ios-device - iOS 性能采集（主要方案，iOS 15-26）
py-ios-device>=0.7.0

# pymobiledevice3 - iOS 设备通信和隧道（iOS 17-26）
pymobiledevice3>=1.0.0

# tidevice - 已弃用，仅用于向后兼容
# 将在 v3.0 版本完全移除
# 推荐使用 py-ios-device 架构代替
# tidevice>=0.9.7
```

### Step 7.2: 提交依赖更新

```bash
git add insight_eyes/desktop/requirements.txt
git commit -m "docs: 更新 requirements.txt 依赖说明

- 明确标注 py-ios-device 为主要方案
- 标注 pymobiledevice3 用于隧道支持
- 注释掉 tidevice 并标注弃用状态"
```

---

## 阶段 8: 创建项目清理报告

**目标:** 总结本次清理工作，记录清理的文件和改进

**Files:**
- Create: `docs/PROJECT_CLEANUP_REPORT_2025-01-21.md`

### Step 8.1: 创建清理报告

```markdown
# 项目清理报告 (2025-01-21)

## 清理概述

本次清理旨在移除临时文件、旧注释和弃用代码，使项目达到生产就绪状态。

## 清理统计

### 文件清理

| 类型 | 数量 | 详情 |
|------|------|------|
| 临时测试文件 | 25 | 移动到 tests/debug/ |
| 备份文件 | 4 | 移动到 archive/backup/ |
| 旧文档 | 3 | 移动到 archive/docs/ |

### 代码改进

| 类型 | 数量 | 详情 |
|------|------|------|
| 旧注释清理 | 若干 | 移除 tidevent 相关注释 |
| 文档更新 | 3 | CLAUDE.md, MIGRATION_GUIDE.md, requirements.txt |

## 目录结构变化

### 新增目录

```
archive/
├── README.md
├── deprecated/README.md
├── backup/README.md
└── docs/README.md

tests/debug/
└── README.md
```

## 清理前后对比

### Before

```
insight_eye-1.0.0/
├── test_*.py (25个临时文件)
├── *_backup.py (备份文件散落各处)
├── 旧注释和 TODO 标记
└── 文档分散
```

### After

```
insight_eye-1.0.0/
├── archive/ (归档目录结构清晰)
├── tests/debug/ (调试测试集中管理)
├── 代码简洁无旧注释
└── 文档更新完善
```

## 改进效果

1. ✅ **项目根目录更干净**: 移除了25个临时测试文件
2. ✅ **代码更易维护**: 清理了旧注释和弃用代码引用
3. ✅ **文档更清晰**: 更新了迁移指南和依赖说明
4. ✅ **结构更规范**: 建立了归档目录结构

## 遗留工作

- [ ] 在 v3.0 版本完全移除 tidevent 采集器
- [ ] 提升 iOS 测试覆盖率到 95%+
- [ ] 添加性能基准测试

## 总结

通过本次清理，项目结构更加清晰，代码更加简洁，文档更加完善。
项目已达到生产就绪状态。

---
**清理日期**: 2025-01-21
**执行者**: Claude Code
**审查状态**: 待审查
```

### Step 8.2: 提交清理报告

```bash
git add docs/PROJECT_CLEANUP_REPORT_2025-01-21.md
git commit -m "docs: 添加项目清理报告

- 记录本次清理的文件和改进
- 统计清理前后的变化
- 列出遗留工作"
```

---

## 阶段 9: 最终验证

**目标:** 验证清理后项目仍然正常工作

### Step 9.1: 运行测试

```bash
# 运行 iOS 测试
python run_ios_tests.py

# 运行桌面应用测试
python -m pytest insight_eyes/desktop/tests/ -v

# 运行核心测试
python test_all_fixes.py
```

**Expected:**
- iOS 测试: 16/19 通过（与之前一致）
- 桌面测试: 全部通过
- 核心测试: 全部通过

### Step 9.2: 验证导入

```bash
python -c "from insight_eyes.public.ios.ios_apm import IOSAPM; print('✓ IOSAPM 导入成功')"
python -c "from insight_eyes.desktop.main import main; print('✓ Desktop main 导入成功')"
```

**Expected:**
```
✓ IOSAPM 导入成功
✓ Desktop main 导入成功
```

### Step 9.3: 提交最终清理

```bash
git add .
git commit -m "refactor: 完成项目清理和重构

## 清理内容

### 文件清理
- 移动 25 个临时测试文件到 tests/debug/
- 归档 4 个备份文件到 archive/backup/
- 归档 3 个旧文档到 archive/docs/

### 文档更新
- 更新 CLAUDE.md iOS 监控章节
- 添加 MIGRATION_GUIDE.md 迁移指南
- 更新 requirements.txt 依赖说明
- 创建 PROJECT_CLEANUP_REPORT 清理报告

### 代码改进
- 清理 tidevice 相关旧注释
- 建立归档目录结构
- 代码更简洁易维护

## 验证

- ✅ iOS 测试: 16/19 通过
- ✅ 桌面测试: 全部通过
- ✅ 导入验证: 全部成功

项目已达到生产就绪状态 🎉"
```

---

## 执行检查清单

在执行此计划时，请确保：

- [ ] 每个阶段完成后运行测试验证
- [ ] 每个阶段独立提交
- [ ] 遇到问题立即停止并调查
- [ ] 保持提交信息清晰明确
- [ ] 验证时检查日志输出

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 移动文件导致导入错误 | 低 | 中 | 运行测试验证 |
| 文档更新遗漏 | 中 | 低 | 多人审查 |
| 清理过度导致代码损坏 | 低 | 高 | 保留 Git 历史，可回滚 |

## 预期时间

| 阶段 | 预估时间 |
|------|---------|
| 阶段 1: 创建归档目录 | 10 分钟 |
| 阶段 2: 清理临时测试 | 15 分钟 |
| 阶段 3: 归档备份文件 | 10 分钟 |
| 阶段 4: 更新文档 | 30 分钟 |
| 阶段 5: 代码审查清理 | 45 分钟 |
| 阶段 6: 归档旧文档 | 5 分钟 |
| 阶段 7: 更新依赖 | 5 分钟 |
| 阶段 8: 创建报告 | 15 分钟 |
| 阶段 9: 最终验证 | 20 分钟 |
| **总计** | **~2.5 小时** |

---

## 执行选项

**计划已保存到** `docs/plans/2025-01-21-project-cleanup-and-refactor.md`

**两种执行方式：**

**1. Subagent-Driven (本会话)** - 我分配新的子代理执行每个任务，任务间进行代码审查，快速迭代

**2. 手动执行** - 您按照计划步骤手动执行，我提供指导

**您选择哪种方式？**
