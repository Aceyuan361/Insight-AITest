# Claude Code Skills 实用手册

> 版本：v1.0
> 更新时间：2025-01-16
> 适用范围：Claude Code CLI / Desktop App

---

## 目录

1. [什么是 Skills](#什么是-skills)
2. [核心概念与架构](#核心概念与架构)
3. [快速入门](#快速入门)
4. [创建你的第一个 Skill](#创建你的第一个-skill)
5. [Skill 结构详解](#skill-结构详解)
6. [触发机制](#触发机制)
7. [最佳实践](#最佳实践)
8. [实用场景示例](#实用场景示例)
9. [故障排查](#故障排查)
10. [高级技巧](#高级技巧)
11. [Skills vs Prompts vs MCP](#skills-vs-prompts-vs-mcp)

---

## 什么是 Skills

### 为什么需要 Skills

**没有 Skills 时：**
- 每个对话都要重复提供背景信息
- Claude 无法持续学习你的习惯和要求
- 项目规范难以统一执行
- 上下文窗口很快被占满

**有了 Skills 后：**
- ✅ 一次编写，重复使用
- ✅ Claude 自动提供专业指导
- ✅ 团队规范统一执行
- ✅ 智能加载，高效省资源

### 核心特点

| 特性 | 说明 | 实际价值 |
|------|------|----------|
| **智能触发** | 自动识别相关查询 | 无需手动调用，自然集成 |
| **渐进披露** | 三层资源加载策略 | 节省上下文窗口，提升性能 |
| **资源分层** | 核心 + 参考资料 + 示例 | 结构清晰，易于维护 |
| **即插即用** | 放入插件即可使用 | 分发简单，团队共享方便 |
| **可执行脚本** | 包含实用工具脚本 | 代码复用，避免重复编写 |

---

## 核心概念与架构

### 三层资源加载架构

```
┌─────────────────────────────────────────────────────┐
│                  Claude 系统提示                      │
│  （预加载所有 Skills 的 name + description）          │
└─────────────────────────────────────────────────────┘
                        ↓ 用户查询匹配
┌─────────────────────────────────────────────────────┐
│                  SKILL.md（按需加载）                 │
│  核心说明，约 1,500-2,000 词                         │
└─────────────────────────────────────────────────────┘
                        ↓ 需要详细信息时
┌─────────────────────────────────────────────────────┐
│           references/ + examples/（按需加载）          │
│  详细参考文档、完整示例、实用脚本                      │
└─────────────────────────────────────────────────────┘
```

### 与传统 Prompt 的区别

| Aspect | 传统 Prompts | Claude Code Skills |
|--------|-------------|-------------------|
| **复用性** | 每次会话复制粘贴 | 跨会话持久化 |
| **版本控制** | 不支持 | Git 原生支持 |
| **团队共享** | 聊天记录/文档 | 安装包/市场 |
| **复杂度限制** | ~500 词后易碎 | 多文件工作流 10K+ tokens |
| **工具权限** | 所有工具始终可用 | 精细的允许/拒绝列表 |
| **上下文隔离** | 全局命名空间污染 | 每个 Skill 独立作用域 |
| **最佳场景** | 临时性问题 | 重复性工作流 |

---

## 快速入门

### 环境要求

- **Claude Desktop App** (v0.7.0+) 或 **Claude CLI** (v2.1.0+)
- **操作系统**：macOS 11+, Windows 10+, Linux (Ubuntu 20.04+)

### 安装路径

```
# 全局 Skills（所有项目可用）
~/.claude/skills/

# 项目级 Skills（仅当前项目）
project/.claude/skills/

# 插件级 Skills
my-plugin/skills/
```

### 验证安装

```bash
# 查看 Claude 版本
claude --version

# 列出已安装的 Skills
claude skills list

# 测试 Skill 执行
echo "测试触发" | claude
```

---

## 创建你的第一个 Skill

### 步骤 1：规划 Skill

回答三个问题：

1. **用途是什么？** - 为 Claude 提供什么专业知识
2. **何时触发？** - 用户说什么时应该加载这个 Skill
3. **包含什么内容？** - 需要哪些参考资料和示例

### 步骤 2：创建目录结构

```bash
# 创建 Skill 目录
mkdir -p ~/.claude/skills/my-first-skill/{references,examples,scripts}

# 创建核心文件
touch ~/.claude/skills/my-first-skill/SKILL.md
```

### 步骤 3：编写 SKILL.md

```markdown
---
name: code-review-guide
description: This skill should be used when the user asks to "review code",
             "check code quality", "analyze code", or requests code review feedback.
             Provides comprehensive code review standards and best practices.
version: 1.0.0
---

# Code Review Guide

This skill provides standardized code review guidance.

## Core Review Principles

When reviewing code, evaluate these aspects:

### 1. Security
- Check for injection vulnerabilities (SQL, command, XSS)
- Verify input validation and sanitization
- Ensure sensitive data is handled properly

### 2. Performance
- Identify unnecessary computations
- Check for N+1 query problems
- Review algorithm complexity

### 3. Maintainability
- Evaluate code clarity and readability
- Check for appropriate abstraction
- Verify error handling completeness

## Additional Resources

- **`references/security-checklist.md`** - 详细安全检查清单
- **`examples/sample-review.md`** - 完整审查示例
```

### 步骤 4：添加配套资源

```bash
# 创建参考资料
cat > ~/.claude/skills/code-review-guide/references/security-checklist.md << 'EOF'
# Security Checklist

## Input Validation
- [ ] All external inputs are validated
- [ ] Input lengths/sizes are checked
- [ ] Special characters are handled properly

## Authentication & Authorization
- [ ] Auth tokens are validated
- [ ] Permissions are checked
- [ ] Role-based access is correct
EOF
```

### 步骤 5：测试 Skill

```bash
# 重启 Claude 使其加载新 Skill
claude reload

# 测试触发
echo "请帮我审查这段代码的安全性" | claude
```

---

## Skill 结构详解

### 标准目录结构

```
skill-name/
├── SKILL.md                     # 核心说明文件（必需）
├── references/                   # 参考文档（可选）
│   ├── patterns.md              # 详细模式
│   ├── advanced.md              # 高级用法
│   └── api-docs.md              # API 文档
├── examples/                     # 示例文件（可选）
│   ├── example1.js              # 示例代码
│   ├── config.json              # 配置示例
│   └── workflow.md              # 流程示例
└── scripts/                      # 脚本工具（可选）
    ├── validate.sh              # 验证脚本
    └── analyze.py               # 分析工具
```

### YAML Frontmatter（元数据）

```yaml
---
name: skill-name              # 必需：小写字母、数字、连字符，最大64字符
description: 技能描述        # 必需：最大1024字符，说明何时使用
version: 1.0.0               # 可选：语义化版本
author: your-name            # 可选：作者
license: MIT                 # 可选：许可证
---
```

### description 最佳实践

**✅ 好的示例：**

```yaml
description: This skill should be used when the user asks to "create a hook",
             "add a PreToolUse hook", "validate tool use", "implement prompt-based hooks",
             or mentions hook events (PreToolUse, PostToolUse, Stop).
```

**❌ 不好的示例：**

```yaml
# 太笼统
description: Use this skill when working with hooks.

# 不具体
description: Load when user needs help with code.

# 第一人称错误
description: I will help you with code review.
```

### 写作风格要求

- ✅ 使用**命令式/不定式**（"Do X"），不用第二人称（"You should"）
- ✅ 清晰的标题层次
- ✅ 具体的操作步骤
- ✅ 明确的资源引用

**正确示例：**

```markdown
# Create a Hook

## Define Event Type

Determine which hook event to use:

1. For tool validation, use `PreToolUse`
2. For post-action logging, use `PostToolUse`

## Write Hook Implementation

Create a script in the `hooks/` directory:

```bash
touch hooks/my-hook.py
```

Refer to `examples/sample-hook.py` for the complete implementation.
```

---

## 触发机制

### 触发原理

```
1. Claude 分析用户提示
       ↓
2. 扫描所有 Skill 的 description
       ↓
3. 匹配关键词触发 Skill
       ↓
4. 加载 SKILL.md 内容
       ↓
5. 后续对话基于 Skill 指导
```

### 如何写好触发描述

**原则：**
- 具体，不笼统
- 包含多种表达方式
- 覆盖常见场景
- 避免歧义

**实战技巧：**

1. **动词多样性**

```yaml
description: ..."create", "build", "generate", "make", "develop"...
```

2. **名词同义词**

```yaml
description: ..."hook", "plugin", "extension", "middleware"...
```

3. **完整短语**

```yaml
description: This skill should be used when the user asks to
             "create a React component",
             "build a UI component with React",
             "make a React widget"...
```

4. **反例排除**

```yaml
# 避免误判
description: ...when working with Git hooks (not webhooks)...
```

### 触发测试清单

创建 Skill 后，验证这些场景：

- ✅ 直接请求："Please use [skill name] to…"
- ✅ 间接提及：涉及 Skill 相关话题
- ✅ 模糊表达：用不同方式说同一件事
- ✅ 边界情况：不会误判的不相关请求

---

## 最佳实践

### 1. 简洁原则（Concise is Key）

**上下文窗口是公共资源** - SKILL.md 中的每个 token 都在与对话历史竞争。

**默认假设：Claude 已经很聪明**

**✅ 简洁示例**（约 50 tokens）：

```markdown
## Extract PDF text

Use pdfplumber for text extraction:

```python
import pdfplumber

with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```
```

**❌ 冗长示例**（约 150 tokens）：

```markdown
## Extract PDF text

PDF (Portable Document Format) files are a common file format that contains
text, images, and other content. To extract text from a PDF, you'll need to
use a library. There are many libraries available for PDF processing, but we
recommend pdfplumber because it's easy to use and handles most cases well.
First, you'll need to install it using pip. Then you can use the code below...
```

### 2. 设置适当的自由度

| 自由度 | 使用场景 | 示例 |
|--------|----------|------|
| **高自由度** | 多种有效方法、依赖上下文 | 代码审查流程 |
| **中等自由度** | 有首选模式、允许变化 | 生成报告模板 |
| **低自由度** | 操作脆弱、一致性关键 | 数据库迁移脚本 |

### 3. 渐进披露模式

**SKILL.md 主体应控制在 500 行以内**

```markdown
# SKILL.md（始终加载）

## 核心内容（约 1,500 词）
1. 功能概述
2. 基础使用步骤
3. 常见问题

## 参考资料
- `references/advanced-patterns.md` - 高级模式详情（需要时加载）
- `references/api-spec.md` - API 完整规范（需要时加载）
```

### 4. 命名规范

**✅ 好的命名：**

```yaml
name: frontend-design
name: security-audit
name: database-migration
```

**❌ 不好的命名：**

```yaml
name: My Skill
name: helper
name: utility
```

### 5. Skill 粒度控制

**一个 Skill = 一个专业领域**

**✅ 正确：**

```
skills/
├── frontend-design/           # 前端设计规范
├── security-audit/            # 安全审计
└── api-testing/               # API 测试
```

**❌ 错误：**

```
skills/
└── everything-about-dev/      # 太大，什么都放
```

### 6. 版本管理

```yaml
---
name: my-skill
version: 1.2.3  # MAJOR.MINOR.PATCH
---

# 版本号规则：
# MAJOR: 重大功能变更
# MINOR: 新增功能
# PATCH: Bug 修复
```

---

## 实用场景示例

### 场景 1：团队编码规范

```markdown
---
name: coding-standards
description: This skill should be used when the user asks to "check code style",
             "review code quality", "apply coding standards", "format code",
             or "improve code quality".
---

# Team Coding Standards

## Code Style

### Naming
- Variables: camelCase (`userName`)
- Constants: UPPER_SNAKE_CASE (`MAX_RETRY`)
- Functions: camelCase (`fetchData()`)
- Classes: PascalCase (`UserService`)

### Formatting
- Indent: 2 spaces
- Line length: 80 characters
- Semicolons: required
- Quotes: single quotes for strings

## Best Practices

See `references/best-practices.md` for detailed guidelines.

### JavaScript
- Use `const` by default
- Use `let` when rebinding needed
- Avoid `var`
- Use arrow functions for short functions
```

### 场景 2：前端组件库使用

```markdown
---
name: ui-component-library
description: This skill should be used when the user asks to "create a UI component",
             "build a form", "add a button", "use design system components",
             or works with React components and UI elements.
---

# UI Component Library Guide

When building UI components, use our Design System:

## Available Components

### Button
Use `import { Button } from '@company/design-system'`

Variations:
- `primary` - Main actions
- `secondary` - Secondary actions
- `danger` - Destructive actions

See `references/component-api.md` for full props.

### Form
Use `import { Form, FormField } from '@company/design-system'`

Layout example in `examples/form-layout.js`.
```

### 场景 3：API 开发规范

```markdown
---
name: api-development
description: This skill should be used when the user asks to "create an API",
             "design endpoint", "build REST API", "add API route",
             or works with backend API development.
---

# API Development Standards

## Endpoint Design

### URL Structure
Use kebab-case for URLs:

```
✅ GET /api/users/:userId/orders
❌ GET /api/users/:userId/orders/:orderId  # Too deep
```

Max URL depth: 3 levels

### HTTP Methods
- GET - Retrieve
- POST - Create
- PUT - Replace
- PATCH - Update
- DELETE - Remove

### Status Codes
- 200 OK - Successful GET/PUT/PATCH
- 201 Created - Successful POST
- 400 Bad Request - Invalid input
- 401 Unauthorized - Missing auth
- 404 Not Found - Resource doesn't exist
- 500 Server Error - Unexpected error
```

---

## 故障排查

### 问题 1：Skill 不触发

**症状：** 说了相关的话，但 Skill 没有加载

**解决方案：**

1. 检查 description 是否太泛泛
2. 添加更多触发词和短语
3. 测试不同的表达方式
4. 查看日志确认 Skill 是否被扫描

### 问题 2：Skill 触发误判

**症状：** 不相关的请求也触发了 Skill

**解决方案：**

1. 缩小 description 的范围
2. 使用更精确的专业术语
3. 添加限定词排除不相关场景

### 问题 3：上下文溢出

**症状：** Skill 加载后上下文窗口不够用

**解决方案：**

1. 检查 SKILL.md 大小（应 < 3000 词）
2. 将详细内容移到 references/
3. 考虑拆分成多个 Skill

### 问题 4：资源找不到

**症状：** Claude 说找不到 references/examples/scripts 中的文件

**检查清单：**

- ✅ 文件实际存在
- ✅ 路径正确（使用正斜杠 `/`）
- ✅ 大小写一致（Unix 系统敏感）
- ✅ 相对路径正确

---

## 高级技巧

### 技巧 1：Skill 组合使用

当用户说 "create a React component with tests" 时，多个 Skill 可以同时触发：

```yaml
# Skill A: frontend-design
description: ... when building frontend components...

# Skill B: testing-guide
description: ... when writing tests...
```

### 技巧 2：可执行脚本

在 SKILL.md 中引用实用脚本：

```markdown
## Utility Scripts

**analyze_form.py**: Extract all form fields from PDF

```bash
python scripts/analyze_form.py input.pdf > fields.json
```

**validate_boxes.py**: Check for overlapping bounding boxes

```bash
python scripts/validate_boxes.py fields.json
```
```

### 技巧 3：基于项目的 Skill

```bash
project/
├── .claude/
│   ├── settings.json
│   └── skills/  # 项目专用 Skills
│       └── project-specific-skill/
│           └── SKILL.md
└── src/
```

### 技巧 4：工作流和反馈循环

```markdown
## Code Review Workflow

Copy this checklist and track your progress:

```
Review Progress:
- [ ] Step 1: Read all source documents
- [ ] Step 2: Identify key themes
- [ ] Step 3: Cross-reference claims
- [ ] Step 4: Create structured summary
- [ ] Step 5: Verify citations
```

**Step 1: Read all source documents**

Review each document in the `sources/` directory...

**Step 2: Identify key themes**

Look for patterns across sources...
```

---

## Skills vs Prompts vs MCP

### 何时使用哪种方式

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 一次性问题 | 传统 Prompt | 无需重复，即时性好 |
| 每周 3+ 次的重复工作流 | Skills | 可复用，一致性好 |
| 需要外部系统集成 | MCP Server | 可访问外部 API 和数据库 |
| 团队规范统一执行 | Skills | Git 版本控制，易于共享 |

### 决策树

```
你的任务需要重复执行吗？
    │
    ├─ 否 → 使用 Prompt
    │
    └─ 是 → 是否需要访问外部系统？
              │
              ├─ 是 → 考虑 MCP Server
              │
              └─ 否 → 使用 Skills
```

---

## 快速参考

### Skill 创建步骤

```bash
# 1. 创建结构
mkdir -p ~/.claude/skills/my-skill/{references,examples,scripts}

# 2. 写 SKILL.md
cat > ~/.claude/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: This skill should be used when...
---

# Skill Title

Content here...
EOF

# 3. 测试触发
echo "测试触发词" | claude
```

### 最佳实践清单

创建或维护 Skill 时检查：

- [ ] description 包含具体触发短语
- [ ] 使用第三人称（"This skill should be used when…"）
- [ ] SKILL.md 字数适中（1,500-2,000 词）
- [ ] 正文使用命令式风格（"Do X", not "You should X"）
- [ ] 配套资源放在正确目录
- [ ] 明确引用 references/, examples/, scripts/
- [ ] examples 可以完整运行
- [ ] scripts 有执行权限和 shebang
- [ ] 版本号已更新
- [ ] 命名符合规范（kebab-case）

---

## 参考资源

- [Claude Skills 官方文档](https://platform.claude.com/docs/en/agents-and-tools/agent-skills)
- [Claude Code 最佳实践](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [社区 Skills 市场](https://github.com/travisvn/awesome-claude-skills)

---

*本文档基于 Claude Code 官方文档和社区实践整理而成*
