# 获取帮助

如果你在使用 Insight-AITest 时遇到问题，这里有一些获取帮助的途径。

## 文档

首先，请查看我们的文档：

- [README.md](README.md) - 项目概述和快速开始指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [项目架构概览](docs/project-overview.md) - 架构与模块体系
- [API 文档](http://localhost:8001/docs) - FastAPI 自动生成的 API 文档（需要运行后端服务）

## 常见问题

### Q: iOS 设备无法连接？

**A:** 请确保：
1. 设备已信任电脑
2. 已启用开发者模式
3. pymobiledevice3 版本 >= 9.0.0（iOS 17+ 需 tunnel 支持）
4. USB 连接稳定

### Q: Android 设备检测不到？

**A:** 请确保：
1. 已安装 ADB
2. USB 调试已启用
3. 已授权电脑调试
4. 运行 `adb devices` 确认设备连接

### Q: 前端无法连接后端？

**A:** 请检查：
1. 后端服务是否在运行（默认端口 8001）
2. 前端开发服务器是否在运行（默认端口 80）
3. 前端通过 Vite 代理把 `/api/*` 转发到后端 8001，确认代理配置正常（`insight_aitest/shell-frontend/vite.config.ts`）
4. 确保防火墙没有阻止连接

### Q: 数据显示延迟或卡顿？

**A:** 可能原因：
1. 网络连接不稳定
2. 设备性能问题
3. 同时监控设备过多
4. 浏览器性能问题

### Q: 如何查看实时日志？

**A:**
- 后端日志：查看控制台输出或配置的日志文件
- 前端日志：打开浏览器开发者工具 (F12) 查看 Console

## 获取支持

### 报告 Bug

如果你发现了 Bug，请：
1. 搜索 [Issues](https://github.com/Aceyuan361/Insight-AITest/issues) 确认问题未被报告
2. 创建新 Issue，使用 Bug 报告模板
3. 提供详细的复现步骤和环境信息

### 功能建议

如果你有好的想法：
1. 先搜索 [Issues](https://github.com/Aceyuan361/Insight-AITest/issues) 确认未被提议
2. 创建新 Issue，使用功能建议模板
3. 详细描述你的想法和用例

### 提问

如果你有使用问题：
1. 先查阅文档和常见问题
2. 搜索 [Issues](https://github.com/Aceyuan361/Insight-AITest/issues) 查看类似问题
3. 创建新 Issue，使用问题模板

## 社区

- **GitHub**: [Aceyuan361/Insight-AITest](https://github.com/Aceyuan361/Insight-AITest)
- **Discussions**: [GitHub Discussions](https://github.com/Aceyuan361/Insight-AITest/discussions)


## 贡献

我们欢迎所有形式的贡献！查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与。
