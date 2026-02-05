# 目录重命名指南: insight_eyes → insight_eye

## 问题描述

当前包名为 `insight_eyes`，应该改为 `insight_eye` 以匹配项目名称。

## 前置条件

1. **停止所有服务**
   ```bash
   # 查找占用端口的进程
   netstat -ano | findstr ":8001"
   # 停止进程
   taskkill //F //PID <进程ID>
   ```

2. **关闭 IDE 和编辑器**
   - 关闭 VSCode
   - 关闭所有打开的文件

## 方法一：手动重命名（推荐）

### 步骤 1: 重命名目录
在文件资源管理器中：
1. 导航到 `.worktrees\1.0.0\`
2. 将 `insight_eyes` 文件夹重命名为 `insight_eye`

### 步骤 2: 批量更新文件引用
运行以下 Python 脚本批量更新所有文件：

```python
import os
import re

# 需要更新的文件扩展名
extensions = ['.py', '.md', '.toml', '.txt', '.json', '.ts', '.tsx']

# 遍历目录
for root, dirs, files in os.walk('.'):
    # 跳过 node_modules 和 __pycache__
    dirs[:] = [d for d in dirs if d not in ['node_modules', '__pycache__', '.git', 'dist']]

    for file in files:
        if any(file.endswith(ext) for ext in extensions):
            filepath = os.path.join(root, file)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 替换所有引用
                new_content = content.replace('insight_eyes', 'insight_eye')

                if content != new_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f'Updated: {filepath}')

            except Exception as e:
                print(f'Error processing {filepath}: {e}')
```

### 步骤 3: 提交更改
```bash
cd .worktrees/1.0.0
git add -A
git commit -m "refactor: rename insight_eyes to insight_eye"
git push origin 1.0.0
```

## 方法二：使用 Git 批量重命名

如果方法一遇到权限问题，可以使用 Git 的方式：

```bash
cd .worktrees/1.0.0

# 1. 提交当前所有更改
git add -A
git commit -m "chore: prepare for rename"

# 2. 使用 Git 批量重命名（需要停止所有服务）
git mv insight_eyes insight_eye

# 3. 批量更新文件引用
find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.toml" \) -exec sed -i 's/insight_eyes/insight_eye/g' {} +

# 4. 提交
git add -A
git commit -m "refactor: rename insight_eyes to insight_eye"
git push origin 1.0.0
```

## 需要更新的关键文件

- `pyproject.toml` - 包名和依赖
- `requirements.txt` - 依赖路径
- `README.md` - 文档引用
- `README.zh-CN.md` - 中文文档引用
- 所有 Python 文件的 import 语句
- 所有文档中的路径引用

## 验证清单

重命名后需要验证：
- [ ] `python -m insight_eye` 可以正常启动
- [ ] 所有 import 语句正确
- [ ] 文档中的链接正确
- [ ] pyproject.toml 中的包名正确
- [ ] Git 历史保持完整

## 注意事项

1. **不要删除旧目录**：使用 git mv 或手动重命名以保留 Git 历史
2. **备份重要数据**：在执行前备份 `.worktrees/1.0.0` 目录
3. **测试所有功能**：重命名后需要重新测试所有功能
4. **更新文档**：确保所有文档引用都已更新

## 回滚方案

如果出现问题，可以使用 Git 回滚：

```bash
git revert HEAD
git push origin 1.0.0
```
