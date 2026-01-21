#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份文件归档脚本

将备份文件移动到 archive/backup/ 目录
"""
import shutil
import sys
from pathlib import Path

# 设置标准输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 备份文件列表
BACKUP_FILES = [
    ('insight_eyes/public/android/fps_collector_backup.py', 'archive/backup/android/fps_collector_backup.py'),
    ('insight_eyes/desktop/ui/main_window_fixed.py', 'archive/backup/desktop/ui/main_window_fixed.py'),
    ('insight_eyes/desktop/ui/main_window_batch.py', 'archive/backup/desktop/ui/main_window_batch.py'),
]

def archive_backups():
    """归档备份文件"""
    project_root = Path.cwd()

    for source_path, dest_path in BACKUP_FILES:
        source = project_root / source_path
        dest = project_root / dest_path

        if source.exists():
            # 创建目标目录
            dest.parent.mkdir(parents=True, exist_ok=True)

            # 移动文件
            shutil.move(str(source), str(dest))
            print(f"✓ 归档: {source_path}")
        else:
            print(f"⊘ 跳过: {source_path} (不存在)")

    print("\n备份文件归档完成")

if __name__ == '__main__':
    archive_backups()
