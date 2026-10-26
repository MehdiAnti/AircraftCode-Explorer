"""Import locally obtained OpenSky aircraft metadata CSV files."""

from __future__ import annotations

import csv
import gzip
import json
import os
import re
import tempfile
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



_REGISTRY_FIELDS = {
    "icao24": "icao24",
    "registration": "registration",
    "manufacturericao": "manufacturer_icao",
    "manufacturername": "manufacturer",
    "model": "model",
    "typecode": "icao_type_designator",
    "serialnumber": "serial_number",
    "linenumber": "line_number",
    "icaoaircrafttype": "icao_aircraft_type",
    "operator": "operator",
    "operatorcallsign": "operator_callsign",
    "operatoricao": "operator_icao",
    "operatoriata": "operator_iata",
    "owner": "owner",
    "testreg": "test_registration",
    "registered": "registered",
    "reguntil": "registration_until",
    "status": "status",
    "built": "built",
    "firstflightdate": "first_flight_date",
    "seatconfiguration": "seat_configuration",
    "engines": "engines",
    "modes": "modes",
    "adsb": "adsb",
    "acars": "acars",
    "notes": "notes",
    "categorydescription": "category_description",
}


def write_opensky_registry_csv(
    csv_path: str | Path,
    output_path: str | Path,
    *,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Stream individual OpenSky airframes to a compact gzip-compressed JSON array."""
    source_path = Path(csv_path)
    destination = Path(output_path)
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    rows_read = records_written = rows_skipped = 0
    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames:
                raise OpenSkyImportError("OpenSky metadata CSV is empty or has no header row")
            headers = {_header_key(h): h for h in reader.fieldnames if isinstance(h, str)}
            if not any(key in headers for key in ("registration", "icao24")):
                raise OpenSkyImportError("OpenSky CSV needs a registration or icao24 column")
            with gzip.open(temporary, "wt", encoding="utf-8", newline="") as output:
                output.write("[")
                first = True
                for row in reader:
                    if not isinstance(row, dict):
                        rows_skipped += 1
                        continue
                    rows_read += 1
                    record = {
                        target: _clean(row.get(headers[source]))
                        for source, target in _REGISTRY_FIELDS.items()
                        if source in headers
                    }
                    if not any(record.values()):
                        rows_skipped += 1
                        continue
                    record["source"] = "OpenSky Aircraft Metadata"
                    record["source_url"] = OPENSKY_SOURCE_URL
                    record["source_retrieved_at"] = timestamp
                    record["verification_status"] = "imported_unverified"
                    if not first:
                        output.write(",")
                    json.dump(record, output, ensure_ascii=False, separators=(",", ":"))
                    first = False
                    records_written += 1
                output.write("]")
        os.replace(temporary, destination)
    except UnicodeDecodeError as exc:
        temporary.unlink(missing_ok=True)
        raise OpenSkyImportError("OpenSky metadata CSV must be UTF-8 encoded") from exc
    except csv.Error as exc:
        temporary.unlink(missing_ok=True)
        raise OpenSkyImportError(f"Could not parse metadata CSV: {exc}") from exc
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "rows_read": rows_read,
        "rows_skipped": rows_skipped,
        "registry_records": records_written,
        "output_file": destination.name,
        "source_retrieved_at": timestamp,
    }



def write_opensky_registry_shards(
    csv_path: str | Path,
    output_dir: str | Path,
    *,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    """Stream airframe records into compressed, field-specific first-character shards."""
    source_path = Path(csv_path)
    destination = Path(output_dir)
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    fields = {
        "registration": "registration",
        "icao_type_designator": "typecode",
        "operator": "operator",
    }
    field_dirs = {name: destination / name for name in fields}
    for directory in field_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)

    writers: dict[tuple[str, str], Any] = {}
    temporary_paths: dict[tuple[str, str], Path] = {}
    final_paths: dict[tuple[str, str], Path] = {}
    counts: dict[str, dict[str, int]] = {name: {} for name in fields}
    rows_read = rows_skipped = 0
    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames:
                raise OpenSkyImportError("OpenSky metadata CSV is empty or has no header row")
            headers = {_header_key(h): h for h in reader.fieldnames if isinstance(h, str)}
            if not any(key in headers for key in ("registration", "icao24")):
                raise OpenSkyImportError("OpenSky CSV needs a registration or icao24 column")
            mapped_headers = {
                target: headers[source_key]
                for source_key, target in _REGISTRY_FIELDS.items()
                if source_key in headers
            }
            for row in reader:
                if not isinstance(row, dict):
                    rows_skipped += 1
                    continue
                rows_read += 1
                record = {
                    target: _clean(row.get(header))
                    for target, header in mapped_headers.items()
                }
                if not any(record.values()):
                    rows_skipped += 1
                    continue
                record["source"] = "OpenSky Aircraft Metadata"
                record["source_url"] = OPENSKY_SOURCE_URL
                record["source_retrieved_at"] = timestamp
                record["verification_status"] = "imported_unverified"
                for field, directory in field_dirs.items():
                    value = record.get(field)
                    if not value:
                        continue
                    first = re.sub(r"[^a-z0-9]", "", value.casefold())[:1] or "_"
                    key = (field, first)
                    if key not in writers:
                        final_path = directory / f"{first}.json.gz"
                        temp_path = directory / f".{first}.json.gz.tmp"
                        temporary_paths[key] = temp_path
                        final_paths[key] = final_path
                        writer = gzip.open(temp_path, "wt", encoding="utf-8", newline="")
                        writer.write("[")
                        writers[key] = writer
                        counts[field][first] = 0
                    writer = writers[key]
                    if counts[field][first]:
                        writer.write(",")
                    json.dump(record, writer, ensure_ascii=False, separators=(",", ":"))
                    counts[field][first] += 1
            for writer in writers.values():
                writer.write("]")
                writer.close()
            writers.clear()
        for key, temp_path in temporary_paths.items():
            os.replace(temp_path, final_paths[key])
        for field, directory in field_dirs.items():
            valid_names = {path.name for key, path in final_paths.items() if key[0] == field}
            for old_path in directory.glob("*.json.gz"):
                if old_path.name not in valid_names:
                    old_path.unlink()
    except (UnicodeDecodeError, csv.Error) as exc:
        for writer in writers.values():
            writer.close()
        for path in temporary_paths.values():
            path.unlink(missing_ok=True)
        if isinstance(exc, UnicodeDecodeError):
            raise OpenSkyImportError("OpenSky metadata CSV must be UTF-8 encoded") from exc
        raise OpenSkyImportError(f"Could not parse metadata CSV: {exc}") from exc
    except OSError:
        for writer in writers.values():
            writer.close()
        for path in temporary_paths.values():
            path.unlink(missing_ok=True)
        raise

    return {
        "rows_read": rows_read,
        "rows_skipped": rows_skipped,
        "registry_records": max((sum(values.values()) for values in counts.values()), default=0),
        "shards": {field: dict(sorted(values.items())) for field, values in counts.items()},
        "source_retrieved_at": timestamp,
    }
