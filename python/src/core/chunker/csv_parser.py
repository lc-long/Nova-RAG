"""CSV document parser using pandas with the same rigorous cleaning pipeline as Excel."""
import pandas as pd


def extract_text_from_csv(file_path: str) -> str:
    """Read a CSV file and emit a clean Markdown table.

    Uses header=None to avoid polluted column names from dirty CSVs.
    All-empty rows/columns are dropped, NaN cells are filled with empty strings,
    then the DataFrame is serialised as a Markdown grid.

    Args:
        file_path: Path to the .csv file.

    Returns:
        Markdown table string.
    """
    df = pd.read_csv(file_path, header=None)

    # Strict cleaning — mirrors the Excel parser pipeline
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")
    df = df.fillna("")

    if df.empty:
        return ""

    # Suppress auto-generated numeric column labels
    df.columns = [""] * len(df.columns)

    return df.to_markdown(index=False)
