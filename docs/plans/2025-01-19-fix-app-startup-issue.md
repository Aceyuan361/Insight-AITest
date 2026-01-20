# 修复应用启动问题

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 修复 Insight-Eye 应用在 Windows 上启动时卡住的问题

**根本原因:** ConfigManager (继承自 QObject) 在 QApplication 之前被单例模式创建，导致 Qt 对象在没有 Qt 事件循环的情况下初始化失败

**技术栈:** PyQt6, Python 3.13, Windows

---

## 问题诊断结果

经过详细诊断，发现：
1. ConfigManager 继承自 QObject，需要 QApplication 存在才能正确初始化
2. ConfigPanel 在 __init__ 中调用 `get_config_manager()`
3. 模块导入时可能在 QApplication 之前就触发了 ConfigManager 单例创建
4. 导致应用卡在 MainWindow 初始化阶段

---

## Task 1: 修复 ConfigManager 的单例初始化时机

**文件:**
- Modify: `insight_eyes/desktop/config/config_manager.py`

**Step 1: 修改 ConfigManager 的 __new__ 方法**

将单例模式改为懒加载，避免在模块导入时创建实例：

```python
def __new__(cls):
    """实现单例模式（懒加载，仅在需要时创建）"""
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                # 不在这里创建实例，延迟到第一次调用时
                pass
    return cls._instance or super(ConfigManager, cls).__new__(cls)
```

**Step 2: 修改 __init__ 方法添加检查**

添加 QApplication 存在性检查：

```python
def __init__(self):
    """初始化配置管理器"""
    if self._initialized:
        return

    # 检查 QApplication 是否存在
    from PyQt6.QtWidgets import QApplication
    if QApplication.instance() is None:
        raise RuntimeError(
            "ConfigManager 必须在 QApplication 创建之后初始化。"
            "请确保先创建 QApplication 实例。"
        )

    super().__init__()
    self._initialized = True

    # 配置目录和文件路径
    self.config_dir = Path.home() / '.insight-eye'
    self.config_file = self.config_dir / 'config.json'

    # 当前配置
    self._config: Optional[AppConfig] = None

    # 确保配置目录存在
    self._ensure_config_dir()
```

**Step 3: 运行测试验证**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
python -c "
import sys
import os
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication
app = QApplication([])

from insight_eyes.desktop.config.config_manager import get_config_manager
manager = get_config_manager()
print(f'ConfigManager 创建成功: {manager}')
"
```

预期输出: `ConfigManager 创建成功: <insight_eyes.desktop.config.config_manager.ConfigManager object at 0x...>`

**Step 4: 提交修改**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
git add insight_eyes/desktop/config/config_manager.py
git commit -m "fix: 修复 ConfigManager 在 QApplication 之前创建的问题"
```

---

## Task 2: 修复 ConfigPanel 的延迟初始化

**文件:**
- Modify: `insight_eyes/desktop/ui/panels/config_panel.py`

**Step 1: 修改 ConfigPanel 的 __init__ 方法**

将 config_manager 的获取延迟到第一次使用时：

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.config = CollectionConfig()
    self.alerts: List[AlertRecord] = []
    self._config_manager = None  # 延迟初始化
    self.auto_save_enabled = False

    # 延迟自动保存定时器
    self._auto_save_timer = QTimer(self)
    self._auto_save_timer.setSingleShot(True)
    self._auto_save_timer.timeout.connect(self._auto_save_config)

    self._init_ui()
```

**Step 2: 添加 config_manager 属性**

```python
@property
def config_manager(self):
    """延迟获取配置管理器"""
    if self._config_manager is None:
        from ...config.config_manager import get_config_manager
        self._config_manager = get_config_manager()
    return self._config_manager
```

**Step 3: 运行测试验证**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
python -c "
import sys
import os
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication
app = QApplication([])

from insight_eyes.desktop.ui.panels.config_panel import ConfigPanel
panel = ConfigPanel()
print(f'ConfigPanel 创建成功')
"
```

预期输出: `ConfigPanel 创建成功`

**Step 4: 提交修改**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
git add insight_eyes/desktop/ui/panels/config_panel.py
git commit -m "fix: ConfigPanel 延迟初始化 config_manager"
```

---

## Task 3: 修复 MainWindow 的配置加载

**文件:**
- Modify: `insight_eyes/desktop/ui/main_window.py`

**Step 1: 修改 __init__ 中的 config_manager 初始化**

移除直接调用 `get_config_manager()`，改为延迟初始化：

```python
def __init__(self, debug_mode=False):
    super().__init__()

    # 调试模式
    self.debug_mode = debug_mode
    if self.debug_mode:
        logger.info("[主窗口] 调试模式已启用，将打印全链路日志")

    # 核心组件
    self.device_manager = DeviceManager()
    self._config_manager = None  # 延迟初始化

    # ... 其他初始化代码保持不变 ...

    # 初始化UI
    self._init_ui()
    self._connect_signals()
    self._setup_shortcuts()

    # 加载样式表
    self._load_styles()

    # 加载配置（延迟到 UI 创建后）
    self._load_app_config()

    # 刷新设备列表
    QTimer.singleShot(1000, self._refresh_devices)
