"""Import locally obtained OpenSky aircraft metadata CSV files."""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENSKY_SOURCE_URL = "https://opensky-network.org/data/aircraft"


class OpenSkyImportError(ValueError):
    """Raised when an OpenSky metadata CSV cannot be interpreted safely."""


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _normalized(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value or None


_MODEL_HEADERS = ("model", "aircraftmodel", "aircrafttype", "typename", "type")
_MANUFACTURER_HEADERS = ("manufacturer", "manufacturername", "maker", "builder")
_CODE_HEADERS = ("typecode", "icaotypecode", "icaotypedesignator", "icao", "icaoaircrafttype")


def import_opensky_csv(
    path: str | Path, *, retrieved_at: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Group aircraft-level CSV rows into unique model/manufacturer/type-code records."""
    source_path = Path(path)
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                raise OpenSkyImportError("OpenSky metadata CSV is empty or has no header row")
            headers = {_header_key(h): h for h in reader.fieldnames if isinstance(h, str)}
            model_header = next((headers[k] for k in _MODEL_HEADERS if k in headers), None)
            manufacturer_header = next((headers[k] for k in _MANUFACTURER_HEADERS if k in headers), None)
            code_header = next((headers[k] for k in _CODE_HEADERS if k in headers), None)
            if model_header is None and code_header is None:
                raise OpenSkyImportError("OpenSky CSV needs a recognizable model or ICAO type-code column")

            grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
            rows_read = rows_skipped = 0
            for row in reader:
                if not isinstance(row, dict):
                    rows_skipped += 1
                    continue
                rows_read += 1
                model = _clean(row.get(model_header)) if model_header else None
                manufacturer = _clean(row.get(manufacturer_header)) if manufacturer_header else None
                code = _clean(row.get(code_header)) if code_header else None
                code = code.upper() if code else None
                if not model and not code:
                    rows_skipped += 1
                    continue
                key = (_normalized(manufacturer), _normalized(model), _normalized(code))
                grouped.setdefault(key, {
                    "icao_type_designator": code,
                    "model": model,
                    "manufacturer": manufacturer,
                    "description": None,
                    "source": "OpenSky Aircraft Metadata",
                    "source_id": None,
                    "source_url": OPENSKY_SOURCE_URL,
                    "source_retrieved_at": timestamp,
                    "verification_status": "imported_unverified",
                })
            records = list(grouped.values())
    except UnicodeDecodeError as exc:
        raise OpenSkyImportError("OpenSky metadata CSV must be UTF-8 encoded") from exc
    except csv.Error as exc:
        raise OpenSkyImportError(f"Could not parse metadata CSV: {exc}") from exc

    models_by_code: dict[str, set[tuple[str, str]]] = {}
    for record in records:
        code = _normalized(record.get("icao_type_designator"))
        if code:
            models_by_code.setdefault(code, set()).add(
                (_normalized(record.get("model")), _normalized(record.get("manufacturer")))
            )
    return records, {
        "rows_read": rows_read,
        "rows_skipped": rows_skipped,
        "unique_records": len(records),
        "conflicting_codes": sum(len(values) > 1 for values in models_by_code.values()),
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
    existing_records: list[dict[str, Any]], imported_records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Merge exact matches while retaining imported source provenance; preserve conflicts."""
    merged = [dict(record) for record in existing_records]
    index: dict[tuple[str, str, str], int] = {}
    for i, record in enumerate(merged):
        key = _record_key(record)
        if any(key):
            index.setdefault(key, i)
    added = enriched = 0
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
        source_name = imported.get("source")
        source_url = imported.get("source_url")
        retrieved_at = imported.get("source_retrieved_at")
        if existing.get("source") == source_name and existing.get("source_url") == source_url:
            if existing.get("source_retrieved_at") != retrieved_at:
                existing["source_retrieved_at"] = retrieved_at
                enriched += 1
            continue
        history = existing.get("source_records")
        if not isinstance(history, list):
            history = []
        match = next((item for item in history if isinstance(item, dict) and item.get("source") == source_name and item.get("source_url") == source_url), None)
        if match is None:
            history.append({"source": source_name, "source_url": source_url, "source_retrieved_at": retrieved_at})
            existing["source_records"] = history
            enriched += 1
        elif match.get("source_retrieved_at") != retrieved_at:
            match["source_retrieved_at"] = retrieved_at
            existing["source_records"] = history
            enriched += 1
    return merged, {"added": added, "enriched": enriched}
