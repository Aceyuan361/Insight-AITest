# -*- coding: utf-8 -*-
"""Mock LLM 中转服务器（OpenAI 兼容协议）。

用途：不用真实 API key 也能跑通 AI 模块完整端到端。
- /v1/embeddings  ：对所有文本返回同一向量（保证检索恒命中，distance=0）
- /v1/chat/completions：返回固定带引用提示的回答（支持 stream 与非 stream）

用法：
    1. 启动本服务：  py scripts\mock_llm_server.py
       （默认监听 http://localhost:8088，可用 --port 改）
    2. 启动平台后端时配置指向本服务，二选一：
       a) 环境变量：
          set INSIGHT_EYE_AI_LLM_BASE_URL=http://localhost:8088/v1
          set INSIGHT_EYE_AI_LLM_API_KEY=mock-key
          set INSIGHT_EYE_AI_EMBED_DIM=8
          py -m insight_aitest
       b) 或在前端 /ai 设置页把 base_url 填 http://localhost:8088/v1、key 随便填、embed_dim=8
    3. 浏览器打开 /ai → 上传文档 → 提问，即可看到带引用的流式回答（全本地，不联网）

注意：embed_dim 必须与启动后端时一致（默认 8）。换维度需重建向量表。
"""
from __future__ import annotations

import argparse
import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

EMBED_DIM = 8  # 默认向量维度；与后端 INSIGHT_EYE_AI_EMBED_DIM 保持一致

app = FastAPI(title="Mock LLM (OpenAI 兼容)")


def _embedding_vec(_text: str) -> list[float]:
    # 所有文本返回同一向量：检索恒命中，distance=0, score=1
    return [1.0] * EMBED_DIM


@app.post("/v1/embeddings")
async def embeddings(req: Request):
    body = await req.json()
    inputs = body.get("input", [])
    if isinstance(inputs, str):
        inputs = [inputs]
    data = [
        {"object": "embedding", "index": i, "embedding": _embedding_vec(t)}
        for i, t in enumerate(inputs)
    ]
    return JSONResponse({"object": "list", "data": data, "model": body.get("model", "mock"), "usage": {"prompt_tokens": 0}})


@app.post("/v1/chat/completions")
async def chat_completions(req: Request):
    body = await req.json()
    stream = body.get("stream", False)
    full = "这是基于知识库的回答。根据[1]，相关内容已检索到。具体细节可参考上传的文档。"

    if not stream:
        return JSONResponse({
            "id": "mock-chat-1",
            "object": "chat.completion",
            "model": body.get("model", "mock"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": full}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        })

    # 流式：按标点切分逐块吐出（模拟真实流式体验）
    tokens = _split_tokens(full)

    async def gen():
        for tok in tokens:
            chunk = {
                "id": "mock-chat-1",
                "object": "chat.completion.chunk",
                "model": body.get("model", "mock"),
                "choices": [{"index": 0, "delta": {"content": tok}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            time.sleep(0.05)
        # 结束 sentinel
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def _split_tokens(text: str) -> list[str]:
    """按标点和空格切分成小块（模拟 token 流）。"""
    tokens: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in "，。！？,.!? \n":
            tokens.append(cur)
            cur = ""
    if cur:
        tokens.append(cur)
    return tokens


@app.get("/v1/models")
async def list_models():
    return JSONResponse({
        "object": "list",
        "data": [{"id": "mock", "object": "model", "owned_by": "mock"}],
    })


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mock-llm"}


def main():
    global EMBED_DIM
    parser = argparse.ArgumentParser(description="Mock LLM (OpenAI 兼容) 中转服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    parser.add_argument("--embed-dim", type=int, default=EMBED_DIM,
                        help="向量维度，必须与后端 INSIGHT_EYE_AI_EMBED_DIM 一致")
    args = parser.parse_args()
    EMBED_DIM = args.embed_dim
    print(f"Mock LLM 启动: http://{args.host}:{args.port}/v1  (embed_dim={EMBED_DIM})")
    print("后端配置示例:")
    print(f"  set INSIGHT_EYE_AI_LLM_BASE_URL=http://{args.host}:{args.port}/v1")
    print(f"  set INSIGHT_EYE_AI_LLM_API_KEY=mock-key")
    print(f"  set INSIGHT_EYE_AI_EMBED_DIM={EMBED_DIM}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
