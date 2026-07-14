# 贡献指南

感谢你对 Insight-AITest 项目的关注！我们欢迎任何形式的贡献。

## 🤝 如何贡献

### 报告 Bug

如果你发现了 Bug，请：

1. 检查 [Issues](https://github.com/Aceyuan361/Insight-AITest/issues) 是否已有相同问题
2. 如果没有，创建新的 Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤
   - 期望行为与实际行为
   - 环境信息（OS、Python 版本、Node 版本、浏览器版本等）
   - 相关日志或截图

### 提出新功能

1. 先在 [Issues](https://github.com/Aceyuan361/Insight-AITest/issues) 讨论你的想法
2. 等待维护者反馈
3. 获得批准后再开始开发

### 提交代码

#### 1. Fork 仓库

点击 GitHub 页面右上角的 Fork 按钮。

#### 2. 克隆你的 Fork 并基于 `2.0.0` 分支开发

```bash
git clone https://github.com/你的用户名/Insight-AITest.git
cd Insight-AITest
git checkout 2.0.0
```

#### 3. 创建特性分支

```bash
git checkout -b feature/你的功能名称
```

分支命名规范：
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 代码重构
- `test/xxx` - 测试相关

#### 4. 搭建开发环境

**后端（Python 3.10+）：**

```bash
# 安装应用 + 开发依赖（含 pytest、black、ruff 等）
pip install -e ".[dev]"
```

**前端（Node.js 20+ 推荐）：**

```bash
cd insight_aitest/shell-frontend
npm install
```

#### 5. 编写代码

- 遵循现有代码风格（后端 Black + Ruff，前端 TypeScript 严格类型）
- 添加必要的注释和 Docstring
- 编写测试（如果适用）
- 更新相关文档

#### 6. 测试

**后端测试：**

```bash
pytest tests/ -q
```

**前端构建 / Lint：**

```bash
cd insight_aitest/shell-frontend
npm run build    # TypeScript 编译 + Vite 构建
npm run lint     # ESLint
```

#### 7. 提交更改

```bash
git add .
git commit -m "feat: 添加某功能的描述"
```

提交信息规范（Conventional Commits）：
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具链相关

#### 8. 推送并创建 Pull Request

```bash
git push origin feature/你的功能名称
```

然后访问你 Fork 的 GitHub 页面，点击 "Compare & pull request"，填写 PR 描述并等待审查。

## 📝 代码规范

### Python 代码
- 遵循 [PEP 8](https://pep8.org/)，由 Black 自动格式化、Ruff 检查
- 使用类型注解
- 添加 Docstring

### TypeScript / React 代码
- 使用 TypeScript 严格类型
- 遵循 React Hooks 规范
- 组件使用函数式声明

### 模块化
Insight-AITest 采用「平台内核 + 可插拔模块」架构。新增功能应优先考虑作为一个模块（在 `insight_aitest/modules/` 下创建目录并编写 `manifest.yaml`），而不是改动平台内核。详见 [项目架构概览](docs/project-overview.md)。

## 🎨 设计原则

- **简洁性**：保持代码简洁易懂
- **模块化**：功能解耦，高内聚低耦合
- **可测试性**：编写可测试的代码
- **文档化**：及时更新文档

## 📧 联系方式

- GitHub Issues: [提交问题](https://github.com/Aceyuan361/Insight-AITest/issues)
- GitHub Discussions: [交流讨论](https://github.com/Aceyuan361/Insight-AITest/discussions)

## 📄 许可证

通过贡献代码，你同意你的贡献将使用 [MIT License](LICENSE) 许可。
