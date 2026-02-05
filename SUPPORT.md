# 获取帮助

如果你在使用 Insight-Eye Web 时遇到问题，这里有一些获取帮助的途径。

## 文档

首先，请查看我们的文档：

- [README.md](README.md) - 项目概述和快速开始指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [API 文档](http://localhost:8000/docs) - FastAPI 自动生成的 API 文档（需要运行后端服务）

## 常见问题

### Q: iOS 设备无法连接？

**A:** 请确保：
1. 设备已信任电脑
2. 已启用开发者模式
3. pymobiledevice3 版本 >= 7.0.0
4. USB 连接稳定

### Q: Android 设备检测不到？

**A:** 请确保：
1. 已安装 ADB
2. USB 调试已启用
3. 已授权电脑调试
4. 运行 `adb devices` 确认设备连接

### Q: 前端无法连接后端？

**A:** 请检查：
1. 后端服务是否在运行（默认 8000 端口）
2. 检查 `insight_eyes/web-frontend/.env.production` 中的 API 地址配置
3. 确保防火墙没有阻止连接

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
1. 搜索 [Issues](https://github.com/Aceyuan361/Insight_eye/issues) 确认问题未被报告
2. 创建新 Issue，使用 Bug 报告模板
3. 提供详细的复现步骤和环境信息

### 功能建议

如果你有好的想法：
1. 先搜索 [Issues](https://github.com/Aceyuan361/Insight_eye/issues) 确认未被提议
2. 创建新 Issue，使用功能建议模板
3. 详细描述你的想法和用例

### 提问

如果你有使用问题：
1. 先查阅文档和常见问题
2. 搜索 [Issues](https://github.com/Aceyuan361/Insight_eye/issues) 查看类似问题
3. 创建新 Issue，使用问题模板

## 社区

- **GitHub**: [Aceyuan361/Insight_eye](https://github.com/Aceyuan361/Insight_eye)
- **Discussions**: [GitHub Discussions](https://github.com/Aceyuan361/Insight_eye/discussions)

## 联系方式

- Email: your-email@example.com
- Twitter: [@yourusername](https://twitter.com/yourusername)

## 贡献

我们欢迎所有形式的贡献！查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与。
