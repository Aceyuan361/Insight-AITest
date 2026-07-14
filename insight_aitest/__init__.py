"""
Insight-AITest - AI 驱动的测试与监控平台

版本: v2.0.0

Web 应用特性:
    - 基于 FastAPI 的 RESTful API 和 WebSocket 服务
    - React + TypeScript + Vite 前端
    - 实时性能监控和数据可视化
    - 多设备并发监控支持

支持平台:
    - Android (无需 ROOT)
    - iOS (无需越狱)

监控指标:

    Android 平台:
        - CPU 使用率 (应用/系统)
        - 内存使用 (PSS/Native/Dalvik)
        - FPS 帧率 & BigJank 严重卡顿
        - GPU 能耗
        - 网络流量 (应用级)
        - 电池状态 (电量/温度)

    iOS 平台:
        - CPU 使用率 (应用/系统)
        - 内存使用 (physFootprint)
        - FPS (系统刷新率参考值 60fps)
        - 网络流量 (系统级)
        - 电池状态 (电量/温度)
        - 能耗监控

使用示例 - Android:

    from insight_aitest.platform.services.collectors.android.android_apm import AndroidAPM

    apm = AndroidAPM(
        package_name='com.example.app',
        device_id='emulator-5554'
    )
    apm.start()

    cpu = apm.collectCpu()
    print(f"CPU: {cpu['cpu_app']}%")

    apm.stop()

使用示例 - iOS:

    from insight_aitest.platform.services.collectors.ios.ios_apm import IOSAPM

    apm = IOSAPM(
        bundle_name='com.example.app',
        device_id='iphone-udid'
    )
    apm.start()

    cpu = apm.collectCpu()
    print(f"CPU: {cpu['cpu_app']}%")

    apm.stop()

注意事项:
    - iOS 设备需要信任电脑并启用开发者模式
    - iOS 需要 pymobiledevice3 >= 9.0.0（iOS 17+ 需 tunnel 支持）
    - iOS GPU 监控受系统限制暂不支持
    - iOS FPS 为系统刷新率参考值，非应用级数据
"""

__version__ = "2.0.0"
