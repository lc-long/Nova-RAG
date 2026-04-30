"""Structure-aware Markdown splitter that preserves heading hierarchy.

Splits on Markdown heading boundaries (h1–h6), keeping all content under
a heading together. When a section exceeds max_size, the heading path is
prepended to every sub-chunk so LLM always sees the structural context.
"""
import re
from dataclasses import dataclass


@dataclass
class MarkdownSection:
    heading_path: str  # e.g. "## Getting Started\n### Installation"
    content: str


# Regex: optional leading #, spaces, heading text
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)")


def split_markdown(text: str, max_size: int) -> list[MarkdownSection]:
    """Split Markdown text on heading boundaries, preserving heading context.

    Algorithm:
      1. Scan lines, maintain a heading_stack of (level, text) pairs.
      2. When a heading is encountered, pop all entries of equal/higher level,
         then push the new heading.
      3. Accumulate content lines under the current heading stack.
      4. When accumulated section chars exceed max_size, emit a chunk
         (with the full heading_path prepended) and start a new accumulation.
         The split body retains as many complete paragraphs as possible.

    Args:
        text: Full Markdown document text.
        max_size: Approximate character size limit per section.

    Returns:
        List of MarkdownSection, each with heading_path and body content.
    """
    lines = text.split("\n")
    sections: list[MarkdownSection] = []

    # Heading stack: list of (level, text) in order h1 > h2 > h3 ...
    heading_stack: list[tuple[int, str]] = []

    # Current accumulation buffer
    acc_lines: list[str] = []
    acc_size = 0

    def flush() -> MarkdownSection | None:
        """Emit the current accumulated block as one section."""
        nonlocal acc_lines, acc_size
        if not acc_lines:
            return None
        body = "\n".join(acc_lines).strip()
        if not body:
            return None
        path = "\n".join(h for _, h in heading_stack)
        acc_lines = []
        acc_size = 0
        return MarkdownSection(heading_path=path, content=body)

    def try_split_large_section(section: MarkdownSection) -> list[MarkdownSection]:
        """Split a section that already exceeds max_size using paragraph boundaries."""
        if len(section.content) <= max_size:
            return [section]

        # Split body by paragraph boundaries (\n\n)
        para_blocks = section.content.split("\n\n")
        results: list[MarkdownSection] = []
        current_para: list[str] = []
        current_size = 0

        for para in para_blocks:
            para_len = len(para) + 2  # +2 for \n\n
            if current_size + para_len > max_size and current_para:
                # Emit accumulated paragraphs as one section
                results.append(MarkdownSection(
                    heading_path=section.heading_path,
                    content="\n\n".join(current_para)
                ))
                current_para = []
                current_size = 0
            current_para.append(para)
            current_size += para_len

        if current_para:
            results.append(MarkdownSection(
                heading_path=section.heading_path,
                content="\n\n".join(current_para)
            ))

        # If still one giant paragraph, split by line instead
        final: list[MarkdownSection] = []
        for sec in results:
            if len(sec.content) <= max_size:
                final.append(sec)
            else:
                sub_lines = sec.content.split("\n")
                cur: list[str] = []
                cur_sz = 0
                for ln in sub_lines:
                    ln_sz = len(ln) + 1
                    if cur_sz + ln_sz > max_size and cur:
                        final.append(MarkdownSection(
                            heading_path=sec.heading_path,
                            content="\n".join(cur)
                        ))
                        cur = []
                        cur_sz = 0
                    cur.append(ln)
                    cur_sz += ln_sz
                if cur:
                    final.append(MarkdownSection(
                        heading_path=sec.heading_path,
                        content="\n".join(cur)
                    ))
        return final

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            # Flush accumulated content under the previous heading
            sec = flush()
            if sec:
                # Apply sub-splitting if the section itself is too large
                sections.extend(try_split_large_section(sec))

            level = len(m.group(1))
            heading_text = m.group(2).strip()

            # Pop entries of equal or higher level
            heading_stack = [h for h in heading_stack if h[0] < level]
            heading_stack.append((level, f"{'#' * level} {heading_text}"))
            acc_lines = []
            acc_size = 0
        else:
            acc_lines.append(line)
            acc_size += len(line) + 1

            if acc_size >= max_size:
                # The accumulated block is large enough: flush it
                sec = flush()
                if sec:
                    sections.extend(try_split_large_section(sec))

    # Final flush
    sec = flush()
    if sec:
        sections.extend(try_split_large_section(sec))

    return sections
