# -*- coding: utf-8 -*-
"""Agent Skill 注册表（子项目2 + 执行闭环）。

每个 skill 是一个 SkillSpec：声明名称、描述、参数说明，和一个 execute 函数。
execute 接收 (params, ctx) 执行并返回结果摘要 dict。

现有 skill：
- rag_search: 检索知识库（复用 Retriever）
- write_functional_case: 生成功能用例（复用 Generator + TestCaseDatabase 落库）
- write_api_case: 生成接口用例（同上，type=api）
- execute_api_case: 执行一条 API 用例（复用 api/engine/executor），返回 pass/fail + 失败明细
- analyze_failure: LLM 分析执行失败步骤，输出根因摘要（闭环用）
- fix_api_case: LLM 基于根因重写 content，落库（闭环用）
- fix_ui_case: LLM 基于根因重写 UI 用例 content，落库（闭环用）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    import httpx
    from insight_aitest.platform.services.llm.client import LLMClient
    from insight_aitest.platform.services.llm.config import LLMConfig
    from insight_aitest.platform.services.kb.retriever import Retriever
    from insight_aitest.modules.api.backend.persistence.database import RunDatabase
    from insight_aitest.modules.api.backend.persistence.suite_database import (
        SuiteDatabase,
        SuiteRunDatabase,
    )
    from insight_aitest.modules.testcase.backend.generator.generator import Generator
    from insight_aitest.modules.testcase.backend.persistence.database import TestCaseDatabase
    from insight_aitest.modules.ui.backend.persistence.database import UIRunDatabase


@dataclass
class SkillContext:
    """skill 执行时的上下文（由 executor 注入依赖）。"""

    llm: "LLMClient"
    config: "LLMConfig"
    retriever: "Retriever"
    generator: "Generator"
    case_db: "TestCaseDatabase"
    project_id: int | None = None
    version_id: int | None = None
    task_id: int | None = None  # 当前 task ID，供 skill 更新进度
    task_db: "Any | None" = None  # AIDatabase，供 skill 更新 task 进度
    queue: "Any | None" = None  # SSE 事件队列，供 skill 推送进度事件
    _loop: "Any | None" = None  # 事件循环，供 skill 跨线程推送队列事件
    # 执行闭环依赖（execute_api_case 用；不注入则执行类 skill 不可用）
    api_run_db: "RunDatabase | None" = None
    http_transport: "httpx.BaseTransport | None" = None  # 测试注入 MockTransport
    # UI 执行依赖（execute_ui_case 用；不注入则 UI 执行 skill 不可用）
    ui_run_db: "UIRunDatabase | None" = None
    ui_agent_factory: "Callable | None" = None  # 测试注入 FakeAgent 工厂
    ui_batch_db: "Any | None" = None  # UI 批量执行记录库（run_ui_batch 用）
    # 套件执行依赖（run_api_suite 用；不注入则套件 skill 不可用）
    suite_db: "SuiteDatabase | None" = None
    suite_run_db: "SuiteRunDatabase | None" = None


@dataclass
class SkillSpec:
    """skill 声明。"""

    id: str
    name: str  # 给用户看的名称
    description: str  # 给 LLM prompt 看的能力描述
    params_description: str  # 参数说明（给 LLM prompt 看）
    execute: Callable[[dict, SkillContext], dict]  # (params, ctx) -> 结果摘要


# ===== skill 实现 =====


def _rag_search(params: dict, ctx: SkillContext) -> dict:
    """检索知识库，返回命中片段摘要。

    KB 升级：强制按 ctx.project_id 隔离检索范围，杜绝跨项目文档污染。
    project_id=None 时检索未分类文档（兼容旧行为），但推荐用户始终绑定项目。
    """
    query = params.get("query", "")
    document_ids = params.get("document_ids")  # 可选，限定文档范围
    try:
        scored = ctx.retriever.retrieve(
            query, document_ids=document_ids, project_id=ctx.project_id
        )
    except Exception:
        scored = []
    chunks = [
        {"doc": s.document.filename, "snippet": s.chunk.text[:200], "score": round(s.score, 3)}
        for s in scored[:5]  # 最多取 top 5
    ]
    return {"chunks": chunks, "count": len(chunks)}


def _write_case(params: dict, ctx: SkillContext, case_type: str) -> dict:
    """生成测试用例并落库。case_type = functional | api。"""
    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType

    query = params.get("query", "")
    design = params.get("design", "positive")
    document_ids = params.get("document_ids")

    # 构造一个 TestPoint 驱动 Generator
    point = TestPoint(
        id=f"agent-{case_type}",
        summary=query,
        suggested_type=CaseType(case_type),
        suggested_design=TestType(design),
        rationale="Agent 自动生成",
    )
    case = ctx.generator.generate(point, document_ids=document_ids, project_id=ctx.project_id)

    # 落库 + 关联 project
    case.project_id = ctx.project_id
    case.version_id = ctx.version_id
    case.source = f"ai:agent:{ctx.config.chat_model}"
    case_id = ctx.case_db.create_case(case)

    return {
        "case_id": case_id,
        "title": case.title,
        "type": case_type,
        "source": case.source,
    }


def _write_functional_case(params: dict, ctx: SkillContext) -> dict:
    return _write_case(params, ctx, "functional")


def _write_api_case(params: dict, ctx: SkillContext) -> dict:
    return _write_case(params, ctx, "api")


# ===== 执行闭环 skill =====


def _collect_failures(steps: list) -> list[dict]:
    """从 RunRecord.steps 抽取未通过步骤的失败明细（供 analyze_failure / 前端展示）。

    兼容 API StepResult（request/status_code/assertions）和 UIStepResult（kind/prompt/screenshot），
    以及历史 dict 记录。缺失字段统一为 None。
    """
    failures = []
    for sr in steps:
        # sr 是 StepResult/UIStepResult（dataclass）或 dict（历史记录）
        is_dict = isinstance(sr, dict)

        def _get(key, default=None):
            return sr.get(key, default) if is_dict else getattr(sr, key, default)

        if _get("passed"):
            continue
        failures.append(
            {
                "step_index": _get("step_index"),
                "error": _get("error"),
                # API 步骤特有（UI 步骤为 None）
                "request": _get("request"),
                "status_code": _get("status_code"),
                "assertions": _get("assertions"),
                # UI 步骤特有（API 步骤为 None）
                "kind": _get("kind"),
                "prompt": _get("prompt"),
                "screenshot": _get("screenshot"),
            }
        )
    return failures


def _execute_api_case(params: dict, ctx: SkillContext) -> dict:
    """执行一条 API 用例，返回 pass/fail + 失败明细。

    与 routes/runs.py::execute_case 同构：读 content → execute() → create_run → 回填 D。
    断言失败不抛异常（失败是闭环输入），只有用例不存在/content 非法才抛。
    """
    if ctx.api_run_db is None:
        raise RuntimeError("执行引擎未就绪：SkillContext.api_run_db 未注入")

    from insight_aitest.modules.api.backend.engine.executor import (
        _validate_content,
        execute,
    )

    case_id = params.get("case_id")
    if not isinstance(case_id, int):
        raise ValueError("execute_api_case 缺少合法的 case_id")

    case = ctx.case_db.get_case(case_id)
    if case is None:
        raise ValueError(f"用例 {case_id} 不存在")

    content = case.content or {}
    # 可选环境覆盖
    environment_id = params.get("environment_id")
    if environment_id is not None:
        from insight_aitest.modules.api.backend.deps import get_env_db

        env = get_env_db().get(environment_id)
        if env is None:
            raise ValueError(f"环境 {environment_id} 不存在")
        import copy

        content = copy.deepcopy(content)
        content["base_url"] = env.base_url

    _validate_content(content)  # 非法 schema 抛 ValueError → 记为 step_error
    run = execute(
        content,
        transport=ctx.http_transport,
        case_id=case_id,
        case_title=case.title or "",
    )
    run.id = ctx.api_run_db.create_run(run)

    # 回填 D 的 last_result / last_run_at（失败不阻断）
    try:
        ctx.case_db.update_result(case_id, run.status.value, run.finished_at)
    except Exception:
        pass

    failures = _collect_failures(run.steps)
    return {
        "case_id": case_id,
        "run_id": run.id,
        "status": run.status.value,  # passed | failed | error
        "passed_steps": run.passed_steps,
        "total_steps": run.total_steps,
        "duration_ms": run.duration_ms,
        "failures": failures,
    }


def _execute_ui_case(params: dict, ctx: SkillContext) -> dict:
    """执行一条 UI 用例（异步引擎 → asyncio.run 桥接到同步 skill）。

    与 routes/ui/runs.py::execute_case 同构，区别：UI 引擎是 async 协程（真启动
    Playwright Chromium），故用 asyncio.run 在后台线程的临时事件循环里执行。
    """
    import asyncio

    if ctx.ui_run_db is None:
        raise RuntimeError("UI 执行引擎未就绪：SkillContext.ui_run_db 未注入")

    from insight_aitest.modules.ui.backend.engine.executor import (
        _validate_content,
        execute,
    )

    case_id = params.get("case_id")
    if not isinstance(case_id, int):
        raise ValueError("execute_ui_case 缺少合法的 case_id")

    case = ctx.case_db.get_case(case_id)
    if case is None:
        raise ValueError(f"用例 {case_id} 不存在")

    content = case.content or {}
    base_url_override = params.get("base_url")  # 可选 base_url 覆盖
    _validate_content(content)

    # async → sync 桥接：后台线程无运行中事件循环，asyncio.run 创建临时 loop
    # async sync bridge: asyncio.run fails if thread already has a running loop
    async def _do_execute():
        return await execute(
            content,
            agent_factory=ctx.ui_agent_factory,
            case_id=case_id,
            case_title=case.title or "",
            base_url_override=base_url_override,
        )

    try:
        run = asyncio.run(_do_execute())
    except RuntimeError:
        # thread already has a running event loop: spin up a dedicated thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _do_execute())
            run = future.result()
    run.id = ctx.ui_run_db.create_run(run)

    # 回填 D 的 last_result / last_run_at（失败不阻断）
    try:
        ctx.case_db.update_result(case_id, run.status.value, run.finished_at)
    except Exception:
        pass

    failures = _collect_failures(run.steps)
    # 收集失败步截图路径（UI 特有）
    screenshots = [
        {"step_index": f.get("step_index"), "path": _ui_step_screenshot(f)}
        for f in failures
        if _ui_step_screenshot(f)
    ]
    return {
        "case_id": case_id,
        "run_id": run.id,
        "status": run.status.value,  # passed | failed | error
        "passed_steps": run.passed_steps,
        "total_steps": run.total_steps,
        "duration_ms": run.duration_ms,
        "failures": failures,
        "screenshots": screenshots,
    }


def _ui_step_screenshot(failure: dict) -> str | None:
    """从 UI 失败步提取截图路径（API 步骤无此字段，返回 None）。"""
    # UIStepResult 序列化后可能有 screenshot 字段；失败步 dict 当前不含它
    # 从原始 step dict 取（_collect_failures 当前只取 request/assertions/error）
    return failure.get("screenshot")


_ANALYZE_PROMPT = """你是一个资深接口测试工程师。一条 API 用例执行失败了，请分析失败根因。

