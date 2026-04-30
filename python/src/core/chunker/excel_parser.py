"""Excel (.xlsx) document parser with multi-sheet Markdown conversion."""
import pandas as pd


def extract_text_from_excel(file_path: str) -> str:
    """Extract all sheets from an Excel file as clean Markdown tables.

    Reads with header=None so merged-cell titles are treated as ordinary data
    rows — no "Unnamed" column pollution. All-empty rows/columns are stripped,
    NaN cells are filled with empty strings, and the sheet name is emitted as
    a semantic anchor before each table.

    Args:
        file_path: Path to the .xlsx file.

    Returns:
        All sheets joined as Markdown text with sheet anchors.
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

        # Suppress the auto-generated numeric column labels (0, 1, 2, ...)
        # by replacing them with empty strings before markdown serialisation
        df.columns = [""] * len(df.columns)

        blocks.append(f"\n--- [工作表: {sheet_name}] ---\n")
        blocks.append(df.to_markdown(index=False))

    return "\n".join(blocks)

