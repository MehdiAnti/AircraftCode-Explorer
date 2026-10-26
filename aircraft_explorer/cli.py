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
from .ingestion import verified_records
from .metadata import MetadataError, cross_check_candidates, load_metadata_csv, write_cross_check_report
from .opensky_import import OpenSkyImportError, import_opensky_csv, merge_opensky_records
from .wikidata import WikidataError, fetch_wikidata_aircraft, fetch_wikidata_candidates


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

    discover_parser = subparsers.add_parser(
        "discover", help="Discover broad Wikidata aircraft candidates without changing the catalog."
    )
    discover_parser.add_argument(
        "--output", default="data/candidates.json",
        help="Candidate JSON path (default: data/candidates.json)."
    )
    discover_parser.add_argument(
        "--timeout", type=float, default=20.0, help="Request timeout in seconds."
    )
    discover_parser.add_argument(
        "--retries", type=int, default=3, help="Retries after transient errors (0-5)."
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
        help="Catalog JSON path (default: the selected catalog, normally data/aircraft.json).",
    )
    opensky_parser.add_argument(
        "--dry-run", action="store_true",
        help="Show the proposed import summary without writing the catalog.",
    )

    promote_parser = subparsers.add_parser(
        "promote", help="Write only independently verified candidates to a catalog."
    )
    promote_parser.add_argument(
        "--input", default="data/candidates.json", help="Candidate JSON path."
    )
    promote_parser.add_argument(
        "--output", default="data/verified-aircraft.json",
        help="Output catalog path; defaults to a separate file, not data/aircraft.json."
    )

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

    if args.command == "discover":
        if args.timeout <= 0:
            parser.error("--timeout must be greater than zero")
        if not 0 <= args.retries <= 5:
            parser.error("--retries must be between 0 and 5")
        try:
            diagnostics: list[str] = []
            records = fetch_wikidata_candidates(
                timeout=args.timeout, retries=args.retries, diagnostics=diagnostics
            )
            if not records:
                raise WikidataError(
                    "Wikidata returned zero usable candidates; no output file was written."
                )
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            save_aircraft(records, output_path)
        except (OSError, ValueError, WikidataError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        for message in diagnostics:
            print(f"warning: {message}", file=sys.stderr)
        model_candidates = sum(
            record.get("candidate_classification") == "model_candidate"
            for record in records
        )
        individual_aircraft = sum(
            record.get("candidate_classification") == "individual_aircraft"
            for record in records
        )
        ambiguous = sum(
            record.get("candidate_classification") == "ambiguous"
            for record in records
        )
        print(
            f"Discovered {len(records)} candidate record(s): "
            f"{model_candidates} model candidate(s), "
            f"{individual_aircraft} individual aircraft, "
            f"{ambiguous} ambiguous; catalog unchanged."
        )
        return 0

    if args.command == "cross-check":
        try:
            candidate_path = Path(args.input)
            with candidate_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
                raise ValueError("Candidate file must contain a JSON list of objects")
            metadata_records = load_metadata_csv(args.metadata)
            report = cross_check_candidates(
                payload,
                metadata_records,
                metadata_source=Path(args.metadata).name,
            )
            write_cross_check_report(report, args.output)
        except (OSError, ValueError, json.JSONDecodeError, MetadataError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        counts = report["summary"]["statuses"]
        print(
            f"Cross-checked {report['summary']['candidates']} candidate(s) against "
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
            f"usable unique model/type records: {len(imported)}; "
            f"skipped rows: {import_summary['rows_skipped']}; "
            f"records added: {merge_summary['added']}; "
            f"existing records enriched with OpenSky provenance: {merge_summary['enriched']}; "
            f"code conflicts requiring review: {import_summary['conflicting_codes']}."
        )
        if args.dry_run:
            print(f"Dry run only; catalog not changed. Target: {output_path}")
        else:
            print(f"Catalog updated: {output_path}")
        print(
            "Imported OpenSky records remain unverified; this command does not satisfy "
            "the independent-evidence promotion gate."
        )
        return 0

    if args.command == "promote":
        try:
            candidate_path = Path(args.input)
            with candidate_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
                raise ValueError("Candidate file must contain a JSON list of objects")
            accepted, rejected = verified_records(payload)
            if not accepted:
                print(
                    f"No verified records to promote; {len(rejected)} candidate(s) rejected. "
                    "Output was not changed.",
                    file=sys.stderr,
                )
                return 2
            save_aircraft(accepted, args.output)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Promoted {len(accepted)} verified record(s); rejected {len(rejected)} candidate(s).")
        if rejected:
            for item in rejected[:10]:
                print(f"  {item.get('source_id') or 'unknown'}: {'; '.join(item['issues'])}", file=sys.stderr)
            if len(rejected) > 10:
                print(f"  ... and {len(rejected) - 10} more rejected candidate(s).", file=sys.stderr)
        return 0

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
