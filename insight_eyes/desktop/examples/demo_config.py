# -*- coding: utf-8 -*-
"""
配置管理器功能演示脚本

Copyright (c) 2025 Aceyuan361
GitHub: https://github.com/Aceyuan361/Insight-Eye
License: MIT License

Author: Aceyuan361
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from insight_eyes.desktop.config.config_manager import (
    ConfigManager,
    AppConfig,
    get_config_manager
)


def print_config(config: AppConfig):
    """打印配置信息"""
    print("\n" + "="*60)
    print("配置信息")
    print("="*60)
    print(f"版本: {config.config_version}")
    print(f"最后修改: {config.last_modified}")
    print(f"\n采集配置:")
    print(f"  - 采样间隔: {config.collection.interval_ms}ms")
    print(f"  - 启用CPU: {config.collection.enable_cpu}")
    print(f"  - 启用内存: {config.collection.enable_memory}")
    print(f"  - 启用FPS: {config.collection.enable_fps}")
    print(f"  - 启用网络: {config.collection.enable_network}")
    print(f"  - 启用电池: {config.collection.enable_battery}")
    print(f"  - 启用GPU: {config.collection.enable_gpu}")
    print(f"\n告警阈值:")
    print(f"  - FPS: {config.fps_threshold}")
    print(f"  - 内存: {config.memory_threshold_mb}MB")
    print(f"  - CPU: {config.cpu_threshold_percent}%")
    print(f"  - 温度: {config.battery_threshold_temp}°C")
    print(f"\nUI配置:")
    print(f"  - 窗口大小: {config.ui.window_width}x{config.ui.window_height}")
    print(f"  - 主题: {config.ui.theme}")
    print("="*60 + "\n")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("Insight-Eye 配置持久化功能演示")
    print("="*60)

    # 1. 获取配置管理器实例
    print("\n[1] 获取配置管理器实例（单例模式）...")
    config_manager = get_config_manager()
    print(f"配置文件路径: {config_manager.get_config_file_path()}")

    # 2. 加载配置
    print("\n[2] 加载配置...")
    config = config_manager.load_config()
    print_config(config)

    # 3. 修改配置
    print("\n[3] 修改配置...")
    config_manager.update_config(
        fps_threshold=40,
        memory_threshold_mb=600,
        cpu_threshold_percent=85.0
    )
    print("配置已更新: fps_threshold=40, memory_threshold_mb=600")

    # 4. 验证保存
    print("\n[4] 验证配置已保存...")
    config = config_manager.get_config()
    print(f"FPS阈值: {config.fps_threshold}")
    print(f"内存阈值: {config.memory_threshold_mb}MB")
    print(f"CPU阈值: {config.cpu_threshold_percent}%")

    # 5. 创建备份
    print("\n[5] 创建配置备份...")
    backup_path = config_manager.backup_config()
    if backup_path:
        print(f"备份已创建: {backup_path}")

    # 6. 导出配置
    print("\n[6] 导出配置...")
    export_path = os.path.join(os.path.expanduser("~"), "insight-eye-demo-config.json")
    if config_manager.export_config(export_path):
        print(f"配置已导出到: {export_path}")

    # 7. 重置为默认
    print("\n[7] 重置为默认配置...")
    if config_manager.reset_to_default():
        config = config_manager.get_config()
        print(f"FPS阈值已重置为: {config.fps_threshold}")
        print(f"内存阈值已重置为: {config.memory_threshold_mb}MB")

    # 8. 从导出文件恢复
    if os.path.exists(export_path):
        print("\n[8] 从导出文件恢复配置...")
        if config_manager.import_config(export_path):
            config = config_manager.get_config()
            print(f"FPS阈值已恢复为: {config.fps_threshold}")
            print(f"内存阈值已恢复为: {config.memory_threshold_mb}MB")

    # 9. 显示最终配置
    print("\n[9] 最终配置:")
    print_config(config)

    print("\n演示完成！")
    print(f"\n提示：配置文件位于: {config_manager.get_config_file_path()}")
    print("您可以使用任何文本编辑器查看或修改配置文件。")


if __name__ == "__main__":
    main()