用例标题：{title}
用例 content（请求定义）：
{content}

失败的步骤明细：
{failures}

请分析失败原因并输出 JSON（不要额外解释）：
{{"root_cause": "一句话根因（如：断言期望200但实际返回404，因为路径拼写错误）", "analysis": "2-3句详细分析", "suggested_fix": "具体修复建议（如：把 path 从 /usre/login 改为 /user/login）"}}"""


def _analyze_failure(params: dict, ctx: SkillContext) -> dict:
    """LLM 分析执行失败步骤 → 根因摘要。"""
    import json

    from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json

    case_id = params.get("case_id")
    if not isinstance(case_id, int):
        raise ValueError("analyze_failure 缺少合法的 case_id")

    case = ctx.case_db.get_case(case_id)
    if case is None:
        raise ValueError(f"用例 {case_id} 不存在")

    failures = params.get("failures") or []
    prompt = _ANALYZE_PROMPT.format(
        title=case.title or "",
        content=json.dumps(case.content or {}, ensure_ascii=False)[:2000],
        failures=json.dumps(failures, ensure_ascii=False)[:2000],
    )
    raw = ctx.llm.chat([{"role": "user", "content": prompt}])
    data = _extract_json(raw)

    if not data or not isinstance(data, dict):
        # 降级：机械摘要
        data = {
            "root_cause": "无法解析失败原因",
            "analysis": f"共 {len(failures)} 个步骤未通过",
            "suggested_fix": "请人工检查用例请求与断言",
        }

    return {
        "case_id": case_id,
        "run_id": params.get("run_id"),
        "root_cause": data.get("root_cause", ""),
        "analysis": data.get("analysis", ""),
        "suggested_fix": data.get("suggested_fix", ""),
    }


_FIX_PROMPT = """你是一个资深接口测试工程师。一条 API 用例执行失败了，根据根因分析修复用例的 content。

