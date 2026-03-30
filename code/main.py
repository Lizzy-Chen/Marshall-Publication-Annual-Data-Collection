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

Active sources in 2026 (in execution order):
  [1] Google Scholar           — via SerpAPI (auto-generates Top-N list after run)
  [2] Web of Science (WoS)     — via Clarivate REST API
  [3] ScholarGPS               — via Selenium (manual CAPTCHA solving required)

Re-aggregate only (skips extraction, uses existing raw data):
  [4] Re-aggregate WoS
  [5] Re-aggregate Google Scholar
  [6] Re-aggregate ScholarGPS

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
from utils                import outlier_report


# ── Source registry ───────────────────────────────────────────────────────────
# Each entry: key → (display_name, extractor_module, aggregator_module, active_in_2026)
SOURCES = {
    "1": ("Google Scholar",       gs_ext,   gs_agg,   True),
    "2": ("Web of Science (WoS)", wos_ext,  wos_agg,  True),
    "3": ("ScholarGPS",           sgps_ext, sgps_agg, True),
}

# Source keys that map to credential validation IDs
SOURCE_CRED_MAP = {
    "1": "google_scholar",
    "2": "wos",
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
    print("  Run in order:\n")
    print("  [1] Google Scholar          ← always run first")
    print("        Covers all faculty via SerpAPI.")
    print(f"        Auto-generates Top-{config.TOP50_N} list when done — review before Step 2.\n")
    print("  [2] Web of Science          ← after reviewing Top-N list")
    print("        Covers Top-N faculty via Clarivate API.\n")
    print("  [3] ScholarGPS              ← can run alongside [2], requires manual CAPTCHA solving")
    print("        Covers Top-N faculty via browser automation (~30–60 min).\n")
    print("  [C] Compare + Outlier Report  ← after 2+ sources complete")
    print("        Merges sources, ranks faculty, flags anomalies.\n")
    print("  " + "─" * 58)
    print("  [A] Run all sources at once  (1 → 2 → 3 → C)")
    print("  [Q] Quit\n")
    print("  Advanced (not regularly needed):")
    print(f"  [G] Regenerate Top-{config.TOP50_N} list   [O] Outlier report only")
    print("  [4] Re-agg WoS   [5] Re-agg Google Scholar   [6] Re-agg ScholarGPS")
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

        if raw == "O":
            return ["O"]

        if raw in ("4", "5", "6"):
            return [raw]

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


# Maps re-aggregate keys → (display name, aggregator module, source key for SOURCES)
REAGGREGATE_MAP = {
    "4": ("Web of Science (WoS)",    wos_agg,  "1"),
    "5": ("Google Scholar",          gs_agg,   "2"),
    "6": ("ScholarGPS",              sgps_agg, "3"),
}


def _run_aggregator_only(key: str) -> None:
    """Run only the aggregator for a source (skips extraction)."""
    name, aggregator, _ = REAGGREGATE_MAP[key]
    print(f"\n{'─' * 62}")
    print(f"  Re-aggregating: {name}")
    print(f"{'─' * 62}")
    aggregator.run()


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


def _run_selection(selection: list[str]) -> None:
    """Execute a menu selection and print a completion summary."""

    # Handle utility-only modes
    if selection == ["C"]:
        comparison.run()
        return

    if selection == ["G"]:
        top_n_gen.run()
        return

    if selection == ["O"]:
        outlier_report.run()
        return

    if selection[0] in REAGGREGATE_MAP:
        _run_aggregator_only(selection[0])
        return

    # Run selected sources
    ran_sources = []
    for key in selection:
        success = _run_source(key)
        if success:
            ran_sources.append(key)

    # ── Auto-generate Top-N list after Google Scholar runs ────────────────────
    if "1" in ran_sources:
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

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 62}")
    print("  Run complete!")
    print(f"  Sources processed: {len(ran_sources)}")
    if ran_sources:
        source_names = [SOURCES[k][0] for k in ran_sources]
        print(f"  Sources: {', '.join(source_names)}")
    print(f"  Results saved to: {config.RESULTS_ROOT}/")
    print(f"{'=' * 62}\n")


def main() -> None:
    _print_banner()

    while True:
        _print_menu()
        selection = _get_user_selection()
        _run_selection(selection)
        input("  Press Enter to return to the menu…\n")


if __name__ == "__main__":
    main()
