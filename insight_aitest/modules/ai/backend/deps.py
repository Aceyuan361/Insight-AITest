# -*- coding: utf-8 -*-
"""AI 模块依赖注入。

瘦身后：KB/LLM 服务从平台 platform.services.kb.deps 获取；ai 模块只保留
AIDatabase（会话/消息，ai.db）和 RagAgent（组合平台 retriever/llm）。
PUT /config 时调用 reset_singletons() 重建。
"""

from __future__ import annotations

import os

from insight_aitest.platform.services.llm.config import AIConfig
from insight_aitest.modules.ai.backend.persistence.database import AIDatabase

# KB/LLM 单例委托给平台服务
import insight_aitest.platform.services.kb.deps as _kb_deps

# ai 模块自己的 ai.db（会话/消息）
_db: AIDatabase | None = None
_agent = None  # RagAgent，延迟 import 避免循环
_planner = None  # Agent Planner（子项目2）
_executor = None  # Agent TaskExecutor（子项目2）


def get_config() -> AIConfig:
    """配置（平台共享，ai 用别名 AIConfig）。"""
    return _kb_deps.get_llm_config()


def set_config_file(path: str | None) -> None:
    _kb_deps.set_config_file(path)


def get_db() -> AIDatabase:
    """ai 模块会话/消息库（ai.db）。"""
    global _db
    if _db is None:
        _db = AIDatabase(os.path.expanduser("~/.insight_eye/ai.db"))
    return _db


def get_llm():
    return _kb_deps.get_llm()


def get_kb_db():
    """平台知识库（文档/分块/向量，kb.db）。"""
    return _kb_deps.get_kb_db()


def get_vector_store():
    return _kb_deps.get_vector_store()


def get_retriever():
    return _kb_deps.get_retriever()


def get_agent():
    global _agent
    if _agent is None:
        from insight_aitest.modules.ai.backend.agent.rag import RagAgent

        _agent = RagAgent(get_retriever(), get_llm(), get_config())
    return _agent


def get_planner():
    """Agent Plan 生成器（子项目2）。"""
    global _planner
    if _planner is None:
        from insight_aitest.modules.ai.backend.agent.planner import Planner

        _planner = Planner(get_llm(), get_config())
    return _planner


def get_executor(
    project_id: int | None = None,
    version_id: int | None = None,
    use_kb: bool = True,
    task_id: int | None = None,
    task_db=None,
    queue=None,
    evt_loop=None,
):
    """Agent Task 执行器（子项目2 + 执行闭环）。每次调用构建新的 SkillContext。

    use_kb=False 时注入 NullRetriever（检索器/生成器均不查知识库），
    适合"纯 LLM 生成"场景——不是所有需求文档都需要 RAG 召回。
    task_id/task_db/queue 非 None 时注入 SkillContext，供 skill 推送进度事件。
    """
    from insight_aitest.modules.ai.backend.agent.skills import SkillContext
    from insight_aitest.modules.ai.backend.agent.executor import TaskExecutor
    from insight_aitest.modules.testcase.backend.deps import get_tc_db, get_generator
    from insight_aitest.platform.services.kb.retriever import NullRetriever

    # 执行闭环依赖：API 运行记录库（延迟 import 避免循环）
    try:
        from insight_aitest.modules.api.backend.deps import get_run_db

        api_run_db = get_run_db()
    except Exception:
        api_run_db = None  # API 模块未启用时，执行类 skill 不可用

    # UI 执行依赖：UI 运行记录库（延迟 import 避免循环）
    try:
        from insight_aitest.modules.ui.backend.deps import get_run_db as get_ui_run_db

        ui_run_db = get_ui_run_db()
    except Exception:
        ui_run_db = None  # UI 模块未启用时，UI 执行 skill 不可用

    # 套件执行依赖（延迟 import 避免循环）
    try:
        from insight_aitest.modules.api.backend.deps import get_suite_db, get_suite_run_db

        suite_db = get_suite_db()
        suite_run_db = get_suite_run_db()
    except Exception:
        suite_db = None
        suite_run_db = None

    if use_kb:
        retriever = get_retriever()
        generator = get_generator()
    else:
        # use_kb=False：注入空检索器，生成器也用空检索器构建（无参考资料 → 纯 LLM 生成）
        retriever = NullRetriever()
        from insight_aitest.modules.testcase.backend.generator.generator import Generator

        generator = Generator(retriever, get_llm(), get_config())

    ctx = SkillContext(
        llm=get_llm(),
        config=get_config(),
        retriever=retriever,
        generator=generator,
        case_db=get_tc_db(),
        project_id=project_id,
        version_id=version_id,
        task_id=task_id,
        task_db=task_db,
        queue=queue,
        _loop=evt_loop,
        api_run_db=api_run_db,
        ui_run_db=ui_run_db,
        suite_db=suite_db,
        suite_run_db=suite_run_db,
    )
    return TaskExecutor(ctx)


def reset_singletons() -> None:
    """PUT /config 后调用：重建平台 KB/LLM + ai agent。"""
    global _agent, _planner
    _kb_deps.reset_llm_singletons()
    _agent = None
    _planner = None