当前用例 content：
{content}

根因分析：
- 根因：{root_cause}
- 分析：{analysis}
- 建议：{suggested_fix}

请输出修复后的完整 content JSON（不要额外解释，直接输出 JSON 对象）。
content 必须包含 base_url（字符串）和 steps（数组），每个 step 至少有 method 和 path：
{{"base_url": "...", "steps": [{{"method": "GET", "path": "/...", "headers": {{}}, "body": {{}}, "assertions": [{{"type": "status_code", "expected": 200}}]}}]}}"""


def _fix_api_case(params: dict, ctx: SkillContext) -> dict:
    """LLM 基于根因重写 content，校验后落库。"""
    import json

    from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json
    from insight_aitest.modules.testcase.backend.generator.schemas import validate_content

    case_id = params.get("case_id")
    if not isinstance(case_id, int):
        raise ValueError("fix_api_case 缺少合法的 case_id")

    case = ctx.case_db.get_case(case_id)
    if case is None:
        raise ValueError(f"用例 {case_id} 不存在")

    analysis = params.get("analysis") or {}
    prompt = _FIX_PROMPT.format(
        content=json.dumps(case.content or {}, ensure_ascii=False)[:2000],
        root_cause=analysis.get("root_cause", ""),
        analysis=analysis.get("analysis", ""),
        suggested_fix=analysis.get("suggested_fix", ""),
    )
    raw = ctx.llm.chat([{"role": "user", "content": prompt}])
    data = _extract_json(raw)

    if not data or not isinstance(data, dict):
        return {"case_id": case_id, "fixed": False, "reason": "LLM 未返回合法 JSON"}

    if not validate_content("api", data):
        return {
            "case_id": case_id,
            "fixed": False,
            "reason": "修复后 content 校验未通过，保留原内容",
        }

    # 落库（保留 base_url，因为 LLM 可能改它）
    ctx.case_db.update_case(case_id, content=data)
    return {
        "case_id": case_id,
        "fixed": True,
        "content": data,
    }


_FIX_UI_PROMPT = """你是测试工程师。UI 用例执行失败，请根据根因重写用例 content。

当前 content：
{content}

失败根因：{root_cause}
分析：{analysis}
建议：{suggested_fix}

请输出修复后的完整 content JSON（不要额外解释）。
content 必须包含 base_url（字符串）和 steps（数组），每个 step 至少有 kind（action|assert|extract）：
{{"base_url": "...", "steps": [{{"kind": "action", "action": "操作描述"}}]}}"""


def _fix_ui_case(params: dict, ctx: SkillContext) -> dict:
    """LLM 基于根因重写 UI 用例 content，校验后落库。"""
    import json
    from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json
    from insight_aitest.modules.testcase.backend.generator.schemas import validate_content

    case_id = params.get("case_id")
    if not isinstance(case_id, int):
        raise ValueError("fix_ui_case 缺少合法的 case_id")
    case = ctx.case_db.get_case(case_id)
    if case is None:
        raise ValueError(f"用例 {case_id} 不存在")

    analysis = params.get("analysis") or {}
    prompt = _FIX_UI_PROMPT.format(
        content=json.dumps(case.content or {}, ensure_ascii=False)[:2000],
        root_cause=analysis.get("root_cause", ""),
        analysis=analysis.get("analysis", ""),
        suggested_fix=analysis.get("suggested_fix", ""),
    )
    raw = ctx.llm.chat([{"role": "user", "content": prompt}])
    data = _extract_json(raw)
    if not data or not isinstance(data, dict):
        return {"case_id": case_id, "fixed": False, "reason": "LLM 未返回合法 JSON"}
    if not validate_content("ui", data):
        return {
            "case_id": case_id,
            "fixed": False,
            "reason": "修复后 content 校验未通过，保留原内容",
        }
    ctx.case_db.update_case(case_id, content=data)
    return {"case_id": case_id, "fixed": True, "content": data}


# ===== 截图 → UI 用例 skill =====


def _write_ui_case_from_image(params: dict, ctx: SkillContext) -> dict:
    """从截图生成 UI 用例并落库。

    复用 Generator.generate_from_image（vision 模型理解截图布局 + 交互元素）。
    图片以 base64（无 data: 前缀）+ mime 在 params.images 直传，与 /testcases/generate-from-image 路由一致。
    base_url 必填，强制覆盖 LLM 输出（防编造）。
    """
    raw_images = params.get("images") or []
    if not raw_images:
        raise ValueError("write_ui_case_from_image 缺少 images（至少 1 张截图）")

    base_url = params.get("base_url")
    if not isinstance(base_url, str) or not base_url:
        raise ValueError("write_ui_case_from_image 缺少合法的 base_url")

    images = [(img["data"], img.get("mime", "image/png")) for img in raw_images]
    point_summary = params.get("point_summary", "")

    case = ctx.generator.generate_from_image(images, base_url, point_summary)
    case.project_id = ctx.project_id
    case.version_id = ctx.version_id
    case.source = f"ai:agent-vision:{ctx.config.chat_model}"
    case_id = ctx.case_db.create_case(case)

    return {
        "case_id": case_id,
        "title": case.title,
        "type": "ui",
        "source": case.source,
    }


# ===== 数据驱动 skill =====


_DATA_DRIVEN_PROMPT = """你是一名资深接口测试工程师。请生成一条「数据驱动」的 API 测试用例：用一个模板请求（body 里的可变字段用占位符）+ 多组测试数据，覆盖边界值和等价类。

