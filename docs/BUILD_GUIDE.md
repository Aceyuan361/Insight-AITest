# Insight-Eye Windows 打包指南

本文档说明如何为 Insight-Eye 创建 Windows 安装包。

## 准备工作

### 1. 环境要求

- Python 3.8+
- pip 包管理器

### 2. 安装打包依赖

```bash
pip install pyinstaller==5.13.2
pip install -r insight_eyes/desktop/requirements.txt
```

### 3. 确认 ADB 可用

运行 `adb devices` 确认能识别设备。

## 打包流程

### 自动化打包

使用提供的打包脚本：

```bash
python build.py
```

脚本会自动完成以下步骤：
1. 清理旧的构建目录
2. 准备源代码
3. 使用 PyInstaller 构建可执行文件
4. 创建便携版包
5. 创建安装程序脚本

### 手动打包

如果需要手动控制打包过程：

```bash
# 1. 清理旧构建
rd /s /q build dist

# 2. 构建可执行文件
pyinstaller insight_eye.spec --clean

# 3. 测试可执行文件
dist\Insight-Eye\insight_eye.exe
```

## 打包配置

### 核心配置文件: `insight_eye.spec`

**关键配置说明**:

1. **数据文件**:
   - 包含 UI 样式文件 (`.qss`)
   - 包含默认配置文件
   - 排除测试文件和开发文件

2. **隐藏导入**:
   - PyQt6 核心模块
   - pyqtgraph 图表库
   - numpy, PIL 等依赖

3. **排除模块**:
   - tkinter, matplotlib 等不需要的库
   - 测试框架 (pytest, unittest)

4. **控制台**:
   - `console=True` - 保留控制台用于调试
   - 发布版本可改为 `False`

## 输出结构

### 便携版目录结构

```
Insight-Eye-Portable/
├── Insight-Eye.exe          # 主程序
├── 启动应用.bat             # 启动脚本
├── data/                   # 数据目录（自动创建）
├── logs/                   # 日志目录（自动创建）
└── README.txt              # 使用说明
```

### 安装包结构

```
dist/
├── Insight-Eye/
│   └── insight_eye.exe    # 可执行文件
├── Insight-Eye-Portable/    # 便携版完整包
└── installer/              # 安装脚本
    └── install.bat
```

## 文件过滤规则

### 需要排除的文件

**测试文件**:
- `test_*.py`
- `verify_*.py`
- `fix_*.py`
- `diagnose_*.py`
- `simple_test.py`
- `final_test.py`
- `quick_test*.py`
- `nul`

**开发文件**:
- `.agents/`
- `.claude/`
- `.pytest_cache/`
- `venv/`
- `*.pyc`

**临时文件**:
- `app.log`
- `crash_log.txt`
- `test_results.txt`
- `*.log`

**开发文档**（排除）:
- `docs/plans/`
- `docs/daily/`
- `agents/`

**保留的文档**:
- `docs/WINDOWS_INSTALLATION_GUIDE.md` - 用户安装指南
- `insight_eyes/desktop/README.md` - 架构说明
- `CLAUDE.md` - 项目文档（核心）

## 依赖处理

### 核心依赖

从 `insight_eyes/desktop/requirements.txt`:

```
PyQt6>=6.4.0
pyqtgraph>=0.13.0
numpy>=1.23.0
logzero>=1.7.0
pyinstaller>=5.13.0
```

### ADB 依赖

ADB 是外部工具，不包含在安装包中。用户需要单独安装。

## 测试清单

打包完成后，需要测试：

- [ ] 双击 `启动应用.bat` 能正常启动
- [ ] 应用界面正常显示
- [ ] 能识别 Android 设备
- [ ] 能枚举应用列表
- [ ] 能开始/停止监控
- [ ] 数据采集正常（CPU、内存、FPS、网络）
- [ ] 鼠标悬停显示数据
- [ ] 停止监控后面板清空
- [ ] 能导出数据
- [ ] 退出程序无错误

## 发布流程

### 1. 版本准备

1. 更新版本号（如需要）
2. 更新 CHANGELOG.md
3. 测试所有功能

### 2. 打包

```bash
python build.py
```

### 3. 测试安装包

1. 在干净的 Windows 10 系统上测试
2. 测试便携版
3. 测试安装程序
4. 测试所有核心功能

### 4. 分发

- 创建 GitHub Release
- 上传安装包到 Release 页面
- 更新下载链接

## 已知限制

1. **不含 ADB**: 用户需要单独安装
2. **Windows 专用**: 不支持 macOS/Linux
3. **Python 依赖**: 虽然打包了 Python，但仍需要兼容的运行时
4. **文件大小**: 完整安装包约 100-200MB

## 故障排除

### 打包失败

**问题**: PyInstaller 找不到模块
**解决**: 检查 `hiddenimports` 列表是否包含

**问题**: 打包后运行缺少 DLL
**解决**: 检查 `binaries` 是否包含所有依赖

**问题**: 打包文件过大
**解决**:
- 使用 UPX 压缩
- 排除不需要的模块
- 启用 `strip` 选项

### 运行问题

**问题**: 双击 exe 一闪而过
**解决**: 临时启用 `console=True` 查看错误

**问题**: 找不到数据文件
**解决**: 检查 `datas` 配置是否正确

**问题**: ADB 连接失败
**解决**: 确保用户安装了 ADB 并添加到 PATH

## 版本历史

- **v1.0.0** (2025-01-21): 初始 Windows 版本
