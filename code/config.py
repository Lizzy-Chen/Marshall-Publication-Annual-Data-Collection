"""
config.py
---------
Central configuration for the Marshall Faculty Publication Data Collection pipeline.

All file paths, year window settings, and shared column name constants are defined
here. Source scripts import from this module rather than hardcoding values inline.

To customize the year window or file paths, edit this file — not the source scripts.
"""

import os
import datetime
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env credentials ────────────────────────────────────────────────────
# Looks for .env in the same directory as this config file.
_HERE = Path(__file__).parent
load_dotenv(_HERE / ".env")

# ── API Credentials (loaded from .env) ───────────────────────────────────────
WOS_API_KEY = os.getenv("WOS_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# ── Year Window ───────────────────────────────────────────────────────────────
# Publications are filtered to the most recent 5 complete years.
# Example: if today is 2026, YEAR_START=2021, YEAR_END=2025 (2026 is excluded
# because the year is not yet complete).
CURRENT_YEAR = datetime.datetime.now().year
YEAR_END     = CURRENT_YEAR - 1          # Last fully completed year
YEAR_START   = YEAR_END - 4              # 5-year window (inclusive)

# ── Directory Paths ───────────────────────────────────────────────────────────
# Paths are relative to the project root (one level up from code/).
_ROOT = _HERE.parent

# ── Faculty input files ───────────────────────────────────────────────────────
# The Spring faculty list (project root) is the single master file for 2026.
# It contains: Last Name, First Name, Department, Email, Faculty Type,
#              WoS, scholargps, Google Scholar Profile Link, ORCID, SCOPUS_ID, …
# Used by: Google Scholar extractor AND generate_top_N_faculty.py (WoS ID lookup)
FACULTY_FULL_PATH = _ROOT / "2026_Spring_Faculty_List.xlsx"

# data/ folder — stores auto-generated files (the Top-N list output)
DATA_DIR = _ROOT / "data"

# How many top faculty to select for WoS / ScholarGPS extraction
TOP50_N = 50

# The auto-generated Top-N list.
# generate_top_N_faculty.py writes here; WoS + ScholarGPS extractors read here.
FACULTY_TOP50_PATH = DATA_DIR / f"Top_{TOP50_N}_Faculty_{CURRENT_YEAR}.xlsx"

# Output results directories (auto-created by each source script)
RESULTS_ROOT  = _ROOT / "results"
WOS_RESULTS   = RESULTS_ROOT / "wos"
GS_RESULTS    = RESULTS_ROOT / "google_scholar"
SGPS_RESULTS  = RESULTS_ROOT / "scholargps"
COMP_RESULTS  = RESULTS_ROOT / "comparison"

# ── Shared Column Name Constants ──────────────────────────────────────────────
# Using constants avoids typos when column names are referenced in multiple files.
COL_LAST_NAME    = "Last Name"
COL_FIRST_NAME   = "First Name"
COL_DEPARTMENT   = "Department"
COL_EMAIL        = "Email"
COL_FACULTY_TYPE = "Faculty Type"
COL_PUB_YEAR     = "Publication Year"
COL_CITATIONS    = "Citations"       # WoS label
COL_CITED_BY     = "Cited By"        # Google Scholar / ScholarGPS label
COL_JOURNAL      = "Journal"
COL_TITLE        = "Title"
COL_RANK         = "Rank"
COL_TOTAL_CITES  = "Total Citations"

# Columns used as join keys across all sources
FACULTY_KEY_COLS = [COL_LAST_NAME, COL_FIRST_NAME, COL_DEPARTMENT,
                    COL_EMAIL, COL_FACULTY_TYPE]

# ── WoS API Settings ──────────────────────────────────────────────────────────
WOS_BASE_URL    = "https://api.clarivate.com/apis/wos-starter/v1/documents"
WOS_DB          = "WOK"
WOS_PAGE_SIZE   = 50
WOS_SLEEP_SEC   = 1       # Pause between API pages (rate-limit compliance)
WOS_MAX_RETRIES = 3       # Retry attempts on transient HTTP errors
WOS_RETRY_BASE  = 2       # Base for exponential backoff (2^attempt seconds)

# ── Google Scholar / SerpAPI Settings ────────────────────────────────────────
GS_PAGE_SIZE    = 100     # Publications per SerpAPI request
GS_SLEEP_SEC    = 2       # Pause between paginated requests
GS_MAX_RETRIES  = 3

# ── ScholarGPS / Selenium Settings ────────────────────────────────────────────
# ChromeDriver path — update if your installation differs.
# macOS via Homebrew: /opt/homebrew/bin/chromedriver (Apple Silicon)
#                  or /usr/local/bin/chromedriver (Intel)
# You can also set CHROMEDRIVER_PATH in .env to override.
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
SGPS_PAGE_WAIT_MIN = 10   # Minimum seconds to wait after loading a page
SGPS_PAGE_WAIT_MAX = 15   # Maximum seconds to wait after loading a page
SGPS_NAV_WAIT_MIN  = 5    # Minimum seconds between pagination clicks
SGPS_NAV_WAIT_MAX  = 7    # Maximum seconds between pagination clicks


def validate_credentials(sources: list[str]) -> None:
    """
    Check that required API keys are set for the selected sources.
    Raises ValueError with a helpful message if any key is missing.
    """
    missing = []
    if "wos" in sources and not WOS_API_KEY:
        missing.append("WOS_API_KEY (needed for Web of Science)")
    if "google_scholar" in sources and not SERPAPI_KEY:
        missing.append("SERPAPI_KEY (needed for Google Scholar)")

    if missing:
        raise ValueError(
            "Missing credentials in .env file:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n\nCopy code/.env.example to code/.env and fill in the values."
        )


def print_config_summary() -> None:
    """Print key configuration values for operator confirmation at startup."""
    print(f"  Year window : {YEAR_START}–{YEAR_END}")
    print(f"  Faculty (full)  : {FACULTY_FULL_PATH.name}")
    print(f"  Faculty (top-50): {FACULTY_TOP50_PATH.name}")
    print(f"  Results root    : {RESULTS_ROOT}")
