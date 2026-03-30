"""
sources/wos/aggregator.py
--------------------------
Aggregates the raw WoS publication data:
  1. Filters to the configured year window (YEAR_START to YEAR_END, inclusive)
  2. Sums citations per faculty member
  3. LEFT JOINs with the full Top-50 faculty list (so 0-citation faculty appear)
  4. Ranks faculty by total citations (highest first)
  5. Saves two output CSVs: citation rankings and ranked individual publications

Run via main.py or directly:
    python -m sources.wos.aggregator

Inputs  (produced by extractor.py)
-------
results/wos/WoS_Publications_FULL.csv

Outputs
-------
results/wos/WoS_Citations_Last_Five_Years.csv      — one row per faculty, ranked
results/wos/WoS_Publication_Last_Five_Years.csv    — one row per publication, ranked
"""

import sys
import pandas as pd
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


def run() -> None:
    """Main aggregation entry point. Called by main.py or run directly."""
    print("\n[WoS] Starting aggregation…")
    print(f"  Year window: {config.YEAR_START}–{config.YEAR_END}")

    full_csv = config.WOS_RESULTS / "WoS_Publications_FULL.csv"
    if not full_csv.exists():
        print(f"[WoS] ERROR: {full_csv} not found. Run the extractor first.")
        return

    # ── Load data ─────────────────────────────────────────────────────────────
    df_pub = pd.read_csv(full_csv)

    # Load full top-50 faculty list for LEFT JOIN (ensures 0-citation faculty appear)
    # Include WoS ResearchID if the column exists in the file
    top50_cols = pd.read_excel(config.FACULTY_TOP50_PATH, nrows=0).columns.tolist()
    id_col     = "WoS ResearchID" if "WoS ResearchID" in top50_cols else None
    load_cols  = config.FACULTY_KEY_COLS + ([id_col] if id_col else [])

    df_faculty = pd.read_excel(config.FACULTY_TOP50_PATH, usecols=load_cols)
    for col in df_faculty.select_dtypes(include="object").columns:
        df_faculty[col] = df_faculty[col].str.strip()

    # ── Normalise types ───────────────────────────────────────────────────────
    df_pub[config.COL_PUB_YEAR] = pd.to_numeric(
        df_pub[config.COL_PUB_YEAR], errors="coerce"
    )
    df_pub = df_pub.dropna(subset=[config.COL_PUB_YEAR])
    df_pub[config.COL_PUB_YEAR] = df_pub[config.COL_PUB_YEAR].astype(int)

    df_pub[config.COL_CITATIONS] = (
        pd.to_numeric(df_pub[config.COL_CITATIONS], errors="coerce").fillna(0).astype(int)
    )

    # ── Filter to year window ─────────────────────────────────────────────────
    mask = (
        (df_pub[config.COL_PUB_YEAR] >= config.YEAR_START) &
        (df_pub[config.COL_PUB_YEAR] <= config.YEAR_END)
    )
    df_window = df_pub[mask].copy()

    # ── Aggregate citations per faculty ───────────────────────────────────────
    df_agg = (
        df_window
        .groupby(config.FACULTY_KEY_COLS)[config.COL_CITATIONS]
        .sum()
        .reset_index()
    )

    # LEFT JOIN: include all Top-50 faculty, filling 0 for those with no pubs
    df_ranked = df_faculty.merge(df_agg, on=config.FACULTY_KEY_COLS, how="left")
    df_ranked[config.COL_CITATIONS] = df_ranked[config.COL_CITATIONS].fillna(0).astype(int)

    # Sort descending by citations, then alphabetically as tiebreaker
    df_ranked = df_ranked.sort_values(
        by=[config.COL_CITATIONS, config.COL_LAST_NAME, config.COL_FIRST_NAME],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    # Add Rank column (1 = most citations)
    df_ranked.insert(0, config.COL_RANK, range(1, len(df_ranked) + 1))
    df_ranked.rename(columns={config.COL_CITATIONS: config.COL_TOTAL_CITES}, inplace=True)

    # Move WoS ResearchID to appear right after the faculty key columns
    if id_col and id_col in df_ranked.columns:
        other_cols = [c for c in df_ranked.columns if c != id_col]
        insert_at  = other_cols.index(config.COL_TOTAL_CITES)
        cols_order = other_cols[:insert_at] + [id_col] + other_cols[insert_at:]
        df_ranked  = df_ranked[cols_order]

    # ── Build ranked publications file ────────────────────────────────────────
    # Merge rank back into per-publication rows
    rank_lookup = df_ranked[[config.COL_RANK] + config.FACULTY_KEY_COLS]
    df_pub_ranked = (
        df_faculty
        .merge(df_window, on=config.FACULTY_KEY_COLS, how="left")
        .merge(rank_lookup, on=config.FACULTY_KEY_COLS, how="left")
        .sort_values(
            by=[config.COL_RANK, config.COL_LAST_NAME,
                config.COL_FIRST_NAME, config.COL_PUB_YEAR],
            ascending=[True, True, True, False],
        )
    )
    # Put Rank first
    cols = [config.COL_RANK] + [c for c in df_pub_ranked.columns if c != config.COL_RANK]
    df_pub_ranked = df_pub_ranked[cols]

    # ── Save outputs ──────────────────────────────────────────────────────────
    citations_csv = config.WOS_RESULTS / "WoS_Citations_Last_Five_Years.csv"
    pubs_csv      = config.WOS_RESULTS / "WoS_Publication_Last_Five_Years.csv"

    df_ranked.to_csv(citations_csv, index=False, encoding="utf-8")
    df_pub_ranked.to_csv(pubs_csv, index=False, encoding="utf-8")

    print(f"[WoS] Saved citation rankings  → {citations_csv.name} ({len(df_ranked)} faculty)")
    print(f"[WoS] Saved ranked publications → {pubs_csv.name} ({len(df_pub_ranked)} records)")
    print(f"[WoS] Aggregation complete.")

    # Quick summary: top 5
    print("\n  Top 5 by WoS citations:")
    top5 = df_ranked.head(5)[
        [config.COL_RANK, config.COL_FIRST_NAME, config.COL_LAST_NAME, config.COL_TOTAL_CITES]
    ]
    for _, r in top5.iterrows():
        print(f"    #{int(r[config.COL_RANK])} {r[config.COL_FIRST_NAME]} {r[config.COL_LAST_NAME]}"
              f" — {int(r[config.COL_TOTAL_CITES])} citations")


if __name__ == "__main__":
    run()
