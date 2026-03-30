"""
sources/scholargps/aggregator.py
----------------------------------
Aggregates raw ScholarGPS publication data:
  1. Filters to the configured year window
  2. Sums citations per faculty member
  3. LEFT JOINs with the Top-50 faculty list
  4. Ranks faculty by total citations
  5. Saves citation rankings and ranked publications

Run via main.py or directly:
    python -m sources.scholargps.aggregator

Inputs  (produced by extractor.py)
-------
results/scholargps/ScholarGPS_Publications_FULL.csv

Outputs
-------
results/scholargps/ScholarGPS_Citations_Last_Five_Years.csv
results/scholargps/ScholarGPS_Publication_Last_Five_Years.csv
"""

import sys
import pandas as pd
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


def run() -> None:
    """Main aggregation entry point. Called by main.py or run directly."""
    print("\n[ScholarGPS] Starting aggregation…")
    print(f"  Year window: {config.YEAR_START}–{config.YEAR_END}")

    full_csv = config.SGPS_RESULTS / "ScholarGPS_Publications_FULL.csv"
    if not full_csv.exists():
        print(f"[ScholarGPS] ERROR: {full_csv} not found. Run the extractor first.")
        return

    # ── Load data ─────────────────────────────────────────────────────────────
    df_pub = pd.read_csv(full_csv)

    # Load faculty list, including the ScholarGPS profile URL as the authoritative source.
    # The column is named "scholargps" in the faculty list; rename to "ScholarGPS Profile Link"
    # for consistency with the rest of the pipeline.
    # Reading from df_pub would lose the link for faculty whose extraction failed.
    link_col        = "ScholarGPS Profile Link"
    faculty_link_col = "scholargps"
    top50_cols      = pd.read_excel(config.FACULTY_TOP50_PATH, nrows=0).columns.tolist()
    load_cols       = config.FACULTY_KEY_COLS + ([faculty_link_col] if faculty_link_col in top50_cols else [])

    df_faculty = pd.read_excel(config.FACULTY_TOP50_PATH, usecols=load_cols)
    for col in df_faculty.select_dtypes(include="object").columns:
        df_faculty[col] = df_faculty[col].str.strip()
    if faculty_link_col in df_faculty.columns:
        df_faculty = df_faculty.rename(columns={faculty_link_col: link_col})

    # ── Normalise types ───────────────────────────────────────────────────────
    df_pub[config.COL_PUB_YEAR] = pd.to_numeric(
        df_pub[config.COL_PUB_YEAR], errors="coerce"
    )
    df_pub = df_pub.dropna(subset=[config.COL_PUB_YEAR])
    df_pub[config.COL_PUB_YEAR] = df_pub[config.COL_PUB_YEAR].astype(int)

    df_pub[config.COL_CITED_BY] = (
        pd.to_numeric(df_pub[config.COL_CITED_BY], errors="coerce").fillna(0).astype(int)
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
        .groupby(config.FACULTY_KEY_COLS)[config.COL_CITED_BY]
        .sum()
        .reset_index()
    )

    # LEFT JOIN: include all Top-50 faculty
    df_ranked = df_faculty.merge(df_agg, on=config.FACULTY_KEY_COLS, how="left")
    df_ranked[config.COL_CITED_BY] = df_ranked[config.COL_CITED_BY].fillna(0).astype(int)

    df_ranked = df_ranked.sort_values(
        by=[config.COL_CITED_BY, config.COL_LAST_NAME, config.COL_FIRST_NAME],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    df_ranked.insert(0, config.COL_RANK, range(1, len(df_ranked) + 1))
    df_ranked.rename(columns={config.COL_CITED_BY: config.COL_TOTAL_CITES}, inplace=True)

    # Place ScholarGPS Profile Link right before Total Citations (it came in via df_faculty)
    if link_col in df_ranked.columns:
        other_cols = [c for c in df_ranked.columns if c != link_col]
        insert_at  = other_cols.index(config.COL_TOTAL_CITES)
        df_ranked  = df_ranked[other_cols[:insert_at] + [link_col] + other_cols[insert_at:]]

    # ── Build ranked publications file ────────────────────────────────────────
    rank_lookup   = df_ranked[[config.COL_RANK] + config.FACULTY_KEY_COLS]
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

    cols = [config.COL_RANK] + [c for c in df_pub_ranked.columns if c != config.COL_RANK]
    df_pub_ranked = df_pub_ranked[cols]

    # ── Save outputs ──────────────────────────────────────────────────────────
    citations_csv = config.SGPS_RESULTS / "ScholarGPS_Citations_Last_Five_Years.csv"
    pubs_csv      = config.SGPS_RESULTS / "ScholarGPS_Publication_Last_Five_Years.csv"

    df_ranked.to_csv(citations_csv, index=False, encoding="utf-8")
    df_pub_ranked.to_csv(pubs_csv, index=False, encoding="utf-8")

    print(f"[ScholarGPS] Saved citation rankings  → {citations_csv.name} ({len(df_ranked)} faculty)")
    print(f"[ScholarGPS] Saved ranked publications → {pubs_csv.name} ({len(df_pub_ranked)} records)")
    print(f"[ScholarGPS] Aggregation complete.")

    # Quick summary: top 5
    print("\n  Top 5 by ScholarGPS citations:")
    top5 = df_ranked.head(5)[
        [config.COL_RANK, config.COL_FIRST_NAME, config.COL_LAST_NAME, config.COL_TOTAL_CITES]
    ]
    for _, r in top5.iterrows():
        print(f"    #{int(r[config.COL_RANK])} {r[config.COL_FIRST_NAME]} {r[config.COL_LAST_NAME]}"
              f" — {int(r[config.COL_TOTAL_CITES])} citations")


if __name__ == "__main__":
    run()
