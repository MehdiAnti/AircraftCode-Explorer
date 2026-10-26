"""Core helpers for loading, saving, and searching the local aircraft catalog."""

from __future__ import annotations

import json
import os
import tempfile
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
