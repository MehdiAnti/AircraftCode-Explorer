"""CSV export helpers for the local aircraft catalog."""

from __future__ import annotations

import csv
import json
from typing import Any, Iterable, TextIO

from .core import STRING_FIELDS


def _csv_value(value: Any) -> str:
    """Convert a record value to a CSV-safe scalar representation."""
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def write_csv(aircraft: Iterable[dict[str, Any]], output: TextIO) -> None:
    """Write aircraft records to a text stream using a stable column order.

    Known catalog fields appear first. Additional source fields are included as
    extra columns, and missing values are represented by empty cells.
    """
    records = [dict(record) for record in aircraft]
    extra_fields = sorted(
        {key for record in records for key in record if key not in STRING_FIELDS}
    )
    fieldnames = [*STRING_FIELDS, *extra_fields]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        writer.writerow({key: _csv_value(record.get(key)) for key in fieldnames})
