"""CSV document parser using pandas with rigorous cleaning and semantic header injection."""
import pandas as pd


def extract_text_from_csv(file_path: str) -> str:
    """Read a CSV file and emit a clean Markdown table with semantic header.

    Reads with default header (first row = column names) so real column names
    are preserved. Extracts those names and injects a structured semantic
    prefix that bridges the lexical gap between user queries like "超参数"
    and the raw ASCII table columns.

    Prefix format:
        [文档属性]: 结构化数据表
        [包含的字段/列名]: col1, col2, col3, ...
        [数据内容概要]: 以下是该数据表的具体 Markdown 网格内容。
        --- 表格数据开始 ---

    Args:
        file_path: Path to the .csv file.

    Returns:
        Markdown table string prefixed with semantic header.
    """
    df = pd.read_csv(file_path)

    # Strict cleaning — mirrors the Excel parser pipeline
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    df = df.fillna("")

    if df.empty:
        return ""

    # Extract real column names for semantic injection
    columns = list(df.columns)
    col_list = ", ".join(str(c) for c in columns)

    # Build semantic prefix
    prefix = (
        f"[文档属性]: 结构化数据表\n"
        f"[包含的字段/列名]: {col_list}\n"
        f"[数据内容概要]: 以下是该数据表的具体 Markdown 网格内容。\n"
        f"--- 表格数据开始 ---\n"
    )

    return prefix + df.to_markdown(index=False)
