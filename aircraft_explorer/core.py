"""Core helpers for loading, saving, and searching the local aircraft catalog."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "aircraft.json"
STRING_FIELDS = (
    "icao_type_designator",
    "model",
    "manufacturer",
    "description",
    "source",
    "source_id",
    "source_url",
    "source_retrieved_at",
    "verification_status",
    "candidate_kind",
)
SORT_FIELDS = {
    "manufacturer": "manufacturer",
    "model": "model",
    "icao": "icao_type_designator",
    "description": "description",
}


def _text(value: Any) -> str:
    """Return a safe, normalized string for comparisons."""
    if value is None:
        return ""
    return " ".join(str(value).casefold().split())


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize known text fields while preserving unknown source fields."""
    normalized = dict(record)
    for key in STRING_FIELDS:
        value = normalized.get(key)
        if isinstance(value, str):
            value = " ".join(value.split())
            if key == "icao_type_designator":
                value = value.upper()
            normalized[key] = value or None
    return normalized


def _deduplication_key(record: dict[str, Any]) -> tuple[str, ...] | None:
    """Prefer source identity; use a conservative complete-field fallback."""
    source_id = _text(record.get("source_id"))
    source = _text(record.get("source"))
    if source_id:
        return ("source", source, source_id)

    designator = _text(record.get("icao_type_designator"))
    model = _text(record.get("model"))
    manufacturer = _text(record.get("manufacturer"))
    if designator and model and manufacturer:
        return ("fallback", designator, model, manufacturer)
    return None


def deduplicate_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate deterministically and retain non-empty values from duplicates."""
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    result: list[dict[str, Any]] = []

    for original in records:
        record = normalize_record(original)
        key = _deduplication_key(record)
        if key is None:
            result.append(record)
            continue

        previous = unique.get(key)
        if previous is None:
            unique[key] = record
            result.append(record)
            continue

        for field, value in record.items():
            if (
                previous.get(field) is None or previous.get(field) == ""
            ) and value not in (None, ""):
                previous[field] = value

    return result


def load_aircraft(path: str | Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    """Load, validate, and normalize the basic shape of the aircraft JSON catalog."""
    data_path = Path(path)

    try:
        with data_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except FileNotFoundError:
        return []

    if not isinstance(payload, list):
        raise ValueError(f"Aircraft catalog must contain a JSON list: {data_path}")

    records: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Aircraft record at index {index} must be a JSON object")

        for key in STRING_FIELDS:
            value = item.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"Aircraft record at index {index}: {key} must be a string or null"
                )
        records.append(normalize_record(item))

    return deduplicate_records(records)


def save_aircraft(aircraft: Iterable[dict[str, Any]], path: str | Path) -> None:
    """Atomically replace a catalog file after normalizing and serializing it."""
    data_path = Path(path)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(deduplicate_records(aircraft), indent=2, ensure_ascii=False) + "\n"

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=data_path.parent,
            prefix=f".{data_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temp_path = Path(file.name)
            file.write(serialized)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, data_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def search_aircraft(
    aircraft: Iterable[dict[str, Any]],
    query: str = "",
    *,
    manufacturer: str = "",
    icao_type_designator: str = "",
    model: str = "",
    sort_by: str = "manufacturer",
    descending: bool = False,
) -> list[dict[str, Any]]:
    """Search records using case-insensitive substring matching and stable sorting.

    Missing values always sort last, including when descending order is selected.
    """
    if sort_by not in SORT_FIELDS:
        choices = ", ".join(SORT_FIELDS)
        raise ValueError(f"sort_by must be one of: {choices}")

    query_text = _text(query)
    manufacturer_text = _text(manufacturer)
    designator_text = _text(icao_type_designator)
    model_text = _text(model)

    results: list[dict[str, Any]] = []
    for original in aircraft:
        item = normalize_record(original)
        designator = _text(item.get("icao_type_designator"))
        model_name = _text(item.get("model"))
        maker = _text(item.get("manufacturer"))
        searchable = " ".join(
            value for value in (designator, model_name, maker, _text(item.get("description")))
            if value
        )

        if query_text and query_text not in searchable:
            continue
        if manufacturer_text and manufacturer_text not in maker:
            continue
        if designator_text and designator_text not in designator:
            continue
        if model_text and model_text not in model_name:
            continue
        results.append(dict(item))

    field = SORT_FIELDS[sort_by]
    results.sort(
        key=lambda item: (
            _text(item.get(field)),
            _text(item.get("manufacturer")),
            _text(item.get("model")),
            _text(item.get("icao_type_designator")),
        ),
        reverse=descending,
    )
    # A second stable sort keeps blank values last in both sort directions.
    results.sort(key=lambda item: not bool(_text(item.get(field))))
    return results


def catalog_stats(aircraft: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Return basic catalog counts."""
    records = list(aircraft)
    return {
        "aircraft": len(records),
        "with_icao_type_designator": sum(
            bool(_text(item.get("icao_type_designator"))) for item in records
        ),
        "manufacturers": len(
            {
                _text(item.get("manufacturer"))
                for item in records
                if _text(item.get("manufacturer"))
            }
        ),
    }


