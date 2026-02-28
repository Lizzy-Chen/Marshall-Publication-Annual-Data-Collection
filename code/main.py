"""
main.py
-------
Marshall Faculty Publication Data Collection — 2026
Single entry point for all data extraction, aggregation, and comparison.

Usage
-----
    cd code
    python main.py

The script presents an interactive menu. Enter the numbers of the sources
you want to run (comma-separated), or press A for all active sources.

Active sources in 2026:
  [1] Web of Science (WoS)     — via Clarivate REST API
  [2] Google Scholar           — via SerpAPI (auto-generates Top-N list after run)

Inactive (kept for reference):
  [3] ScholarGPS               — via Selenium (requires manual CAPTCHA solving)

Utilities:
  [G] Generate Top-N faculty list only (from existing GS results)
"""

import sys
from pathlib import Path

# ── Make sure imports work when running from code/ directory ─────────────────
sys.path.insert(0, str(Path(__file__).parent))

import config
from config import validate_credentials, print_config_summary


# ── Source module imports ─────────────────────────────────────────────────────
from sources.wos          import extractor as wos_ext,     aggregator as wos_agg
from sources.google_scholar import extractor as gs_ext,    aggregator as gs_agg
from sources.scholargps   import extractor as sgps_ext,    aggregator as sgps_agg
from utils                import comparison
from utils                import generate_top_N_faculty as top_n_gen


# ── Source registry ───────────────────────────────────────────────────────────
# Each entry: key → (display_name, extractor_module, aggregator_module, active_in_2026)
SOURCES = {
    "1": ("Web of Science (WoS)",     wos_ext,   wos_agg,   True),
    "2": ("Google Scholar",           gs_ext,    gs_agg,    True),
    "3": ("ScholarGPS ⚠  (manual CAPTCHA required)", sgps_ext, sgps_agg, False),
}

# Source keys that map to credential validation IDs
SOURCE_CRED_MAP = {
    "1": "wos",
    "2": "google_scholar",
    "3": None,   # ScholarGPS uses no API key
}


def _print_banner() -> None:
    """Print the startup banner with year window and config info."""
    print("=" * 62)
    print("  Marshall Faculty Publication Data Collection — 2026")
    print("=" * 62)
    print_config_summary()
    print()


def _print_menu() -> None:
    """Print the source selection menu."""
    print("Select data sources to run (enter numbers separated by commas,")
    print("e.g.  1,2  to run WoS and Google Scholar):\n")
    for key, (name, _, _, active) in SOURCES.items():
        status = "" if active else "  [not active in 2026]"
        print(f"  [{key}] {name}{status}")
    print()
    print("  [A] Run all ACTIVE sources (WoS + Google Scholar)")
    print("  [C] Cross-source comparison only (requires 2+ sources already run)")
    print(f"  [G] Generate Top-{config.TOP50_N} faculty list from existing GS results")
    print("  [Q] Quit")
    print()


def _get_user_selection() -> list[str]:
    """
    Prompt the user for source selection and return a list of source keys.
    Loops until a valid selection is entered.
    """
    while True:
        raw = input("  Your choice: ").strip().upper()

        if raw == "Q":
            print("\nExiting. No sources run.")
            sys.exit(0)

        if raw == "A":
            # All active sources (those with active=True in SOURCES)
            return [k for k, (_, _, _, active) in SOURCES.items() if active]

        if raw == "C":
            return ["C"]

        if raw == "G":
            return ["G"]

        # Parse comma-separated numbers
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        valid = [p for p in parts if p in SOURCES]
        invalid = [p for p in parts if p not in SOURCES]

        if invalid:
            print(f"  Unknown option(s): {', '.join(invalid)}. Please try again.\n")
            continue

        if not valid:
            print("  No valid selection. Please enter a number like 1, 2, or 1,2\n")
            continue

        return valid


def _run_source(key: str) -> bool:
    """
    Run the extractor and aggregator for a given source key.
    Returns True on apparent success, False on early exit due to missing credentials.
    """
    name, extractor, aggregator, _ = SOURCES[key]
    print(f"\n{'─' * 62}")
    print(f"  Running: {name}")
    print(f"{'─' * 62}")

    # Validate credentials for this source before starting
    cred_key = SOURCE_CRED_MAP.get(key)
    if cred_key:
        try:
            validate_credentials([cred_key])
        except ValueError as exc:
            print(f"\n[ERROR] {exc}")
            return False

    extractor.run()
    aggregator.run()
    return True


def main() -> None:
    _print_banner()
    _print_menu()

    selection = _get_user_selection()

    # Handle utility-only modes
    if selection == ["C"]:
        comparison.run()
        return

    if selection == ["G"]:
        top_n_gen.run()
        return

    # Run selected sources
    ran_sources = []
    for key in selection:
        success = _run_source(key)
        if success:
            ran_sources.append(key)

    # ── Auto-generate Top-N list after Google Scholar runs ────────────────────
    if "2" in ran_sources:
        print(f"\n{'─' * 62}")
        print(f"  Google Scholar complete — generating Top-{config.TOP50_N} faculty list…")
        print(f"{'─' * 62}")
        top_n_gen.run()

    # ── Auto-run comparison if 2+ sources were successfully run ───────────────
    if len(ran_sources) >= 2:
        print(f"\n{'─' * 62}")
        print("  Multiple sources run — generating cross-source comparison…")
        print(f"{'─' * 62}")
        comparison.run()
    elif len(ran_sources) == 1:
        print(f"\n[NOTE] Only 1 source run. Run a second source, then select [C] for comparison.")

    # ── Final summary ─────────────────────────────────────────────────────────
    print(f"\n{'=' * 62}")
    print("  Run complete!")
    print(f"  Sources processed: {len(ran_sources)}")
    if ran_sources:
        source_names = [SOURCES[k][0].split(" ⚠")[0] for k in ran_sources]
        print(f"  Sources: {', '.join(source_names)}")
    print(f"  Results saved to: {config.RESULTS_ROOT}/")
    print(f"{'=' * 62}\n")


if __name__ == "__main__":
    main()
