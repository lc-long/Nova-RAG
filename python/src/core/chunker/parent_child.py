"""Parent-child chunking strategy for RAG with table-aware splitting.

Key design:
- Pre-split tables that exceed child_chunk_size BEFORE text splitting.
- Each sub-table is collapsed independently, then treated as a single atomic token
  by RecursiveCharacterTextSplitter (no internal newlines in collapsed form).
- After chunking, _restore_tables reconstructs full markdown tables.
"""
import re
from dataclasses import dataclass
from typing import Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter


_TABLE_SENTINEL = "\x00TBL\x00"


@dataclass
class Chunk:
    chunk_id: str
    content: str
    doc_id: str
    chunk_type: str  # "parent" or "child"
    parent_id: Optional[str] = None
    page_number: Optional[int] = None
    order: int = 0


def _is_table_line(line: str) -> bool:
    return line.startswith("|") and line.rstrip().endswith("|")


def _split_table_lines(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect all consecutive markdown table lines starting at `start`."""
    end = start
    while end < len(lines) and _is_table_line(lines[end]):
        end += 1
    return lines[start:end], end


def _pre_split_tables(text: str, max_size: int) -> str:
    """Pre-split tables in text that exceed max_size.

    Tables larger than max_size are split at row boundaries; each sub-table
    includes the original header row so it remains self-contained.
    The returned text still contains multi-line markdown tables (not collapsed).
    """
    lines = text.split("\n")
    n = len(lines)
    result = []
    i = 0

    while i < n:
        if not _is_table_line(lines[i]):
            result.append(lines[i])
            i += 1
            continue

        table_lines, next_i = _split_table_lines(lines, i)
        total = sum(len(l) + 1 for l in table_lines)  # +1 for newline

        if total <= max_size or len(table_lines) <= 2:
            # Fits as-is
            result.extend(table_lines)
        else:
            # Split at row boundaries
            header_cells = [
                c.strip() for c in
                table_lines[0].strip().strip("|").split("|")
            ]
            sep = "| " + " | ".join(["---"] * len(header_cells)) + " |"
            header_line = "| " + " | ".join(header_cells) + " |"
            data_rows = [
                [c.strip() for c in row.strip().strip("|").split("|")]
                for row in table_lines[2:]
            ]
            # Build sub-tables, each under max_size
            cur_rows, cur_size = [], len(header_line) + len(sep) + 2
            for row in data_rows:
                row_line = "| " + " | ".join(row) + " |"
                row_sz = len(row_line) + 1
                if cur_rows and cur_size + row_sz > max_size:
                    sub = [header_line, sep]
                    sub += ["| " + " | ".join(r) + " |" for r in cur_rows]
                    result.extend(sub)
                    cur_rows, cur_size = [], len(header_line) + len(sep) + 2
                cur_rows.append(row)
                cur_size += row_sz
            if cur_rows:
                sub = [header_line, sep]
                sub += ["| " + " | ".join(r) + " |" for r in cur_rows]
                result.extend(sub)

        i = next_i

    return "\n".join(result)


def _collapse_tables(text: str) -> str:
    """Collapse each markdown table block into a single-line sentinel token.

    Paragraph breaks (double newlines) are preserved as a special sentinel
    so they are not lost when the text is later joined for text splitting.
    """
    # Protect paragraph breaks: replace '\n\n' with a placeholder
    text = text.replace("\n\n", "\x00P\x00")
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|") and line.rstrip().endswith("|"):
            table_lines, next_i = _split_table_lines(lines, i)
            collapsed = (" " + _TABLE_SENTINEL + " ").join(
                t.strip() for t in table_lines
            )
            result.append(collapsed)
            i = next_i
        else:
            # Restore paragraph breaks
            result.append(line.replace("\x00P\x00", "\n\n"))
            i += 1
    return "\n".join(result)


def _restore_tables(text: str) -> str:
    """Restore collapsed table sentinel tokens to multi-line markdown.

    Handles both complete collapsed rows and partial rows (when the text splitter
    cut mid-token at a space between rows). The restoration reconstructs
    valid markdown table rows from the pipe-separated cell fragments.
    """
    if _TABLE_SENTINEL not in text:
        return text

    parts = text.split(_TABLE_SENTINEL)
    restored = []

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "|" not in part:
            restored.append(part)
            continue

        # Split by ' | ' (the separator between rows in collapsed form)
        # But handle partial rows: if we have " | Col1 | Col2 |  | --- |"
        # that's header+separator (partial), or "| val1 | val2 |  | val3 |" (partial data)
        raw_rows = part.split(" | ")
        # Filter empty strings and rebuild rows
        cells = []
        for token in raw_rows:
            token = token.strip()
            if not token:
                continue
            if token.startswith("|"):
                # Start of a new row
                if cells:
                    # Previous row is complete — emit it
                    restored.append("| " + " | ".join(cells) + " |")
                    cells = []
                # Parse this token's cells
                inner = token.strip().strip("|")
                if inner:
                    cells = [c.strip() for c in inner.split("|")]
            else:
                # Continuation of previous row
                inner = token.strip().strip("|")
                if inner:
                    extra = [c.strip() for c in inner.split("|")]
                    cells.extend(extra)

        # Emit last row
        if cells:
            restored.append("| " + " | ".join(cells) + " |")

    return "\n".join(restored)


class ParentChildChunker:
    """Parent-child chunking with table-aware splitting.

    Pre-splits oversized tables at row boundaries before text splitting.
    Each sub-table is then collapsed to a single token (no newlines), so
    RecursiveCharacterTextSplitter treats it as atomic. After chunking,
    _restore_tables reconstructs multi-line markdown tables.
    """

    def __init__(
        self,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 500,
        overlap: int = 50
    ):
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.overlap = overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""]
        )

    def chunk(self, text: str, doc_id: str) -> list[Chunk]:
        chunks = []
        parents = self._create_parent_chunks(text, doc_id)
        for parent in parents:
            children = self._create_child_chunks(parent, doc_id)
            chunks.append(parent)
            chunks.extend(children)
        return chunks

    def _create_parent_chunks(self, text: str, doc_id: str) -> list[Chunk]:
        """Split text into parent chunks.

        Pre-splits oversized tables, then accumulates content by units
        (paragraphs or pre-split tables) at parent_chunk_size boundaries.
        """
        pre = _pre_split_tables(text, self.parent_chunk_size)

        max_len = 0
        chunks = []
        accumulated: list[str] = []
        acc_size = 0
        unit_count = 0

        # Split on protected paragraph breaks
        units = pre.split("\x00P\x00")

        for unit in units:
            if not unit.strip():
                continue
            unit_lines = unit.split("\n")
            is_table = any(_is_table_line(l) for l in unit_lines)
            unit_size = len(unit) + 1

            if is_table:
                # Flush accumulated non-table content first
                if accumulated:
                    content = "\n".join(accumulated).strip()
                    if content:
                        max_len = max(max_len, len(content))
                        chunks.append(Chunk(
                            chunk_id=f"{doc_id}_parent_{unit_count}",
                            content=content,
                            doc_id=doc_id,
                            chunk_type="parent",
                            parent_id=None,
                            order=unit_count
                        ))
                        unit_count += 1
                        accumulated = []
                        acc_size = 0
                    else:
                        accumulated = []
                        acc_size = 0
                # Emit table as its own parent chunk
                max_len = max(max_len, len(unit))
                chunks.append(Chunk(
                    chunk_id=f"{doc_id}_parent_{unit_count}",
                    content=unit,
                    doc_id=doc_id,
                    chunk_type="parent",
                    parent_id=None,
                    order=unit_count
                ))
                unit_count += 1
            else:
                # Non-table unit: accumulate with size check
                if acc_size + unit_size > self.parent_chunk_size and accumulated:
                    content = "\n".join(accumulated).strip()
                    if content:
                        max_len = max(max_len, len(content))
                        chunks.append(Chunk(
                            chunk_id=f"{doc_id}_parent_{unit_count}",
                            content=content,
                            doc_id=doc_id,
                            chunk_type="parent",
                            parent_id=None,
                            order=unit_count
                        ))
                        unit_count += 1
                    # Overlap: carry last 2 non-empty, non-table lines
                    carry = [
                        l for l in accumulated[-2:]
                        if l.strip() and not _is_table_line(l)
                    ]
                    accumulated = carry
                    acc_size = sum(len(l) + 1 for l in accumulated)
                accumulated.append(unit)
                acc_size += unit_size

        if accumulated:
            content = "\n".join(accumulated).strip()
            if content:
                max_len = max(max_len, len(content))
                chunks.append(Chunk(
                    chunk_id=f"{doc_id}_parent_{unit_count}",
                    content=content,
                    doc_id=doc_id,
                    chunk_type="parent",
                    parent_id=None,
                    order=unit_count
                ))

        if chunks:
            print(f"[Chunker] doc_id={doc_id} | parents={len(chunks)} | max_chars={max_len}")
        return chunks

    def _create_child_chunks(self, parent: Chunk, doc_id: str) -> list[Chunk]:
        """Split a parent chunk into children using direct line accumulation.

        Uses _pre_split_tables to pre-split oversized tables at row boundaries,
        then accumulates lines with paragraph-aware boundaries.
        """
        pre = _pre_split_tables(parent.content, self.child_chunk_size)

        chunks = []
        child_index = 0

        # Split on protected paragraph breaks to get logical units
        # (we use a sentinel that _pre_split_tables does not produce)
        units = pre.split("\x00P\x00")

        for unit in units:
            if not unit.strip():
                continue
            # Each unit: either non-table paragraph, or one pre-split table
            unit_lines = unit.split("\n")
            if any(_is_table_line(l) for l in unit_lines):
                # It's a table (pre-split sub-table) — emit as single atomic child
                chunks.append(Chunk(
                    chunk_id=f"{doc_id}_child_{parent.order}_{child_index}",
                    content=unit,
                    doc_id=doc_id,
                    chunk_type="child",
                    parent_id=parent.chunk_id,
                    order=child_index
                ))
                child_index += 1
            else:
                # Non-table paragraph: accumulate into child chunks by lines
                accumulated: list[str] = []
                acc_size = 0
                for line in unit_lines:
                    line_sz = len(line) + 1
                    if acc_size + line_sz > self.child_chunk_size and accumulated:
                        content = "\n".join(accumulated).strip()
                        if content:
                            chunks.append(Chunk(
                                chunk_id=f"{doc_id}_child_{parent.order}_{child_index}",
                                content=content,
                                doc_id=doc_id,
                                chunk_type="child",
                                parent_id=parent.chunk_id,
                                order=child_index
                            ))
                            child_index += 1
                        # Overlap: carry last non-empty, non-data line
                        carry = [
                            l for l in accumulated[-2:]
                            if l.strip() and not _is_table_line(l)
                        ]
                        accumulated = carry
                        acc_size = sum(len(l) + 1 for l in accumulated)
                    accumulated.append(line)
                    acc_size += line_sz
                if accumulated:
                    content = "\n".join(accumulated).strip()
                    if content:
                        chunks.append(Chunk(
                            chunk_id=f"{doc_id}_child_{parent.order}_{child_index}",
                            content=content,
                            doc_id=doc_id,
                            chunk_type="child",
                            parent_id=parent.chunk_id,
                            order=child_index
                        ))
                        child_index += 1

        return chunks