可用 skill：{catalog}

测试目标：{query}
{refs_section}
要求：
1. body 中需要变化的字段用占位符 `"{{{{占位符}}}}"` 形式（注意：占位符必须放在双引号内，即使是数字字段，如 `"age": "{{{{age}}}}"`）
2. datasets 是多组测试数据，每组 {{name, vars}}：name 是数据组描述，vars 是占位符 → 值的映射（值可以是字符串或数字）
3. 至少 3 组数据（正向 / 边界 / 非法），覆盖典型场景
4. assertions 至少包含 status_code 断言
5. 输出严格的 JSON 对象（不要额外解释，不要 markdown 代码块）：
{{
  "title": "用例标题",
  "description": "用例描述",
  "preconditions": "前置条件",
  "content": {{
    "base_url": "https://目标地址",
    "steps": [
      {{
        "method": "POST",
        "path": "/api/xxx",
        "headers": {{"Content-Type": "application/json"}},
        "body": {{"username": "{{{{username}}}}", "age": "{{{{age}}}}"}},
        "assertions": [{{"type": "status_code", "expected": 200}}]
      }}
    ],
    "datasets": [
      {{"name": "正向-合法值", "vars": {{"username": "alice", "age": 25}}}},
      {{"name": "边界-最小", "vars": {{"username": "a", "age": 0}}}},
      {{"name": "非法-异常值", "vars": {{"username": "<script>", "age": -1}}}}
    ]
  }}
}}"""


def _generate_data_driven_api_case(params: dict, ctx: SkillContext) -> dict:
    """LLM 生成一条数据驱动 API 用例（模板 content + datasets 多组数据），落库。

    content.body 用 {{{{var}}}} 占位，datasets 提供多组测试数据。
    执行时由 execute_data_driven_api_case 循环每组数据。
    """
    from insight_aitest.modules.testcase.backend.generator.analyzer import _extract_json
    from insight_aitest.modules.testcase.backend.generator.prompts import _format_refs
    from insight_aitest.modules.testcase.backend.persistence.models import (
        CasePriority,
        CaseStatus,
        CaseType,
        TestCase,
        TestType,
    )
    from insight_aitest.modules.testcase.backend.generator.schemas import validate_content

    query = params.get("query", "")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("generate_data_driven_api_case 缺少 query（测试目标描述）")
    document_ids = params.get("document_ids")

    # 可选 RAG 检索（与 _write_case 一致的检索逻辑）
    refs_section = ""
    chunks: list[tuple[str, str]] = []
    try:
        scored = ctx.retriever.retrieve(
            query, document_ids=document_ids, project_id=ctx.project_id
        )
        chunks = [(s.document.filename, s.chunk.text[:500]) for s in scored[:3]]
        if chunks:
            refs_section = f"\n参考资料：\n{_format_refs(chunks)}"
    except Exception:
        pass

    prompt = _DATA_DRIVEN_PROMPT.format(
        catalog=get_skill_catalog(),
        query=query,
        refs_section=refs_section,
    )
    raw = ctx.llm.chat([{"role": "user", "content": prompt}])
    data = _extract_json(raw)

    if not data or not isinstance(data, dict):
        raise ValueError("LLM 未返回合法的 JSON")

    content = data.get("content", {})
    if not isinstance(content, dict):
        content = {}

    # datasets 缺失 → 降级为单组空 vars（等价普通用例）
    if not isinstance(content.get("datasets"), list) or not content["datasets"]:
        content["datasets"] = [{"name": "默认", "vars": {}}]

    is_valid = validate_content("api", content)
    case = TestCase(
        title=data.get("title", f"数据驱动用例 ({query[:30]})"),
        type=CaseType.API,
        description=data.get("description", ""),
        priority=CasePriority.P2,
        status=CaseStatus.DRAFT,
        test_design=TestType.POSITIVE,
        preconditions=data.get("preconditions", ""),
        content=content,
        source=f"ai:agent-datadriven:{ctx.config.chat_model}",
        tags=["data-driven"],
    )
    case.project_id = ctx.project_id
    case.version_id = ctx.version_id
    case_id = ctx.case_db.create_case(case)

    return {
        "case_id": case_id,
        "title": case.title,
        "type": "api",
        "source": case.source,
        "datasets_count": len(content["datasets"]),
        "valid": is_valid,
    }


def _execute_data_driven_api_case(params: dict, ctx: SkillContext) -> dict:
    """循环执行数据驱动 API 用例的每组 dataset，返回聚合结果。

    复用 api/engine/executor.execute(initial_vars=...)：每组 dataset 的 vars
    作为 initial_vars 注入，execute 内部用 inject_variables 替换 {{{{var}}}} 占位。
    缺值的 dataset 会因 UndefinedVariableError 记为 error（正确行为）。
    """
    if ctx.api_run_db is None:
        raise RuntimeError("执行引擎未就绪：SkillContext.api_run_db 未注入")

    from insight_aitest.modules.api.backend.engine.executor import _validate_content, execute

    case_id = params.get("case_id")
    if not isinstance(case_id, int):
        raise ValueError("execute_data_driven_api_case 缺少合法的 case_id")

    case = ctx.case_db.get_case(case_id)
    if case is None:
        raise ValueError(f"用例 {case_id} 不存在")

    content = case.content or {}
    _validate_content(content)

    datasets = content.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        datasets = [{"name": "默认", "vars": {}}]

    base_title = (case.title or "").replace("[数据驱动] ", "")
    per_dataset: list[dict] = []
    passed = 0

    for ds in datasets:
        ds_name = ds.get("name", "未命名") if isinstance(ds, dict) else "未命名"
        ds_vars = ds.get("vars", {}) if isinstance(ds, dict) else {}

        try:
            run = execute(
                content,
                transport=ctx.http_transport,
                case_id=case_id,
                case_title=f"{base_title} [{ds_name}]",
                initial_vars=ds_vars,
            )
            run.id = ctx.api_run_db.create_run(run)
            failures = _collect_failures(run.steps)
            status = run.status.value
            if status == "passed":
                passed += 1
            per_dataset.append(
                {
                    "name": ds_name,
                    "run_id": run.id,
                    "status": status,
                    "passed_steps": run.passed_steps,
                    "total_steps": run.total_steps,
                    "failures": failures,
                }
            )
        except Exception as e:
            per_dataset.append(
                {
                    "name": ds_name,
                    "status": "error",
                    "error": str(e),
                }
            )

    # 回填 case 的 last_result（用整体通过率）
    # 注意：last_result 的已知域是 passed/failed/error（run_api_suite 的回归判定只认这三个），
    # 所以 partial（部分通过）映射为 failed——per-dataset 细节在 RunRecord 里可查。
    overall = "passed" if passed == len(datasets) else "failed"
    try:
        from datetime import datetime

        ctx.case_db.update_result(case_id, overall, datetime.now())
    except Exception:
        pass

    return {
        "case_id": case_id,
        "total_datasets": len(datasets),
        "passed": passed,
        "failed": len(datasets) - passed,
        "overall_status": overall,
        "per_dataset": per_dataset,
    }


# ===== 套件执行 skill =====


def _run_api_suite(params: dict, ctx: SkillContext) -> dict:
    """执行一组 API 用例（套件），含回归判定。

    复用 api/engine/suite_executor.execute_suite。
    回归判定：执行前读每个 case 的 last_result（旧值），执行后对比 ——
    was passed → now failed/error = 回归。
    """
    if ctx.suite_run_db is None:
        raise RuntimeError("套件执行引擎未就绪：SkillContext.suite_run_db 未注入")

    from insight_aitest.modules.api.backend.engine.suite_executor import execute_suite
    from insight_aitest.modules.api.backend.persistence.suite_models import (
        SuiteRunRecord,
        SuiteRunStatus,
    )
    from insight_aitest.modules.api.backend.engine.executor import execute as _exec  # noqa: F401

    # 确定要跑的 case_ids：优先显式传入，其次从已存套件加载
    case_ids = params.get("case_ids")
    suite_id = params.get("suite_id")

    if case_ids and isinstance(case_ids, list):
        suite_def = {
            "id": suite_id or 0,
            "name": params.get("name", "Agent 临时套件"),
            "case_ids": [int(c) for c in case_ids],
            "setup": params.get("setup") or [],
            "teardown": params.get("teardown") or [],
        }
    elif suite_id:
        if ctx.suite_db is None:
            raise RuntimeError("套件库未注入，无法按 suite_id 加载")
        suite = ctx.suite_db.get(int(suite_id))
        if suite is None:
            raise ValueError(f"套件 {suite_id} 不存在")
        suite_def = {
            "id": suite.id,
            "name": suite.name,
            "case_ids": suite.case_ids or [],
            "setup": suite.setup or [],
            "teardown": suite.teardown or [],
        }
    else:
        raise ValueError("run_api_suite 需要 suite_id 或 case_ids")

    # 环境（可选）
    environment = None
    environment_id = params.get("environment_id")
    if environment_id is not None:
        from insight_aitest.modules.api.backend.deps import get_env_db

        environment = get_env_db().get(int(environment_id))

    # 执行前快照每个 case 的 last_result（回归基线）
    baselines: dict[int, str | None] = {}
    for cid in suite_def["case_ids"]:
        case = ctx.case_db.get_case(cid)
        baselines[cid] = case.last_result if case else None

    # cases_provider / run_saver（对齐 routes/suites.py 模式）
    def cases_provider(cid: int) -> dict | None:
        case = ctx.case_db.get_case(cid)
        if case is None:
            return None
        return {"title": case.title, "content": case.content or {}}

    def run_saver(run) -> int:
        run_id = ctx.api_run_db.create_run(run)
        try:
            ctx.case_db.update_result(run.case_id, run.status.value, run.finished_at)
        except Exception:
            pass
        return run_id

    # 持久化 SuiteRunRecord
    started_at = __import__("datetime").datetime.now()
    suite_run = SuiteRunRecord(
        suite_id=suite_def["id"],
        suite_name=suite_def["name"],
        suite_snapshot=suite_def,
        environment_id=int(environment_id) if environment_id else None,
        environment_name=environment.name if environment else None,
        status=SuiteRunStatus.RUNNING,
        total=len(suite_def["case_ids"]),
        done=0,
        case_run_ids=[],
        started_at=started_at,
    )
    srid = ctx.suite_run_db.create(suite_run)

    # 执行
    # per-case SSE progress callback
    def _on_case_done(done_count: int, run_id: int) -> None:
        if ctx.queue is not None and ctx._loop is not None:
            import asyncio as _aio
            evt = {
                "type": "suite_case_done",
                "data": {"done": done_count, "total": len(suite_def["case_ids"]), "run_id": run_id},
            }
            try:
                ctx.queue.put_nowait(evt)
            except _aio.QueueFull:
                pass

    result = execute_suite(
        suite=suite_def,
        cases_provider=cases_provider,
        run_saver=run_saver,
        transport=ctx.http_transport,
        environment=environment,
        on_case_done=_on_case_done,
    )

    # 收尾 SuiteRunRecord
    ctx.suite_run_db.finish(
        srid,
        status=result["status"],
        error=result.get("error"),
    )
    if result.get("setup_status"):
        ctx.suite_run_db.update_setup_status(srid, result["setup_status"])

    # 回归判定：用 case_run_ids 对应的 run 反查每个 case 的最终状态
    # run_saver 已回填 case.last_result，重读对比基线
    case_results = []
    regressions = []
    for cid in suite_def["case_ids"]:
        case = ctx.case_db.get_case(cid)
        new_result = case.last_result if case else None
        baseline = baselines.get(cid)
        is_regression = baseline == "passed" and new_result in ("failed", "error")
        case_results.append(
            {
                "case_id": cid,
                "baseline": baseline,
                "current": new_result,
                "regression": is_regression,
            }
        )
        if is_regression:
            regressions.append(cid)

    status_value = (
        result["status"].value if hasattr(result["status"], "value") else str(result["status"])
    )
    return {
        "suite_run_id": srid,
        "status": status_value,  # completed | failed
        "done": result["done"],
        "total": len(suite_def["case_ids"]),
        "setup_status": result.get("setup_status"),
        "case_results": case_results,
        "regressions": regressions,
        "regression_count": len(regressions),
    }


# ===== 审阅面板批量 skill（阶段1：提取测试点 + 阶段2：批量生成）=====


def _extract_test_points(params: dict, ctx: SkillContext) -> dict:
    """阶段1：通过 Analyzer.analyze()（统一 prompt）从需求文档提取测试点列表。

    返回 {{"test_points": [...], "count": N}}，每条含
    id/summary/suggested_type/suggested_design/rationale（与 Analyzer 的 TestPoint 同字段）。
    prompt 统一走 ``build_analyze_prompt``（与 testcase 模块 /analyze 同源），
    消除此前分叉的 ``_EXTRACT_POINTS_PROMPT``。
    """
    query = params.get("query", "")
    document_ids = params.get("document_ids")

    from insight_aitest.modules.testcase.backend.deps import get_analyzer

    analyzer = get_analyzer()
    points = analyzer.analyze(query, document_ids=document_ids)

    serialized = [
        {
            "id": p.id,
            "summary": p.summary,
            "suggested_type": p.suggested_type.value,
            "suggested_design": p.suggested_design.value,
            "rationale": p.rationale,
        }
        for p in points
    ]
    return {"test_points": serialized, "count": len(serialized)}


def _write_cases_batch(params: dict, ctx: SkillContext) -> dict:
    """阶段2：批量生成用例（逐条调 generator.generate）。

    对每个测试点构造 TestPoint → generator.generate → 落库。单条失败不中断，记录 failed。
    每条标记 source=ai:batch:{{model}}、task_id、batch_id。
    """
    import time

    from insight_aitest.modules.testcase.backend.generator.analyzer import TestPoint
    from insight_aitest.modules.testcase.backend.persistence.models import CaseType, TestType

    test_points = params.get("test_points") or []
    task_id = params.get("task_id")
    document_ids = params.get("document_ids")  # 需求文档 ID 列表，传给 generator 限定 RAG 检索范围
    batch_id = (
        f"batch-{task_id}-{int(time.time())}"
        if task_id is not None
        else f"batch-manual-{int(time.time())}"
    )
    case_ids = []
    failed = 0
    total = len(test_points)
    # 推送进度事件到 SSE 队列（供前端实时展示）
    queue = ctx.queue
    loop = None
    if queue is not None and hasattr(ctx, "_loop"):
        loop = ctx._loop

    for i, tp in enumerate(test_points):
        if not isinstance(tp, dict):
            continue
        # 每生成一条推送进度
        if queue is not None and loop is not None:
            try:
                import asyncio
                from collections import namedtuple
                Evt = namedtuple("Evt", ["type", "data"])
                asyncio.run_coroutine_threadsafe(
                    queue.put(Evt("progress", {
                        "step": "generate_case",
                        "current": i + 1,
                        "total": total,
                        "message": f"生成用例 {i + 1}/{total}",
                    })),
                    loop,
                )
            except Exception:
                pass
        try:
            # 从测试点 dict 构造 TestPoint 驱动 Generator.generate（字段非法时跳过）
            # 字段映射：优先新结构 summary/suggested_type/suggested_design，
            # 兼容旧结构 description/type_hint/design_hint（审阅面板历史数据）。
            try:
                case_type = CaseType(tp.get("suggested_type", tp.get("type_hint", "functional")))
            except ValueError:
                case_type = CaseType.FUNCTIONAL
            try:
                design = TestType(tp.get("suggested_design", tp.get("design_hint", "positive")))
            except ValueError:
                design = TestType.POSITIVE
            point = TestPoint(
                id=tp.get("id", f"tp-{len(case_ids) + failed + 1}"),
                summary=tp.get("summary", tp.get("description", "")),
                suggested_type=case_type,
                suggested_design=design,
                rationale=tp.get("rationale", "批量生成"),
            )
            case = ctx.generator.generate(
                point,
                document_ids=document_ids,
                project_id=ctx.project_id,
            )
            case.project_id = ctx.project_id
            case.version_id = ctx.version_id
            case.source = f"ai:batch:{ctx.config.chat_model}"
            if task_id is not None:
                case.task_id = task_id
            case.batch_id = batch_id
            case_id = ctx.case_db.create_case(case)
            case_ids.append(case_id)
        except Exception:
            failed += 1
            continue

    # 质量自检：批量生成后自动校验+修复（不合格用例重试生成 1 次，仍不合格标记 ai:invalid）
    from insight_aitest.modules.ai.backend.agent.quality import validate_and_fix_cases
    validation = validate_and_fix_cases(batch_id, document_ids, ctx)

    return {
        "case_ids": case_ids,
        "generated": len(case_ids),
        "failed": failed,
        "batch_id": batch_id,
        "validation": validation,
    }


def _validate_and_fix_cases(params: dict, ctx: SkillContext) -> dict:
    """用例质量自检修复：批量校验用例质量，对不合格用例重试生成。

    校验规则：title/description/preconditions 非空，steps 非空，expected 可验证。
    不合格用例携带需求点 + document_ids 重试生成（1次），仍不合格标记 ai:invalid。
    """
    from insight_aitest.modules.ai.backend.agent.quality import validate_and_fix_cases

    batch_id = params.get("batch_id")
    if not batch_id:
        return {"error": "batch_id 必填"}
    document_ids = params.get("document_ids")
    stats = validate_and_fix_cases(batch_id, document_ids, ctx)
    return stats


def _analyze_coverage(params: dict, ctx: SkillContext) -> dict:
    """需求覆盖度分析：对比需求文档与已生成用例，输出覆盖矩阵+遗漏/冗余+可选补充。"""
    from insight_aitest.modules.ai.backend.agent.coverage import analyze_coverage

    batch_id = params.get("batch_id")
    if not batch_id:
        return {"error": "batch_id 必填"}
    document_ids = params.get("document_ids")
    supplement = params.get("supplement", True)
    result = analyze_coverage(batch_id, document_ids, ctx, supplement=supplement)
    return result


def _summarize_context(params: dict, ctx: SkillContext) -> dict:
    """会话上下文摘要：对长会话历史生成结构化摘要，支持缓存。"""
    from insight_aitest.modules.ai.backend.agent.summarizer import summarize_context

    task_id = params.get("task_id")
    if not task_id:
        return {"error": "task_id 必填"}
    force = params.get("force_refresh", False)

    import insight_aitest.modules.ai.backend.deps as deps
    db = deps.get_db()
    task = db.get_task(task_id)
    if not task or not task.conversation_id:
        return {"summary": None, "reason": "task 无关联会话"}

    summary = summarize_context(task.conversation_id, db, ctx.llm, force_refresh=force)
    return {"summary": summary}




def _run_ui_batch(params: dict, ctx: SkillContext) -> dict:
    """Execute multiple UI cases sequentially (batch mode).

