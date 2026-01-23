from __future__ import absolute_import

# 项目描述
__doc__ = """
Insight-Eye - 移动端性能监控工具

支持平台:
    - Android (无需 ROOT)
    - iOS (无需越狱)

监控指标:
    - CPU 使用率
    - 内存使用 (PSS)
    - FPS 帧率 & BigJank 严重卡顿
    - GPU 使用率
    - 网络流量
    - 电池状态 (电量/温度/功耗)

使用示例:
    from insight_eyes.public.apm import APM

    apm = APM(pkgName='com.example.app', deviceId='device_id')
    apm.start()

    cpu = apm.collectCpu()
    print(f"CPU: {cpu['appCpuRate']}%")

    apm.stop()
"""


