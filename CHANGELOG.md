# Changelog

本项目所有显著变更记录于此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

## [Unreleased]

### Fixed

- **API 自动化模块深链接白屏（用户级 bug）**：Vite 代理规则 `'/api'` 按前缀匹配，
  误把前端路由 `/api-runner`（及其子页）转发给后端，直链/刷新直接 404 白屏。
  改为正则 `'^/api/'` 锚定真实 API 前缀。README 的 API 截图与演示 GIF 中被拍进的
  白屏已随修复重拍重录；e2e 新增深链接回归用例堵住此类漏洞（此前 e2e 只访问 `/`）。
- **依赖补全（第二轮，CI e2e 门禁挖出）**：`httpx`（API 执行引擎运行时导入，此前只在
  dev 依赖）与 `pyyaml`（平台内核解析 manifest.yaml 必需，此前两份依赖清单都没有——
  本机能跑纯属其他包传递安装的侥幸）补入核心依赖。`pip install -e .` 后全部模块可加载。
- **black 版本锁定 24.10.0**：不同大版本的格式决策不同（25+ 改了字符串拆分等），
  本地与 CI 必须同版本，否则 check 永远对不齐；CI Backend Lint 对齐 Python 3.12。

## [2.2.0] - 2026-09-14 — 可信度冲刺

聚焦：让访客看完 README 敢 star、clone 完能一次跑通。

### Fixed

- **安装**：`pyproject.toml` 补上缺失的 `apscheduler` 依赖——此前按文档 `pip install -e .`
  安装后 API/UI 定时调度功能直接不可用（requirements.txt 有但 pyproject 漏了）。
- **测试**：`test_build_app_root_returns_version` 断言的硬编码版本与 kernel 实际返回不一致
  （在 2.1.0 上即已红），改为动态断言 `__version__`。
- **静默失败治理**（失败不再无声消失，均记 warning 日志）：
  - RAG 检索失败原先静默返回空，用户无法区分「没命中」与「检索坏了」（`agent/rag.py`）；
  - 任务附件存入知识库失败原先 `pass`，上传文档无声消失（`routes/tasks.py`）；
  - 删除文档时向量清理失败会导致已删文档继续被 RAG 引用（ai/kb 两处 `routes/documents.py`）；
  - 知识库文档编辑后写回原始文件失败会导致文件与 DB 内容分叉。
- **性能模块**：清理 `MainWindow.tsx` 中被注释掉的设备加载死代码与永不生效的
  `loadError` 死状态（设备加载实际由 `DeviceSelectionPanel` 负责，面板本来就是接线的）。

### Changed

- **版本号单一来源**：`insight_aitest.__version__` 升至 2.2.0，kernel 根端点/health 端点
  改为动态引用；前端 TopBar 原先硬编码 `v2.0.0`（落后两个版本），改为启动时从
  `/api/platform/health` 拉取，失败回退常量；`shell-frontend` 包名从 v1 遗留的
  `web-frontend@0.0.0` 更名为 `insight-aitest-shell-frontend@2.2.0`。
- **前端**：图表时间轴 locale 跟随界面语言（原先写死 zh-CN）；会话图表标题接入 i18n
  （原先硬编码英文）；清理全部死 Tailwind-v3 类（`bg-dark-card`/`text-text-secondary`/
  `border-gray-800`）与 SideNav 硬编码 rgba，统一走 tokens.css；移除 28 处调试 console.log
  与零引用的 `StatusBar.tsx`。

### Added

- **品牌**：全新 logo 与 favicon（emerald「洞察之眼 + 性能脉搏」，与产品主题同源），
  替换 Vite 默认图标；`docs/brand/` 提供横版组合标。
- **README**：全部界面截图重拍为带真实数据的版本（API 执行统计、Agent 引用对话、
  知识库文档）；首屏新增「零 LLM key 快速体验路径」指引；新增演示 GIF。
- **社区**：新增 bug 反馈 Issue 模板；Dependabot 配置迁移到 GitHub 实际识别的
  `.github/dependabot.yml`（原位置不生效）；CI 触发分支更新为 `main` + `2.*`。

### Removed

- 仓库卫生：移除误提交的 `playwright-results.json/.xml`（含个人路径）、半成品
  `example` 占位模块及其注册项、`modules/testcase/nul` 垃圾文件、Vite/React 默认图标。

## [2.1.0] - 2026-08-02 — iOS 26 全面支持

完整解决 iOS 17+/26 设备监控的兼容性问题，真机验证通过。

- 连接层：pymobiledevice3 v10.x userspace tunnel + 死锁修复
- Developer Mode：自动挂载 personalized DDI + reveal 开关（无需 Xcode）
- CPU：进程名大小写匹配修复 + 核心数归一化（PerfDog 标准）
- FPS：DVT Graphics 服务真实帧率采集 + Jank 检测
- 应用列表：iOS 26 ApplicationType 退化启发式分类
- 网络：pcapd 不可用时优雅降级

## [2.0.0] - 2026-07-14 — 模块化平台

从单一性能工具（Insight Eye v1）演进为插件化平台，六大子系统全部完成：

- A 平台外壳 + manifest 驱动的模块系统（FastAPI 内核 + React 外壳）
- B 性能监控模块化（Android ADB + iOS pymobiledevice3）
- C AI 测试 Agent（RAG 知识库 + 计划/确认/执行 + ReAct 反思循环）
- D AI 测试用例生成（分析 → 选点 → 生成 → 人工评审）
- E API 自动化（多步用例 + 断言 + 环境变量 + 套件 + 定时调度）
- F UI 自动化（Midscene 视觉驱动 + 分步截图）

## [1.0.0] - 2026-02-05 — Insight Eye 首个正式版本

- 设备发现与连接
- 实时性能监控
- Web 监控界面
- 性能报告生成