Mirrors UI module batch execution: iterates over case_ids, runs each
via the async UI executor (bridged to sync), persists individual runs,
and returns an aggregate summary.
    """
    import asyncio
    import copy
    from datetime import datetime

    if ctx.ui_run_db is None:
        raise RuntimeError("UI run db not available")
    if ctx.ui_batch_db is None:
        raise RuntimeError("UI batch db not available")

    from insight_aitest.modules.ui.backend.engine.executor import (
        _validate_content,
        execute,
    )
    from insight_aitest.modules.ui.backend.persistence.batch_models import (
        BatchRunStatus,
        UIBatchRun,
    )

    case_ids = params.get("case_ids")
    if not case_ids or not isinstance(case_ids, list):
        raise ValueError("run_ui_batch requires case_ids list")
    case_ids = [int(c) for c in case_ids]
    base_url = params.get("base_url")

    batch = UIBatchRun(
        name=params.get("name", "Agent UI batch"),
        case_ids=case_ids,
        config={"base_url": base_url} if base_url else {},
        status=BatchRunStatus.RUNNING,
        total=len(case_ids),
        started_at=datetime.now(),
    )
    batch_id = ctx.ui_batch_db.create(batch)

    case_results = []
    passed = 0
    failed = 0
    error_count = 0
    case_run_ids = []

    for cid in case_ids:
        case = ctx.case_db.get_case(cid)
        if case is None:
            error_count += 1
            case_results.append({"case_id": cid, "status": "error", "error": "case not found"})
            continue

        content = copy.deepcopy(case.content or {})
        if base_url:
            content["base_url"] = base_url

        try:
            _validate_content(content)
        except ValueError as e:
            error_count += 1
            case_results.append({"case_id": cid, "status": "error", "error": str(e)})
            continue

        async def _do_run():
            return await execute(
                content,
                agent_factory=ctx.ui_agent_factory,
                case_id=cid,
                case_title=case.title or "",
            )

        try:
            try:
                run = asyncio.run(_do_run())
            except RuntimeError:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, _do_run())
                    run = future.result()

            run.id = ctx.ui_run_db.create_run(run)
            case_run_ids.append(run.id)
            status = run.status.value
            if status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
            else:
                error_count += 1
            case_results.append({
                "case_id": cid, "run_id": run.id, "status": status,
                "passed_steps": run.passed_steps, "total_steps": run.total_steps,
            })
        except Exception as e:
            error_count += 1
            case_results.append({"case_id": cid, "status": "error", "error": str(e)})

    if error_count > 0:
        final_status = BatchRunStatus.ERROR
    elif failed > 0:
        final_status = BatchRunStatus.FAILED
    else:
        final_status = BatchRunStatus.PASSED

    ctx.ui_batch_db.update(
        batch_id, status=final_status, passed=passed, failed=failed,
        error=error_count, case_run_ids=case_run_ids, finished_at=datetime.now(),
    )

    return {
        "batch_id": batch_id, "total": len(case_ids),
        "passed": passed, "failed": failed, "error": error_count,
        "overall_status": final_status.value if hasattr(final_status, "value") else str(final_status),
        "per_case": case_results,
    }
# ===== 注册表 =====

SKILLS: dict[str, SkillSpec] = {
    "rag_search": SkillSpec(
        id="rag_search",
        name="检索知识库",
        description="检索项目知识库中与查询相关的文档片段。用于在生成用例前获取需求上下文。",
        params_description='{"query": "检索关键词或问题描述", "document_ids": [可选，限定文档ID]}',
        execute=_rag_search,
    ),
    "write_functional_case": SkillSpec(
        id="write_functional_case",
        name="写功能用例",
        description="基于需求文档生成一条功能测试用例（含操作步骤和预期结果）。",
        params_description='{"query": "测试目标描述", "design": "positive|negative|boundary|edge"}',
        execute=_write_functional_case,
    ),
    "write_api_case": SkillSpec(
        id="write_api_case",
        name="写接口用例",
        description="基于接口文档生成一条 API 接口测试用例（含请求方法、路径、断言）。",
        params_description='{"query": "接口目标描述", "design": "positive|negative|boundary|edge"}',
        execute=_write_api_case,
    ),
    "execute_api_case": SkillSpec(
        id="execute_api_case",
        name="执行接口用例",
        description="执行一条已生成的 API 用例，返回通过/失败状态和失败步骤明细。失败不报错，作为闭环输入。",
        params_description='{"case_id": 用例ID或"$prev"(取上一步生成的用例), "environment_id": [可选，环境ID]}',
        execute=_execute_api_case,
    ),
    "analyze_failure": SkillSpec(
        id="analyze_failure",
        name="分析失败原因",
        description="分析 API 用例执行失败的根因，输出根因摘要和修复建议。通常在 execute_api_case 失败后调用。",
        params_description='{"case_id": 用例ID, "run_id": 执行记录ID, "failures": 失败步骤明细数组}',
        execute=_analyze_failure,
    ),
    "fix_api_case": SkillSpec(
        id="fix_api_case",
        name="修复接口用例",
        description="根据失败分析重写 API 用例的 content（请求/断言），校验通过后落库。通常在 analyze_failure 后调用。",
        params_description='{"case_id": 用例ID, "analysis": analyze_failure 返回的分析对象}',
        execute=_fix_api_case,
    ),
    "fix_ui_case": SkillSpec(
        id="fix_ui_case",
        name="修复UI用例",
        description="根据失败分析重写 UI 用例的 steps（kind/action/assert），校验通过后落库。",
        params_description='{"case_id": 用例ID, "analysis": analyze_failure 返回的分析对象}',
        execute=_fix_ui_case,
    ),
    "execute_ui_case": SkillSpec(
        id="execute_ui_case",
        name="执行UI用例",
        description="执行一条已生成的 UI 用例（启动浏览器模拟用户操作），返回通过/失败状态、失败步骤明细和截图。失败不报错，作为闭环输入。",
        params_description='{"case_id": 用例ID或"$prev"(取上一步生成的用例), "base_url": [可选，覆盖用例的base_url]}',
        execute=_execute_ui_case,
    ),
    "run_api_suite": SkillSpec(
        id="run_api_suite",
        name="执行接口套件",
        description="批量执行一组 API 用例（套件），自动检测回归（之前通过的现在失败=回归）。可传 case_ids 直接指定用例，或传 suite_id 用已存套件。",
        params_description='{"case_ids": [用例ID数组], "suite_id": [可选，已存套件ID], "environment_id": [可选，环境ID], "setup": [可选], "teardown": [可选]}',
        execute=_run_api_suite,
    ),
    "write_ui_case_from_image": SkillSpec(
        id="write_ui_case_from_image",
        name="截图生成UI用例",
        description="从一张或多张 UI 截图（设计稿/页面截图）生成 UI 测试用例。用 vision 模型理解截图布局和交互元素，生成可执行的 UI 操作步骤。",
        params_description='{"images":[{"data":"base64无data前缀","mime":"image/png"}],"base_url":"目标URL必填","point_summary":"[可选]测试重点描述"}',
        execute=_write_ui_case_from_image,
    ),
    "generate_data_driven_api_case": SkillSpec(
        id="generate_data_driven_api_case",
        name="生成数据驱动用例",
        description="生成一条数据驱动 API 用例：模板请求（body 用占位符）+ 多组测试数据（边界值/等价类），一次定义覆盖多组场景。",
        params_description='{"query":"接口测试目标描述","document_ids":[可选,限定文档ID]}',
        execute=_generate_data_driven_api_case,
    ),
    "execute_data_driven_api_case": SkillSpec(
        id="execute_data_driven_api_case",
        name="执行数据驱动用例",
        description="循环执行数据驱动 API 用例的每组测试数据，返回每组通过/失败状态和聚合结果。占位符缺值的组自动记为 error。",
        params_description='{"case_id":用例ID或"$prev"}',
        execute=_execute_data_driven_api_case,
    ),
    "extract_test_points": SkillSpec(
        id="extract_test_points",
        name="提取测试点",
        description="从需求文档提取测试点列表（测试点的描述/类型/设计维度），作为批量生成用例的输入。"
        "统一走 Analyzer.analyze()（与 testcase 模块 /analyze 同 prompt 源）。",
        params_description='{"query": "测试目标描述", "document_ids": [可选，限定文档ID]}',
        execute=_extract_test_points,
    ),
    "write_cases_batch": SkillSpec(
        id="write_cases_batch",
        name="批量生成用例",
        description="为一批测试点逐条生成用例并落库（每条标记 batch_id/task_id/source=ai:batch）。单条失败不中断，记录 failed。通常接 extract_test_points。",
        params_description='{"test_points": [{"id":"tp1","summary":"测试点描述","suggested_type":"functional|api|ui","suggested_design":"positive|negative|boundary|edge","rationale":"理由"}], "task_id": [可选，Agent task ID], "document_ids": [可选，需求文档ID列表]}',
        execute=_write_cases_batch,
    ),
    "validate_and_fix_cases": SkillSpec(
        id="validate_and_fix_cases",
        name="用例质量自检修复",
        description="批量校验已生成用例的质量（description/preconditions/steps/expected 非空可验证），对不合格用例携带需求点重试生成。修复缺陷1中无描述用例的兜底。",
        params_description='{"batch_id": "批次ID", "document_ids": [可选，需求文档ID用于重试检索]}',
        execute=_validate_and_fix_cases,
    ),
    "analyze_coverage": SkillSpec(
        id="analyze_coverage",
        name="需求覆盖度分析",
        description="对比需求文档与已生成用例，输出覆盖矩阵（需求点×用例），标记遗漏/冗余，可选自动补充遗漏用例。依赖 document_ids 贯穿。",
        params_description='{"batch_id": "批次ID", "document_ids": [需求文档ID], "supplement": [可选，是否自动补充遗漏用例，默认true]}',
        execute=_analyze_coverage,
    ),
    "summarize_context": SkillSpec(
        id="summarize_context",
        name="会话上下文摘要",
        description="对长会话历史（>20条消息）生成结构化摘要（主题/决策/产物/待解决），缓存到会话，注入LLM上下文替代被截断的早期消息。解决长会话失忆。",
        params_description='{"task_id": "任务ID", "force_refresh": [可选，强制重新生成摘要]}',
        execute=_summarize_context,
    ),
    "run_ui_batch": SkillSpec(
        id="run_ui_batch",
        name="UI batch run",
        description="Execute multiple UI test cases sequentially as a batch. Iterates over case_ids, runs each with the vision-driven UI engine, and returns per-case pass/fail results with an aggregate summary.",
        params_description='{"case_ids":[case_id list], "base_url":"[optional]"}',
        execute=_run_ui_batch,
    ),
}


def get_skill_catalog() -> str:
    """返回 skill 清单的文本描述（给 Planner 的 prompt 用）。"""
    lines = []
    for spec in SKILLS.values():
        lines.append(f"- {spec.id}: {spec.description}。参数: {spec.params_description}")
    return "\n".join(lines)
