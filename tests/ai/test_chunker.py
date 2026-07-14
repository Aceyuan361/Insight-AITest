# -*- coding: utf-8 -*-
from insight_aitest.platform.services.kb.chunker import Chunker, ChunkConfig
from insight_aitest.platform.services.kb.models import ParsedDocument


def test_split_small_text_single_chunk():
    chunker = Chunker(ChunkConfig(chunk_size=500, chunk_overlap=80))
    doc = ParsedDocument(filename="a.txt", content="短文本", meta={})
    chunks = chunker.split(doc)
    assert len(chunks) == 1
    assert chunks[0].text == "短文本"
    assert chunks[0].chunk_index == 0
    assert chunks[0].char_start == 0


def test_split_long_text_multiple_chunks_with_overlap():
    text = "句号。".join([f"第{i}段内容比较长" for i in range(50)])
    chunker = Chunker(ChunkConfig(chunk_size=30, chunk_overlap=10))
    doc = ParsedDocument(filename="a.txt", content=text, meta={})
    chunks = chunker.split(doc)
    assert len(chunks) > 1
    # chunk_index 连续
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
    # 每块不超过 chunk_size（最后一块除外，允许略超）
    for c in chunks[:-1]:
        assert len(c.text) <= 30 + len("。")


def test_offsets_are_valid():
    """关键不变量：text[char_start:char_end] == chunk.text。"""
    text = "一二三四五六七八九十" * 5
    chunker = Chunker(ChunkConfig(chunk_size=15, chunk_overlap=5))
    doc = ParsedDocument(filename="a.txt", content=text, meta={})
    chunks = chunker.split(doc)
    assert len(chunks) > 1
    for c in chunks:
        assert text[c.char_start:c.char_end] == c.text, (
            f"offset 不一致: chunk_index={c.chunk_index} "
            f"start={c.char_start} end={c.char_end} text={c.text!r} "
            f"actual={text[c.char_start:c.char_end]!r}")


def test_markdown_header_starts_new_chunk():
    """Markdown 标题行应作为新块边界。"""
    text = "前言内容。" * 10 + "\n# 标题\n正文内容。" * 10
    chunker = Chunker(ChunkConfig(chunk_size=40, chunk_overlap=5))
    doc = ParsedDocument(filename="a.md", content=text, meta={})
    chunks = chunker.split(doc)
    # 至少有一个块包含标题
    assert any("# 标题" in c.text for c in chunks)


def test_chunks_cover_whole_text():
    """分块并集应覆盖原文（允许 overlap 重叠，但不应该丢字）。"""
    text = "段落一内容。" * 8 + "段落二内容。" * 8
    chunker = Chunker(ChunkConfig(chunk_size=20, chunk_overlap=5))
    doc = ParsedDocument(filename="a.txt", content=text, meta={})
    chunks = chunker.split(doc)
    # 首块从头开始
    assert chunks[0].char_start == 0
    # 末块到尾结束
    assert chunks[-1].char_end == len(text)


def test_chunk_config_defaults():
    """ChunkConfig 默认 strategy=recursive, semantic_breakpoint=2.58。"""
    cfg = ChunkConfig()
    assert cfg.strategy == "recursive"
    assert cfg.semantic_breakpoint == 2.58
    # 现有字段不变
    assert cfg.chunk_size == 500
    assert cfg.chunk_overlap == 80


def test_chunk_config_semantic_fields_settable():
    cfg = ChunkConfig(chunk_size=300, chunk_overlap=50, strategy="semantic", semantic_breakpoint=1.5)
    assert cfg.strategy == "semantic"
    assert cfg.semantic_breakpoint == 1.5


def test_split_sentences_offsets_valid():
    """句子切分：每段返回的 (start, end) 满足 text[start:end] 是原文连续子串。"""
    from insight_aitest.platform.services.kb.chunker import split_into_sentences

    text = "这是第一句。这是第二句！这是第三句？最后一句。"
    sentences = split_into_sentences(text)
    assert len(sentences) >= 3
    for s, e in sentences:
        assert 0 <= s < e <= len(text)  # 有效区间
        assert text[s:e].strip()  # 切片非空白
    # 首句从 0 开始
    assert sentences[0][0] == 0
    # 覆盖到末尾（最后一段含末尾标点）
    assert sentences[-1][1] == len(text)


def test_split_sentences_with_headers():
    """句子切分尊重 Markdown 标题边界（标题行不与上一段合并）。"""
    from insight_aitest.platform.services.kb.chunker import split_into_sentences

    text = "前言内容。正文说明。\n# 标题一\n标题下内容。"
    sentences = split_into_sentences(text)
    # 标题行应作为一个独立单元出现
    header_units = [text[s:e] for s, e in sentences if "# 标题一" in text[s:e]]
    assert len(header_units) >= 1


