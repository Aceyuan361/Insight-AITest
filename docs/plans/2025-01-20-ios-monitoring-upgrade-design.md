# iOS 17+ 性能监控升级设计方案

## 一、方案概述

### 背景
当前 iOS 监控使用 `tidevice` 工具，存在以下问题：
- iOS 17+ 设备支持有限
- 数据解析不准确
- Network、Battery 指标未实现
- FPS 缺少卡顿检测

### 解决方案
采用 **py-ios-device + pymobiledevice3** 的混合架构：
- **pymobiledevice3**: 建立 iOS 17+ 远程隧道连接
- **py-ios-device**: 实现 Instruments 协议通信
- **tidevice**: 作为降级方案（iOS < 17）

### 核心特性
1. **混合模式**：根据 iOS 版本自动选择最佳采集方案
2. **优雅降级**：依赖不可用时自动降级到 tidevice
3. **统一接口**：对上层完全透明，无需修改调用代码
4. **可选依赖**：不影响现有用户，按需安装

---

## 二、架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────┐
│              IOSAPM (统一门面)                       │
│  collectCpu() / collectMemory() / collectFps()...  │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│         IOSCollectorFactory (工厂)                  │
│  - create_collector(udid, ios_version)             │
│  - 检测 py-ios-device 可用性                        │
│  - iOS 17+ 优先用 PyIOSDevice，降级用 Tidevice      │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│      IOSCollectorAdapter (统一接口适配器)            │
│  - collect_cpu(bundle_id)                           │
│  - collect_memory(bundle_id)                        │
│  - collect_fps(bundle_id)                           │
│  - collect_network(bundle_id)                       │
│  - collect_battery()                                │
│  - collect_gpu()                                    │
└──────────────────────┬──────────────────────────────┘
                       │
           ┌───────────┴───────────┐
           ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│ PyIOSDeviceCollector│    │  TideviceCollector  │
│ (iOS 17+ 优化)   │    │  (iOS <17 降级)    │
└──────────────────┘    └──────────────────┘
```

### 设计模式

1. **工厂模式**：根据 iOS 版本和依赖可用性创建采集器
2. **适配器模式**：统一不同采集方案的接口
3. **策略模式**：运行时可切换采集方案
4. **单例模式**：连接管理器确保只有一个活跃连接

---

## 三、核心组件设计

### 1. IOSDependencyChecker（依赖检测器）

```python
class IOSDependencyChecker:
    """iOS 依赖检测器"""

    @staticmethod
    def check_pyios_device() -> bool:
        """检查 py-ios-device 是否可用"""

    @staticmethod
    def check_pymobiledevice3() -> bool:
        """检查 pymobiledevice3 是否可用"""

    @staticmethod
    def suggest_ios_full_support():
        """提示用户安装完整 iOS 支持"""
