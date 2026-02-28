# Architecture: Marshall Faculty Publication Data Collection System

**Project:** Marshall Faculty Publication Data Collection
**Version:** 2026
**Date:** 2026-02-27
**Author:** Lizzy Chen
**Contact:** LizzyChen@outlook.com

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architectural Drivers](#2-architectural-drivers)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Technology Stack](#4-technology-stack)
5. [System Components](#5-system-components)
6. [Data Architecture](#6-data-architecture)
7. [Directory & File Structure](#7-directory--file-structure)
8. [Execution Workflow](#8-execution-workflow)
9. [NFR Coverage](#9-nfr-coverage)
10. [Security Architecture](#10-security-architecture)
11. [Extensibility: Adding New Data Sources](#11-extensibility-adding-new-data-sources)
12. [Development & Deployment](#12-development--deployment)
13. [Traceability & Trade-offs](#13-traceability--trade-offs)
14. [Changes from 2025](#14-changes-from-2025)



## 1. Project Overview

### Purpose

The Marshall Faculty Publication Data Collection system automates the extraction, aggregation, and cross-source comparison of academic publication and citation data for Marshall School of Business faculty. It pulls data from multiple authoritative academic databases, filters to a configurable recent-year window, ranks faculty by citation count, and produces structured CSV/Excel outputs for analysis and reporting.

### Scope

- **Data Sources (2026 active):** Web of Science (WoS), Google Scholar (via SerpAPI)
- **Data Sources (kept, not active in 2026):** ScholarGPS (Selenium scraping)
- **Faculty Coverage:** Full faculty list for Google Scholar; Top-50 filtered list for WoS and ScholarGPS
- **Time Window:** Last 5 years (dynamic, calculated from current year)
- **Outputs:** Per-source ranked publications and citation summaries, cross-source comparison

### Key 2026 Improvements

| Area | 2025 | 2026 |
|------|------|------|
| Entry Point | Run scripts individually | Single `main.py` with source selector |
| Credentials | Hardcoded in scripts | `.env` file (not committed to git) |
| Code Structure | Flat scripts per source | Modular packages with base classes |
| Configuration | Hardcoded paths/values | Centralized `config.py` |
| Error Handling | Basic try/except | Structured logging, retry logic |
| Extensibility | Duplicate code per source | Plugin pattern: add a new source in one place |
| Documentation | Per-source docs | Unified architecture + per-source docs |
| Dependencies | No requirements file | `requirements.txt` |



## 2. Architectural Drivers

The following requirements most heavily influence design decisions:

**AD-1: Extensibility**
> New data sources (e.g., Scopus, OpenAlex) may need to be added in future years. The architecture must make adding a source a localized, low-effort change — not a full rewrite.
> → Requires: plugin/strategy pattern, shared base classes, centralized orchestration.

**AD-2: Selective Execution**
> Different sources have different automation constraints (ScholarGPS requires manual CAPTCHA solving). The system must allow the operator to choose which sources to run per session.
> → Requires: source-selection UI in main entry point, independent source modules.

**AD-3: Credential Security**
> API keys (WoS, SerpAPI) must not be hardcoded in source files or committed to version control.
> → Requires: `.env`-based credential management.

**AD-4: Operational Reliability**
> API calls can fail due to network issues, rate limits, or invalid IDs. The system must log errors clearly and continue processing remaining faculty — not crash on the first failure.
> → Requires: per-faculty error isolation, structured error logs, retry logic for transient failures.

**AD-5: Reproducibility**
> The same input files and credentials should produce the same outputs when run again. Year window must be dynamically computed, not hardcoded.
> → Requires: dynamic year calculation, deterministic sorting, idempotent output writes.

**AD-6: Maintainability**
> Scripts will be handed off to future RAs with varying Python experience. Code must be clearly structured, documented, and runnable with a single command.
> → Requires: clear directory structure, inline comments, comprehensive README.



## 3. High-Level Architecture

### Pattern: Modular Pipeline with Plugin Sources

```
┌─────────────────────────────────────────────────────────┐
│                       main.py                           │
│             (Orchestrator / Source Selector)            │
└──────────────┬──────────────────────────────────────────┘
               │  User selects: [WoS] [Google Scholar] [ScholarGPS] [Compare]
               ▼
┌─────────────────────────────────────────────────────────┐
│                    config.py                            │
│   (Year window, file paths, faculty list config)        │
└──────────────┬──────────────────────────────────────────┘
               │
     ┌─────────┼──────────────────┐
     ▼         ▼                  ▼
┌─────────┐ ┌──────────────┐ ┌──────────────┐
│  WoS    │ │Google Scholar│ │  ScholarGPS  │
│ Source  │ │    Source    │ │   Source     │
│ Module  │ │    Module    │ │   Module     │
└────┬────┘ └──────┬───────┘ └──────┬───────┘
     │             │                │
  extractor      extractor       extractor
     │              │                │
  aggregator    aggregator      aggregator
     │              │                │
     └──────────────┴────────────────┘
                    │
                    ▼
          ┌─────────────────┐
          │  results/       │
          │  ├── wos/       │
          │  ├── google_    │
          │  │   scholar/   │
          │  ├── scholargps/│
          │  └── comparison/│
          └─────────────────┘
                    │
                    ▼
          ┌─────────────────────┐
          │  utils/comparison.py│
          │  (Multi-source rank │
          │   + visualizations) │
          └─────────────────────┘
```

### Architecture Principles

1. **Each source is self-contained** — a source module handles its own extraction, aggregation, and output. It knows nothing about other sources.
2. **main.py is the only entry point** — the user runs one command. main.py presents a menu and delegates to the appropriate source modules.
3. **Configuration is centralized** — file paths, year window, and column names are defined in `config.py`. Source scripts import from config; they do not define paths themselves.
4. **Credentials are external** — API keys live in `.env`, never in code.
5. **Comparison is a downstream step** — the comparison/ranking script runs after at least two sources have been collected, using their output CSVs.



## 4. Technology Stack

**Python Runtime**

- **Choice:** Python 3.9+
- **Rationale:** Pandas 2.x requires 3.9+. Type hints, f-strings, and `pathlib` used throughout.
- **Trade-off:** Slightly higher minimum version requirement vs. broader compatibility.

**Data Processing**

- **Choice:** pandas 2.x
- **Rationale:** Industry standard for tabular data in Python. Handles Excel, CSV, groupby, merge, and filtering in a unified API.
- **Trade-off:** Memory-heavy for very large datasets, but faculty lists (~100 rows) and publications (~15,000 rows) are well within limits.

**HTTP / API Calls**

- **Choice:** `requests` (for WoS API)
- **Rationale:** Simple, mature, well-documented. WoS Starter API is a standard REST API with JSON responses.

**Google Scholar API**

- **Choice:** `google-search-results` (SerpAPI SDK)
- **Rationale:** SerpAPI provides a reliable abstraction over Google Scholar with built-in pagination. Direct Google Scholar scraping violates ToS and is fragile.
- **Trade-off:** Paid API with rate limits. Free tier may be exhausted on large runs.

**Web Scraping (ScholarGPS)**

- **Choice:** Selenium + ChromeDriver
- **Rationale:** ScholarGPS renders content via JavaScript; static HTML parsers (BeautifulSoup) cannot access it. Selenium drives a real browser.
- **Trade-off:** Requires ChromeDriver installation. CAPTCHA blocking requires manual intervention. **Not active in 2026.**

**Credential Management**

- **Choice:** `python-dotenv`
- **Rationale:** Industry-standard `.env` file approach. Zero configuration overhead. `.env` is excluded from version control via `.gitignore`.

**Excel I/O**

- **Choice:** `openpyxl` (via pandas `read_excel`)
- **Rationale:** Standard library for reading `.xlsx` files. Required by pandas for Excel support.

**Visualization**

- **Choice:** `matplotlib`
- **Rationale:** Used in 2025, straightforward API for bar charts and comparison plots.



### Full Dependency List (`requirements.txt`)

```
pandas>=2.0.0
openpyxl>=3.1.0
requests>=2.31.0
google-search-results>=2.4.2
python-dotenv>=1.0.0
matplotlib>=3.7.0
selenium>=4.15.0
```



## 5. System Components

### Component 1: `main.py` — Orchestrator

**Purpose:** Single entry point. Presents an interactive menu for source selection, then delegates to the appropriate source modules.

**Responsibilities:**

- Load configuration from `config.py` and `.env`
- Display a numbered menu of available data sources
- Accept user input to select one or more sources
- Invoke the extractor then aggregator for each selected source, in order
- Optionally invoke the comparison module if multiple sources are selected/available
- Print a final summary of outputs generated

**Interface:** CLI (`python main.py`)

**Key Design:**
```python
SOURCES = {
    "1": ("Web of Science",    wos_extractor,   wos_aggregator),
    "2": ("Google Scholar",    gs_extractor,    gs_aggregator),
    "3": ("ScholarGPS",        sgps_extractor,  sgps_aggregator),
    "4": ("Cross-Source Comparison Only", None, None),
}
```



### Component 2: `config.py` — Central Configuration

**Purpose:** Single source of truth for all configurable values.

**Responsibilities:**
- Define data year window (`YEAR_START`, `YEAR_END`) dynamically from current date
- Define all file paths for input faculty files and output result folders
- Define column name constants to avoid typo-driven bugs
- Load and expose environment variables via `python-dotenv`

**Key Values:**
```python
# Year window (dynamic)
CURRENT_YEAR = datetime.now().year
YEAR_END     = CURRENT_YEAR - 1      # Last complete year
YEAR_START   = YEAR_END - 4          # 5-year window (e.g., 2021–2025)

# Faculty input files
FACULTY_FULL_PATH  = _ROOT / "{year}_{semester}_Faculty_List.xlsx"  # update each semester or year
FACULTY_TOP50_PATH = DATA_DIR / "Top_{N}_Faculty_{year}.xlsx"        # auto-generated

# Output directories
RESULTS_ROOT  = _ROOT / "results"
WOS_RESULTS   = RESULTS_ROOT / "wos"
GS_RESULTS    = RESULTS_ROOT / "google_scholar"
SGPS_RESULTS  = RESULTS_ROOT / "scholargps"
COMP_RESULTS  = RESULTS_ROOT / "comparison"

# Shared column names
COL_LAST_NAME    = "Last Name"
COL_FIRST_NAME   = "First Name"
COL_DEPARTMENT   = "Department"
COL_EMAIL        = "Email"
COL_FACULTY_TYPE = "Faculty Type"
FACULTY_KEY_COLS = [COL_LAST_NAME, COL_FIRST_NAME, COL_DEPARTMENT, COL_EMAIL, COL_FACULTY_TYPE]
```



### Component 3: WoS Source Module (`sources/wos/`)

**Purpose:** Extract publication data from Web of Science REST API; aggregate and rank by citation count.

**Sub-components:**
- `extractor.py`: Queries the WoS Starter API using each faculty member's WoS ResearchID. Fetches all pages (50/page). Saves full publication CSV and error log.
- `aggregator.py`: Filters to the configured year window. Aggregates total citations per faculty (LEFT JOIN to include 0-citation faculty). Ranks and saves two output CSVs.

**Key API Details:**
- Base URL: `https://api.clarivate.com/apis/wos-starter/v1/documents`
- Auth: `X-ApiKey` header (from `.env`)
- Query format: `AI=(researcher_id)`
- Citation field: `citations[].count` where `citations[].db == "WOK"`
- Pagination: `page` param, 50 records/page

**Input:** `data/Top_{N}_Faculty_{year}.xlsx` (auto-generated by `generate_top_N_faculty.py`)
**Required column:** `WoS ResearchID`
**Outputs:**
- `results/wos/WoS_Publications_FULL.csv`
- `results/wos/WoS_Publication_Last_Five_Years.csv`
- `results/wos/WoS_Citations_Last_Five_Years.csv`
- `results/wos/WoS_error_log.txt`



### Component 4: Google Scholar Source Module (`sources/google_scholar/`)

**Purpose:** Extract publication data via SerpAPI's Google Scholar Author engine; aggregate and rank.

**Sub-components:**
- `extractor.py`: Parses Google Scholar Author IDs from profile URLs. Calls SerpAPI with pagination. Saves full CSV and JSON.
- `aggregator.py`: Same filter/aggregate/rank logic as WoS. Uses "Cited By" column.

**Key API Details:**
- SerpAPI engine: `google_scholar_author`
- Auth: `api_key` param (from `.env`)
- Pagination: `start` param, 100 results/page
- Citation field: `articles[].cited_by.value`

**Input:** `{year}_{semester}_Faculty_List.xlsx` (project root — the master faculty file)
**Required column:** `Google Scholar Profile Link`
**Outputs:**
- `results/google_scholar/Google_Scholar_Publications_FULL.csv`
- `results/google_scholar/Google_Scholar_Publications_FULL.json`
- `results/google_scholar/Google_Scholar_Publication_Last_Five_Years.csv`
- `results/google_scholar/Google_Scholar_Citations_Last_Five_Years.csv`
- `results/google_scholar/Google_Scholar_error_log.txt`



### Component 5: ScholarGPS Source Module (`sources/scholargps/`) — Kept, Not Active 2026

**Purpose:** Extract publication data via Selenium browser automation of ScholarGPS website.

**Status:** Code is maintained and functional, but **not selected by default in 2026** due to CAPTCHA interruptions. Can be activated via the main.py menu when needed.

**Sub-components:**
- `extractor.py`: Selenium-driven browser automation. Handles CAPTCHA by pausing for manual intervention. Extracts publications across paginated pages.
- `aggregator.py`: Same filter/aggregate/rank pattern as other sources.

**Input:** `data/Top_{N}_Faculty_{year}.xlsx` (auto-generated by `generate_top_N_faculty.py`)
**Required column:** `scholargps` (profile URL)
**Outputs:**
- `results/scholargps/ScholarGPS_Publications_FULL.csv`
- `results/scholargps/ScholarGPS_Publication_Last_Five_Years.csv`
- `results/scholargps/ScholarGPS_Citations_Last_Five_Years.csv`



### Component 6: `utils/comparison.py` — Cross-Source Comparison

**Purpose:** Merge citation rankings from multiple sources, compute average citations, and produce visualizations.

**Responsibilities:**
- Load citation ranking CSVs from available sources
- INNER JOIN on faculty key columns
- Calculate average citations across sources
- Rank by average citations
- Save `Comparison_Ranked.csv`
- Generate comparison bar charts (PNG)
- Generate Excel comparison file with formatting

**Inputs:** Per-source `_Citations_Last_Five_Years.csv` files
**Outputs:**
- `results/comparison/Comparison_Ranked.csv`
- `results/comparison/GPS_GS_citation_comparison.xlsx`
- `results/comparison/comparison_chart_by_gs_rank.png`
- `results/comparison/comparison_chart_by_sgps_rank.png`



### Component 7: `utils/faculty_loader.py` — Faculty List Utilities

**Purpose:** Shared utility for loading and validating faculty Excel files. Avoids duplicating the same pandas `read_excel` + column-check logic in every source.

**Responsibilities:**
- Load Excel file and validate required columns are present
- Normalize text fields (strip whitespace, consistent casing)
- Filter rows with missing IDs for a given source
- Return a clean DataFrame ready for iteration



### Component 8: `code/update_faculty_list.py` — Faculty List Updater

**Purpose:** Merges the new semester's faculty list with the prior year's researcher IDs (WoS, Google Scholar, ORCID, Scopus). Matches by email, exact name, or fuzzy name similarity. Flags uncertain and new matches for human review.

**Status:** Standalone script; not part of the extraction pipeline. Run once at the start of each semester or year before running the pipeline.

**Input:** New semester faculty list (Excel) + prior year faculty list (Excel)

**Output:** Two-sheet Excel file:
- **Sheet 1 "Updated Faculty List"** — all faculty, colour-coded MATCHED / UNSURE / NEW
- **Sheet 2 "Review Required"** — only UNSURE + NEW rows for manual actioning

**Matching logic:**
- **MATCHED** — email match or exact name match → IDs carried over automatically
- **UNSURE** — full-name similarity ≥ threshold (default 82%) → human verification needed
- **NEW** — no match → contact faculty for researcher IDs



## 6. Data Architecture

### Faculty Input Schema

**Full Faculty List** (`{year}_{semester}_Faculty_List.xlsx` — project root)

| Column | Type | Notes |
|--------|------|-------|
| Last Name | string | Required for all sources |
| First Name | string | Required |
| Department | string | Marshall dept abbreviation |
| Email | string | Used as join key |
| Faculty Type | string | T/TT, NTT, etc. |
| Google Scholar Profile Link | URL | Required for Google Scholar source |
| WoS | string | WoS ResearchID |
| scholargps | URL | ScholarGPS profile URL |
| ORCID | string | Optional |
| SCOPUS_ID | string | Optional |

**Top-N List** (`data/Top_{N}_Faculty_{year}.xlsx` — auto-generated)

Auto-generated by `generate_top_N_faculty.py` after Google Scholar runs. Contains the top N faculty by GS citations, with WoS ResearchID and scholargps URL looked up from the full faculty list. Required columns: all Faculty key columns + `WoS ResearchID` + `scholargps`.

### Publication Record Schema (per source)

**Common fields across all sources:**

| Column | Type | Notes |
|--------|------|-------|
| Last Name | string | From faculty input |
| First Name | string | From faculty input |
| Department | string | From faculty input |
| Email | string | From faculty input |
| Faculty Type | string | From faculty input |
| Title | string | Publication title |
| Publication Year | int | Year of publication |
| Citations | int | Citation count (source-specific label) |
| Journal | string | Source/venue name |

**WoS-specific extra fields:** `WoS ResearchID Link`, `DOI`
**Google Scholar-specific extra fields:** `Google Scholar Profile Link`, `GoogleScholarID`, `Authors`, `Link`
**ScholarGPS-specific extra fields:** `ScholarGPS Profile Link`, `Authors`, `DOI`

### Output Schema: Citation Rankings

Produced by each aggregator:

| Column | Type | Notes |
|--------|------|-------|
| Rank | int | 1 = most citations |
| Last Name | string | |
| First Name | string | |
| Department | string | |
| Email | string | |
| Faculty Type | string | |
| Total Citations | int | Sum of citations in year window |

### Output Schema: Cross-Source Comparison

| Column | Type | Notes |
|--------|------|-------|
| Average_Citations_Rank | int | Ranked by average across sources |
| Last Name | string | |
| First Name | string | |
| Department | string | |
| Email | string | |
| Faculty Type | string | |
| WoS_Rank | int | |
| WoS_Total Citations | int | |
| Google_Rank | int | |
| Google_Total Citations | int | |
| Average_Citations | float | Mean across available sources |

### Data Flow

```
Faculty Excel Files
        │
        ▼
  faculty_loader.py  ──────────────────────────────────────┐
        │                                                  │
        ▼                                                  │
  [Source Extractor]                                       │
  - API calls / scraping                                   │
  - Records per publication                                │
        │                                                  │
        ▼                                                  │
  [Source]_Publications_FULL.csv                           │
        │                                                  │
        ▼                                                  │
  [Source Aggregator]                                      │
  - Filter: YEAR_START ≤ year < YEAR_END+1                 │
  - groupby → sum citations                                │
  - LEFT JOIN with faculty list ◄───────────────────────────┘
  - Sort descending → add Rank
        │
        ├──► [Source]_Citations_Last_Five_Years.csv
        └──► [Source]_Publication_Last_Five_Years.csv
                          │
                          ▼
               comparison.py (if 2+ sources run)
               - INNER JOIN sources
               - Average citations
               - Rank + visualize
                          │
                          ▼
              Comparison_Ranked.csv + charts
```

---

## 7. Directory & File Structure

```
Publication_Data_Collection_{year}/
├── {year}_{semester}_Faculty_List.xlsx      # Master faculty + ID file (update each semester or year)
│
├── data/                                    # Auto-generated files (Top-N list output)
│   └── Top_{N}_Faculty_{year}.xlsx          # Auto-generated after Google Scholar run
│
├── code/                                    # All Python source code
│   ├── main.py                              # Entry point; source selector
│   ├── config.py                            # Centralized configuration (update FACULTY_FULL_PATH)
│   ├── update_faculty_list.py               # Merges new faculty list with prior-year IDs
│   ├── .env                                 # API credentials (NOT committed)
│   ├── .env.example                         # Template for .env
│   ├── requirements.txt                     # Python dependencies
│   │
│   ├── sources/                             # One package per data source
│   │   ├── wos/
│   │   │   ├── extractor.py                 # WoS API extraction
│   │   │   └── aggregator.py                # WoS aggregation & ranking
│   │   ├── google_scholar/
│   │   │   ├── extractor.py                 # SerpAPI extraction
│   │   │   └── aggregator.py                # GS aggregation & ranking
│   │   └── scholargps/                      # Kept but not active in 2026
│   │       ├── extractor.py                 # Selenium scraping
│   │       └── aggregator.py                # ScholarGPS aggregation
│   │
│   └── utils/
│       ├── faculty_loader.py                # Shared faculty file loading
│       ├── generate_top_N_faculty.py        # Auto-generates Top-N list from GS results
│       └── comparison.py                    # Cross-source comparison & charts
│
├── results/                                 # All outputs (auto-created)
│   ├── wos/
│   ├── google_scholar/
│   ├── scholargps/
│   └── comparison/
│
├── docs/                                    # Documentation
│   ├── architecture-publication-data-collection-2026-02-27.md  (this file)
│   ├── WoS_documentation_2026.md
│   ├── google_scholar_documentation_2026.md
│   └── scholargps_documentation_2026.md
│
└── Publication_Data_Collection_2025/        # Previous year reference (read-only)
```



## 8. Execution Workflow

### Setup (First Time Only)

```bash
# 1. Install dependencies
pip install -r code/requirements.txt

# 2. Create .env file (copy from template, fill in your API keys)
cp code/.env.example code/.env
# Edit .env and add:
#   WOS_API_KEY=your_wos_key_here
#   SERPAPI_KEY=your_serpapi_key_here

# 3. Ensure the master faculty list is in the project root
# {year}_{semester}_Faculty_List.xlsx
# Update FACULTY_FULL_PATH in config.py to point to it
```

### Standard Run

```bash
cd code
python main.py
```

**Interactive Menu (displayed at runtime):**
```
============================================================
  Marshall Faculty Publication Data Collection — 2026
============================================================
  Year window: 2021–2025

  Select data sources to run (comma-separated, e.g. 1,2):

  [1] Web of Science (WoS)
  [2] Google Scholar              ← run this first
  [3] ScholarGPS  ⚠  (manual CAPTCHA required)  [not active in 2026]

  [A] Run all ACTIVE sources (WoS + Google Scholar)
  [C] Cross-source comparison only (requires 2+ sources already run)
  [G] Generate Top-N faculty list from existing GS results
  [Q] Quit

  Your choice: _
```

### Expected Run Times

| Source | Time | Notes |
|--------|------|-------|
| WoS | ~3–5 minutes | API rate-limited (1s/page) |
| Google Scholar | ~5–10 minutes | SerpAPI rate-limited (2s/page) |
| ScholarGPS | 30–60+ minutes | Includes manual CAPTCHA solving |
| Comparison | < 30 seconds | Pure data processing |

### Output Confirmation

After each source, the script prints:
```
[WoS] Extraction complete. 48/50 faculty processed.
[WoS] Errors: 2 faculty missing WoS IDs → see results/wos/WoS_error_log.txt
[WoS] Saved: results/wos/WoS_Publications_FULL.csv (1,842 records)
[WoS] Aggregation complete.
[WoS] Saved: results/wos/WoS_Citations_Last_Five_Years.csv (50 researchers)
[WoS] Saved: results/wos/WoS_Publication_Last_Five_Years.csv (612 records)
```



## 9. NFR Coverage

### NFR-1: Extensibility — Adding New Data Sources

**Requirement:** The system must support adding new data sources (e.g., Scopus, OpenAlex) in future years with minimal code changes.

**Solution:**
- All sources follow the same pattern: `extractor.py` → CSV → `aggregator.py` → ranked CSVs
- New source: create a new folder under `sources/`, implement extractor and aggregator following existing patterns, add an entry to `main.py`'s source menu
- `config.py` centralizes path and column constants — new source adds its paths there
- `utils/faculty_loader.py` is reused; no duplication

**Validation:** A new source can be added by a developer in ~2 hours, touching only 3 files.

---

### NFR-2: Selective Execution

**Requirement:** The operator must be able to run only specific sources per session (e.g., skip ScholarGPS due to CAPTCHA, run only WoS on a quick refresh).

**Solution:**
- `main.py` presents a numbered menu. User enters comma-separated selection.
- Each source module is invoked independently. Selecting "1,2" runs only WoS and Google Scholar.
- ScholarGPS is listed with a clear warning about CAPTCHA requirements.
- "Run All Active" option runs WoS + Google Scholar only (excludes ScholarGPS by default).

**Validation:** User can run `python main.py`, select "1", and only WoS runs.

---

### NFR-3: Credential Security

**Requirement:** API keys must not appear in any committed source code file.

**Solution:**
- `.env` file stores `WOS_API_KEY` and `SERPAPI_KEY`
- `.env` is listed in `.gitignore`
- Scripts load keys with `os.getenv("WOS_API_KEY")` via `python-dotenv`
- `.env.example` (committed) shows the required key names with placeholder values
- Documentation instructs operators to copy `.env.example` → `.env` and fill in keys

**Validation:** `grep -r "API_KEY" code/` returns no hardcoded key values.

---

### NFR-4: Operational Reliability

**Requirement:** A failure for one faculty member (missing ID, API error, network timeout) must not stop the pipeline. All errors must be logged.

**Solution:**
- Each faculty member's extraction is wrapped in a `try/except` block
- Errors are appended to an in-memory list and written to a source-specific error log at the end
- `continue` skips to the next faculty on error
- HTTP errors receive a warning print and are retried up to 3 times with exponential backoff (new in 2026)
- Missing IDs are detected upfront (before API call) and logged immediately

**Retry Logic (new in 2026):**
```python
for attempt in range(MAX_RETRIES):
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        break
    if response.status_code == 429:  # Rate limit
        time.sleep(RETRY_BACKOFF ** attempt)
    else:
        break  # Non-retriable error
```

**Validation:** Injecting a bad WoS ID for one faculty member does not stop extraction for the rest.

---

### NFR-5: Reproducibility

**Requirement:** Running the pipeline twice with the same inputs produces identical outputs (deterministic).

**Solution:**
- Year window is computed from `datetime.now().year` — same on any run within the same calendar year
- All DataFrames are sorted with explicit, deterministic keys before ranking
- Output CSVs are overwritten (not appended) on each run
- LEFT JOIN ensures all faculty appear in outputs, even with 0 citations

**Validation:** Running the pipeline twice in succession produces byte-identical output CSVs.

---

### NFR-6: Maintainability

**Requirement:** A new RA with basic Python experience should be able to set up and run the system with only this documentation.

**Solution:**
- Single `requirements.txt` for one-command dependency install
- `.env.example` clearly shows what credentials are needed
- `main.py` is the only script to run
- Inline comments in all scripts explain non-obvious logic
- Architecture document (this file) explains the full system
- Per-source documentation maintained at `docs/WoS_documentation_2026.md` etc.

---

### NFR-7: Data Coverage

**Requirement:** All faculty in the input list must appear in output rankings, even those with 0 publications or citations in the time window.

**Solution:**
- Aggregators use `LEFT JOIN` (faculty list as left table, citations as right)
- Missing citation values are filled with 0 after join
- Faculty with no publications are ranked last (0 citations)
- Extraction errors (missing IDs) are recorded in the error log so the operator knows who is excluded



## 10. Security Architecture

### Credential Management

```
.env (local only, never committed)
├── WOS_API_KEY=<clarivate_api_key>
└── SERPAPI_KEY=<serpapi_key>

.env.example (committed to version control)
├── WOS_API_KEY=your_wos_api_key_here
└── SERPAPI_KEY=your_serpapi_key_here
```

**Loading in code:**
```python
from dotenv import load_dotenv
import os

load_dotenv()  # reads .env from working directory or parent

WOS_API_KEY  = os.getenv("WOS_API_KEY")
SERPAPI_KEY  = os.getenv("SERPAPI_KEY")

if not WOS_API_KEY:
    raise ValueError("WOS_API_KEY not set. Copy .env.example to .env and fill in your key.")
```

### Data Privacy

- Faculty data (names, emails) is used only internally for data collection; not shared with external APIs beyond what is necessary (WoS query uses only the ResearchID, not name or email)
- SerpAPI receives Google Scholar Author IDs only
- Output CSV/Excel files should be stored on university-controlled or secure personal storage

### .gitignore Entries

```
.env
results/
*.pyc
__pycache__/
.DS_Store
```

---

## 11. Extensibility: Adding New Data Sources

To add a new source (e.g., Scopus) in a future year:

### Step 1: Create the source module

```
code/sources/scopus/
├── extractor.py
└── aggregator.py
```

**`extractor.py` must:**
- Read the appropriate faculty Excel file (full list or top-50)
- Load API key from `.env` via `os.getenv()`
- Iterate faculty, call the API, collect publication records
- Save to `results/scopus/Scopus_Publications_FULL.csv`
- Save error log to `results/scopus/Scopus_error_log.txt`

**`aggregator.py` must:**
- Read `results/scopus/Scopus_Publications_FULL.csv`
- Filter to `YEAR_START ≤ Publication Year < CURRENT_YEAR`
- LEFT JOIN with faculty list
- Sort by total citations descending, add Rank column
- Save `Scopus_Citations_Last_Five_Years.csv` and `Scopus_Publication_Last_Five_Years.csv`

### Step 2: Add to `config.py`

```python
SCOPUS_RESULTS = RESULTS_ROOT + "/scopus"
```

### Step 3: Register in `main.py`

```python
from sources.scopus import extractor as scopus_extractor
from sources.scopus import aggregator as scopus_aggregator

SOURCES = {
    ...
    "5": ("Scopus", scopus_extractor, scopus_aggregator),
}
```

### Step 4: Add API key to `.env.example`

```
SCOPUS_API_KEY=your_scopus_api_key_here
```

### Step 5: Update `utils/comparison.py` to include the new source in comparison

That's all. The core orchestration logic and comparison utilities work for any number of sources.



## 12. Development & Deployment

### Environment Setup

```bash
# From the project root — first time only
python3 -m venv venv
source venv/bin/activate
pip install -r code/requirements.txt
```

Each new terminal session, activate the venv before running anything:
```bash
source venv/bin/activate   # from the project root
```

The `venv/` folder is excluded from version control via `.gitignore`.

### Platform Notes

| Component | macOS | Windows | Linux |
|-----------|-------|---------|-------|
| WoS extractor | Works | Works | Works |
| Google Scholar extractor | Works | Works | Works |
| ScholarGPS (Selenium) | Works (arm64 + Intel) | Works (with ChromeDriver) | Works |

**ChromeDriver Setup (ScholarGPS only):**
- Install ChromeDriver matching your Chrome version
- macOS: `brew install --cask chromedriver` or manual download
- Add to PATH or specify path in `config.py`
- 2026 improvement: path configurable in `config.py` and `.env`, not hardcoded in the script

### Testing

No automated test suite is required for this research tool. Manual validation:

1. **Smoke test**: Run with 1–2 faculty rows, verify output CSV structure matches expected schema
2. **Year filter test**: Verify `YEAR_START` and `YEAR_END` in output match `config.py` values
3. **Error handling test**: Remove a WoS ID from the Excel, verify it appears in error log without crashing
4. **Zero-citation test**: Faculty with no recent publications should appear in rankings with `Total Citations = 0`

### Version Control

- Use `.gitignore` to exclude `.env`, `results/`, `venv/`, `*.pyc`, `.DS_Store`
- Commit `requirements.txt`, `config.py`, all source scripts, and `.env.example`
- Do not commit API keys, the `venv/` folder, or output data files (may contain PII)



## 13. Traceability & Trade-offs

### Functional Requirement Traceability

| Requirement | Component | Notes |
|-------------|-----------|-------|
| Extract WoS publications | `sources/wos/extractor.py` | Via Clarivate REST API |
| Extract Google Scholar publications | `sources/google_scholar/extractor.py` | Via SerpAPI |
| Extract ScholarGPS publications | `sources/scholargps/extractor.py` | Via Selenium (kept, not active 2026) |
| Filter to last 5 years | All `aggregator.py` files | Uses `config.YEAR_START/YEAR_END` |
| Rank faculty by citations | All `aggregator.py` files | LEFT JOIN + sort + rank |
| Cross-source comparison | `utils/comparison.py` | INNER JOIN, average citations |
| Visualize comparison | `utils/comparison.py` | matplotlib bar charts |
| Select which sources to run | `main.py` | Interactive CLI menu |
| Support new sources in future | Plugin structure | Add folder + register in main.py |
| Merge faculty lists semester/year-over-year | `code/update_faculty_list.py` | Standalone utility; MATCHED/UNSURE/NEW output |
| Auto-generate Top-N list from GS results | `utils/generate_top_N_faculty.py` | Runs automatically after GS; also available via [G] |

### Key Trade-offs

**1. Interactive CLI vs. command-line flags**
- ✓ Interactive menu is easier for non-technical RAs
- ✗ Cannot be fully scripted/automated (requires human input at startup)
- Rationale: Users are research assistants running the script manually; ease of use outweighs automation.

**2. Google Scholar via SerpAPI (paid) vs. direct scraping**
- ✓ SerpAPI is reliable, handles CAPTCHAs, legal, and maintained
- ✗ Has a cost and API credit limits
- Rationale: Direct Google Scholar scraping violates ToS and is fragile; SerpAPI is the right tool.

**3. ScholarGPS: keep code vs. remove**
- ✓ Keeping code preserves historical comparison continuity option
- ✗ Adds maintenance surface area for unused code
- Rationale: User explicitly requested keeping the code for future optionality.

**4. Two faculty lists vs. one unified list**
- ✓ Matches existing workflow and is familiar to current operators
- ✗ Two files to maintain and keep in sync
- Rationale: User requested keeping the 2025 approach; unified list is a future improvement option.

**5. Flat CSV outputs vs. database**
- ✓ CSVs are universally accessible, easy to share, open in Excel
- ✗ No query capability, manual aggregation required
- Rationale: Research tools benefit from human-readable outputs; no web interface or API needed.

---

## 14. Changes from 2025

| Area | 2025 | 2026 |
|------|------|------|
| Entry point | Multiple scripts, run manually | `python main.py` with interactive menu |
| Source selection | All sources always run | User chooses which sources to run |
| API credentials | Hardcoded in source files | `.env` file via `python-dotenv` |
| File paths | Hardcoded per-script | Centralized in `config.py` |
| Year window | `datetime.now().year` in each aggregator | Defined once in `config.py` |
| Column names | String literals duplicated | Constants in `config.py` |
| Error handling | Basic try/except, print to console | Structured error list → log file |
| HTTP retries | None | Up to 3 retries with backoff (WoS) |
| Faculty loading | `pd.read_excel()` inline per script | `utils/faculty_loader.py` shared util |
| Comparison | Separate script, run manually | Integrated in main.py flow |
| Directory structure | Flat per source | Organized: `code/sources/`, `results/source/` |
| Dependencies | No file | `requirements.txt` |
| Documentation | Per-source markdown | Architecture doc + per-source docs |
| ScholarGPS | Always included | Optional (kept in code, not active) |
| New sources | Requires duplicating full script | Add folder + register (3 file changes) |

---

*Architecture document prepared by: Lizzy Chen (LizzyChen@outlook.com)*
*Based on analysis of 2025 system codebase and documentation*
