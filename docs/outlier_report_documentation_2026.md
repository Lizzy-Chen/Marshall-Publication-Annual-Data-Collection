# Outlier Report — 2026

## Overview

The outlier report automatically flags citation anomalies across data sources after the cross-source comparison runs. It helps identify faculty whose citation counts look suspicious — either because of a wrong researcher ID, a mismatched profile, or a data-currency issue — so they can be manually verified before results are shared.

The report is generated automatically at the end of every comparison run, and can also be re-run at any time via `main.py` option `[O]`.



## Running the Report

### Automatically (recommended)

The outlier report runs automatically after the cross-source comparison completes. Just run the comparison as normal:

```bash
cd code
python main.py   # select [C] or run sources first
```

### Standalone (re-run without re-running comparison)

```bash
cd code
python main.py   # select [O] Outlier report only
```

Or directly:

```bash
cd code
python -m utils.outlier_report
```



## What It Flags

**Expected citation trend: Google Scholar > WoS > ScholarGPS.**

Thresholds are **SD-based**: for each ratio, the cohort mean and standard deviation are computed each run, and faculty are flagged if their ratio deviates beyond `mean ± SD_MULTIPLIER × SD` (default `SD_MULTIPLIER = 1.5`). This flags roughly the top or bottom ~7% of the cohort per ratio — typically around 10–15 faculty total across all three flag types.

### 1. Zero WoS Citations (with significant GS citations)

Faculty with **zero WoS citations** but **20+ Google Scholar citations** are flagged. These cannot be assigned a ratio but are clearly anomalous. Common causes:

- Newly registered WoS ResearchID — citations take 1–2 months to propagate after account creation
- Missing or blank WoS ResearchID in the Top-N faculty list
- Stale ResearchID — faculty changed their WoS account (see Issue 004 in `data_issues_log.md`)

### 2. Abnormal GS:WoS Ratio (either direction)

`GS:WoS = Google Scholar citations ÷ WoS citations`

Expected to be around **2.5** (SD ~1.0–1.5) based on historical data. Faculty are flagged if their ratio falls outside the fixed bounds **< 1.0 or > 4.0** (mean ± 1.5) — typically ~12 faculty in a cohort of 50.

| Flag | Direction | Likely cause |
|------|-----------|-------------|
| **High GS:WoS ratio** (`> 4.0`) | WoS too low | WoS ResearchID is wrong, stale, incomplete, or the account was recently created |
| **Low GS:WoS ratio** (`< 1.0`) | GS too high | Google Scholar profile is merged with another researcher, or includes non-Marshall publications |

### 3. Low SGPS:GS Ratio (ScholarGPS under-counting)

`SGPS:GS = ScholarGPS citations ÷ Google Scholar citations`

Expected to be less than 1 (ScholarGPS < GS). A **low** ratio means ScholarGPS citations are unusually low even relative to that expectation, typically because the profile URL points to the wrong person or an incomplete profile.

| Flag | Likely cause |
|------|-------------|
| **Low SGPS:GS ratio** (`< mean − 1.5 × SD`) | Wrong or mismatched ScholarGPS profile URL |



## Threshold Configuration

| Constant | Default | Effect |
|----------|---------|--------|
| `GS_WOS_LO` | `1.0` | Lower bound for GS:WoS ratio — flag if below this |
| `GS_WOS_HI` | `4.0` | Upper bound for GS:WoS ratio — flag if above this |
| `SD_MULTIPLIER` | `1.0` | SD multiplier for ScholarGPS ratios (cohort-computed) |
| `MIN_GS_FOR_ZERO_WOS_FLAG` | `20` | Minimum GS citations to flag a zero-WoS case |

These constants are defined at the top of `code/utils/outlier_report.py`.



## Output File

**`results/comparison/Outlier_Report.xlsx`**

| Column | Description |
|--------|-------------|
| Last Name, First Name, … | Standard faculty identifiers |
| Google_Total Citations | GS citations (last 5 years) |
| WoS_Total Citations | WoS citations (last 5 years) |
| ScholarGPS_Total Citations | SGPS citations, if available |
| GS:WoS Ratio | Google Scholar ÷ WoS (blank if WoS = 0) |
| SGPS:GS Ratio | ScholarGPS ÷ Google Scholar, if available |
| Outlier Flags | Human-readable description of each flag, including the ratio value and threshold |

### Colour coding

| Colour | Meaning |
|--------|---------|
| Red | Zero WoS citations with 20+ GS citations |
| Gold | Abnormal GS:WoS ratio (too high or too low) |
| Orange | Low SGPS:GS ratio — ScholarGPS under-counting |



## Investigating Flagged Faculty

For each flagged faculty member:

1. **Zero WoS or high GS:WoS ratio (red or gold rows)**
   - Open `data/Top_N_Faculty_{year}.xlsx` and check the `WoS ResearchID` column
   - Search for the faculty member on [webofscience.com](https://webofscience.com) directly to confirm the correct ID
   - For newly registered accounts, re-run the WoS extractor after a few weeks to allow citations to propagate

2. **Low SGPS:GS ratio (orange rows)**
   - Open the `scholargps` URL from `data/Top_N_Faculty_{year}.xlsx` in a browser
   - Verify the profile page belongs to the correct person (check name, institution, publication list)
   - If wrong, find and update the correct profile URL in `2026_Spring_Faculty_List.xlsx`



## Known Limitations

- The outlier report reads from `Comparison_Ranked.csv`, which uses an **inner join** across sources. Faculty who appear in only one source are not included in the outlier analysis.
- SD-based thresholds are computed from the actual cohort each run. With a very small cohort (<10 faculty), mean/SD estimates can be unstable — the method requires at least 4 data points to compute a threshold.
- Zero WoS cases with fewer than 20 GS citations are not flagged to avoid noise from faculty with genuinely low publication output.



## Note on WoS API vs. Website Discrepancy

You may notice small differences between citation counts returned by the API and what is shown on the WoS website. This is expected and is a known limitation of the WoS Starter API:

- The website shows citations aggregated across **all subscribed databases** (Core Collection, BIOSIS, MEDLINE, etc.)
- The Starter API was designed as a metadata-linking tool, not a citation analytics platform. It may not include citations from all non-Core-Collection sub-databases depending on the institutional licence
- Counts from the API are best treated as a **consistent lower bound** suitable for ranking faculty relative to each other, not as definitive absolute citation totals

For definitive absolute counts, the WoS website (logged in via institutional subscription) or the WoS Expanded API would be more complete.



## Contact

- **Author:** Lizzy Chen
- **Email:** LizzyChen@outlook.com
