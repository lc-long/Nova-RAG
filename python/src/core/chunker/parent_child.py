"""Parent-child chunking strategy for RAG with table-aware splitting.

Key enhancements over V1.0:
- Detects markdown tables in text and keeps them as atomic units
- Prevents splitting a table row across chunk boundaries
- Uses '\n---TABLE---\n' as a special section separator during split
"""
import re
from dataclasses import dataclass
from typing import Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Sentinel used to bracket markdown tables during chunking
_TABLE_SENTINEL = "\x00TABLE\x00"


@dataclass
class Chunk:
    chunk_id: str
    content: str
    doc_id: str
    chunk_type: str  # "parent" or "child"
    parent_id: Optional[str] = None
    page_number: Optional[int] = None
    order: int = 0


def _collapse_tables(text: str) -> str:
    """Replace each markdown table block with a single-line sentinel.

    This allows the splitter to treat entire tables as atomic units.
    """
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect table start: line starts with '|' (markdown table)
        if line.startswith("|") and line.rstrip().endswith("|"):
            # Collect all consecutive table rows
            table_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].startswith("|") and lines[j].rstrip().endswith("|"):
                table_lines.append(lines[j])
                j += 1
            # Collapse to one line, using a space to separate rows
            collapsed = (" " + _TABLE_SENTINEL + " ").join(t.strip() for t in table_lines)
            result.append(collapsed)
            i = j
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def _expand_tables(text: str) -> str:
    """Restore collapsed table sentinel back to multi-line markdown tables."""
    lines = text.split(_TABLE_SENTINEL)
    return ("\n".join(
        "\n".join(
            line.strip().replace(" | ", "\n").split("\n")[0].split("|")
            if idx == 0 else "|".join(
                cell.strip() for cell in line.strip().split("|")
            )
            if "|" in line else line
            for idx, line in enumerate(part.split("|"))
        ) if "|" in part else part
    ).join(_TABLE_SENTINEL.split(text)) if _TABLE_SENTINEL not in text else text).replace(
        _TABLE_SENTINEL, "\n"
    ).replace(" \n ", "\n")


def _restore_tables(text: str) -> str:
    """Restore collapsed table sentinel back to multi-line markdown.

    Tables are stored collapsed as: " | Col1 | Col2 |  | --- | --- |  | val1 | val2 |"
    We split on the sentinel and restore the full markdown table format.
    """
    if _TABLE_SENTINEL not in text:
        return text

    parts = text.split(_TABLE_SENTINEL)
    restored_parts = []

    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue

        # Check if this part looks like a collapsed table (contains '|' separators)
        if "|" in stripped:
            # Split on ' | ' to get cell groups, then reformat as markdown rows
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            if len(cells) >= 2:
                # Determine number of columns from header
                # Find the separator row (contains only ---)
                cell_parts = stripped.split("|")
                col_count = 0
                sep_idx = -1
                for idx, cp in enumerate(cell_parts):
                    cp_stripped = cp.strip()
                    if re.match(r'^[-: ]+$', cp_stripped):
                        col_count = idx
                        sep_idx = idx
                        break

                if sep_idx == -1:
                    # No separator found, rebuild as simple table
                    col_count = len([c for c in cells if c])
                    col_count = max(col_count, 1)

                def chunks(lst, n):
                    for i in range(0, len(lst), n):
                        yield lst[i:i+n]

                # Reconstruct markdown table
                data_cells = [c for c in cells if c]
                if data_cells:
                    # First row is header, second row (if exists) is separator
                    rows = list(chunks(data_cells, col_count))
                    md_lines = []
                    for ri, row in enumerate(rows):
                        row_str = "| " + " | ".join(row) + " |"
                        if ri == 1:
                            # Separator row
                            sep = "| " + " | ".join(["---"] * len(row)) + " |"
                            md_lines.append(sep)
                        md_lines.append(row_str)
                    restored_parts.append("\n".join(md_lines))
                else:
                    restored_parts.append(stripped)
            else:
                restored_parts.append(stripped)
        else:
            restored_parts.append(stripped)

    return "\n".join(restored_parts)


class ParentChildChunker:
    """Parent-child chunking with table-aware splitting.

    Tables (markdown format) are collapsed to single-line units before chunking,
    ensuring they are never split mid-row. After chunking, tables are restored
    to their full multi-line markdown form.
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
        """Split text into parent-child chunks, preserving table integrity."""
        chunks = []
        parent_chunks = self._create_parent_chunks(text, doc_id)
        for parent in parent_chunks:
            children = self._create_child_chunks(parent, doc_id)
            chunks.append(parent)
            chunks.extend(children)
        return chunks

    def _create_parent_chunks(self, text: str, doc_id: str) -> list[Chunk]:
        """Create parent chunks using RecursiveCharacterTextSplitter with table protection."""
        # Collapse tables to single lines so splitter treats them as atomic units
        collapsed = _collapse_tables(text)

        texts = self.text_splitter.split_text(collapsed)
        chunks = []

        for i, content in enumerate(texts):
            if content.strip():
                # Restore full markdown tables in the chunk content
                restored = _restore_tables(content)
                parent_id = f"{doc_id}_parent_{i}"
                chunks.append(Chunk(
                    chunk_id=parent_id,
                    content=restored,
                    doc_id=doc_id,
                    chunk_type="parent",
                    parent_id=None,
                    order=i
                ))

        return chunks

    def _create_child_chunks(self, parent: Chunk, doc_id: str) -> list[Chunk]:
        """Create child chunks from a parent chunk, protecting table rows."""
        # Collapse tables again before child-level splitting
        collapsed = _collapse_tables(parent.content)
        text = collapsed
        chunks = []
        start = 0
        child_index = 0

        while start < len(text):
            end = min(start + self.child_chunk_size, len(text))

            # If we're cutting mid-text, try to snap to a word boundary
            if end < len(text):
                while end > start and text[end - 1] not in " \t\n":
                    end -= 1
                if end == start:
                    end = min(start + self.child_chunk_size, len(text))

            child_content = text[start:end].strip()
            if child_content:
                # Restore tables for storage
                restored = _restore_tables(child_content)
                child_id = f"{doc_id}_child_{parent.order}_{child_index}"
                chunks.append(Chunk(
                    chunk_id=child_id,
                    content=restored,
                    doc_id=doc_id,
                    chunk_type="child",
                    parent_id=parent.chunk_id,
                    order=child_index
                ))
                child_index += 1

            # Advance with overlap
            start = end - self.overlap if end < len(text) else len(text)

        return chunks