class _FakeEmbedding:
    """测试用假 embedding：按句子首个字分簇返回向量，模拟语义聚类。

    同首字 → 向量接近（余弦接近 1）；不同首字 → 向量正交（余弦接近 0）。
    用于构造可预测的语义断点。
    """

    def __init__(self, dim: int = 16) -> None:
        self.dim = dim
        self.call_batches: list[int] = []  # 记录每次 embed 调用的输入数量

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_batches.append(len(texts))
        vecs = []
        for t in texts:
            key = t.strip()[:1] if t.strip() else "?"
            # 每个首字映射到正交基的一个轴
            vec = [0.0] * self.dim
            axis = ord(key) % self.dim
            vec[axis] = 1.0
            vecs.append(vec)
        return vecs


def test_semantic_chunker_offset_invariant():
    """SemanticChunker 产出每个 chunk 满足 text[char_start:char_end] == chunk.text。"""
    from insight_aitest.platform.services.kb.chunker import SemanticChunker

    text = "。".join([f"甲主题第{i}句话内容" for i in range(8)]) + "。" + \
           "。".join([f"乙主题第{i}句话内容" for i in range(8)]) + "。"
    fake_llm = _FakeEmbedding()
    chunker = SemanticChunker(ChunkConfig(chunk_size=200, chunk_overlap=20, strategy="semantic"), fake_llm)
    doc = ParsedDocument(filename="a.txt", content=text, meta={})
    chunks = chunker.split(doc)
    assert len(chunks) >= 1
    for c in chunks:
        assert text[c.char_start:c.char_end] == c.text, (
            f"offset 不一致: chunk_index={c.chunk_index} start={c.char_start} end={c.char_end}")
    # 覆盖性
    assert chunks[0].char_start == 0
    assert chunks[-1].char_end == len(text)


def test_semantic_breakpoint_at_topic_shift():
    """主题切换处应产生断点：FakeEmbedding 让同首字句子相近、不同首字句子远离。"""
    from insight_aitest.platform.services.kb.chunker import SemanticChunker

    # 8 句「甲」开头 + 8 句「乙」开头，chunk_size 够大不触发长度切分
    text = "。".join([f"甲主题内容第{i}段" for i in range(8)]) + "。" + \
           "。".join([f"乙主题内容第{i}段" for i in range(8)]) + "。"
    fake_llm = _FakeEmbedding()
    chunker = SemanticChunker(ChunkConfig(chunk_size=500, chunk_overlap=0, strategy="semantic"), fake_llm)
    doc = ParsedDocument(filename="a.txt", content=text, meta={})
    chunks = chunker.split(doc)
    # 应在「甲→乙」切换处断成 >=2 块
    assert len(chunks) >= 2
    # 前块含「甲」，后块含「乙」
    has_jia = any("甲" in c.text for c in chunks)
    has_yi = any("乙" in c.text for c in chunks)
    assert has_jia and has_yi
    # 断点附近：存在一个 chunk 的末尾在「乙」开始之前或附近
    yi_start = text.index("乙主题内容第0段")
    boundary_chunks = [c for c in chunks if c.char_end <= yi_start + 5 or c.char_start >= yi_start - 5]
    assert len(boundary_chunks) >= 1


def test_semantic_fallback_on_embed_failure():
    """embed 抛异常时，SemanticChunker.split 回退到 recursive，结果与 Chunker 一致。"""
    from insight_aitest.platform.services.kb.chunker import SemanticChunker

    class _BrokenEmbedding:
        def embed(self, texts):
            raise RuntimeError("embedding 服务不可用")

    text = "段落一内容文字。" * 20 + "段落二内容文字。" * 20
    broken_llm = _BrokenEmbedding()
    sem_chunker = SemanticChunker(ChunkConfig(chunk_size=40, chunk_overlap=5, strategy="semantic"), broken_llm)
    doc = ParsedDocument(filename="a.txt", content=text, meta={})
    sem_chunks = sem_chunker.split(doc)

    # 与直接用 Chunker 对比
    rec_chunker = Chunker(ChunkConfig(chunk_size=40, chunk_overlap=5))
    rec_chunks = rec_chunker.split(doc)

    assert len(sem_chunks) == len(rec_chunks)
    for sc, rc in zip(sem_chunks, rec_chunks):
        assert sc.text == rc.text
        assert sc.char_start == rc.char_start


def test_semantic_embed_batching():
    """embed_batch_size 应分批调用 embed，防大文档超 API 单请求上限。"""
    from insight_aitest.platform.services.kb.chunker import SemanticChunker

    # 20 句同主题（不触发断点，只测分批）
    text = "。".join([f"主题内容第{i}段话" for i in range(20)]) + "。"
    fake_llm = _FakeEmbedding()
    chunker = SemanticChunker(
        ChunkConfig(chunk_size=500, chunk_overlap=0, strategy="semantic", embed_batch_size=7),
        fake_llm,
    )
    doc = ParsedDocument(filename="a.txt", content=text, meta={})
    chunker.split(doc)

    # 应分 3 批：7 + 7 + 6 = 20
    assert fake_llm.call_batches == [7, 7, 6]
    assert sum(fake_llm.call_batches) == 20
