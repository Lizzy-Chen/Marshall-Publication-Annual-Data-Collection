# ScholarGPS Data Extraction — 2026

## Status

> **Active in 2026.** ScholarGPS is included alongside WoS and Google Scholar. Select **[3]** in
> `main.py` to run it, or **[A]** to run all three sources together. Note that ScholarGPS requires
> manual CAPTCHA solving — budget 30–60 minutes and keep the terminal open during the run.

---

## Overview

The ScholarGPS module extracts publication and citation data for the **Top-N faculty** (same list used by WoS) by automating a Google Chrome browser via **Selenium**. It navigates each faculty member's ScholarGPS profile page, scrapes publications across all paginated pages, then filters to the most recent 5 years and ranks faculty by total citations.



## What's New in 2026

| Area | 2025 | 2026 |
|------|------|------|
| Entry point | Run `scholargps_extractor.py` manually | Run `python main.py` and select `[3]` |
| File paths | Hardcoded | Centralized in `config.py` |
| ChromeDriver path | Hardcoded in script | Configurable via `config.py` or `.env` |
| Output location | `results/` (root) | `results/scholargps/` |



## Setup

### Prerequisites

1. **Virtual environment activated and dependencies installed** (see README for first-time setup):
   ```bash
   source venv/bin/activate          # from project root
   pip install -r code/requirements.txt
   ```

2. **Google Chrome installed** on your machine.

3. **ChromeDriver installed** and matching your Chrome version:
   - macOS (Homebrew): `brew install --cask chromedriver`
   - Or download manually from: https://chromedriver.chromium.org/downloads
   - After install, allow it in System Settings → Privacy & Security if prompted

4. **ChromeDriver path configured** (if not at the default `/usr/local/bin/chromedriver`):
   - Option A — set in `code/.env`:
     ```
     CHROMEDRIVER_PATH=/opt/homebrew/bin/chromedriver
     ```
   - Option B — update `CHROMEDRIVER_PATH` in `code/config.py`



## Input File

**File:** `data/Top_{N}_Faculty_{year}.xlsx` (auto-generated after running Google Scholar)

**Required columns:**

| Column | Description |
|--------|-------------|
| Last Name | Faculty last name |
| First Name | Faculty first name |
| Department | Marshall department abbreviation |
| Email | Faculty email |
| Faculty Type | T/TT, NTT, etc. |
| scholargps | Full ScholarGPS profile URL |

**Note:** Faculty rows with a missing or blank `scholargps` URL are skipped silently.



## Running the Pipeline

### Via main.py (recommended)

```bash
cd code
python main.py
# Select [3] ScholarGPS
```

### Directly (for testing)

```bash
cd code
python -m sources.scholargps.extractor    # Step 1: Extract
python -m sources.scholargps.aggregator   # Step 2: Aggregate & rank
```



## CAPTCHA Handling

ScholarGPS detects automated access and periodically shows a CAPTCHA challenge.
The script handles this as follows:

1. After loading each faculty page, the script checks for "confirm you are human" in the page source.
2. If a CAPTCHA is detected, the script **pauses and prints:**
   ```
   ⚠  CAPTCHA detected. Please solve it in the browser window.
   Press Enter here after completing the CAPTCHA…
   ```
3. Solve the CAPTCHA in the Chrome window that opened, then press **Enter** in the terminal.
4. The script resumes automatically.

**Budget 30–60+ minutes** for a full run of ~50 faculty, depending on how often CAPTCHAs appear.



## Output Files

All outputs are saved to `results/scholargps/`.

| File | Description |
|------|-------------|
| `ScholarGPS_Publications_FULL.csv` | All publications for all faculty, all years |
| `ScholarGPS_Publication_Last_Five_Years.csv` | Publications from the last 5 years, with Rank column |
| `ScholarGPS_Citations_Last_Five_Years.csv` | One row per faculty: total citations and rank |

### Output Schema: `ScholarGPS_Citations_Last_Five_Years.csv`

| Column | Description |
|--------|-------------|
| Rank | 1 = most citations |
| Last Name | |
| First Name | |
| Department | |
| Email | |
| Faculty Type | |
| Total Citations | Sum of "Cited By" for publications in year window |

### Output Schema: `ScholarGPS_Publications_FULL.csv`

| Column | Description |
|--------|-------------|
| Last Name | Faculty last name |
| First Name | Faculty first name |
| Department | |
| Email | |
| Faculty Type | |
| ScholarGPS Profile Link | Full profile URL |
| Title | Publication title |
| Publication Year | Year published |
| Cited By | ScholarGPS citation count |
| Journal | Publication venue |
| Authors | Author list string |
| DOI | Digital Object Identifier |



## Year Window

The year window is defined in `config.py` and computed dynamically:

```
YEAR_END   = current_year - 1  (last complete year)
YEAR_START = YEAR_END - 4      (5-year window)
```

In 2026: **2021–2025**



## Page Wait Times

To mimic human browsing and reduce CAPTCHA frequency, the script waits a random
interval between page loads. These are configurable in `config.py`:

```python
SGPS_PAGE_WAIT_MIN = 10   # Minimum seconds after loading a faculty profile page
SGPS_PAGE_WAIT_MAX = 15   # Maximum seconds after loading a faculty profile page
SGPS_NAV_WAIT_MIN  = 5    # Minimum seconds between pagination clicks
SGPS_NAV_WAIT_MAX  = 7    # Maximum seconds between pagination clicks
```



## Citation Count Differences vs. WoS / Google Scholar

- ScholarGPS citation counts are typically between WoS and Google Scholar counts.
- ScholarGPS indexes peer-reviewed journals more broadly than WoS but is more selective than Google Scholar (which includes preprints and grey literature).



## Known Limitations

- **CAPTCHA interruptions** — frequency varies; can break automation flow on certain IP addresses or if accessed too frequently.
- **No API** — data is scraped from rendered HTML. Any change to ScholarGPS's page structure may break parsing and require code updates.
- **Requires a `scholargps` column** in the Top-N faculty list with valid profile URLs. Faculty without a URL are skipped.
- **Chrome + ChromeDriver version must match** — mismatches cause the browser to fail to launch.



## Contact

- **Author:** Lizzy Chen
- **Email:** LizzyChen@outlook.com
