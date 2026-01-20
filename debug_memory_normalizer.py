# -*- coding: utf-8 -*-
"""
调试内存规范化测试
"""
from insight_eyes.public.ios import IOSDataNormalizer

# 测试数据
mem_raw = {'memResidentSize': 120000000}

# 执行规范化
mem_norm = IOSDataNormalizer.normalize_memory(mem_raw)

# 预期值
expected = 120000000 / (1024 * 1024)

# 打印结果
print(f"输入数据: {mem_raw}")
print(f"预期值: {expected:.2f} MB")
print(f"实际返回: {mem_norm}")
print(f"totalPass 值: {mem_norm.get('totalPass', 'NOT FOUND')}")

# 检查是否相等
if 'totalPass' in mem_norm:
    if abs(mem_norm['totalPass'] - expected) < 0.01:
        print("✓ 测试通过")
    else:
        print(f"✗ 测试失败: 差值 {abs(mem_norm['totalPass'] - expected):.2f}")
else:
    print("✗ totalPass 键不存在!")
