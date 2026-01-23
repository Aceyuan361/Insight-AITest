# 开发工作流和约定

## Data Flow Pattern（数据流模式）

所有采集器遵循统一的三层降级模式：

### 1. 主要方法（Primary Method）
尝试最精确、最可靠的采集方式。

### 2. 降级方案（Fallback Method）
主要方法失败时，尝试替代解析方式。

### 3. 默认值（Default Value）
全部失败时返回 0 或空字典，确保程序继续运行。

### 示例代码模式

```python
def collect_metric(self, device_id: str) -> dict:
    # 1. 尝试主要方法
    try:
        return self._primary_method(device_id)
    except Exception as e:
        logger.debug(f"主要方法失败: {e}")

    # 2. 尝试降级方案
    try:
        return self._fallback_method(device_id)
    except Exception as e:
        logger.warning(f"降级方案失败: {e}")

    # 3. 返回默认值
    return {'metric': 0}
```

---

## Thread Safety（线程安全）

### 数据锁使用

| 数据类型 | 锁类型 | 用途 |
|---------|--------|------|
| FPS 数据 | `_fps_data_lock` (RLock) | 帧率数据保护 |
| CPU 数据 | `_cpu_data_lock` (Lock) | CPU 数据保护 |

### Qt Signals 线程安全

- 使用 Qt signals 进行跨线程通信
- Signals 自动确保线程安全

### 数据库线程本地连接

- 每个线程使用独立的数据库连接
- 避免跨线程共享连接对象

---

## iOS 监控特殊约定

### 降级方案

iOS 监控受 pymobiledevice3 限制，部分指标使用降级方案：

| 指标 | 主要方法 | 降级方案 |
|-----|---------|---------|
| CPU | sysmon | psutil + top |
| Memory | sysmon | diagnostics 内存信息 |
| Energy | sysmon | diagnostics 能耗信息 |

### 超时设置

- sysmon 采集超时：**8 秒**
- 连接超时：**5 秒**

---

## Android 监控特殊约定

### CPUCollector 算法

**精确算法**（推荐）：
- 读取 `/proc/stat` 和 `/proc/[pid]/stat`
- 计算 delta 值（线程安全）

**降级方案**：
- 解析 `top -n 1` 输出
- 支持多核 CPU
- 支持小米设备 ANSI 过滤

---

## 错误处理约定

### 异常处理原则

1. **具体化**：捕获具体异常类型，避免裸 except
2. **日志记录**：所有异常必须记录日志
3. **降级处理**：遵循 Data Flow Pattern

### 示例

```python
# 好的异常处理
try:
    data = self._collect_via_adb(device_id)
except ADBTimeoutError as e:
    logger.warning(f"ADB 超时: {e}")
    return self._fallback_collect(device_id)
except ADBDeviceNotFoundError as e:
    logger.error(f"设备未找到: {e}")
    return {}

# 不好的异常处理
try:
    data = self._collect_via_adb(device_id)
except:  # 裸 except
    pass
```

---

## 测试约定

### 单元测试

```bash
pytest tests/
```

### 集成测试

```bash
python -m insight_eyes
```

---

## Git 提交约定

### Commit Message 格式

```
<type>: <subject>

<body>
```

### Type 类型

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试相关
- `debug`: 调试相关

### 示例

```
fix: 修复 iOS CPU 采集超时问题

增加 sysmon 采集超时时间至 8 秒，添加重试机制
```
