"""Local CSV cross-checking for aircraft discovery candidates.

This module never downloads third-party datasets and never treats a CSV match as
independent verification. It produces a review report only.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class MetadataError(ValueError):
    """Raised when a local metadata CSV cannot be interpreted safely."""


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _normalize_model(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _normalize_code(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", "", value).upper()


_MODEL_HEADERS = ("model", "aircraftmodel", "aircrafttype", "typename", "type")
_CODE_HEADERS = ("typecode", "icaotypecode", "icao", "icaotypedesignator", "icaoaircrafttype")


def load_metadata_csv(path: str | Path) -> list[dict[str, str | None]]:
    """Read a user-supplied CSV and map common header variants to model/type code."""
    source_path = Path(path)
    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise MetadataError("Metadata CSV is empty or has no header row")
            headers = {
                _header_key(header): header
                for header in reader.fieldnames
                if isinstance(header, str)
            }
            model_header = next((headers[key] for key in _MODEL_HEADERS if key in headers), None)
            code_header = next((headers[key] for key in _CODE_HEADERS if key in headers), None)
            if model_header is None and code_header is None:
                raise MetadataError(
                    "Metadata CSV needs a recognizable model or ICAO type-code column"
                )

            records: list[dict[str, str | None]] = []
            for row in reader:
                if not isinstance(row, dict):
                    continue
                model = row.get(model_header) if model_header else None
                code = row.get(code_header) if code_header else None
                model = model.strip() if isinstance(model, str) and model.strip() else None
                code = code.strip().upper() if isinstance(code, str) and code.strip() else None
                if model or code:
                    records.append({"model": model, "icao_type_designator": code})
            return records
    except UnicodeDecodeError as exc:
        raise MetadataError("Metadata CSV must be UTF-8 encoded") from exc
    except csv.Error as exc:
        raise MetadataError(f"Could not parse metadata CSV: {exc}") from exc


def _candidate_matches(
    candidate: dict[str, Any], metadata: dict[str, str | None]
) -> tuple[list[str], list[str]]:
    candidate_model = _normalize_model(candidate.get("model"))
    candidate_code = _normalize_code(candidate.get("icao_type_designator"))
    metadata_model = _normalize_model(metadata.get("model"))
    metadata_code = _normalize_code(metadata.get("icao_type_designator"))
    matched_fields: list[str] = []
    conflicting_fields: list[str] = []

    if candidate_model and metadata_model and candidate_model == metadata_model:
        matched_fields.append("model")
    if candidate_code and metadata_code:
        if candidate_code == metadata_code:
            matched_fields.append("icao_type_designator")
        else:
            conflicting_fields.append("icao_type_designator")
    if candidate_model and metadata_model and candidate_model != metadata_model:
        # Model differences are only a conflict when the designator is the same,
        # avoiding noisy conflicts from unrelated rows in a large CSV.
        if candidate_code and metadata_code and candidate_code == metadata_code:
            conflicting_fields.append("model")
    return matched_fields, conflicting_fields


def cross_check_candidates(
    candidates: Iterable[dict[str, Any]],
    metadata_records: Iterable[dict[str, str | None]],
    *,
    metadata_source: str,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Build a conservative report; a match is never a verification decision."""
    candidate_list = list(candidates)
    metadata_list = list(metadata_records)
    checked_timestamp = checked_at or datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    for candidate in candidate_list:
        if not isinstance(candidate, dict):
            continue
        model_key = _normalize_model(candidate.get("model"))
        code_key = _normalize_code(candidate.get("icao_type_designator"))
        code_rows = [
            row for row in metadata_list
            if code_key and _normalize_code(row.get("icao_type_designator")) == code_key
        ]
        model_rows = [
            row for row in metadata_list
            if model_key and _normalize_model(row.get("model")) == model_key
        ]
        related_rows: list[dict[str, str | None]] = []
        for row in code_rows + model_rows:
            if row not in related_rows:
                related_rows.append(row)

        matched_fields: set[str] = set()
        conflicting_fields: set[str] = set()
        for row in related_rows:
            matched, conflicts = _candidate_matches(candidate, row)
            matched_fields.update(matched)
            conflicting_fields.update(conflicts)

        if not related_rows:
            status = "no_match"
        elif len(related_rows) > 1:
            status = "multiple_matches"
        elif conflicting_fields:
            status = "conflict"
        elif (
            "model" in matched_fields
            and "icao_type_designator" in matched_fields
        ):
            status = "corroborated"
        elif "model" in matched_fields:
            status = "model_match_code_unknown"
        elif "icao_type_designator" in matched_fields:
            status = "code_match_model_unconfirmed"
        else:
            status = "conflict"

        results.append({
            "source_id": candidate.get("source_id"),
            "model": candidate.get("model"),
            "icao_type_designator": candidate.get("icao_type_designator"),
            "candidate_classification": candidate.get("candidate_classification"),
            "status": status,
            "matched_fields": sorted(matched_fields),
            "conflicting_fields": sorted(conflicting_fields),
            "metadata_matches": related_rows,
            "review_required": True,
        })

    statuses: dict[str, int] = {}
    for result in results:
        status = result["status"]
        statuses[status] = statuses.get(status, 0) + 1

    return {
        "report_type": "local_metadata_cross_check",
        "metadata_source": metadata_source,
        "checked_at": checked_timestamp,
        "note": (
            "Comparison only: results are not verification evidence and do not "
            "authorize promotion. Review the source and dataset terms manually."
        ),
        "summary": {
            "candidates": len(results),
            "metadata_rows": len(metadata_list),
            "statuses": dict(sorted(statuses.items())),
        },
        "results": results,
    }


def write_cross_check_report(report: dict[str, Any], path: str | Path) -> None:
    """Write a JSON review report to a separate user-selected path."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(output_path.name + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(report, file, indent=2, ensure_ascii=False)
            file.write("\n")
        temporary_path.replace(output_path)
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
