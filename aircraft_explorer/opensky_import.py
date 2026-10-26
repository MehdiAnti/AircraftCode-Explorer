"""Import locally obtained OpenSky aircraft metadata CSV files.

The importer does not download data and does not treat imported metadata as verified.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENSKY_SOURCE_URL = "https://opensky-network.org/data/aircraft"


class OpenSkyImportError(ValueError):
    """Raised when an OpenSky metadata CSV cannot be safely interpreted."""


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _normalized(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


_MODEL_HEADERS = ("model", "aircraftmodel", "aircrafttype", "typename", "type")
_MANUFACTURER_HEADERS = ("manufacturer", "manufacturername", "manufacturer_name", "maker", "builder")
_CODE_HEADERS = (
    "typecode",
    "icaotypecode",
    "icaotypedesignator",
    "icao",
    "icaoaircrafttype",
)


def import_opensky_csv(
    path: str | Path,
    *,
    retrieved_at: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert aircraft-level rows into unique model/manufacturer/type-code records."""
    source_path = Path(path)
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise OpenSkyImportError("OpenSky metadata CSV is empty or has no header row")
            headers = {
                _header_key(header): header
                for header in reader.fieldnames
                if isinstance(header, str)
            }
            model_header = next((headers[key] for key in _MODEL_HEADERS if key in headers), None)
            manufacturer_header = next(
                (headers[key] for key in _MANUFACTURER_HEADERS if key in headers), None
            )
            code_header = next((headers[key] for key in _CODE_HEADERS if key in headers), None)
            if model_header is None and code_header is None:
                raise OpenSkyImportError(
                    "OpenSky CSV needs a recognizable model or ICAO type-code column"
                )

            groups: dict[tuple[str, str, str], dict[str, Any]] = {}
            rows_read = 0
            rows_skipped = 0
            for row in reader:
                if not isinstance(row, dict):
                    rows_skipped += 1
                    continue
                rows_read += 1
                model = _clean(row.get(model_header)) if model_header else None
                manufacturer = (
                    _clean(row.get(manufacturer_header)) if manufacturer_header else None
                )
                code = _clean(row.get(code_header)) if code_header else None
                if code:
                    code = code.upper()
                if not model and not code:
                    rows_skipped += 1
                    continue
                key = (_normalized(manufacturer), _normalized(model), _normalized(code))
                if key not in groups:
                    groups[key] = {
                        "icao_type_designator": code,
                        "model": model,
                        "manufacturer": manufacturer,
                        "description": None,
                        "source": "OpenSky Aircraft Metadata",
                        "source_id": None,
                        "source_url": OPENSKY_SOURCE_URL,
                        "source_retrieved_at": timestamp,
                        "verification_status": "imported_unverified",
                    }

            records = list(groups.values())
    except UnicodeDecodeError as exc:
        raise OpenSkyImportError("OpenSky metadata CSV must be UTF-8 encoded") from exc
    except csv.Error as exc:
        raise OpenSkyImportError(f"Could not parse OpenSky metadata CSV: {exc}") from exc

    code_models: dict[str, set[tuple[str, str]]] = {}
    for record in records:
        code = _normalized(record.get("icao_type_designator"))
        if code:
            code_models.setdefault(code, set()).add(
                (_normalized(record.get("model")), _normalized(record.get("manufacturer")))
            )
    conflicting_codes = sum(len(models) > 1 for models in code_models.values())
    return records, {
        "rows_read": rows_read,
        "rows_skipped": rows_skipped,
        "unique_records": len(records),
        "conflicting_codes": conflicting_codes,
        "source_file": source_path.name,
        "source_retrieved_at": timestamp,
    }


def _record_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _normalized(record.get("icao_type_designator")),
        _normalized(record.get("model")),
        _normalized(record.get("manufacturer")),
    )


def merge_opensky_records(
    existing_records: list[dict[str, Any]],
    imported_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Merge exact model/code/manufacturer matches and retain source provenance.

    Conflicting records are retained separately instead of overwriting existing facts.
    """
    merged = [dict(record) for record in existing_records]
    index: dict[tuple[str, str, str], int] = {}
    for position, record in enumerate(merged):
        key = _record_key(record)
        if any(key):
            index.setdefault(key, position)

    added = 0
    enriched = 0
    for imported in imported_records:
        key = _record_key(imported)
        position = index.get(key) if any(key) else None
        if position is None:
            merged.append(dict(imported))
            if any(key):
                index[key] = len(merged) - 1
            added += 1
            continue

        existing = merged[position]
        source_entry = {
            "source": imported.get("source"),
            "source_url": imported.get("source_url"),
            "source_retrieved_at": imported.get("source_retrieved_at"),
        }
        source_records = existing.get("source_records")
        if not isinstance(source_records, list):
            source_records = []
        if source_entry not in source_records:
            source_records.append(source_entry)
            existing["source_records"] = source_records
            enriched += 1

    return merged, {"added": added, "enriched": enriched}
