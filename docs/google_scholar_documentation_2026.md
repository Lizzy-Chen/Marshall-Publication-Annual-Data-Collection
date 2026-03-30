# Google Scholar Data Extraction — 2026

## Overview

The Google Scholar module extracts publication and citation data for **all** Marshall School of Business faculty using **SerpAPI** — a third-party service that provides a reliable, Terms-of-Service-compliant API for Google Scholar data. It fetches each faculty member's full publication list, then filters to the most recent 5 years and ranks faculty by total citations.



## What's New in 2026

| Area | 2025 | 2026 |
|------|------|------|
| Entry point | Run `google_scholar_extractor.py` manually | Run `python main.py` and select `[2]` |
| API key | Hardcoded in script | Loaded from `.env` file |
| File paths | Hardcoded | Centralized in `config.py` |
| Error handling | Basic try/except | Retry loop, structured error log |
| Output location | `results/` (root) | `results/google_scholar/` |



## Setup

### Prerequisites

- Python 3.9+
- Virtual environment created and activated (see README for setup)
- Dependencies installed inside the venv: `pip install -r code/requirements.txt`
- `.env` file with your SerpAPI key (see below)

### SerpAPI Key Setup

1. Log in at [https://serpapi.com/dashboard](https://serpapi.com/dashboard)
   - Account: avdresearch@marshall.usc.edu
   - (password stored in `code/.env`)
2. Copy your API key from the dashboard
3. Add it to `code/.env`:
   ```
   SERPAPI_KEY=your_key_here
   ```



## Input File

**File:** `{year}_{semester}_Faculty_List.xlsx` (project root — the master faculty file, e.g. `2026_Spring_Faculty_List.xlsx`)

**Required columns:**

| Column | Description |
|--------|-------------|
| Last Name | Faculty last name |
| First Name | Faculty first name |
| Department | Marshall department abbreviation |
| Email | Faculty email |
| Faculty Type | T/TT, NTT, etc. |
| Google Scholar Profile Link | Full URL, e.g. `https://scholar.google.com/citations?user=XXXX&hl=en` |

**Note:** Faculty rows with no Google Scholar Profile Link are skipped and logged.



## Running the Pipeline

### Via main.py (recommended)

```bash
cd code
python main.py
# Select [2] Google Scholar
```

### Directly (for testing)

```bash
cd code
python -m sources.google_scholar.extractor    # Step 1: Extract
python -m sources.google_scholar.aggregator   # Step 2: Aggregate & rank
```



## Output Files

All outputs are saved to `results/google_scholar/`.

| File | Description |
|------|-------------|
| `Google_Scholar_Publications_FULL.csv` | All publications for all faculty, all years |
| `Google_Scholar_Publications_FULL.json` | Same data in JSON format |
| `Google_Scholar_Publication_Last_Five_Years.csv` | Publications from the last 5 years, with Rank column |
| `Google_Scholar_Citations_Last_Five_Years.csv` | One row per faculty: total citations and rank |
| `Google_Scholar_error_log.txt` | Missing IDs, API errors, and warnings |

### Output Schema: `Google_Scholar_Citations_Last_Five_Years.csv`

| Column | Description |
|--------|-------------|
| Rank | 1 = most citations |
| Last Name | |
| First Name | |
| Department | |
| Email | |
| Faculty Type | |
| Google Scholar Profile Link | Full URL to the faculty's Google Scholar profile |
| Total Citations | Sum of "Cited By" for publications in year window |

### Output Schema: `Google_Scholar_Publications_FULL.csv`

| Column | Description |
|--------|-------------|
| Last Name | Faculty last name |
| First Name | Faculty first name |
| Department | |
| Email | |
| Faculty Type | |
| Google Scholar Profile Link | Full profile URL |
| GoogleScholarID | Author ID extracted from URL |
| Title | Publication title |
| Publication Year | Year published |
| Cited By | Google Scholar citation count |
| Journal | Publication venue |
| Authors | Author list string |
| Link | Direct URL to the paper on Google Scholar |



## How SerpAPI Works

SerpAPI acts as a proxy that scrapes Google Scholar on your behalf and returns clean JSON data. The key advantage is reliability — Google Scholar's own interface blocks direct automated access.

**Engine used:** `google_scholar_author`
**Pagination:** Up to 100 publications per request; `start` parameter advances through pages
**Rate limit:** 2-second pause between paginated requests



## Year Window

The year window is defined in `config.py` and computed dynamically:

```
YEAR_END   = current_year - 1  (last complete year)
YEAR_START = YEAR_END - 4      (5-year window)
```

In 2026: **2021–2025**



## Citation Count Differences vs. WoS

Google Scholar citation counts are typically 2–5× higher than WoS counts.
This is expected:

- **Google Scholar** indexes preprints, working papers, theses, conference papers, and some books
- **WoS** indexes only peer-reviewed journals in its curated database

Both are valid metrics; they measure different things. The comparison module
provides both side-by-side.



## Known Limitations

- SerpAPI has a monthly credit limit.
- Faculty without a Google Scholar profile cannot be included.
- Some faculty have profiles but no recent publications — they will appear in the error log but not in rankings.

---

## Contact

- **Author:** Lizzy Chen
- **Email:** LizzyChen@outlook.com
