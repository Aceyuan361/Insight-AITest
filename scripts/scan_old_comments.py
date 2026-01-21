#!/usr/bin/env python3
"""
扫描需要清理的旧注释
扫描所有 Python 文件中 tidevice 相关的旧注释和 TODO/FIXME 标记
"""
import re
from pathlib import Path

# 需要搜索的模式
PATTERNS = [
    r'# TODO.*tidevice',
    r'# FIXME.*tidevice',
    r'# XXX.*tidevice',
    r'# HACK.*tidevice',
    r'# 旧.*tidevice',
    r'# tidevice.*弃用',
    r'# deprecated.*tidevice',
    r'### tidevice',
]

def scan_files():
    """扫描所有 Python 文件"""
    project_root = Path.cwd()
    python_files = project_root.rglob('*.py')

    findings = []

    for py_file in python_files:
        # 跳过归档目录
        if 'archive' in str(py_file):
            continue

        try:
            # Try multiple encodings
            content = None
            for encoding in ['utf-8', 'gbk', 'latin-1']:
                try:
                    content = py_file.read_text(encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                print(f"Failed to read: {py_file} (encoding issue)")
                continue

            for pattern in PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    findings.append({
                        'file': str(py_file.relative_to(project_root)),
                        'line': line_num,
                        'text': match.group(),
                        'pattern': pattern
                    })
        except Exception as e:
            print(f"Failed to read: {py_file}: {e}")

    # 输出结果
    if findings:
        print(f"找到 {len(findings)} 个需要审查的注释:\n")
        for finding in findings:
            print(f"  {finding['file']}:{finding['line']}")
            print(f"    {finding['text']}\n")
    else:
        print("✓ 未找到需要清理的旧注释")

    return findings

if __name__ == '__main__':
    scan_files()
