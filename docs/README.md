# Marshall Faculty Publication Data Collection

Automated pipeline for extracting, aggregating, and comparing publication and citation data for Marshall School of Business faculty from multiple academic databases.

**Active sources:** Web of Science (WoS), Google Scholar
**Kept but not active:** ScholarGPS (requires manual CAPTCHA solving)



## Annual Setup (Start of Each Year)

Before running the pipeline, update the faculty list for the new year:

**Step 1: Update the faculty list**

- Run `update_faculty_list.py` to merge the new semester's faculty list with researcher IDs (WoS, Google Scholar, ORCID, SCOPUS) from the prior year:

  ```bash
  cd code
  python update_faculty_list.py
  ```

- This produces a two-sheet Excel file:

  - **Sheet 1 "Updated Faculty List"** — all faculty, colour-coded by match status:
    - **MATCHED** (green) — IDs carried over automatically
    - **UNSURE** (amber) — similar name found; verify it's the same person
    - **NEW** (yellow) — no match; contact for researcher IDs

  - **Sheet 2 "Review Required"** — only UNSURE + NEW rows for quick actioning




**Step 2: Update `config.py`**

- Point `FACULTY_FULL_PATH` to the new faculty list file:

  ```python
  # code/config.py
  FACULTY_FULL_PATH = _ROOT / "2026_Spring_Faculty_List.xlsx"  # ← update each semester or year
  ```

- Everything else (`YEAR_START`, `YEAR_END`, `FACULTY_TOP50_PATH`) updates automatically based on the current calendar year.



## Running the Pipeline

**1. Set up virtual environment and install dependencies (first time only)**

```bash
# From the project root
python3 -m venv venv
source venv/bin/activate
pip install -r code/requirements.txt
```

> **Each new terminal session:** run `source venv/bin/activate` from the project root before running any pipeline commands.

**2. Set up credentials (first time only)**

```bash
cp code/.env.example code/.env
# Open code/.env and fill in your API keys (see below)
```

- **WoS API key (`WOS_API_KEY`)**

  - Register at the [Clarivate Developer Portal](https://developer.clarivate.com/)

  - Subscribe to the [Web of Science Starter API](https://developer.clarivate.com/apis/wos-starter)

  - Once approved, copy your API key from the application details page

- **Google Scholar / SerpAPI key (`SERPAPI_KEY`)**

  - Log in at [https://serpapi.com/dashboard](https://serpapi.com/dashboard)
    - Account: avdresearch@marshall.usc.edu


  - Copy your API key from the dashboard

**3. Run Google Scholar first**

```bash
cd code
python main.py   # select [2] Google Scholar
```

- Covers all faculty. When it finishes, **automatically generates** `data/Top_N_Faculty_{year}.xlsx` — the input list for WoS.

**4. Review the Top-N list**

- Open `data/Top_N_Faculty_{year}.xlsx`. Gold-highlighted rows need attention: fill in any missing **WoS ResearchID**.

**5. Run WoS**

```bash
cd code
python main.py   # select [1] Web of Science
```



## Input Files

| File | Location | Used by |
|------|----------|---------|
| `{year}_{semester}_Faculty_List.xlsx` | project root | Google Scholar extractor, Top-N generator |
| `data/Top_N_Faculty_{year}.xlsx` | `data/` (auto-generated) | WoS extractor, ScholarGPS extractor |

The faculty list is the single master file. It should contain:
`Last Name`, `First Name`, `Department`, `Email`, `Faculty Type`,`Google Scholar Profile Link`, `WoS`, `scholargps`, `ORCID`, `SCOPUS_ID`.



## Project Structure

```
Publication_Data_Collection_{year}/
├── {year}_{semester}_Faculty_List.xlsx ← master faculty + ID file (update each semester or year)
├── data/                              ← auto-generated files (Top-N list output)
├── results/                           ← all extraction outputs (auto-created)
│   ├── wos/
│   ├── google_scholar/
│   ├── scholargps/
│   └── comparison/
├── code/
│   ├── main.py                        ← single entry point — run this
│   ├── config.py                      ← update FACULTY_FULL_PATH each semester or year
│   ├── .env                           ← API keys (not committed to git)
│   ├── .env.example                   ← template for .env
│   ├── requirements.txt               ← Python dependencies
│   ├── update_faculty_list.py         ← merges new faculty list with prior-year IDs
│   ├── sources/
│   │   ├── wos/                       ← Web of Science (API)
│   │   ├── google_scholar/            ← Google Scholar (via SerpAPI)
│   │   └── scholargps/                ← ScholarGPS (Selenium, optional)
│   └── utils/
│       ├── faculty_loader.py          ← shared Excel loading utility
│       ├── generate_top_N_faculty.py  ← auto-generates Top-N list from GS results
│       └── comparison.py              ← cross-source ranking + charts
└── docs/
    ├── README.md
    ├── architecture-publication-data-collection-2026-02-27.md
    ├── WoS_documentation_2026.md
    ├── google_scholar_documentation_2026.md
    └── scholargps_documentation_2026.md
```



## Pipeline Flow

```
{year}_{semester}_Faculty_List.xlsx
        │
        ▼
[2] Google Scholar extractor       (all faculty, via SerpAPI)
        │
        ▼
results/google_scholar/Google_Scholar_Citations_Last_Five_Years.csv
        │
        ▼ auto
generate_top_N_faculty.py          (top N by GS citations + WoS ID lookup)
        │
        ▼
data/Top_N_Faculty_{year}.xlsx     ← review & fill in flagged rows
        │
        ▼
[1] WoS extractor                  (top N faculty, via Clarivate API)
        │
        ▼
results/wos/WoS_Citations_Last_Five_Years.csv
        │
        ▼ auto (if both sources ran)
comparison.py
        │
        ▼
results/comparison/Comparison_Ranked.csv + charts
```



## `main.py` Menu

```
  [1] Web of Science (WoS)
  [2] Google Scholar              ← run this first
  [3] ScholarGPS  (optional, requires manual CAPTCHA solving)
  [A] Run all active sources (WoS + Google Scholar)
  [C] Cross-source comparison only
  [G] Generate Top-N faculty list from existing GS results
  [Q] Quit
```



## Output Files

| Location | File | Description |
|----------|------|-------------|
| `data/` | `Top_N_Faculty_{year}.xlsx` | Auto-generated Top-N list (WoS input) |
| `results/wos/` | `WoS_Publications_FULL.csv` | All WoS publications |
| `results/wos/` | `WoS_Citations_Last_Five_Years.csv` | Faculty rankings by WoS citations |
| `results/google_scholar/` | `Google_Scholar_Publications_FULL.csv` | All GS publications |
| `results/google_scholar/` | `Google_Scholar_Citations_Last_Five_Years.csv` | Faculty rankings by GS citations |
| `results/comparison/` | `Comparison_Ranked.csv` | Cross-source ranking by average citations |
| `results/comparison/` | `GPS_GS_citation_comparison.xlsx` | Formatted Excel comparison |
| `results/comparison/` | `comparison_chart_*.png` | Bar chart visualisations |



## Year Window

Auto-computed in `config.py` — always covers the 5 most recent complete years.
No manual update needed.



## Documentation

- **Architecture:** `docs/architecture-publication-data-collection-2026-02-27.md`
- **WoS details:** `docs/WoS_documentation_2026.md`
- **Google Scholar details:** `docs/google_scholar_documentation_2026.md`
- **ScholarGPS details:** `docs/scholargps_documentation_2026.md`



## Contact

- **Author:** Lizzy Chen
- **Email:** LizzyChen@outlook.com
