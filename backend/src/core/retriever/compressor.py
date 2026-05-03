"""Prompt Compressor: Extract relevant content from retrieved chunks.

After retrieval, chunks often contain 80% irrelevant content.
This module extracts only the sentences/paragraphs relevant to the query,
reducing token usage and improving LLM focus.

Approach:
1. Split each chunk into sentences
2. Score each sentence by keyword overlap with query
3. Keep top-N sentences that exceed relevance threshold
4. Reassemble compressed chunks with context markers
"""
import re
import logging
from typing import Optional

logger = logging.getLogger("nova_rag")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, preserving structure."""
    # Split on Chinese/English sentence endings, keeping the delimiter
    parts = re.split(r'(?<=[。！？.!?])\s*|\n{2,}', text)
    sentences = [s.strip() for s in parts if s.strip()]
    return sentences


def _extract_keywords(query: str) -> set[str]:
    """Extract meaningful keywords from query (Chinese and English)."""
    import jieba

    stop_words = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '这', '那', '吗', '什么', '怎么', '如何', '为什么', '请', '帮', '解释', '说明',
        '中', '里', '里面', '下面', '上面', '文档', '文件', '内容', '什么样', '样的',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
    }

    keywords = set()

    # Use jieba for Chinese word segmentation
    words = jieba.cut(query)
    for word in words:
        word = word.strip().lower()
        if not word or len(word) < 2:
            continue
        if word in stop_words:
            continue
        # Keep Chinese words (2-4 chars) and English words (3+ chars)
        if any('\u4e00' <= c <= '\u9fff' for c in word) and 2 <= len(word) <= 4:
            keywords.add(word)
        elif word.isascii() and len(word) >= 3:
            keywords.add(word)

    return keywords


def _score_sentence(sentence: str, keywords: set[str], query_lower: str) -> float:
    """Score a sentence's relevance to the query."""
    sentence_lower = sentence.lower()

    # Exact query match bonus
    if query_lower in sentence_lower:
        return 1.0

    # Keyword overlap score
    if not keywords:
        return 0.0

    matched = 0
    for kw in keywords:
        if kw in sentence_lower:
            matched += 1

    return matched / len(keywords)


def compress_chunks(chunks: list[dict], query: str, max_tokens: int = 6000) -> list[dict]:
    """Compress retrieved chunks by extracting query-relevant content.

    Args:
        chunks: List of chunk dicts with 'parent_content' or 'child_content'
        query: User query for relevance scoring
        max_tokens: Maximum total tokens (approximate)

    Returns:
        Compressed chunks with relevant content only
    """
    if not chunks or not query:
        return chunks

    keywords = _extract_keywords(query)
    query_lower = query.lower()

    # Approximate chars per token (Chinese ~1.5 chars/token, English ~4 chars/token)
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in query)
    chars_per_token = 2.0 if has_chinese else 4.0
    max_chars = int(max_tokens * chars_per_token)

    compressed = []
    total_chars = 0

    for chunk in chunks:
        content = chunk.get("parent_content", chunk.get("child_content", ""))
        if not content:
            continue

        # Short chunks, keep as-is
        if len(content) < 500:
            if total_chars + len(content) <= max_chars:
                compressed.append(chunk)
                total_chars += len(content)
            continue

        # OCR content (well-structured), keep as-is
        if '[Page' in content or '图片内容描述' in content or '图表描述' in content:
            if total_chars + len(content) <= max_chars:
                compressed.append(chunk)
                total_chars += len(content)
            continue

        # Table data content (structured), keep as-is to preserve data integrity
        if '--- 表格数据开始 ---' in content or '--- 表格结束 ---' in content:
            if total_chars + len(content) <= max_chars:
                compressed.append(chunk)
                total_chars += len(content)
            continue

        # Split into sentences
        sentences = _split_sentences(content)
        if len(sentences) <= 3:
            # Few sentences, keep as-is
            if total_chars + len(content) <= max_chars:
                compressed.append(chunk)
                total_chars += len(content)
            continue

        # Score each sentence
        scored = []
        for sent in sentences:
            score = _score_sentence(sent, keywords, query_lower)
            scored.append((sent, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Keep sentences with score > 0, up to 80% of original
        relevant_sentences = [(s, sc) for s, sc in scored if sc > 0]

        if not relevant_sentences:
            # No relevant sentences found, keep top 5
            relevant_sentences = scored[:5]

        # Limit to 80% of original sentences (keep more context)
        max_keep = max(5, int(len(sentences) * 0.8))
        relevant_sentences = relevant_sentences[:max_keep]

        # Reassemble in original order
        kept_texts = set(s for s, _ in relevant_sentences)
        compressed_content = []
        for sent in sentences:
            if sent in kept_texts:
                compressed_content.append(sent)

        compressed_text = "\n".join(compressed_content)

        # Add compression marker if content was reduced
        if len(compressed_text) < len(content) * 0.8:
            compressed_text = f"[提取的相关内容]\n{compressed_text}"

        if total_chars + len(compressed_text) <= max_chars:
            compressed_chunk = dict(chunk)
            compressed_chunk["parent_content"] = compressed_text
            compressed.append(compressed_chunk)
            total_chars += len(compressed_text)
        else:
            # Budget exhausted
            break

    if len(compressed) < len(chunks):
        logger.info(f"[Compress] {len(chunks)} chunks → {len(compressed)} (budget: {max_chars} chars)")

    return compressed if compressed else chunks[:3]  # Always return at least something
