"""
utils/comparison.py
--------------------
Cross-source comparison and visualisation.

Merges citation rankings from all available sources (WoS, Google Scholar,
ScholarGPS), computes average citations, ranks faculty by the average, and
produces:
  - Comparison_Ranked.csv
  - GPS_GS_citation_comparison.xlsx  (formatted Excel comparison)
  - comparison_chart_by_gs_rank.png  (bar chart sorted by Google Scholar rank)
  - comparison_chart_by_sgps_rank.png (bar chart sorted by ScholarGPS rank)

Called by main.py after extraction/aggregation, or run directly:
    python -m utils.comparison

Outputs
-------
results/comparison/
"""

import sys
import pandas as pd
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import config

try:
    import matplotlib
    matplotlib.use("Agg")   # Non-interactive backend — works without a display
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[Comparison] WARNING: matplotlib not installed. Charts will be skipped.")


def _load_citations_csv(path: Path, source_label: str) -> pd.DataFrame | None:
    """
    Load a per-source citation rankings CSV.
    Returns None (with a warning) if the file doesn't exist.
    """
    if not path.exists():
        print(f"  [SKIP] {source_label} citations file not found: {path.name}")
        return None
    df = pd.read_csv(path)
    return df


def _make_bar_chart(
    df: pd.DataFrame,
    sort_by_col: str,
    gs_col: str,
    sgps_col: str,
    out_path: Path,
    title: str,
) -> None:
    """
    Create a grouped/stacked bar chart comparing Google Scholar vs ScholarGPS
    citations, sorted by the given column.
    Saves to out_path as PNG.
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    df_sorted = df.sort_values(sort_by_col).head(30)  # Top 30 for readability
    names = df_sorted[config.COL_LAST_NAME] + ", " + df_sorted[config.COL_FIRST_NAME]

    fig, ax = plt.subplots(figsize=(14, 7))
    x = range(len(names))

    ax.bar(x, df_sorted[gs_col],   label="Google Scholar", alpha=0.8, color="#1f77b4")
    ax.bar(x, df_sorted[sgps_col], label="ScholarGPS",     alpha=0.8, color="#ff7f0e",
           bottom=0)

    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Total Citations (Last 5 Years)")
    ax.set_title(title)
    ax.legend()
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Chart saved → {out_path.name}")


def run() -> None:
    """
    Main comparison entry point. Discovers which source result files exist,
    merges them, and produces comparison outputs.
    """
    print("\n[Comparison] Starting cross-source comparison…")

    config.COMP_RESULTS.mkdir(parents=True, exist_ok=True)

    # ── Load available source rankings ────────────────────────────────────────
    sources_loaded = {}

    wos_path = config.WOS_RESULTS / "WoS_Citations_Last_Five_Years.csv"
    df_wos   = _load_citations_csv(wos_path, "WoS")
    if df_wos is not None:
        df_wos = df_wos.rename(columns={
            config.COL_RANK:        "WoS_Rank",
            config.COL_TOTAL_CITES: "WoS_Total Citations",
        })
        sources_loaded["wos"] = df_wos

    gs_path = config.GS_RESULTS / "Google_Scholar_Citations_Last_Five_Years.csv"
    df_gs   = _load_citations_csv(gs_path, "Google Scholar")
    if df_gs is not None:
        df_gs = df_gs.rename(columns={
            config.COL_RANK:        "Google_Rank",
            config.COL_TOTAL_CITES: "Google_Total Citations",
        })
        sources_loaded["google_scholar"] = df_gs

    sgps_path = config.SGPS_RESULTS / "ScholarGPS_Citations_Last_Five_Years.csv"
    df_sgps   = _load_citations_csv(sgps_path, "ScholarGPS")
    if df_sgps is not None:
        df_sgps = df_sgps.rename(columns={
            config.COL_RANK:        "ScholarGPS_Rank",
            config.COL_TOTAL_CITES: "ScholarGPS_Total Citations",
        })
        sources_loaded["scholargps"] = df_sgps

    if len(sources_loaded) < 2:
        print("[Comparison] Need at least 2 sources to compare. Run more sources first.")
        return

    print(f"  Sources available: {', '.join(sources_loaded.keys())}")

    # ── Merge all sources (INNER JOIN on faculty key columns) ─────────────────
    # Start with the first source, then inner-join the rest
    source_list = list(sources_loaded.values())
    df_merged   = source_list[0]
    for df_next in source_list[1:]:
        df_merged = df_merged.merge(df_next, on=config.FACULTY_KEY_COLS, how="inner")

    # ── Compute average citations across available sources ────────────────────
    citation_cols = [c for c in df_merged.columns if c.endswith("Total Citations")]
    df_merged["Average_Citations"] = df_merged[citation_cols].mean(axis=1).round(2)

    df_merged = df_merged.sort_values(
        "Average_Citations", ascending=False
    ).reset_index(drop=True)
    df_merged.insert(0, "Average_Citations_Rank", range(1, len(df_merged) + 1))

    # ── Reorder columns for readability ───────────────────────────────────────
    # Key cols first, then source-specific rank + citation pairs, then average
    priority_order = ["Average_Citations_Rank"] + config.FACULTY_KEY_COLS

    # Add source columns in a consistent order
    for src_prefix, rank_col, cit_col in [
        ("WoS",        "WoS_Rank",        "WoS_Total Citations"),
        ("Google",     "Google_Rank",     "Google_Total Citations"),
        ("ScholarGPS", "ScholarGPS_Rank", "ScholarGPS_Total Citations"),
    ]:
        for col in [rank_col, cit_col]:
            if col in df_merged.columns:
                priority_order.append(col)

    priority_order.append("Average_Citations")
    remaining = [c for c in df_merged.columns if c not in priority_order]
    df_merged  = df_merged[priority_order + remaining]

    # ── Save Comparison_Ranked.csv ────────────────────────────────────────────
    ranked_csv = config.COMP_RESULTS / "Comparison_Ranked.csv"
    df_merged.to_csv(ranked_csv, index=False, encoding="utf-8")
    print(f"  Saved: {ranked_csv.name} ({len(df_merged)} faculty)")

    # ── Excel comparison (Google Scholar vs ScholarGPS) ────────────────────────
    if "google_scholar" in sources_loaded and "scholargps" in sources_loaded:
        _save_excel_comparison(df_merged)
        _save_comparison_charts(df_merged)

    print("[Comparison] Complete.")

    # Print top 5 by average
    print("\n  Top 5 by average citations across sources:")
    avg_col_name = "Average_Citations"
    top5 = df_merged.head(5)[
        ["Average_Citations_Rank", config.COL_FIRST_NAME,
         config.COL_LAST_NAME, avg_col_name]
    ]
    for _, r in top5.iterrows():
        print(f"    #{int(r['Average_Citations_Rank'])} "
              f"{r[config.COL_FIRST_NAME]} {r[config.COL_LAST_NAME]} "
              f"— avg {r[avg_col_name]:.0f} citations")


def _save_excel_comparison(df_merged: pd.DataFrame) -> None:
    """
    Save a formatted Excel file comparing Google Scholar vs ScholarGPS rankings.
    Highlights faculty where the rank difference is >= 10 and they are in the top 20.
    """
    try:
        from openpyxl import load_workbook
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("  [SKIP] openpyxl not installed — Excel comparison skipped.")
        return

    # Select relevant columns
    cols_to_keep = (
        config.FACULTY_KEY_COLS
        + [c for c in ["Google_Rank", "Google_Total Citations",
                        "ScholarGPS_Rank", "ScholarGPS_Total Citations"]
           if c in df_merged.columns]
    )
    df_comp = df_merged[cols_to_keep].copy()

    # Add rank difference column (if both sources present)
    if "Google_Rank" in df_comp.columns and "ScholarGPS_Rank" in df_comp.columns:
        df_comp["Rank Difference"] = (
            df_comp["Google_Rank"] - df_comp["ScholarGPS_Rank"]
        ).abs()
        df_comp["Notable Discrepancy"] = (
            (df_comp["Rank Difference"] >= 10) &
            ((df_comp["Google_Rank"] <= 20) | (df_comp["ScholarGPS_Rank"] <= 20))
        )

    out_path = config.COMP_RESULTS / "GPS_GS_citation_comparison.xlsx"
    df_comp.to_excel(out_path, index=False)

    # Apply formatting
    wb = load_workbook(out_path)
    ws = wb.active

    HEADER_FILL   = PatternFill("solid", fgColor="1F4E79")
    ALERT_FILL    = PatternFill("solid", fgColor="FFD700")  # Gold for discrepancies
    BORDER = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"),  bottom=Side(style="thin"),
    )

    header_vals = [cell.value for cell in ws[1]]

    # Header row
    for cell in ws[1]:
        cell.fill      = HEADER_FILL
        cell.font      = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border    = BORDER

    # Data rows
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        is_discrepancy = False
        if "Notable Discrepancy" in header_vals:
            disc_col_idx = header_vals.index("Notable Discrepancy")
            is_discrepancy = str(row[disc_col_idx].value).upper() == "TRUE"

        for cell in row:
            cell.border    = BORDER
            cell.alignment = Alignment(vertical="center")
            if is_discrepancy:
                cell.fill = ALERT_FILL

    # Auto-size columns
    for col in ws.columns:
        max_len = max(
            (len(str(cell.value)) if cell.value else 0) for cell in col
        )
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"
    wb.save(out_path)
    print(f"  Excel comparison saved → {out_path.name}")


def _save_comparison_charts(df_merged: pd.DataFrame) -> None:
    """Generate bar chart comparisons sorted by Google Scholar rank and ScholarGPS rank."""
    if not MATPLOTLIB_AVAILABLE:
        return

    gs_col   = "Google_Total Citations"
    sgps_col = "ScholarGPS_Total Citations"

    if gs_col not in df_merged.columns or sgps_col not in df_merged.columns:
        return

    _make_bar_chart(
        df_merged,
        sort_by_col="Google_Rank",
        gs_col=gs_col,
        sgps_col=sgps_col,
        out_path=config.COMP_RESULTS / "comparison_chart_by_gs_rank.png",
        title="Citation Comparison: Google Scholar vs ScholarGPS\n(Sorted by Google Scholar Rank)",
    )

    _make_bar_chart(
        df_merged,
        sort_by_col="ScholarGPS_Rank",
        gs_col=gs_col,
        sgps_col=sgps_col,
        out_path=config.COMP_RESULTS / "comparison_chart_by_sgps_rank.png",
        title="Citation Comparison: Google Scholar vs ScholarGPS\n(Sorted by ScholarGPS Rank)",
    )


if __name__ == "__main__":
    run()
