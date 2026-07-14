# -*- coding: utf-8 -*-
"""LLM 配置（平台共享服务）。加载优先级：环境变量 > 配置文件 > 默认值。

从 ai 模块上提（原 AIConfig → LLMConfig），ai 和 testcase 模块共用。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field


@dataclass
class LLMConfig:
    # LLM（OpenAI 兼容）
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    vision_model: str = ""  # 视觉模型（Midscene 用），空则回退 chat_model
    llm_timeout: int = 60

    # ===== 向量检索（子分类：默认关，个人版文档量小 ROI 低）=====
    # 关闭后：文档仍可上传/解析/分块/存储/查阅，但 AI 对话不做向量召回（走纯 LLM），用例生成器无参考资料。
    # 开启后：需要配置 embedding 端点（chat 端点无 embedding 模型时，可单独指定 embed_base_url/embed_api_key）。
    vector_enabled: bool = False  # 默认关；需向量召回（RAG）时开启
    embed_base_url: str = ""  # 空 = 回退 llm_base_url
    embed_api_key: str = ""  # 空 = 回退 llm_api_key
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536
    embed_batch_size: int = 64

    # 知识库管线（与向量检索正交：分块在 vector 关闭时仍用于文档存储）
    chunk_size: int = 500
    chunk_overlap: int = 80
    chunk_strategy: str = (
        "recursive"  # "recursive"（字符）| "semantic"（embedding 相似度，需 vector_enabled）
    )
    semantic_breakpoint: float = 2.58  # 语义断点 std 倍数（仅 semantic 生效）
    top_k: int = 4
    min_score: float = 0.1
    max_upload_mb: int = 20
    max_chunks_per_doc: int = 5000

    # Rerank（LLM-as-reranker：向量召回 N 候选 → LLM 打分 → 重排取 top_k）
    rerank_enabled: bool = False  # 默认关，避免拖慢现有 RAG；按需开启
    rerank_fetch_k: int = 12  # rerank 前的候选数（应 ≥ top_k）

    # OCR（多模态：用 vision model 读图，扫描件 PDF / 图片文档抽取文字）
    ocr_enabled: bool = True  # 默认开（需 vision_model 配置；关则扫描件/图片报错引导）

    # 对话
    history_turns: int = 6

    # 存储（~ 由 expand_paths 展开为绝对路径）
    db_path: str = "~/.insight_eye/kb.db"
    docs_dir: str = "~/.insight_eye/ai_docs"
    config_file: str = "~/.insight_eye/llm_config.json"

    # ReAct 大脑层配置（Agent Brain 2.0）：嵌套 dict，由 load_config 自动从
    # llm_config.json 的 "react" 节加载（load_config 的 hasattr 循环已覆盖）。
    # 形如 {"enabled": true, "max_iterations": 8, "budget": {"retry": 2, "fix": 2, "consecutive_fail": 3}}
    react: dict = field(default_factory=dict)

    # ===== UI 自动化视觉模型独立配置 =====
    # UI 自动化需要多模态视觉模型（如 gpt-4o），与全局对话模型（如 deepseek-chat）不同。
    # 此字段允许用户单独配置 UI 专用模型，留空则回退到全局 vision_model → chat_model。
    # 形如 {"base_url": "", "api_key": "", "model": ""}
    ui_vision_config: dict = field(default_factory=dict)

    # ===== 多 Provider 管理（Cursor 风格灵活切换）=====
    # providers 是用户保存的所有 Provider 配置列表；active_provider_id 指向当前生效的那一个。
    # 每条 provider 形如：
    #   {"id": "p1", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1",
    #    "api_key": "sk-...", "chat_model": "deepseek-chat", "vision_model": "deepseek-vision"}
    # 当 active_provider 存在时，其 base_url/api_key/chat_model/vision_model 投影到上面的扁平字段，
    # 保证旧的 LLMClient/LLMConfig 读取路径无感知（向后兼容）。
    providers: list = field(default_factory=list)
    active_provider_id: str = ""

    @property
    def api_key_set(self) -> bool:
        return bool(self.llm_api_key)

    def react_config(self):
        """把 self.react（原始 dict）物化为 ReActConfig（懒导入避免 platform → ai 循环依赖）。"""
        from insight_aitest.modules.ai.backend.agent.reactor import ReActConfig

        return ReActConfig.from_dict(self.react)

    def expand_paths(self) -> "LLMConfig":
        self.db_path = os.path.expanduser(self.db_path)
        self.docs_dir = os.path.expanduser(self.docs_dir)
        self.config_file = os.path.expanduser(self.config_file)
        return self


# 环境变量名映射（INSIGHT_EYE_AI_<UPPER_FIELD>）—— 保留 AI 前缀兼容现有部署
_ENV_KEYS = {
    "llm_base_url": "INSIGHT_EYE_AI_LLM_BASE_URL",
    "llm_api_key": "INSIGHT_EYE_AI_LLM_API_KEY",
    "chat_model": "INSIGHT_EYE_AI_CHAT_MODEL",
    "vision_model": "INSIGHT_EYE_AI_VISION_MODEL",
    "llm_timeout": "INSIGHT_EYE_AI_LLM_TIMEOUT",
    "embed_model": "INSIGHT_EYE_AI_EMBED_MODEL",
    "embed_dim": "INSIGHT_EYE_AI_EMBED_DIM",
    "embed_batch_size": "INSIGHT_EYE_AI_EMBED_BATCH_SIZE",
    "chunk_size": "INSIGHT_EYE_AI_CHUNK_SIZE",
    "chunk_overlap": "INSIGHT_EYE_AI_CHUNK_OVERLAP",
    "chunk_strategy": "INSIGHT_EYE_AI_CHUNK_STRATEGY",
    "semantic_breakpoint": "INSIGHT_EYE_AI_SEMANTIC_BREAKPOINT",
    "top_k": "INSIGHT_EYE_AI_TOP_K",
    "min_score": "INSIGHT_EYE_AI_MIN_SCORE",
    "max_upload_mb": "INSIGHT_EYE_AI_MAX_UPLOAD_MB",
    "rerank_enabled": "INSIGHT_EYE_AI_RERANK_ENABLED",
    "rerank_fetch_k": "INSIGHT_EYE_AI_RERANK_FETCH_K",
    "ocr_enabled": "INSIGHT_EYE_AI_OCR_ENABLED",
    "vector_enabled": "INSIGHT_EYE_AI_VECTOR_ENABLED",
    "embed_base_url": "INSIGHT_EYE_AI_EMBED_BASE_URL",
    "embed_api_key": "INSIGHT_EYE_AI_EMBED_API_KEY",
}

# 需要转 int 的字段
_INT_FIELDS = {
    "llm_timeout",
    "embed_dim",
    "embed_batch_size",
    "chunk_size",
    "chunk_overlap",
    "top_k",
    "max_upload_mb",
    "max_chunks_per_doc",
    "rerank_fetch_k",
}
# 需要转 float 的字段
_FLOAT_FIELDS = {"min_score", "semantic_breakpoint"}

# 需要转 bool 的字段（"1"/"true"/"yes"/"on" → True，其余 False）
_BOOL_FIELDS = {"rerank_enabled", "ocr_enabled", "vector_enabled"}


def get_active_provider(cfg: LLMConfig) -> dict | None:
    """返回当前生效的 Provider dict（按 active_provider_id 查找）；无则 None。"""
    if not cfg.providers or not cfg.active_provider_id:
        return None
    for p in cfg.providers:
        if isinstance(p, dict) and p.get("id") == cfg.active_provider_id:
            return p
    return None


def apply_provider(cfg: LLMConfig, provider_id: str | None = None) -> LLMConfig:
    """把指定 Provider（默认 active_provider_id）的 base_url/api_key/chat_model/vision_model
    投影到扁平字段。切换/加载时调用，保证旧的读取路径无感知。

    provider_id=None 时用 cfg.active_provider_id；找不到则不动扁平字段（保持原值）。
    """
    pid = provider_id or cfg.active_provider_id
    if not pid:
        return cfg
    target = None
    for p in cfg.providers:
        if isinstance(p, dict) and p.get("id") == pid:
            target = p
            break
    if not target:
        return cfg
    cfg.active_provider_id = pid
    # 投影：Provider 字段 → 扁平字段（只覆盖非空字段，空则保留原值以兼容 vision_model 等可选字段）
    if target.get("base_url"):
        cfg.llm_base_url = target["base_url"]
    if target.get("api_key"):
        cfg.llm_api_key = target["api_key"]
    if target.get("chat_model"):
        cfg.chat_model = target["chat_model"]
    # vision_model 允许显式置空（用空串覆盖，表示"回退 chat_model"）
    if "vision_model" in target:
        cfg.vision_model = target.get("vision_model") or ""
    return cfg


def load_config(config_file: str | None = None) -> LLMConfig:
    """按 默认值 → 配置文件 → 环境变量 的顺序叠加（后者覆盖前者）。"""
    cfg = LLMConfig()

    # 配置文件
    path = config_file or cfg.config_file
    path = os.path.expanduser(path)
    # 兼容旧文件名：llm_config.json 不存在时回退读 ai_config.json（上提前的文件名）
    if not config_file and not os.path.exists(path):
        legacy = os.path.join(os.path.dirname(path), "ai_config.json")
        if os.path.exists(legacy):
            path = legacy
    file_data: dict = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            file_data = {}
    for k, v in file_data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)

    # Provider 投影（在 env 覆盖前）：把 active provider 的字段投影到扁平字段。
    # 这样 env 仍是最高优先级（无头部署强制锁定），provider 仅在 env 未设时生效。
    if cfg.providers and cfg.active_provider_id:
        apply_provider(cfg)

    # 环境变量（最高优先级）
    for field_name, env_name in _ENV_KEYS.items():
        val = os.getenv(env_name)
        if val is None:
            continue
        if field_name in _INT_FIELDS:
            val = int(val)
        elif field_name in _FLOAT_FIELDS:
            val = float(val)
        elif field_name in _BOOL_FIELDS:
            val = str(val).strip().lower() in ("1", "true", "yes", "on")
        setattr(cfg, field_name, val)

    return cfg.expand_paths()


def save_config(cfg: LLMConfig, config_file: str | None = None) -> None:
    """把配置写回文件（PUT /config 用）。db_path/docs_dir/config_file 不写回（运行期展开值）。"""
    path = config_file or cfg.config_file
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = asdict(cfg)
    data.pop("db_path", None)
    data.pop("docs_dir", None)
    data.pop("config_file", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 向后兼容别名：ai 模块旧代码以 AIConfig 名字引用，保留无需改调用点
AIConfig = LLMConfig
