"""Excel (.xlsx) document parser with multi-sheet Markdown conversion."""
import pandas as pd


def extract_text_from_excel(file_path: str) -> str:
    """Extract all sheets from an Excel file as clean Markdown tables.

    Reads with header=None so merged-cell titles are treated as ordinary data
    rows — no "Unnamed" column pollution. All-empty rows/columns are stripped,
    NaN cells are filled with empty strings. Each sheet is prefixed with a
    semantic header that lists field indices, bridging the lexical gap between
    natural-language queries and raw numeric table columns.

    Prefix format (per sheet):
        [文档属性]: 结构化数据表
        [包含的字段/列名]: 字段1, 字段2, 字段3, ...  (position-based since header=None)
        [数据内容概要]: 以下是该数据表的具体 Markdown 网格内容。
        --- 表格数据开始 ---

    Args:
        file_path: Path to the .xlsx file.

    Returns:
        All sheets joined as Markdown text with semantic headers and anchors.
    """
    xl_file = pd.ExcelFile(file_path)

    blocks = []
    for sheet_name in xl_file.sheet_names:
        if sheet_name.startswith("_"):
            continue

        # header=None: treat every row as a data row (no auto header inference)
        df = xl_file.parse(sheet_name=sheet_name, header=None)

        # Strict cleaning: drop all-empty rows and columns
        df = df.dropna(axis=1, how="all")
        df = df.dropna(axis=0, how="all")
        df = df.fillna("")

        if df.empty:
            continue

        n_cols = len(df.columns)
        # Since header=None, generate position-based field names
        col_list = ", ".join(f"字段{i+1}" for i in range(n_cols))

        # Build semantic prefix for this sheet
        sheet_prefix = (
            f"\n--- [工作表: {sheet_name}] ---\n"
            f"[文档属性]: 结构化数据表\n"
            f"[包含的字段/列名]: {col_list}\n"
            f"[数据内容概要]: 以下是该数据表的具体 Markdown 网格内容。\n"
            f"--- 表格数据开始 ---\n"
        )

        # Suppress the auto-generated numeric column labels (0, 1, 2, ...)
        df.columns = [""] * n_cols

        blocks.append(sheet_prefix)
        blocks.append(df.to_markdown(index=False))

    return "\n".join(blocks)

