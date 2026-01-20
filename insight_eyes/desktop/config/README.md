# Insight-Eye 配置持久化功能

## 概述

本模块为 Insight-Eye 项目提供了完整的配置持久化功能，支持自动保存、导入导出、恢复默认等操作。

## 功能特性

### 1. 配置数据结构

#### AppConfig
完整的应用配置，包含：
- **采集配置** (`CollectionConfig`): 采样间隔、监控指标开关、阈值设置
- **UI配置** (`UIConfig`): 窗口大小、面板布局、最近使用项目
- **设备配置** (`DeviceConfig`): 自动连接、自动监控、刷新设置
- **导出配置**: 导出格式、导出目录
- **告警配置**: 告警开关、声音、弹窗、最低级别

### 2. 配置管理器 (ConfigManager)

提供线程安全的配置管理：
- `save_config()` - 保存配置到 JSON 文件
- `load_config()` - 从文件加载配置
- `get_default_config()` - 获取默认配置
- `reset_to_default()` - 重置为默认值
- `export_config(file_path)` - 导出配置到指定文件
- `import_config(file_path)` - 从指定文件导入配置
- `backup_config()` - 创建配置备份
- `update_config(**kwargs)` - 更新指定配置项

### 3. 自动保存

- 配置修改后自动保存到文件
- 可在配置面板中启用/禁用自动保存
- 应用关闭时自动保存 UI 配置

### 4. 配置文件位置

- **Windows**: `C:\Users\用户名\.insight-eye\config.json`
- **macOS**: `/Users/用户名/.insight-eye/config.json`
- **Linux**: `/home/用户名/.insight-eye/config.json`

### 5. 配置导入/导出

- 通过主窗口菜单: 配置 -> 导出配置/导入配置
- 通过配置面板按钮: 恢复默认配置、导出配置、导入配置
- 支持导出为 JSON 格式

## 使用示例

### 基本使用

```python
from desktop.config.config_manager import get_config_manager

# 获取配置管理器实例（单例）
config_manager = get_config_manager()

# 加载配置
config = config_manager.load_config()

# 访问配置项
print(f"采样间隔: {config.collection.interval_ms}ms")
print(f"FPS阈值: {config.fps_threshold}")

# 更新配置
config_manager.update_config(
    fps_threshold=40,
    memory_threshold_mb=600
)

# 保存配置
config_manager.save_config()
```

### 导出配置

```python
# 导出到指定文件
config_manager.export_config('/path/to/config.json')
```

### 导入配置

```python
# 从文件导入
config_manager.import_config('/path/to/config.json')
```

### 重置为默认

```python
# 重置所有配置为默认值
config_manager.reset_to_default()
```

### 创建备份

```python
# 自动生成带时间戳的备份文件
backup_path = config_manager.backup_config()
print(f"备份已创建: {backup_path}")
```

## 配置项说明

### 采集配置 (CollectionConfig)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| interval_ms | int | 1000 | 采样间隔（毫秒）|
| enable_cpu | bool | true | 启用CPU监控 |
| enable_memory | bool | true | 启用内存监控 |
| enable_fps | bool | true | 启用FPS监控 |
| enable_network | bool | true | 启用网络监控 |
| enable_battery | bool | true | 启用电池监控 |
| enable_gpu | bool | false | 启用GPU监控 |
| fps_threshold | int | 30 | FPS告警阈值 |
| memory_threshold_mb | int | 500 | 内存告警阈值（MB）|
| cpu_threshold_percent | float | 80.0 | CPU告警阈值（%）|
| battery_threshold_temp | float | 45.0 | 电池温度告警阈值（℃）|

### UI配置 (UIConfig)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| window_width | int | 1600 | 窗口宽度 |
| window_height | int | 1000 | 窗口高度 |
| window_maximized | bool | false | 窗口最大化 |
| splitter_sizes | list | [280, 840, 280] | 面板分割比例 |
| recent_devices | list | [] | 最近设备列表 |
| recent_apps | list | [] | 最近应用列表 |
| show_grid_lines | bool | true | 显示网格线 |
| auto_scroll | bool | true | 自动滚动 |
| theme | string | "dark" | 主题 |

### 设备配置 (DeviceConfig)

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| auto_connect_last_device | bool | false | 自动连接上次设备 |
| last_connected_device | string/null | null | 上次连接的设备ID |
| auto_monitor_last_app | bool | false | 自动监控上次应用 |
| last_monitored_app | string/null | null | 上次监控的应用 |
| auto_refresh_interval | int | 5000 | 自动刷新间隔（ms）|
| auto_refresh_enabled | bool | false | 启用自动刷新 |

## 线程安全

配置管理器使用 `QMutex` 确保线程安全：
- 所有配置读写操作都通过锁保护
- 支持多线程并发访问配置

## 信号机制

配置管理器提供以下信号：

- `config_loaded(AppConfig)` - 配置加载完成
- `config_saved(AppConfig)` - 配置保存完成
- `config_changed(str, object)` - 配置项变更（键名，新值）

## 测试

运行单元测试：

```bash
python -m unittest desktop.tests.test_config_manager
```

测试覆盖：
- AppConfig 数据类测试
- UIConfig 数据类测试
- DeviceConfig 数据类测试
- ConfigManager 功能测试
- 单例模式测试
- 线程安全测试
- 集成测试

## 默认配置文件

参考 `default_config.json` 查看完整的默认配置示例。

## 注意事项

1. 配置文件使用 UTF-8 编码
2. 配置文件修改后会自动备份（带时间戳）
3. 导入配置会完全覆盖当前配置
4. 重置为默认配置不可撤销
5. 配置文件损坏时会自动使用默认配置

## 扩展

如需添加新的配置项：

1. 在对应的数据类中添加字段（`AppConfig`、`UIConfig`、`DeviceConfig`）
2. 更新 `to_dict()` 和 `from_dict()` 方法
3. 在 `get_default_config()` 中设置默认值
4. 添加相应的单元测试

## 维护者

- Aceyuan361

## 许可证

MIT License
