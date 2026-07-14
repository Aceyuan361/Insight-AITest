# AI 助手模块

基于本地知识库的 AI 问答助手（RAG）。文档上传 → 本地向量化 → 多轮对话（带引用）。

- 后端：`backend/routes/`（文档/会话/对话/配置）+ `backend/kb/`（知识库管线）+ `backend/agent/`（RAG 编排）
- 持久层：独立 `~/.insight_eye/ai_kb.db`（sqlite + sqlite-vec）
- LLM：OpenAI 兼容协议（云端 chat + embedding）
- 前端：见 `shell-frontend/src/modules/ai/`

## 配置

优先级：环境变量 > `~/.insight_eye/ai_config.json` > 默认值。

最快上手：复制 `.env.example` 为 `.env` 并填入 API key，或在前端 `/ai` 设置里配置（写入 `~/.insight_eye/ai_config.json`）。

支持任何 OpenAI 兼容端点：
- OpenAI: `https://api.openai.com/v1`
- 通义千问: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- 智谱: `https://open.bigmodel.cn/api/paas/v4`
- DeepSeek: `https://api.deepseek.com`
- 本地 Ollama: `http://localhost:11434/v1`

**注意**：换 embedding 模型（embed_dim 变）需重新索引所有文档（`POST /api/modules/ai/documents/{id}/reindex`）。
