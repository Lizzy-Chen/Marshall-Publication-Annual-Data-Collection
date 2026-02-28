"""
sources/wos/extractor.py
------------------------
Extracts publication data for all faculty in the Top-50 list from the
Web of Science (WoS) Starter API.

Run via main.py or directly:
    python -m sources.wos.extractor

Outputs
-------
results/wos/WoS_Publications_FULL.csv   — all publications, all years
results/wos/WoS_error_log.txt           — missing IDs, API errors
"""

import os
import sys
import time
import requests
import pandas as pd
from pathlib import Path

# Allow running directly (python sources/wos/extractor.py) or as a module
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config
from utils.faculty_loader import load_faculty


# ── Required faculty columns ──────────────────────────────────────────────────
_REQUIRED_COLS = [
    config.COL_LAST_NAME, config.COL_FIRST_NAME,
    config.COL_DEPARTMENT, config.COL_EMAIL,
    config.COL_FACULTY_TYPE, "WoS ResearchID",
]


def _get_citation_count(citation_list: list) -> int:
    """
    Extract the Web of Knowledge (WOK) citation count from the API's
    citations array. The array may contain entries for multiple databases;
    we only want the WOK count.
    """
    if not isinstance(citation_list, list):
        return 0
    for item in citation_list:
        if item.get("db") == "WOK":
            return int(item.get("count", 0))
    return 0


def _fetch_author_publications(
    wos_id: str,
    last_name: str,
    first_name: str,
    department: str,
    email: str,
    faculty_type: str,
) -> tuple[list[dict], str | None]:
    """
    Fetch all publications for one faculty member using their WoS ResearchID.

    Returns
    -------
    (records, error_message)
        records       : list of publication dicts (may be empty)
        error_message : None on success, string description on failure
    """
    headers = {
        "Accept": "application/json",
        "X-ApiKey": config.WOS_API_KEY,
    }
    query  = f"AI=({wos_id})"
    page   = 1
    total  = None
    pubs   = []
    profile_url = f"https://www.webofscience.com/wos/author/record/{wos_id}"

    while total is None or (page - 1) * config.WOS_PAGE_SIZE < total:
        params = {
            "db":        config.WOS_DB,
            "q":         query,
            "limit":     config.WOS_PAGE_SIZE,
            "page":      page,
            "sortField": "PY+D",     # Sort by publication year descending
        }

        # Retry loop for transient HTTP errors
        response = None
        for attempt in range(config.WOS_MAX_RETRIES):
            try:
                response = requests.get(
                    config.WOS_BASE_URL,
                    headers=headers,
                    params=params,
                    timeout=30,
                )
                if response.status_code == 200:
                    break
                if response.status_code == 429:
                    # Rate limited — wait and retry
                    wait = config.WOS_RETRY_BASE ** attempt
                    print(f"    [Rate limit] Waiting {wait}s before retry…")
                    time.sleep(wait)
                else:
                    # Non-retriable error
                    return [], (
                        f"HTTP {response.status_code} fetching page {page} "
                        f"for {first_name} {last_name}"
                    )
            except requests.RequestException as exc:
                if attempt == config.WOS_MAX_RETRIES - 1:
                    return [], f"Network error for {first_name} {last_name}: {exc}"
                time.sleep(config.WOS_RETRY_BASE ** attempt)

        if response is None or response.status_code != 200:
            return [], f"Failed to fetch data for {first_name} {last_name} after retries"

        data  = response.json()
        total = data.get("metadata", {}).get("total", 0)
        if total == 0:
            break

        for hit in data.get("hits", []):
            pubs.append({
                config.COL_LAST_NAME:    last_name,
                config.COL_FIRST_NAME:   first_name,
                config.COL_DEPARTMENT:   department,
                config.COL_EMAIL:        email,
                config.COL_FACULTY_TYPE: faculty_type,
                "WoS ResearchID Link":   profile_url,
                config.COL_TITLE:        hit.get("title"),
                config.COL_PUB_YEAR:     hit.get("source", {}).get("publishYear"),
                config.COL_CITATIONS:    _get_citation_count(hit.get("citations", [])),
                config.COL_JOURNAL:      hit.get("source", {}).get("sourceTitle"),
                "DOI":                   hit.get("identifiers", {}).get("doi"),
            })

        page += 1
        time.sleep(config.WOS_SLEEP_SEC)

    return pubs, None


def run() -> None:
    """Main extraction entry point. Called by main.py or run directly."""
    print("\n[WoS] Starting publication extraction…")
    print(f"  Input : {config.FACULTY_TOP50_PATH.name}")
    print(f"  Output: {config.WOS_RESULTS}/")

    # Validate credentials
    if not config.WOS_API_KEY:
        print("[WoS] ERROR: WOS_API_KEY not set. Check your .env file.")
        return

    # Load faculty list
    df_faculty = load_faculty(
        config.FACULTY_TOP50_PATH,
        required_cols=_REQUIRED_COLS,
    )

    # Ensure output directory exists
    config.WOS_RESULTS.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    error_logs:  list[str]  = []
    success_count = 0

    for _, row in df_faculty.iterrows():
        last       = row[config.COL_LAST_NAME]
        first      = row[config.COL_FIRST_NAME]
        dept       = row[config.COL_DEPARTMENT]
        email      = row[config.COL_EMAIL]
        fac_type   = row[config.COL_FACULTY_TYPE]
        wos_id_raw = row["WoS ResearchID"]

        # Skip faculty with no WoS ID
        if pd.isna(wos_id_raw) or not str(wos_id_raw).strip():
            msg = f"Missing WoS ResearchID for {first} {last}"
            print(f"  [SKIP] {msg}")
            error_logs.append(msg)
            continue

        wos_id = str(wos_id_raw).strip()
        print(f"  Fetching: {first} {last} (WoS ID: {wos_id})")

        pubs, error = _fetch_author_publications(
            wos_id, last, first, dept, email, fac_type
        )

        if error:
            print(f"    [ERROR] {error}")
            error_logs.append(error)
            continue

        if not pubs:
            msg = f"No publications found for {first} {last} (WoS ID: {wos_id})"
            print(f"    [WARN] {msg}")
            error_logs.append(msg)
            continue

        all_records.extend(pubs)
        success_count += 1
        print(f"    → {len(pubs)} publications found")

    # ── Save outputs ──────────────────────────────────────────────────────────
    out_csv = config.WOS_RESULTS / "WoS_Publications_FULL.csv"
    df_out  = pd.DataFrame(all_records)
    df_out.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"\n[WoS] Saved {len(df_out)} records → {out_csv.name}")

    if error_logs:
        log_path = config.WOS_RESULTS / "WoS_error_log.txt"
        log_path.write_text("\n".join(error_logs), encoding="utf-8")
        print(f"[WoS] {len(error_logs)} errors/warnings → {log_path.name}")

    total_faculty = len(df_faculty) + sum(
        1 for m in error_logs if "Missing WoS ResearchID" in m
    )
    print(f"[WoS] Extraction complete: {success_count} / {len(df_faculty)} faculty processed.")


if __name__ == "__main__":
    run()
