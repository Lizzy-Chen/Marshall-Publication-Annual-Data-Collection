"""
sources/scholargps/extractor.py
--------------------------------
Extracts publication data from ScholarGPS using Selenium browser automation.

STATUS: Active in 2026.
        Select option [3] in main.py to run, or [A] to run all sources.

IMPORTANT: ScholarGPS requires manual CAPTCHA solving.
  When a CAPTCHA appears, the script pauses and prints a message.
  You must solve the CAPTCHA in the browser window, then press Enter
  in the terminal to continue. Budget 30–60 minutes for a full run.

Prerequisites
-------------
  1. Google Chrome must be installed.
  2. ChromeDriver must be installed and match your Chrome version.
     - macOS (Homebrew): brew install --cask chromedriver
     - Or download from: https://chromedriver.chromium.org/downloads
  3. Set CHROMEDRIVER_PATH in .env if ChromeDriver is not at the default path.

Run via main.py or directly:
    python -m sources.scholargps.extractor

Outputs
-------
results/scholargps/ScholarGPS_Publications_FULL.csv
"""

import os
import re
import sys
import time
import random
import pandas as pd
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config
from utils.faculty_loader import load_faculty

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    print(f"[ScholarGPS] ERROR: missing package — {e}")
    print("  Run: pip install selenium webdriver-manager")
    sys.exit(1)


# ── Required faculty columns ──────────────────────────────────────────────────
_REQUIRED_COLS = [
    config.COL_LAST_NAME, config.COL_FIRST_NAME,
    config.COL_DEPARTMENT, config.COL_EMAIL,
    config.COL_FACULTY_TYPE, "scholargps",
]


def _setup_driver() -> webdriver.Chrome:
    """
    Configure and return a Selenium Chrome WebDriver.
    Uses a realistic user-agent to reduce bot-detection likelihood.
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("disable-infobars")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Realistic user-agent reduces CAPTCHA frequency slightly
    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    chrome_options.add_argument(f"user-agent={user_agent}")

    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def _extract_publications_from_page(driver) -> list[dict]:
    """
    Parse all publication elements on the current ScholarGPS page.
    Returns a list of raw publication dicts (without faculty metadata).
    """
    results = []
    pub_elements = driver.find_elements(By.CLASS_NAME, "result-content")

    for pub in pub_elements:
        # Title
        try:
            title = pub.find_element(By.CLASS_NAME, "publication_title").text.strip()
        except Exception:
            title = "Unknown"

        # Sub-title contains: "Journal Name (Year)"
        try:
            sub_title_text = pub.find_element(By.CLASS_NAME, "sub-title").text
            # Journal is everything before the last "("
            journal = sub_title_text.rsplit("(", 1)[0].strip()
            # Year is inside the last "(...)"
            year_raw = sub_title_text.rsplit("(", 1)[-1].strip("). ")
            # Validate: year should be a 4-digit number
            pub_year = year_raw if re.match(r"^\d{4}$", year_raw) else "Unknown"
        except Exception:
            journal  = "Unknown"
            pub_year = "Unknown"

        # Authors
        try:
            authors = pub.find_element(By.CLASS_NAME, "authors").text.strip()
        except Exception:
            authors = "Unknown"

        # DOI
        try:
            doi = pub.find_element(By.CLASS_NAME, "doi_container").text.strip()
        except Exception:
            doi = "Unknown"

        # Citations: "Cited by (N)" — extract N
        try:
            source_text = pub.find_element(By.CLASS_NAME, "source").text
            # Pattern: "Cited by (123)" or "Cited by 123"
            cited_match = re.search(r"Cited by\s*\(?(\d+)\)?", source_text, re.IGNORECASE)
            citations = cited_match.group(1) if cited_match else "0"
        except Exception:
            citations = "0"

        results.append({
            config.COL_TITLE:    title,
            config.COL_PUB_YEAR: pub_year,
            config.COL_CITED_BY: citations,
            config.COL_JOURNAL:  journal,
            "Authors":           authors,
            "DOI":               doi,
        })

    return results


def run() -> None:
    """Main extraction entry point. Called by main.py or run directly."""
    print("\n[ScholarGPS] Starting publication extraction…")
    print("  NOTE: This source requires manual CAPTCHA solving.")
    print(f"  Input : {config.FACULTY_TOP50_PATH.name}")
    print(f"  Output: {config.SGPS_RESULTS}/")

    # Load faculty list (Top-50 list, same as WoS)
    df_faculty = load_faculty(
        config.FACULTY_TOP50_PATH,
        required_cols=_REQUIRED_COLS,
    )

    config.SGPS_RESULTS.mkdir(parents=True, exist_ok=True)

    # Initialise browser
    driver = _setup_driver()
    all_records: list[dict] = []

    try:
        for idx, row in df_faculty.iterrows():
            last      = row[config.COL_LAST_NAME]
            first     = row[config.COL_FIRST_NAME]
            dept      = row[config.COL_DEPARTMENT]
            email     = row[config.COL_EMAIL]
            fac_type  = row[config.COL_FACULTY_TYPE]
            url       = row["scholargps"]

            print(f"\n  Processing ({idx + 1}/{len(df_faculty)}): {first} {last}")
            print(f"    URL: {url}")

            try:
                driver.get(url)

                # Wait for page to load; random delay mimics human behaviour
                time.sleep(random.uniform(config.SGPS_PAGE_WAIT_MIN,
                                          config.SGPS_PAGE_WAIT_MAX))

                # Detect and handle CAPTCHA
                if "confirm you are human" in driver.page_source.lower():
                    print("    ⚠  CAPTCHA detected. Please solve it in the browser window.")
                    input("    Press Enter here after completing the CAPTCHA…")
                    driver.refresh()
                    time.sleep(5)

                # Extract publications across all pages
                page_num = 1
                while True:
                    page_pubs = _extract_publications_from_page(driver)
                    print(f"    Page {page_num}: {len(page_pubs)} publications")

                    for pub in page_pubs:
                        all_records.append({
                            config.COL_LAST_NAME:        last,
                            config.COL_FIRST_NAME:       first,
                            config.COL_DEPARTMENT:       dept,
                            config.COL_EMAIL:            email,
                            config.COL_FACULTY_TYPE:     fac_type,
                            "ScholarGPS Profile Link":   url,
                            **pub,
                        })

                    # Try clicking "Next Page" (chevron-right icon)
                    try:
                        next_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable(
                                (By.XPATH, "//i[contains(@class, 'fa-chevron-right')]")
                            )
                        )
                        driver.execute_script("arguments[0].click();", next_btn)
                        time.sleep(random.uniform(config.SGPS_NAV_WAIT_MIN,
                                                  config.SGPS_NAV_WAIT_MAX))
                        page_num += 1
                    except Exception:
                        # No next page — pagination complete for this faculty member
                        break

            except Exception as exc:
                print(f"    [ERROR] {exc}")

    finally:
        driver.quit()

    # ── Save output ───────────────────────────────────────────────────────────
    out_csv = config.SGPS_RESULTS / "ScholarGPS_Publications_FULL.csv"
    df_out  = pd.DataFrame(all_records)
    df_out.to_csv(out_csv, index=False, encoding="utf-8")

    print(f"\n[ScholarGPS] Saved {len(df_out)} records → {out_csv.name}")
    print("[ScholarGPS] Extraction complete.")


if __name__ == "__main__":
    run()