def catalog_status(
    aircraft: Iterable[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return catalog quality, source, and retrieval-freshness information.

    Timestamps are parsed as ISO 8601. Naive timestamps are treated as UTC;
    invalid non-empty timestamp strings are counted but never guessed or repaired.
    The optional clock makes age calculations deterministic in tests.
    """
    records = list(aircraft)
    with_designator = sum(
        bool(_text(item.get("icao_type_designator"))) for item in records
    )
    source_counts: dict[str, int] = {}
    parsed_timestamps: list[datetime] = []
    missing_timestamps = 0
    invalid_timestamps = 0

    for item in records:
        source_value = item.get("source")
        source_label = " ".join(source_value.split()) if isinstance(source_value, str) else ""
        if not source_label:
            source_label = "Unknown"
        source_key = source_label.casefold()
        if source_key in source_counts:
            source_counts[source_key] += 1
        else:
            source_counts[source_key] = 1

        timestamp_value = item.get("source_retrieved_at")
        if not isinstance(timestamp_value, str) or not timestamp_value.strip():
            missing_timestamps += 1
            continue

        timestamp_text = timestamp_value.strip()
        try:
            parsed = datetime.fromisoformat(
                timestamp_text[:-1] + "+00:00" if timestamp_text.endswith("Z") else timestamp_text
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed_timestamps.append(parsed.astimezone(timezone.utc))
        except ValueError:
            invalid_timestamps += 1

    # Keep a readable label while grouping source names case-insensitively.
    source_display: dict[str, str] = {}
    for item in records:
        source_value = item.get("source")
        source_label = " ".join(source_value.split()) if isinstance(source_value, str) else ""
        source_label = source_label or "Unknown"
        source_display.setdefault(source_label.casefold(), source_label)
    sources = {
        source_display[key]: source_counts[key]
        for key in sorted(source_counts)
    }

    latest = max(parsed_timestamps) if parsed_timestamps else None
    oldest = min(parsed_timestamps) if parsed_timestamps else None
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    current_time = current_time.astimezone(timezone.utc)

    return {
        "aircraft": len(records),
        "with_icao_type_designator": with_designator,
        "missing_icao_type_designator": len(records) - with_designator,
        "manufacturers": catalog_stats(records)["manufacturers"],
        "sources": sources,
        "with_retrieval_timestamp": len(parsed_timestamps),
        "missing_retrieval_timestamp": missing_timestamps,
        "invalid_retrieval_timestamp": invalid_timestamps,
        "oldest_retrieved_at": oldest.isoformat().replace("+00:00", "Z") if oldest else None,
        "latest_retrieved_at": latest.isoformat().replace("+00:00", "Z") if latest else None,
        "latest_retrieval_age_days": (
            round(max(0.0, (current_time - latest).total_seconds()) / 86400, 2)
            if latest else None
        ),
    }