```

**Step 2: 添加 config_manager 属性**

```python
@property
def config_manager(self):
    """延迟获取配置管理器"""
    if self._config_manager is None:
        from .config.config_manager import get_config_manager
        self._config_manager = get_config_manager()
    return self._config_manager
```

**Step 3: 运行测试验证**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
python -c "
import sys
import os
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication
from insight_eyes.desktop.ui.main_window import MainWindow

app = QApplication([])
window = MainWindow(debug_mode=True)
print(f'MainWindow 创建成功')
print(f'窗口标题: {window.windowTitle()}')
"
```

预期输出: `MainWindow 创建成功`

**Step 4: 提交修改**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
git add insight_eyes/desktop/ui/main_window.py
git commit -m "fix: MainWindow 延迟初始化 config_manager"
```

---

## Task 4: 验证完整应用启动

**文件:**
- Test: `test_startup_verification.py`

**Step 1: 创建验证测试脚本**

```python
# -*- coding: utf-8 -*-
"""完整应用启动验证"""
import sys
import os
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication
from insight_eyes.desktop.ui.main_window import MainWindow

print("=== 完整应用启动验证 ===")
print()

print("[1] 创建 QApplication...")
app = QApplication([])
print("    成功")

print()
print("[2] 创建 MainWindow...")
window = MainWindow(debug_mode=True)
print("    成功")

print()
print("[3] 显示窗口...")
window.show()
print("    成功")

print()
print("[4] 检查窗口属性...")
print(f"    标题: {window.windowTitle()}")
print(f"    大小: {window.size().width()}x{window.size().height()}")
print(f"    可见: {window.isVisible()}")

print()
print("=== 验证完成 ===")
print("应用启动成功！可以开始功能测试。")
```

**Step 2: 运行验证测试**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
python test_startup_verification.py
```

预期输出: 所有步骤成功，窗口显示

**Step 3: 提交测试脚本**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
git add test_startup_verification.py
git commit -m "test: 添加应用启动验证测试"
```

---

## Task 5: 更新启动脚本

**文件:**
- Modify: `run_debug.bat`

**Step 1: 简化启动脚本**

```batch
@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Insight-Eye 移动设备性能监控
echo ========================================
echo.

echo 启动应用...
python insight_eyes\desktop\run_app.py

if errorlevel 1 (
    echo.
    echo 启动失败！请检查错误信息。
    pause
)
```

**Step 2: 测试启动脚本**

双击运行 `run_debug.bat`，确认应用正常启动

**Step 3: 提交修改**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
git add run_debug.bat
git commit -m "fix: 简化启动脚本"
```

---

## Task 6: 集成测试

**文件:**
- Test: 使用现有的测试框架

**Step 1: 运行现有的集成测试**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
python -m pytest insight_eyes/desktop/tests/test_integration.py -v
```

预期输出: 所有测试通过

**Step 2: 运行 CPU 采集器测试**

验证我们的 CPU 采集器改进没有受到影响：

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
python -c "
from insight_eyes.public.android.cpu_collector import CPUCollector
print('CPU 采集器导入成功')

# 验证新方法存在
assert hasattr(CPUCollector, '_get_app_cpu_time_from_proc')
assert hasattr(CPUCollector, '_get_cpu_data_atomic')
assert hasattr(CPUCollector, '_parse_cpu_from_proc_stat')
print('新的 CPU 精确算法方法存在')
"
```

预期输出: CPU 采集器功能正常

**Step 3: 提交测试结果**

```bash
cd "C:\Users\86132\Desktop\收纳盒\性能工具\insight_eye\insight_eye-1.0.0"
git add docs/plans/2025-01-19-fix-app-startup-issue.md
git commit -m "docs: 完成应用启动修复计划"
```

---

## 总结

修复步骤：
1. ✅ 修复 ConfigManager 单例初始化时机
2. ✅ ConfigPanel 延迟初始化 config_manager
3. ✅ MainWindow 延迟初始化 config_manager
4. ✅ 验证完整应用启动
5. ✅ 更新启动脚本
6. ✅ 集成测试

核心改进：
- ConfigManager 现在会检查 QApplication 是否存在
- 使用属性 (@property) 实现延迟加载
- 避免在模块导入时创建 Qt 对象

验证标准：
- 应用可以在 Windows 上正常启动
- CPU 采集器功能不受影响
- 所有现有测试通过
