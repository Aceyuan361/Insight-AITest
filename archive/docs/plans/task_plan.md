# Task Plan: UI优化重构 - 监控面板布局改进
<!--
  WHAT: UI优化重构任务计划
  WHY: 改进监控面板布局、优化指标显示、移除冗余配置功能
  WHEN: 2025-01-20
-->

## Goal
重构 Insight-Eye 监控面板UI：去掉配置操作区扩展告警记录、优化监控面板为固定2×3布局、调整监控指标（电池→网络上行/下行）、在设备面板显示电池信息、测试报告图表1:1复刻监控面板

## Current Phase
Phase 7 - 集成测试与验证

## Phases

### Phase 1: 需求分析与技术设计
- [x] 理解用户需求和UI结构
- [x] 探索现有代码结构
- [x] 设计电池信息显示组件
- [x] 设计网络上行/下行指标配置
- [x] 设计固定2×3监控面板布局
- [x] 设计告警记录扩展布局
- [x] 文档化设计决策
- **Status:** completed

### Phase 2: 配置面板重构
- [x] 移除配置操作区 (_create_action_group)
- [x] 扩展告警记录区 (_create_alert_group)
- [x] 移除相关方法 (_reset_to_default, _export_config, _import_config, _on_auto_save_changed)
- **Status:** completed

### Phase 3: 监控指标配置调整
- [x] 修改 card_configs.py：移除battery，添加network_up/network_down
- [x] 更新CollectionConfig模型
- [x] 更新monitor_panel_v2.py中的指标处理逻辑
- [x] 支持network_up和network_down独立显示
- **Status:** completed

### Phase 4: 监控面板布局优化
- [x] 修改标题位置：上移居中置顶，改为全大写"REAL-TIME SYSTEM MONITOR"
- [x] 修改网格布局为固定2列
- [x] 限制最多6个卡片（2×3布局）
- [x] _calculate_columns方法固定返回2
- **Status:** completed

### Phase 5: 设备面板添加电池信息
- [x] 创建电池信息显示组件
- [x] 集成到设备选择面板（左下角）
- [x] 添加update_battery_info方法
- [x] 显示电量、温度、容量信息
- **Status:** completed

### Phase 6: 测试报告图表对齐
- [x] 分析当前测试报告图表实现
- [x] 更新图表区域支持network_up
- [x] 确保颜色和样式与监控面板一致
- [x] 更新_update_charts方法支持上行/下行数据
- **Status:** completed

### Phase 7: 集成测试与验证
- [ ] 端到端测试完整流程
- [ ] 验证所有UI变更
- [ ] 更新文档
- [ ] Git提交
- **Status:** in_progress

## Key Questions
1. 电池信息显示在设备面板的哪个位置？→ 左下角区域
2. 网络上行/下行数据如何采集？→ 需要检查网络采集器实现
3. 固定2×3布局是否需要滚动？→ 超过6个指标时需要滚动或限制
4. 测试报告图表是否需要实时更新？→ 否，历史数据展示

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 固定2×3布局 | 用户明确要求，简化布局逻辑 |
| 电池→网络上行/下行 | 电池变化少，网络流量更重要 |
| 电池信息移到设备面板 | 独立显示，不占用监控卡片 |
| 移除配置操作区 | 用户明确要求，扩展告警记录空间 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| | 1 | |
| | 2 | |

## Notes
- 更新phase状态: pending → in_progress → complete
- 在重大决策前重读此计划
- 记录所有错误以避免重复
- 使用git跟踪变更
