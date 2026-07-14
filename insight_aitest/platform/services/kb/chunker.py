# -*- coding: utf-8 -*-
"""递归字符分块器（平台共享服务）。

策略：按 separators 顺序递归切分，直到每块 <= chunk_size。相邻块重叠 chunk_overlap。
Markdown 标题行（# 开头）作为强制的块边界。

核心不变量：对任意输出 chunk，原文 [char_start:char_end] == chunk.text。
"""

from __future__ import annotations

import logging
import re
import statistics
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from insight_aitest.platform.services.kb.models import Chunk, ParsedDocument

if TYPE_CHECKING:
    from insight_aitest.platform.services.llm.client import LLMClient

logger = logging.getLogger(__name__)

_HEADER_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)

# 句子结束标点（中英文句号/问号/叹号/省略号）+ 后续空白
_SENTENCE_END_RE = re.compile(r"(?<=[。！？!?\.…])\s*")


def split_into_sentences(text: str) -> list[tuple[int, int]]:
    """把文本切成句子级 (start, end) offset 列表。

    先按 Markdown 标题预切（标题行作为强边界），再在每个标题段内按句子标点切。
    每个 (start, end) 满足 text[start:end] 是原文连续子串。
    空白片段被跳过（不产生空句子）。
    """
    if not text:
        return []

    # 1. 按 Markdown 标题预切（复用现有逻辑）
    header_positions = [m.start() for m in _HEADER_RE.finditer(text)]
    if not header_positions:
        segments = [(0, len(text))]
    else:
        bounds = sorted({0} | set(header_positions) | {len(text)})
        segments = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]

    # 2. 每段内按句子标点切
    sentences: list[tuple[int, int]] = []
    for seg_start, seg_end in segments:
        seg_text = text[seg_start:seg_end]
        # 找所有句子结束位置（标点后的位置）
        ends = [m.end() for m in _SENTENCE_END_RE.finditer(seg_text)]
        # 加上段末作为最后一个句子结束
        if not ends or ends[-1] < len(seg_text):
            ends.append(len(seg_text))

        sent_start = 0
        for sent_end in ends:
            # 跳过纯空白
            if sent_start < sent_end and seg_text[sent_start:sent_end].strip():
                sentences.append((seg_start + sent_start, seg_start + sent_end))
            sent_start = sent_end

    return sentences


@dataclass
class ChunkConfig:
    chunk_size: int = 500
    chunk_overlap: int = 80
    strategy: str = "recursive"  # "recursive"(existing) | "semantic"(embedding 相似度分块)
    semantic_breakpoint: float = (
        2.58  # 语义断点 std 倍数(仅 strategy=semantic 生效，LangChain 默认)
    )
    embed_batch_size: int = 64  # semantic 策略批量 embed 的批次大小（防超 API 单请求上限）
    separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", "。", ".", " ", ""])


