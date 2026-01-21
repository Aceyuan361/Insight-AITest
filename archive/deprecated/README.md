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
