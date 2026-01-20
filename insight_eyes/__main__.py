# Insight-eyes 包入口点
# 启动桌面应用程序

from __future__ import absolute_import
import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from insight_eyes.desktop.main import main

if __name__ == '__main__':
    main()
