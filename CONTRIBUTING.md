# 贡献指南

感谢你对 Insight-Eye Web 项目的关注！我们欢迎任何形式的贡献。

## 🤝 如何贡献

### 报告 Bug

如果你发现了 Bug，请：

1. 检查 [Issues](https://github.com/Aceyuan361/Insight_eye/issues) 是否已有相同问题
2. 如果没有，创建新的 Issue，包含：
   - 清晰的标题
   - 详细的问题描述
   - 复现步骤
   - 期望行为
   - 实际行为
   - 环境信息（OS、Python 版本、浏览器版本等）
   - 相关日志或截图

### 提出新功能

1. 先在 [Issues](https://github.com/Aceyuan361/Insight_eye/issues) 讨论你的想法
2. 等待维护者反馈
3. 获得批准后再开始开发

### 提交代码

#### 1. Fork 仓库

点击 GitHub 页面右上角的 Fork 按钮

#### 2. 克隆你的 Fork

```bash
git clone https://github.com/你的用户名/Insight_eye.git
cd Insight_eye
git checkout 1.0.0
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
- `style/xxx` - 代码格式调整

#### 4. 安装开发依赖

**后端开发：**
```bash
pip install -r insight_eyes/web/requirements-dev.txt
```

**前端开发：**
```bash
cd insight_eyes/web-frontend
npm install
```

#### 5. 编写代码

- 遵循现有代码风格
- 添加必要的注释
- 编写测试（如果适用）
- 更新相关文档

#### 6. 测试

**后端测试：**
```bash
pytest insight_eyes/tests/
```

**前端测试：**
```bash
cd insight_eyes/web-frontend
npm run test
npm run lint
```

#### 7. 提交更改

```bash
git add .
git commit -m "feat: 添加某功能的描述"
```

提交信息规范：
- `feat:` 新功能
- `fix:` Bug 修复
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具链相关

#### 8. 推送到你的 Fork

```bash
git push origin feature/你的功能名称
```

#### 9. 创建 Pull Request

1. 访问你 Fork 的 GitHub 页面
2. 点击 "Compare & pull request"
3. 填写 PR 描述模板
4. 等待代码审查

## 📝 代码规范

### Python 代码

- 遵循 [PEP 8](https://pep8.org/)
- 使用类型注解
- 添加 Docstring

```python
def get_device_info(device_id: str) -> DeviceInfo:
    """
    获取设备信息

    Args:
        device_id: 设备 ID

    Returns:
        DeviceInfo: 设备信息对象
    """
    pass
```

### TypeScript/React 代码

- 使用 TypeScript 类型
- 遵循 React Hooks 规范
- 组件使用函数式声明

```typescript
interface DeviceInfoProps {
  deviceId: string;
  onConnect: () => void;
}

export const DeviceInfo: React.FC<DeviceInfoProps> = ({ deviceId, onConnect }) => {
  // 组件实现
};
```

## 🎨 设计原则

- **简洁性**: 保持代码简洁易懂
- **模块化**: 功能解耦，高内聚低耦合
- **可测试性**: 编写可测试的代码
- **文档化**: 及时更新文档

## 📧 联系方式

- GitHub Issues: [提交问题](https://github.com/Aceyuan361/Insight_eye/issues)
- Email: your-email@example.com

## 📄 许可证

通过贡献代码，你同意你的贡献将使用 [MIT License](LICENSE) 许可。
