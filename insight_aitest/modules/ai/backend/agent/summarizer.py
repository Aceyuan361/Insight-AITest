# -*- coding: utf-8 -*-
"""会话上下文摘要与注入逻辑。

当历史消息超过阈值时，对早期消息生成结构化摘要：
- topics: 讨论过的主题
- decisions: 已做的决策（如选了策略A）
- artifacts: 生成的产物（用例批次/报告）
- open_questions: 待解决的问题

摘要缓存到 conversation.summary_json，避免重复计算。
注入时作为 system 消息替代被截断的早期消息。
"""

from __future__ import annotations

SUMMARY_THRESHOLD = 20  # 历史消息超过此值时触发摘要
RECENT_KEEP = 10  # 保留最近 N 条不摘要

_SUMMARIZE_PROMPT = """请将以下对话历史压缩为结构化摘要。

对话历史：
{messages_text}

输出严格 JSON：
{{
  "topics": ["讨论的主题1", "主题2"],
  "decisions": ["已做的决策1", "决策2"],
  "artifacts": [{{"type": "test_cases", "batch_id": "...", "count": 10}}],
  "open_questions": ["待解决问题1", "问题2"]
}}

要求：
1. topics: 用户讨论的核心主题
2. decisions: 用户做出的选择（如选了哪个策略）
3. artifacts: 生成的产物（用例/报告/执行结果）
4. open_questions: 未解决或待确认的问题
5. 保持简洁，每个字段不超过5项
6. 不要输出 JSON 以外的内容。"""


def _format_messages_for_summary(messages) -> str:
    """把消息列表格式化为文本。"""
    parts = []
    for m in messages:
        role = m.role.value if hasattr(m.role, "value") else str(m.role)
        content = (m.content or "")[:500]  # 截断防止超长
        parts.append(f"[{role}] {content}")
    return "\n".join(parts)


def summarize_context(
    conv_id: int,
    db,  # AIDatabase
    llm,  # LLMClient
    force_refresh: bool = False,
) -> dict | None:
    """生成或复用会话上下文摘要。

    历史消息不足阈值时返回 None（不摘要）。
    force_refresh=False 时优先使用缓存。
    """
    all_msgs = db.list_messages(conv_id)

    if len(all_msgs) < SUMMARY_THRESHOLD:
        return None

    # 检查缓存
    if not force_refresh:
        cached = db.get_summary(conv_id)
        if cached:
            return cached

    # 对早期消息生成摘要（保留最近 RECENT_KEEP 条不摘要）
    early_msgs = all_msgs[:-RECENT_KEEP] if len(all_msgs) > RECENT_KEEP else all_msgs
    prompt = _SUMMARIZE_PROMPT.format(messages_text=_format_messages_for_summary(early_msgs))

    try:
        raw = llm.chat([{"role": "user", "content": prompt}])
        from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json
        data = _extract_json(raw)
        if not data or not isinstance(data, dict):
            return None
        summary = {
            "topics": data.get("topics", [])[:5],
            "decisions": data.get("decisions", [])[:5],
            "artifacts": data.get("artifacts", [])[:5],
            "open_questions": data.get("open_questions", [])[:5],
        }
        # 缓存
        db.save_summary(conv_id, summary)
        return summary
    except Exception:
        return None


def format_summary_for_injection(summary: dict) -> str:
    """把摘要格式化为 system 消息内容。"""
    parts = ["=== 会话上下文摘要 ==="]
    if summary.get("topics"):
        parts.append(f"讨论主题：{', '.join(summary['topics'])}")
    if summary.get("decisions"):
        parts.append(f"已做决策：{', '.join(summary['decisions'])}")
    if summary.get("artifacts"):
        arts = [f"{a.get('type', '?')}" for a in summary["artifacts"]]
        parts.append(f"已生成产物：{', '.join(arts)}")
    if summary.get("open_questions"):
        parts.append(f"待解决问题：{', '.join(summary['open_questions'])}")
    return "\n".join(parts)
