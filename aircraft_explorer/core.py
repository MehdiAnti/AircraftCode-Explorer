"""Core helpers for loading, saving, and searching the local aircraft catalog."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "aircraft.json"


def load_aircraft(path: str | Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    """Load and validate the basic shape of the aircraft JSON catalog."""
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

        record = dict(item)
        for key in ("icao_type_designator", "model", "manufacturer"):
            value = record.get(key)
            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"Aircraft record at index {index}: {key} must be a string or null"
                )
        records.append(record)

    return records


def save_aircraft(aircraft: Iterable[dict[str, Any]], path: str | Path) -> None:
    """Atomically replace a catalog file after serializing the complete payload."""
    data_path = Path(path)
    data_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(list(aircraft), indent=2, ensure_ascii=False) + "\n"

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


def _text(value: Any) -> str:
    """Return a safe, normalized string for comparisons."""
    if value is None:
        return ""
    return " ".join(str(value).casefold().split())


def search_aircraft(
    aircraft: Iterable[dict[str, Any]],
    query: str = "",
    *,
    manufacturer: str = "",
    icao_type_designator: str = "",
    model: str = "",
) -> list[dict[str, Any]]:
    """Search records using case-insensitive substring matching."""
    query_text = _text(query)
    manufacturer_text = _text(manufacturer)
    designator_text = _text(icao_type_designator)
    model_text = _text(model)

    results: list[dict[str, Any]] = []
    for item in aircraft:
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

    return sorted(
        results,
        key=lambda item: (
            _text(item.get("manufacturer")),
            _text(item.get("model")),
            _text(item.get("icao_type_designator")),
        ),
    )


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
