"""
监控卡片配置定义
定义所有可用的监控指标卡片及其配置
"""
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class MetricCardConfig:
    """单个指标卡片配置"""
    metric_id: str           # 指标ID: 'cpu', 'memory', 'fps', 'network', 'battery', 'gpu'
    title: str               # 卡片标题
    color: str               # 霓虹主题色 (hex格式)
    y_min: Optional[float]   # Y轴最小值 (None=自适应)
    y_max: Optional[float]   # Y轴最大值 (None=自适应)
    y_width: int             # Y轴宽度
    decimals: int            # 小数位数
    unit: str                # 单位
    enabled: bool = True     # 是否启用
    priority: int = 0        # 优先级 (用于排序)


# 定义所有可用的指标卡片配置
ALL_METRIC_CARDS: List[MetricCardConfig] = [
    MetricCardConfig(
        metric_id='cpu',
        title='CPU Usage (%)',
        color='#00f2ff',
        y_min=0,
        y_max=100,
        y_width=55,
        decimals=0,
        unit='%',
        priority=1
    ),
    MetricCardConfig(
        metric_id='memory',
        title='Memory Usage (MB)',
        color='#7000ff',
        y_min=0,
        y_max=None,
        y_width=65,
        decimals=0,
        unit=' MB',
        priority=2
    ),
    MetricCardConfig(
        metric_id='fps',
        title='Frame Rate (FPS)',
        color='#ffb400',
        y_min=None,
        y_max=None,
        y_width=55,
        decimals=0,
        unit=' F',
        priority=3
    ),
    MetricCardConfig(
        metric_id='network_up',
        title='Network Upload (KB/s)',
        color='#00ff87',  # 绿色
        y_min=0,
        y_max=None,
        y_width=65,
        decimals=1,
        unit=' KB/s',
        priority=4
    ),
    MetricCardConfig(
        metric_id='network_down',
        title='Network Download (KB/s)',
        color='#0062ff',  # 蓝色
        y_min=0,
        y_max=None,
        y_width=65,
        decimals=1,
        unit=' KB/s',
        priority=5
    ),
    MetricCardConfig(
        metric_id='gpu',
        title='GPU Usage (%)',
        color='#ff006e',
        y_min=0,
        y_max=100,
        y_width=55,
        decimals=0,
        unit='%',
        enabled=False,  # 默认禁用
        priority=6
    ),
]


def get_enabled_cards() -> List[MetricCardConfig]:
    """获取所有启用的卡片配置（按优先级排序）"""
    return sorted([c for c in ALL_METRIC_CARDS if c.enabled], key=lambda x: x.priority)


def get_card_config(metric_id: str) -> Optional[MetricCardConfig]:
    """根据指标ID获取卡片配置"""
    for card in ALL_METRIC_CARDS:
        if card.metric_id == metric_id:
            return card
    return None
