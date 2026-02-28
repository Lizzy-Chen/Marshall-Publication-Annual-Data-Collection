"""
utils/faculty_loader.py
-----------------------
Shared utility for loading and validating faculty Excel files.

All source extractors use this module to load their faculty list so that
the loading logic (column validation, missing-value handling, whitespace
normalisation) is written once and stays consistent.
"""

import sys
import pandas as pd
from pathlib import Path


def load_faculty(
    file_path: Path,
    required_cols: list[str],
    id_col: str | None = None,
) -> pd.DataFrame:
    """
    Load a faculty Excel file, validate that required columns are present,
    and return a clean DataFrame.

    Parameters
    ----------
    file_path : Path
        Path to the Excel file (.xlsx).
    required_cols : list[str]
        Columns that must exist in the file. Raises SystemExit if any are missing.
    id_col : str | None
        If provided, rows where this column is null/empty are dropped (they
        cannot be queried) and a warning is printed for each dropped row.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with only the required columns, whitespace stripped
        from all string columns.
    """
    if not file_path.exists():
        print(f"[ERROR] Faculty file not found: {file_path}")
        print("  Make sure the file is in the data/ directory.")
        sys.exit(1)

    try:
        df = pd.read_excel(file_path, usecols=required_cols)
    except ValueError as exc:
        # pandas raises ValueError when a usecols column doesn't exist
        print(f"[ERROR] Could not read '{file_path.name}': {exc}")
        print(f"  Make sure the file contains these columns: {required_cols}")
        sys.exit(1)

    # Strip leading/trailing whitespace from all string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Drop rows missing the source-specific ID (can't query without it)
    if id_col:
        missing_mask = df[id_col].isna() | (df[id_col].astype(str).str.strip() == "")
        if missing_mask.any():
            missing = df[missing_mask][["Last Name", "First Name"]].values.tolist()
            for last, first in missing:
                print(f"  [WARN] No {id_col} for {first} {last} — will be logged as error")
        df = df[~missing_mask].reset_index(drop=True)

    return df