class Chunker:
    def __init__(self, config: ChunkConfig) -> None:
        self.config = config

    def split(self, document: ParsedDocument) -> list[Chunk]:
        text = document.content
        if not text:
            return []
        if len(text) <= self.config.chunk_size:
            return [
                Chunk(
                    id=None,
                    document_id=0,
                    chunk_index=0,
                    text=text,
                    char_start=0,
                    char_end=len(text),
                )
            ]

        # 1. 按 Markdown 标题预切为段（带绝对 offset）
        segments = self._split_by_headers(text)
        # 2. 每段递归字符切为原子片段（绝对 offset）
        atoms: list[tuple[int, int]] = []
        for seg_start, seg_end in segments:
            seg_text = text[seg_start:seg_end]
            for s, e in self._recursive_split(seg_text, 0):
                atoms.append((seg_start + s, seg_start + e))
        # 3. 合并过小相邻原子 + 加 overlap，输出最终块
        pieces = self._merge_with_overlap(atoms)
        # 确保覆盖到原文末尾（尾部分隔符产生的空原子可能让末块 end < len(text)）
        if pieces and pieces[-1][1] < len(text):
            last_s, last_e = pieces[-1]
            pieces[-1] = (last_s, len(text))

        chunks: list[Chunk] = []
        for i, (s, e) in enumerate(pieces):
            chunks.append(
                Chunk(
                    id=None,
                    document_id=0,
                    chunk_index=i,
                    text=text[s:e],
                    char_start=s,
                    char_end=e,
                )
            )
        return chunks

    def _split_by_headers(self, text: str) -> list[tuple[int, int]]:
        """按 Markdown 标题行切成 (start, end) 段。无标题则整段。"""
        positions = [m.start() for m in _HEADER_RE.finditer(text)]
        if not positions:
            return [(0, len(text))]
        bounds = sorted({0} | set(positions) | {len(text)})
        return [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]

    def _recursive_split(self, text: str, depth: int) -> list[tuple[int, int]]:
        """递归按 separators 切分。返回相对 text 的 (start, end) 列表。

        每个 (start, end) 满足 text[start:end] 是原文连续子串。
        若整段已 <= chunk_size 直接返回；否则用当前 separator 切，
        过长的子段继续用下一个 separator 递归。
        """
        if len(text) <= self.config.chunk_size or depth >= len(self.config.separators):
            return [(0, len(text))]

        sep = self.config.separators[depth]
        if sep == "":
            # 退化：硬按 chunk_size 切
            return [
                (i, min(i + self.config.chunk_size, len(text)))
                for i in range(0, len(text), self.config.chunk_size)
            ]

        parts = text.split(sep)
        result: list[tuple[int, int]] = []
        offset = 0
        for part in parts:
            start = offset
            end = offset + len(part)
            if len(part) > self.config.chunk_size:
                # 子段仍过长，递归
                for s, e in self._recursive_split(text[start:end], depth + 1):
                    result.append((start + s, start + e))
            else:
                result.append((start, end))
            # 下一段 offset：越过当前 part + separator
            offset = end + len(sep)
        return result

    def _merge_with_overlap(self, atoms: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """合并相邻原子使其尽量接近 chunk_size，并保证相邻块有 overlap。

        约束：不破坏 offset 不变量（每块的 [start:end] 是原文子串）。
        """
        if not atoms:
            return []
        overlap = (
            self.config.chunk_size if self.config.chunk_overlap <= 0 else self.config.chunk_overlap
        )
        size = self.config.chunk_size

        # 先合并：贪心地把相邻原子累加，直到再加一个就超过 size
        merged: list[list[tuple[int, int]]] = []
        current: list[tuple[int, int]] = [atoms[0]]
        cur_end = atoms[0][1]
        for s, e in atoms[1:]:
            if s > cur_end:
                # 段间有 gap（跨 Markdown 段），先收尾再起新块
                merged.append(current)
                current = [(s, e)]
                cur_end = e
                continue
            if (e - current[0][0]) <= size:
                current.append((s, e))
                cur_end = e
            else:
                merged.append(current)
                current = [(s, e)]
                cur_end = e
        merged.append(current)

        # 把每组原子合成一个 (start, end) 块
        blocks = [(grp[0][0], grp[-1][1]) for grp in merged if grp[0][0] < grp[-1][1]]

        if len(blocks) <= 1 or overlap <= 0:
            return blocks

        # 加 overlap：每块的 start 向前回退 overlap（但不越过上一块的起点附近），
        # 保证相邻块共享一段原文。回退后仍是原文连续子串，不变量保持。
        result: list[tuple[int, int]] = [blocks[0]]
        for s, e in blocks[1:]:
            new_start = max(0, s - overlap)
            # 避免与上一块完全重叠或退步
            prev_end = result[-1][1]
            if new_start >= prev_end:
                new_start = s
            result.append((new_start, e))
        return result


class SemanticChunker:
    """语义分块器：用 embedding 相似度在语义转折处断句。

    算法（LangChain SemanticChunker 范式）：
    1. 切句子（split_into_sentences）
    2. 批量 embed 全部句子，算相邻句子 cosine 相似度
    3. 相似度低于 mean - breakpoint_std × std 处为断点
    4. 按断点合并句子成块，超 chunk_size 在句子边界切，加 overlap

    核心不变量：text[char_start:char_end] == chunk.text（与 Chunker 一致）。
    embedding 调用失败时回退到 Chunker。
    """

    def __init__(self, config: ChunkConfig, llm: "LLMClient") -> None:
        self.config = config
        self.llm = llm
        # 内部回退用的字符分块器（embed 失败时用）
        self._fallback = Chunker(config)

    def split(self, document: ParsedDocument) -> list[Chunk]:
        text = document.content
        if not text:
            return []
        try:
            return self._semantic_split(text)
        except Exception as e:
            logger.warning("语义分块失败，回退递归字符分块: %s", e)
            return self._fallback.split(document)

    def _semantic_split(self, text: str) -> list[Chunk]:
        # 1. 切句子
        sentences = split_into_sentences(text)
        if len(sentences) <= 1:
            return self._fallback.split(ParsedDocument(filename="", content=text, meta={}))

        # 2. 分批 embed 全部句子（防大文档超 API 单请求 token 上限）
        sent_texts = [text[s:e] for s, e in sentences]
        vecs: list[list[float]] = []
        batch_size = self.config.embed_batch_size or len(sent_texts)
        for i in range(0, len(sent_texts), batch_size):
            vecs.extend(self.llm.embed(sent_texts[i : i + batch_size]))

        # 3. 算相邻句子 cosine 相似度（向量已 L2 归一化，点积即 cosine）
        sims = []
        for i in range(len(vecs) - 1):
            sims.append(sum(a * b for a, b in zip(vecs[i], vecs[i + 1])))

        # 4. 找断点
        if len(sims) < 2 or statistics.pstdev(sims) < 1e-6:
            # 相似度高度均匀（纯代码/纯列表），无断点，退化为按 chunk_size 兜底切
            breakpoints: set[int] = set()
        else:
            threshold = statistics.fmean(
                sims
            ) - self.config.semantic_breakpoint * statistics.pstdev(sims)
            breakpoints = {i for i, sim in enumerate(sims) if sim < threshold}

        # 5. 按断点把句子分组成块
        groups: list[list[tuple[int, int]]] = []
        current: list[tuple[int, int]] = [sentences[0]]
        for i in range(1, len(sentences)):
            if (i - 1) in breakpoints:
                groups.append(current)
                current = []
            current.append(sentences[i])
        groups.append(current)

        # 6. 每组合成一个 (start, end) 块；超 chunk_size 的组在句子边界切
        blocks: list[tuple[int, int]] = []
        for grp in groups:
            grp_start = grp[0][0]
            grp_end = grp[-1][1]
            if grp_end - grp_start <= self.config.chunk_size:
                blocks.append((grp_start, grp_end))
            else:
                # 组内按 chunk_size 在句子边界切
                cur_s = grp[0][0]
                cur_e = grp[0][1]
                for s, e in grp[1:]:
                    if e - cur_s <= self.config.chunk_size:
                        cur_e = e
                    else:
                        blocks.append((cur_s, cur_e))
                        cur_s, cur_e = s, e
                blocks.append((cur_s, cur_e))

        # 7. 加 overlap（复用 Chunker 的逻辑：每块 start 向前回退 overlap）
        pieces = self._add_overlap(blocks, text)

        # 8. 转 Chunk 列表
        chunks: list[Chunk] = []
        for i, (s, e) in enumerate(pieces):
            chunks.append(
                Chunk(
                    id=None,
                    document_id=0,
                    chunk_index=i,
                    text=text[s:e],
                    char_start=s,
                    char_end=e,
                )
            )
        return chunks

    def _add_overlap(self, blocks: list[tuple[int, int]], text: str) -> list[tuple[int, int]]:
        """每块 start 向前回退 overlap（与 Chunker._merge_with_overlap 同范式）。"""
        if len(blocks) <= 1 or self.config.chunk_overlap <= 0:
            return blocks
        overlap = self.config.chunk_overlap
        result: list[tuple[int, int]] = [blocks[0]]
        for s, e in blocks[1:]:
            new_start = max(0, s - overlap)
            prev_end = result[-1][1]
            if new_start >= prev_end:
                new_start = s
            result.append((new_start, e))
        return result
