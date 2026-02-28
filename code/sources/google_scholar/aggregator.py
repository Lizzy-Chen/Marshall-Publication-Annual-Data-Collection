"""
sources/google_scholar/aggregator.py
--------------------------------------
Aggregates raw Google Scholar publication data:
  1. Filters to the configured year window (YEAR_START to YEAR_END, inclusive)
  2. Sums "Cited By" per faculty member
  3. Ranks faculty by total citations (highest first)
  4. Saves citation rankings and ranked individual publications

Note: Google Scholar aggregator does NOT do a LEFT JOIN with the faculty list
(unlike WoS), because Google Scholar covers all faculty via their profile links.
Faculty with no recent publications simply won't appear in the rankings.

Run via main.py or directly:
    python -m sources.google_scholar.aggregator

Inputs  (produced by extractor.py)
-------
results/google_scholar/Google_Scholar_Publications_FULL.csv

Outputs
-------
results/google_scholar/Google_Scholar_Citations_Last_Five_Years.csv
results/google_scholar/Google_Scholar_Publication_Last_Five_Years.csv
"""

import sys
import pandas as pd
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


def run() -> None:
    """Main aggregation entry point. Called by main.py or run directly."""
    print("\n[Google Scholar] Starting aggregation…")
    print(f"  Year window: {config.YEAR_START}–{config.YEAR_END}")

    full_csv = config.GS_RESULTS / "Google_Scholar_Publications_FULL.csv"
    if not full_csv.exists():
        print(f"[Google Scholar] ERROR: {full_csv} not found. Run the extractor first.")
        return

    # ── Load data ─────────────────────────────────────────────────────────────
    df_pub = pd.read_csv(full_csv)

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
        .sort_values(
            by=[config.COL_CITED_BY, config.COL_LAST_NAME, config.COL_FIRST_NAME],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )

    # Add Rank column
    df_agg.insert(0, config.COL_RANK, range(1, len(df_agg) + 1))
    df_agg.rename(columns={config.COL_CITED_BY: config.COL_TOTAL_CITES}, inplace=True)

    # ── Build ranked publications file ────────────────────────────────────────
    rank_lookup = df_agg[[config.COL_RANK] + config.FACULTY_KEY_COLS]
    df_pub_ranked = (
        df_window
        .merge(rank_lookup, on=config.FACULTY_KEY_COLS)
        .sort_values(
            by=[config.COL_RANK, config.COL_LAST_NAME,
                config.COL_FIRST_NAME, config.COL_PUB_YEAR],
            ascending=[True, True, True, False],
        )
    )
    cols = [config.COL_RANK] + [c for c in df_pub_ranked.columns if c != config.COL_RANK]
    df_pub_ranked = df_pub_ranked[cols]

    # ── Save outputs ──────────────────────────────────────────────────────────
    citations_csv = config.GS_RESULTS / "Google_Scholar_Citations_Last_Five_Years.csv"
    pubs_csv      = config.GS_RESULTS / "Google_Scholar_Publication_Last_Five_Years.csv"

    df_agg.to_csv(citations_csv, index=False, encoding="utf-8")
    df_pub_ranked.to_csv(pubs_csv, index=False, encoding="utf-8")

    print(f"[Google Scholar] Saved citation rankings  → {citations_csv.name} ({len(df_agg)} faculty)")
    print(f"[Google Scholar] Saved ranked publications → {pubs_csv.name} ({len(df_pub_ranked)} records)")
    print(f"[Google Scholar] Aggregation complete.")

    # Quick summary: top 5
    print("\n  Top 5 by Google Scholar citations:")
    top5 = df_agg.head(5)[
        [config.COL_RANK, config.COL_FIRST_NAME, config.COL_LAST_NAME, config.COL_TOTAL_CITES]
    ]
    for _, r in top5.iterrows():
        print(f"    #{int(r[config.COL_RANK])} {r[config.COL_FIRST_NAME]} {r[config.COL_LAST_NAME]}"
              f" — {int(r[config.COL_TOTAL_CITES])} citations")


if __name__ == "__main__":
    run()
