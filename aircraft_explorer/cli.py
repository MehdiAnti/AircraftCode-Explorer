"""Command-line interface for AircraftCode-Explorer."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .core import catalog_stats, load_aircraft, search_aircraft


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aircraft-explorer",
        description="Search a local catalog of aircraft.",
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        aircraft = load_aircraft(args.data) if args.data else load_aircraft()
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
