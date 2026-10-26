"""Command-line interface for AircraftCode-Explorer."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .core import (
    DEFAULT_DATA_PATH,
    catalog_stats,
    load_aircraft,
    save_aircraft,
    search_aircraft,
)
from .wikidata import WikidataError, fetch_wikidata_aircraft


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aircraft-explorer",
        description="Search and refresh a local catalog of aircraft.",
    )
    parser.add_argument(
        "--data",
        help="Path to an aircraft JSON file (defaults to data/aircraft.json).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search aircraft records.")
    search_parser.add_argument("query", nargs="?", default="", help="Text to search for.")
    search_parser.add_argument("--manufacturer", default="", help="Filter by manufacturer.")
    search_parser.add_argument(
        "--icao",
        dest="icao_type_designator",
        default="",
        help="Filter by ICAO type designator.",
    )
    search_parser.add_argument("--model", default="", help="Filter by model name.")
    search_parser.add_argument("--json", action="store_true", help="Print JSON results.")

    stats_parser = subparsers.add_parser("stats", help="Show catalog statistics.")
    stats_parser.add_argument("--json", action="store_true", help="Print JSON statistics.")

    update_parser = subparsers.add_parser(
        "update",
        help="Fetch candidate aircraft records from Wikidata and replace the local catalog.",
    )
    update_parser.add_argument(
        "--timeout", type=float, default=20.0, help="Request timeout in seconds."
    )
    update_parser.add_argument(
        "--retries", type=int, default=3, help="Retries after transient errors (0-5)."
    )
    update_parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow an empty response to replace the catalog (default: refuse).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_path = args.data or DEFAULT_DATA_PATH

    if args.command == "update":
        if args.timeout <= 0:
            parser.error("--timeout must be greater than zero")
        if not 0 <= args.retries <= 5:
            parser.error("--retries must be between 0 and 5")

        try:
            diagnostics: list[str] = []
            records = fetch_wikidata_aircraft(
                timeout=args.timeout,
                retries=args.retries,
                diagnostics=diagnostics,
            )
            if not records and not args.allow_empty:
                raise WikidataError(
                    "Wikidata returned zero usable records; the existing catalog was not changed. "
                    "Use --allow-empty only if replacing it with an empty catalog is intentional."
                )
            save_aircraft(records, data_path)
        except (OSError, ValueError, WikidataError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        for message in diagnostics:
            print(f"warning: {message}", file=sys.stderr)
        print(f"Updated catalog with {len(records)} record(s).")
        return 0

    try:
        aircraft = load_aircraft(data_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "stats":
        result = catalog_stats(aircraft)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Aircraft records: {result['aircraft']}")
            print(f"With ICAO designator: {result['with_icao_type_designator']}")
            print(f"Manufacturers: {result['manufacturers']}")
        return 0

    results = search_aircraft(
        aircraft,
        args.query,
        manufacturer=args.manufacturer,
        icao_type_designator=args.icao_type_designator,
        model=args.model,
    )
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif not results:
        print("No matching aircraft found.")
    else:
        for item in results:
            designator = item.get("icao_type_designator") or "—"
            model = item.get("model") or "Unknown model"
            manufacturer = item.get("manufacturer") or "Unknown manufacturer"
            print(f"{designator:8}  {manufacturer}  {model}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
