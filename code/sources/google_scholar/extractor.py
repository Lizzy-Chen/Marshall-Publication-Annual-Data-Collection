"""
sources/google_scholar/extractor.py
------------------------------------
Extracts publication data for all faculty in the full faculty list from
Google Scholar, using SerpAPI's google_scholar_author engine.

Run via main.py or directly:
    python -m sources.google_scholar.extractor

Outputs
-------
results/google_scholar/Google_Scholar_Publications_FULL.csv
results/google_scholar/Google_Scholar_Publications_FULL.json
results/google_scholar/Google_Scholar_error_log.txt
"""

import re
import sys
import time
import pandas as pd
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config
from utils.faculty_loader import load_faculty

try:
    from serpapi import GoogleSearch
except ImportError:
    print("[Google Scholar] ERROR: serpapi package not installed.")
    print("  Run: pip install google-search-results")
    sys.exit(1)


# ── Required faculty columns ──────────────────────────────────────────────────
_REQUIRED_COLS = [
    config.COL_LAST_NAME, config.COL_FIRST_NAME,
    config.COL_DEPARTMENT, config.COL_EMAIL,
    config.COL_FACULTY_TYPE, "Google Scholar Profile Link",
]


def _extract_scholar_id(profile_url: str) -> str | None:
    """
    Parse the Google Scholar Author ID from a profile URL.
    Example URL: https://scholar.google.com/citations?user=abcd1234&hl=en
    Returns 'abcd1234', or None if not found.
    """
    match = re.search(r"user=([a-zA-Z0-9_-]+)", str(profile_url))
    return match.group(1) if match else None


def _fetch_scholar_publications(author_id: str) -> tuple[list[dict], str | None]:
    """
    Fetch all publications for one Google Scholar author via SerpAPI.

    Uses pagination: each request returns up to GS_PAGE_SIZE articles.
    Continues until no 'next' pagination link is returned.

    Returns
    -------
    (articles, error_message)
        articles      : list of raw SerpAPI article dicts
        error_message : None on success, string on failure
    """
    all_articles: list[dict] = []
    params = {
        "engine":    "google_scholar_author",
        "api_key":   config.SERPAPI_KEY,
        "hl":        "en",
        "author_id": author_id,
        "num":       config.GS_PAGE_SIZE,
    }

    for attempt in range(config.GS_MAX_RETRIES):
        try:
            while True:
                search  = GoogleSearch(params)
                results = search.get_dict()

                # Check for API-level errors
                if "error" in results:
                    return [], f"SerpAPI error: {results['error']}"

                if "articles" in results:
                    all_articles.extend(results["articles"])

                # Pagination: advance start position if more pages exist
                pagination = results.get("serpapi_pagination", {})
                if "next" in pagination:
                    params["start"] = len(all_articles)
                    time.sleep(config.GS_SLEEP_SEC)
                else:
                    break

            return all_articles, None

        except Exception as exc:
            if attempt == config.GS_MAX_RETRIES - 1:
                return [], f"Error after {config.GS_MAX_RETRIES} attempts: {exc}"
            time.sleep(config.WOS_RETRY_BASE ** attempt)

    return [], "Unknown error in _fetch_scholar_publications"


def run() -> None:
    """Main extraction entry point. Called by main.py or run directly."""
    print("\n[Google Scholar] Starting publication extraction…")
    print(f"  Input : {config.FACULTY_FULL_PATH.name}")
    print(f"  Output: {config.GS_RESULTS}/")

    # Validate credentials
    if not config.SERPAPI_KEY:
        print("[Google Scholar] ERROR: SERPAPI_KEY not set. Check your .env file.")
        return

    # Load faculty list (full list — Google Scholar covers all faculty)
    df_faculty = load_faculty(
        config.FACULTY_FULL_PATH,
        required_cols=_REQUIRED_COLS,
    )

    # Ensure output directory exists
    config.GS_RESULTS.mkdir(parents=True, exist_ok=True)

    all_records:  list[dict] = []
    error_logs:   list[str]  = []
    success_count = 0

    for _, row in df_faculty.iterrows():
        last      = row[config.COL_LAST_NAME]
        first     = row[config.COL_FIRST_NAME]
        dept      = row[config.COL_DEPARTMENT]
        email     = row[config.COL_EMAIL]
        fac_type  = row[config.COL_FACULTY_TYPE]
        gs_link   = row["Google Scholar Profile Link"]

        # Extract Google Scholar Author ID from profile URL
        author_id = _extract_scholar_id(str(gs_link))
        if not author_id:
            msg = f"Could not extract Google Scholar ID from URL for {first} {last}: {gs_link}"
            print(f"  [SKIP] {msg}")
            error_logs.append(msg)
            continue

        print(f"  Fetching: {first} {last} (Scholar ID: {author_id})")

        articles, error = _fetch_scholar_publications(author_id)

        if error:
            print(f"    [ERROR] {error}")
            error_logs.append(f"{first} {last}: {error}")
            continue

        if not articles:
            msg = f"No publications found for {first} {last} (Scholar ID: {author_id})"
            print(f"    [WARN] {msg}")
            error_logs.append(msg)
            continue

        for pub in articles:
            all_records.append({
                config.COL_LAST_NAME:           last,
                config.COL_FIRST_NAME:          first,
                config.COL_DEPARTMENT:          dept,
                config.COL_EMAIL:               email,
                config.COL_FACULTY_TYPE:        fac_type,
                "Google Scholar Profile Link":  gs_link,
                "GoogleScholarID":              author_id,
                config.COL_TITLE:               pub.get("title"),
                config.COL_PUB_YEAR:            pub.get("year"),
                config.COL_CITED_BY:            pub.get("cited_by", {}).get("value"),
                config.COL_JOURNAL:             pub.get("publication"),
                "Authors":                      pub.get("authors"),
                "Link":                         pub.get("link"),
            })

        success_count += 1
        print(f"    → {len(articles)} publications found")

    # ── Save outputs ──────────────────────────────────────────────────────────
    df_out = pd.DataFrame(all_records)

    out_csv  = config.GS_RESULTS / "Google_Scholar_Publications_FULL.csv"
    out_json = config.GS_RESULTS / "Google_Scholar_Publications_FULL.json"

    df_out.to_csv(out_csv, index=False, encoding="utf-8")
    df_out.to_json(out_json, orient="records", indent=2, force_ascii=False)

    print(f"\n[Google Scholar] Saved {len(df_out)} records → {out_csv.name}")
    print(f"[Google Scholar] JSON copy                → {out_json.name}")

    if error_logs:
        log_path = config.GS_RESULTS / "Google_Scholar_error_log.txt"
        log_path.write_text("\n".join(error_logs), encoding="utf-8")
        print(f"[Google Scholar] {len(error_logs)} errors/warnings → {log_path.name}")

    print(f"[Google Scholar] Extraction complete: {success_count} / {len(df_faculty)} faculty processed.")


if __name__ == "__main__":
    run()
