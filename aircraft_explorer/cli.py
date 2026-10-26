"""Command-line interface for AircraftCode-Explorer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .core import (
    DEFAULT_DATA_PATH,
    catalog_stats,
    catalog_status,
    load_aircraft,
    save_aircraft,
    search_aircraft,
)
from .csv_export import write_csv
from .ingestion import verify_record
from .metadata import MetadataError, cross_check_candidates, load_metadata_csv, write_cross_check_report
from .review import catalog_review, write_review_report
from .opensky_import import OpenSkyImportError, import_opensky_csv, merge_opensky_records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aircraft-explorer",
        description="Search, review, and maintain a local aircraft catalog.",
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
    search_parser.add_argument(
        "--sort-by",
        choices=("manufacturer", "model", "icao", "description"),
        default="manufacturer",
        help="Sort results by this field (default: manufacturer).",
    )
    search_parser.add_argument(
        "--descending", action="store_true", help="Sort in descending order."
    )
    search_parser.add_argument("--json", action="store_true", help="Print JSON results.")

    stats_parser = subparsers.add_parser("stats", help="Show catalog statistics.")
    stats_parser.add_argument("--json", action="store_true", help="Print JSON statistics.")

    status_parser = subparsers.add_parser(
        "status", help="Show catalog quality, sources, and retrieval freshness."
    )
    status_parser.add_argument("--json", action="store_true", help="Print JSON status.")

    export_parser = subparsers.add_parser("export", help="Export the catalog as CSV.")
    export_parser.add_argument(
        "--output",
        default="-",
        help="Output CSV path; use '-' or omit to write to standard output.",
    )

    cross_check_parser = subparsers.add_parser(
        "cross-check",
        help="Compare candidate records against a locally supplied aircraft metadata CSV.",
    )
    cross_check_parser.add_argument(
        "--input", default="data/candidates.json", help="Candidate JSON path."
    )
    cross_check_parser.add_argument(
        "--metadata", required=True,
        help="Path to a locally obtained aircraft metadata CSV; no download is performed.",
    )
    cross_check_parser.add_argument(
        "--output", default="data/metadata-cross-check.json",
        help="Report JSON path (default: data/metadata-cross-check.json).",
    )

    opensky_parser = subparsers.add_parser(
        "import-opensky",
        help="Import a locally obtained OpenSky metadata CSV into the selected catalog.",
    )
    opensky_parser.add_argument(
        "--metadata", required=True,
        help="Path to a locally obtained OpenSky aircraft metadata CSV; no download is performed.",
    )
    opensky_parser.add_argument(
        "--output", default=None,
        help="Catalog JSON path (default: selected catalog, normally data/aircraft.json).",
    )
    opensky_parser.add_argument(
        "--dry-run", action="store_true",
        help="Show proposed import counts without writing the catalog.",
    )

    review_parser = subparsers.add_parser("review", help="Summarize verification states and ICAO type-code conflicts.")
    review_parser.add_argument("--json", action="store_true", help="Print the full review report as JSON.")
    review_parser.add_argument("--output", default=None, help="Optional path to save the JSON review report.")

    verify_parser = subparsers.add_parser("verify", help="Mark one record verified after independent manual source review.")
    verify_parser.add_argument("--model", required=True, help="Exact model name from the catalog.")
    verify_parser.add_argument("--icao", default=None, help="Optional ICAO designator to disambiguate.")
    verify_parser.add_argument("--source-name", required=True, help="Independent source reviewed by you.")
    verify_parser.add_argument("--source-url", required=True, help="HTTPS URL supporting the populated fields.")
    verify_parser.add_argument("--retrieved-at", required=True, help="ISO-8601 source review timestamp.")
    verify_parser.add_argument("--confirm", action="store_true", help="Confirm you manually checked the source supports every populated factual field.")
    verify_parser.add_argument("--confirm-conflict", action="store_true", help="Allow verification of a conflicting code after manual resolution.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    data_path = args.data or DEFAULT_DATA_PATH

    if args.command == "cross-check":
        try:
            input_path = Path(args.input) if args.input else Path(data_path)
            with input_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
                raise ValueError("Catalog file must contain a JSON list of objects")
            metadata_records = load_metadata_csv(args.metadata)
            report = cross_check_candidates(
                payload,
                metadata_records,
                metadata_source=Path(args.metadata).name,
            )
            report["catalog_source"] = str(input_path)
            write_cross_check_report(report, args.output)
        except (OSError, ValueError, json.JSONDecodeError, MetadataError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        counts = report["summary"]["statuses"]
        print(
            f"Cross-checked {report['summary']['candidates']} catalog record(s) against "
            f"{report['summary']['metadata_rows']} metadata row(s): "
            + ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
            + f". Report: {args.output}. No catalog changes made."
        )
        return 0

    if args.command == "import-opensky":
        try:
            imported, import_summary = import_opensky_csv(args.metadata)
            output_path = Path(args.output) if args.output else Path(data_path)
            existing = load_aircraft(output_path)
            merged, merge_summary = merge_opensky_records(existing, imported)
            if not imported:
                raise OpenSkyImportError(
                    "The CSV contained no usable model/type-code records; catalog was not changed."
                )
            if not args.dry_run:
                save_aircraft(merged, output_path)
        except (OSError, ValueError, json.JSONDecodeError, OpenSkyImportError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(
            f"OpenSky CSV rows: {import_summary['rows_read']}; "
            f"unique model/type records: {len(imported)}; "
            f"skipped rows: {import_summary['rows_skipped']}; "
            f"records added: {merge_summary['added']}; "
            f"records enriched with provenance: {merge_summary['enriched']}; "
            f"conflicting type codes: {import_summary['conflicting_codes']}."
        )
        if args.dry_run:
            print(f"Dry run only; catalog not changed. Target: {output_path}")
        else:
            print(f"Catalog updated: {output_path}")
        print("Imported OpenSky records remain unverified; use review and verify after independent manual review.")
        return 0

    try:
        aircraft = load_aircraft(data_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "review":
        report = catalog_review(aircraft)
        try:
            if args.output:
                write_review_report(report, args.output)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
        print(f"Catalog records: {report['records']}")
        print("Verification status:")
        for status, count in report["verification_statuses"].items():
            print(f"  {status}: {count}")
        print(f"Conflicting ICAO type codes: {len(report['conflicts'])}")
        for conflict in report["conflicts"]:
            models = "; ".join(f"{item['manufacturer'] or 'Unknown manufacturer'} — {item['model'] or 'Unknown model'}" for item in conflict["records"])
            print(f"  {conflict['icao_type_designator']}: {models}")
        if args.output:
            print(f"Review report saved: {args.output}")
        return 0

    if args.command == "verify":
        if not args.confirm:
            parser.error("verify requires --confirm after manually checking the source")
        try:
            matches = [
                index for index, record in enumerate(aircraft)
                if record.get("model") == args.model
                and (args.icao is None or record.get("icao_type_designator") == args.icao.upper())
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one record match; found {len(matches)}. Use --icao to disambiguate.")
            index = matches[0]
            code = aircraft[index].get("icao_type_designator")
            if code and any(conflict["icao_type_designator"] == code for conflict in catalog_review(aircraft)["conflicts"]) and not args.confirm_conflict:
                raise ValueError(f"{code} is listed as conflicting. Review the conflict report first, or pass --confirm-conflict only after resolving it manually.")
            aircraft[index] = verify_record(aircraft[index], source_name=args.source_name, source_url=args.source_url, retrieved_at=args.retrieved_at)
            save_aircraft(aircraft, data_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Marked record verified: {args.model}")
        print(f"Catalog updated: {data_path}")
        return 0

    if args.command == "stats":
        result = catalog_stats(aircraft)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Aircraft records: {result['aircraft']}")
            print(f"With ICAO designator: {result['with_icao_type_designator']}")
            print(f"Manufacturers: {result['manufacturers']}")
        return 0

    if args.command == "status":
        result = catalog_status(aircraft)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Aircraft records: {result['aircraft']}")
            print(f"With ICAO designator: {result['with_icao_type_designator']}")
            print(f"Missing ICAO designator: {result['missing_icao_type_designator']}")
            print(f"Manufacturers: {result['manufacturers']}")
            print("Records by source:")
            for source, count in result["sources"].items():
                print(f"  {source}: {count}")
            print(f"With retrieval timestamp: {result['with_retrieval_timestamp']}")
            print(f"Missing retrieval timestamp: {result['missing_retrieval_timestamp']}")
            print(f"Invalid retrieval timestamp: {result['invalid_retrieval_timestamp']}")
            if result["latest_retrieved_at"] is None:
                print("Latest retrieval: Unknown (no valid retrieval timestamps)")
                print("Latest retrieval age: Unknown")
            else:
                print(f"Oldest retrieval (UTC): {result['oldest_retrieved_at']}")
                print(f"Latest retrieval (UTC): {result['latest_retrieved_at']}")
                print(f"Latest retrieval age (days): {result['latest_retrieval_age_days']}")
        return 0

    if args.command == "export":
        try:
            if args.output == "-":
                write_csv(aircraft, sys.stdout)
            else:
                output_path = Path(args.output)
                with output_path.open("w", encoding="utf-8", newline="") as output_file:
                    write_csv(aircraft, output_file)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        return 0

    results = search_aircraft(
        aircraft,
        args.query,
        manufacturer=args.manufacturer,
        icao_type_designator=args.icao_type_designator,
        model=args.model,
        sort_by=args.sort_by,
        descending=args.descending,
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