```

### 2. PyIOSConnection（连接管理器）

```python
class PyIOSConnection:
    """
    py-ios-device 连接管理器

    职责：
    1. 管理远程隧道连接
    2. 维护 InstrumentServer 会话
    3. 提供单次调用的采集接口（兼容 tidevice 模式）
    4. 自动重连和健康检查
    """

    def __init__(self, udid: str, remote_address: tuple):
        self.udid = udid
        self.remote_address = remote_address
        self._rsd = None  # RemoteLockdownClient
        self._rpc = None  # InstrumentServer
        self._last_use = time.time()

    def connect(self) -> bool:
        """建立连接"""

    def is_alive(self) -> bool:
        """检查连接是否存活"""

    def collect_cpu(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """单次 CPU 采集（兼容接口）"""

    def collect_memory(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """单次 Memory 采集（兼容接口）"""

    def collect_fps(self, bundle_id: str) -> Optional[Dict[str, Any]]:
        """单次 FPS 采集（兼容接口）"""

    def disconnect(self):
        """断开连接"""
```

### 3. IOSDataNormalizer（数据规范化器）

```python
class IOSDataNormalizer:
    """iOS 数据格式规范化"""

    @staticmethod
    def normalize_cpu(raw_data: Any) -> Dict[str, Any]:
        """
        统一 CPU 数据格式

        Tidevice 返回: {'appCpuRate': 15.2, 'sysCpuRate': 35.8}
        PyIOS 返回: {'cpuUsage': 15.2, ...}

        统一输出: {'appCpuRate': float, 'sysCpuRate': float}
        """

    @staticmethod
    def normalize_memory(raw_data: Any) -> Dict[str, Any]:
        """
        统一 Memory 数据格式

        统一输出: {
            'totalPass': float,
            'nativePass': float,
            'dalvikPass': float
        }
        """

    @staticmethod
    def normalize_fps(raw_data: Any) -> Dict[str, Any]:
        """
        统一 FPS 数据格式

        统一输出: {
            'fps': int,
            'jank': int,
            'bigJank': int,
            'ftime_avg': float,
            'ftime_max': float,
            'ftime_min': float
        }
        """

    @staticmethod
    def normalize_network(raw_data: Any) -> Dict[str, Any]:
        """
        统一 Network 数据格式

        统一输出: {'upFlow': float, 'downFlow': float}
        """

    @staticmethod
    def normalize_battery(raw_data: Any) -> Dict[str, Any]:
        """
        统一 Battery 数据格式

        统一输出: {
            'level': int,
            'temperature': float,
            'current': float,
            'voltage': float,
            'power': float,
            'status': str
        }
        """

    @staticmethod
    def normalize_gpu(raw_data: Any) -> Dict[str, Any]:
        """
        统一 GPU 数据格式

        统一输出: {
            'gpu': int,
            'gpu_freq': int,
            'gpu_vendor': str,
            'gpu_model': str
        }
        """
```

### 4. IOSDeviceAdapter 增强

```python
class IOSDeviceAdapter(BaseDeviceAdapter):
    """
    iOS设备适配器（增强版）

    新增功能：
    - iOS 版本自动检测
    - 采集方案自动选择（py-ios-device / tidevice）
    - 连接生命周期管理
    - 优雅降级机制
    """

    def __init__(self, device_id: str):
        super().__init__(device_id)

        # 新增：iOS 版本检测
        self._ios_version: Optional[str] = None

        # 新增：采集方案选择（自动检测）
        self._collector_type: Literal['tidevice', 'pyios'] = 'tidevice'

        # 现有：APM 实例缓存
        self._apm: Optional['IOSAPM'] = None
        self._apm_lock = threading.Lock()

        # 新增：py-ios-device 连接管理
        self._pyios_connection: Optional['PyIOSConnection'] = None
        self._pyios_lock = threading.Lock()

        self._detect_ios_version()  # 启动时检测

    def _detect_ios_version(self):
        """检测 iOS 版本并选择最佳采集方案"""

    def collect_cpu(self, package_name: str) -> Optional[Dict[str, Any]]:
        """采集 CPU 数据（统一接口，内部路由到不同方案）"""

    def _collect_cpu_pyios(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 py-ios-device 采集"""

    def _collect_cpu_tidevice(self, package_name: str) -> Optional[Dict[str, Any]]:
        """使用 tidevice 采集（现有实现）"""
```

---

## 四、数据采集流程

### py-ios-device 采集流程

```
┌──────────────────────────────────────────────────────────┐
│ 1. 设备连接阶段                                           │
│    pymobiledevice3 remote start-tunnel (外部进程)         │
│         ↓                                                 │
│    RemoteLockdownClient.connect(远程地址)                 │
│         ↓                                                 │
│    InstrumentServer.init()                               │
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ 2. 采集配置阶段                                           │
│    rpc.call("sysmontap", "setConfig:", config)           │
│    rpc.call("graphics", "startSamplingAtTimeInterval:", 1.0)│
└──────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────┐
│ 3. 数据接收循环                                           │
│    while monitoring:                                      │
│        message = rpc.receive_dtx_message(timeout=2)       │
│        parsed = parse_message(message)                   │
│        normalized = IOSDataNormalizer.normalize(parsed)  │
│        emit_metrics_updated(normalized)                  │
└──────────────────────────────────────────────────────────┘
```

### 降级流程

```
┌─────────────────────────────────────────┐
│ 尝试 py-ios-device 采集                  │
│         ↓                               │
│    成功？                                │
│    ├─ 是 → 返回数据                      │
│    └─ 否 ↓                              │
│ 记录日志，标记降级                       │
│         ↓                               │
│ 降级到 tidevice 采集                     │
│         ↓                               │
│ 返回数据                                 │
└─────────────────────────────────────────┘
```

---

## 五、目录结构

```
insight_eyes/public/ios/
├── __init__.py
├── ios_apm.py              # 现有，保持不变
├── dependency_checker.py   # 新增：依赖检测
├── pyios_connect.py        # 新增：连接管理器
├── data_normalizer.py      # 新增：数据规范化
├── pyios_collectors/       # 新增：py-ios-device 采集器
│   ├── __init__.py
│   ├── base.py             # 基类
│   ├── sysmontap.py        # CPU/Mem/Net 解析器
│   ├── graphics.py         # FPS/GPU 解析器
│   └── energy.py           # Battery 解析器
└── tidevice_collectors/    # 现有，保持不变
    ├── cpu_collector.py
    ├── memory_collector.py
    ├── fps_collector.py
    ├── network_collector.py
    └── battery_collector.py
```

---

## 六、依赖管理

### setup.py 配置

```python
extras_require = {
    'ios-full': [
        'py-ios-device>=0.7.0',
        'pymobiledevice3>=3.0.0',
        'pymobiledevice3[openssl]',
    ],
}
```

### 用户安装方式

```bash
# 基础安装（仅支持 tidevice）
pip install insight-eye

# 完整 iOS 支持（推荐）
pip install insight-eye[ios-full]

# 或手动安装
pip install py-ios-device pymobiledevice3
pip install 'pymobiledevice3[openssl]'
```

---

## 七、实现计划

### 第一阶段：基础架构（2-3天）

**目标：**搭建框架，支持自动切换

**任务清单：**
- [ ] 创建 `IOSDependencyChecker` 类
- [ ] 创建 `PyIOSConnection` 连接管理器
- [ ] 修改 `IOSDeviceAdapter` 支持方案选择
- [ ] 实现自动检测逻辑（iOS 版本 + 依赖）
- [ ] 添加降级机制

**输出：**
- `dependency_checker.py`
- `pyios_connect.py`
- `data_normalizer.py`
- 修改后的 `device_adapters.py`

### 第二阶段：核心指标实现（3-4天）

**目标：**实现 CPU、Memory、FPS 采集

**任务清单：**
- [ ] 复制 py-ios-device demo 模块到项目
- [ ] 改造 `sysmontap.py` - CPU 采集
- [ ] 改造 `sysmontap.py` - Memory 采集
- [ ] 改造 `graphics.py` - FPS 采集
- [ ] 实现数据规范化器
- [ ] 单元测试（模拟数据）

**输出：**
- `pyios_collectors/sysmontap.py`
- `pyios_collectors/graphics.py`
- 完整的 `data_normalizer.py`
- 单元测试文件

### 第三阶段：扩展指标实现（2-3天）

**目标：**实现 Network、Battery、GPU 采集

**任务清单：**
- [ ] 改造 `sysmontap.py` - Network 采集
- [ ] 改造 `energy.py` - Battery 采集
- [ ] 改造 `graphics.py` - GPU 采集
- [ ] 完善数据规范化器
- [ ] 集成测试

**输出：**
- 完整的 `pyios_collectors/energy.py`
- 完整的 `sysmontap.py` 和 `graphics.py`
- 集成测试文件

### 第四阶段：隧道管理（2天）

**目标：**集成 pymobiledevice3 隧道

**任务清单：**
- [ ] 实现隧道进程管理
- [ ] 自动获取远程地址
- [ ] 隧道健康检查
- [ ] 隧道自动重连
- [ ] UI 提示用户启动隧道（如需要）

**输出：**
- `tunnel_manager.py`
- UI 集成提示

### 第五阶段：测试与优化（2-3天）

**目标：**端到端测试和性能优化

**任务清单：**
- [ ] 真机测试（iOS 15、16、17、18）
- [ ] 性能测试（采集频率、资源占用）
- [ ] 边界测试（网络断开、设备断开）
- [ ] UI 集成测试
- [ ] 文档编写
- [ ] 代码审查

**输出：**
- 测试报告
- 用户文档
- 性能优化报告

**总计：约 12-16 天**

---

## 八、测试策略

### 单元测试

```python
# 测试依赖检测
def test_dependency_checker():
    assert IOSDependencyChecker.check_pyios_device() == expected

# 测试数据规范化
def test_data_normalizer():
    raw = {'cpuUsage': 15.2}
    normalized = IOSDataNormalizer.normalize_cpu(raw)
    assert normalized == {'appCpuRate': 15.2, 'sysCpuRate': 15.2}

# 测试降级机制
def test_fallback_to_tidevice():
    # 模拟 py-ios-device 失败
    # 验证自动降级到 tidevice
    pass
```

### 集成测试

```python
# 测试完整采集流程
def test_full_collection_pipeline():
    adapter = IOSDeviceAdapter(device_id)
    data = adapter.collect_cpu(bundle_id)
    assert data is not None
    assert 'appCpuRate' in data
```

### 真机测试

- iOS 15.x 设备
- iOS 16.x 设备
- iOS 17.x 设备
- iOS 18.x 设备

---

## 九、风险评估与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| py-ios-device 解析失败 | 高 | 中 | 保留 tidevice 降级方案 |
| 隧道连接不稳定 | 高 | 中 | 自动重连 + 超时保护 |
| 数据格式不一致 | 中 | 低 | 数据规范化层 |
| 性能影响 | 中 | 低 | 连接复用 + 健康检查 |
| 依赖冲突 | 低 | 低 | 可选依赖 + 优雅降级 |

---

## 十、后续优化方向

1. **性能优化**
   - 连接池管理
   - 数据缓存策略
   - 异步采集

2. **功能增强**
   - 实时 FPS 卡顿检测
   - GPU 详细指标
   - 网络流量详细统计

3. **用户体验**
   - 隧道自动启动
   - 图形化配置界面
   - 实时连接状态显示

---

**文档版本：** v1.0
**创建日期：** 2025-01-20
**作者：** Claude + Aceyuan361
