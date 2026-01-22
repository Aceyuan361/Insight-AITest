# -*- mode: python ; coding: utf-8 -*-
"""
Insight-Eye Windows 安装包配置文件

使用 PyInstaller 将 Python 应用打包为 Windows 可执行文件

生成命令:
    pyinstaller insight_eye.spec --clean

生成的安装包位置:
    dist/Insight-Eye/
"""
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ==================== 基本配置 ====================
a = Analysis(
    ['insight_eyes/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含 UI 样式文件
        ('insight_eyes/desktop/ui/styles.qss', 'insight_eyes/desktop/ui'),
        ('insight_eyes/desktop/ui/styles_improved.qss', 'insight_eyes/desktop/ui'),

        # 包含配置文件
        ('insight_eyes/desktop/config/default_config.json', 'insight_eyes/desktop/config'),

        # 包含图标资源（如果有）
        # ('insight_eyes/desktop/ui/resources', 'insight_eyes/desktop/ui/resources'),
    ],
    hiddenimports=[
        # PyQt6 相关
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',

        # pyqtgraph
        'pyqtgraph',
        'pyqtgraph.graphicsItems',
        'pyqtgraph.parametertypes',

        # 日志库
        'logzero',
        'logzero.handler',

        # 其他依赖
        'numpy',
        'PIL',
        'PIL._imaging',
        'PIL._binary',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={
        # 收集 PyQt6 插件
        'PyQt6.QtCore': '''
        from PyInstaller.utils.hooks import qt
        qt += ['PyQt6.QtCore']
        ''',
        'PyQt6.QtGui': '''
        from PyInstaller.utils.hooks import qt
        qt += ['PyQt6.QtGui']
        ''',
        'PyQt6.QtWidgets': '''
        from PyInstaller.utils.hooks import qt
        qt += ['PyQt6.QtWidgets']
        ''',

        # 收集 pyqtgraph 数据文件
        'pyqtgraph': '''
        from PyInstaller.utils.hooks import collect_data_files, collect_submodules
        collect_data_files('pyqtgraph.graphicsItems', include_py_files=True)
        ''',
    },
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'pytest',
        'unittest',
        'doctest',
        'email',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 过滤测试和分析模块（在 Analysis 后进行数据过滤）
a.datas = [x for x in a.datas if not any([
    'test_' in x[0].lower(),
    'verify_' in x[0].lower(),
    'fix_' in x[0].lower(),
    'diagnose_' in x[0].lower(),
    'simple_' in x[0].lower(),
    'quick_test' in x[0].lower(),
    'final_test' in x[0].lower(),
    'crash_log' in x[0].lower(),
    'debug_' in x[0].lower(),
])]

# 过滤测试和分析模块
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Insight-Eye',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台用于调试，发布时可改为 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: 添加图标文件
)

# 收集必要的 DLL 和数据文件
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Insight-Eye',
)
