# -*- coding: utf-8 -*-
"""
Insight-Eye - 移动端性能监控工具

一个专业的 Android/iOS 实时性能监控工具，提供桌面 GUI 应用和 Python API。

Author: Aceyuan361
GitHub: https://github.com/Aceyuan361
Version: 1.0.0
License: MIT License

Copyright (c) 2025 Aceyuan361. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import absolute_import

__version__ = '1.0.0'
__author__ = 'Aceyuan361'
__license__ = 'MIT'
__email__ = 'aceyuan361@users.noreply.github.com'
__github__ = 'https://github.com/Aceyuan361/Insight-Eye'

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


