"""Excel (.xlsx) document parser with multi-sheet Markdown conversion."""
import pandas as pd


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove completely empty rows and columns to reduce token noise."""
    # Drop columns that are entirely empty
    df = df.dropna(axis=1, how="all")
    # Drop rows that are entirely empty
    df = df.dropna(axis=0, how="all")
    # Replace any remaining NaN cells with empty string
    df = df.fillna("")
    return df


def extract_text_from_excel(file_path: str) -> str:
    """Extract all sheets from an Excel file as Markdown tables.

    Traverses all visible sheets, converts each to a Markdown table via
    pandas, and prepends a sheet-name anchor so the LLM knows the data
    provenance. Empty rows/columns are stripped before conversion.

    Args:
        file_path: Path to the .xlsx file.

    Returns:
        All sheets joined as Markdown text with sheet anchors.
    """
    xl_file = pd.ExcelFile(file_path)

    blocks = []
    for sheet_name in xl_file.sheet_names:
        # Skip hidden sheets (e.g., those starting with underscore)
        if sheet_name.startswith("_"):
            continue

        df = xl_file.parse(sheet_name=sheet_name)
        df = _clean_dataframe(df)

        if df.empty:
            continue

        # Sheet anchor header
        blocks.append(f"\n--- [工作表: {sheet_name}] ---\n")

        # Convert DataFrame to Markdown table (no index column)
        md_table = df.to_markdown(index=False)
        blocks.append(md_table)

    return "\n".join(blocks)
