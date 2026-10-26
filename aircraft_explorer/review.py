"""Catalog review reports for verification status and ICAO code conflicts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def _normal(value: Any) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def catalog_review(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize verification states and report codes tied to different identities."""
    catalog = [dict(record) for record in records]
    statuses: dict[str, int] = {}
    sources: dict[str, int] = {}
    by_code: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for record in catalog:
        status = str(record.get("verification_status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        source = str(record.get("source") or "Unknown")
        sources[source] = sources.get(source, 0) + 1
        code = str(record.get("icao_type_designator") or "").strip().upper()
        if code:
            identity = (_normal(record.get("model")), _normal(record.get("manufacturer")))
            by_code.setdefault(code, {}).setdefault(identity, {
                "model": record.get("model"),
                "manufacturer": record.get("manufacturer"),
                "verification_status": record.get("verification_status") or "unknown",
            })
    conflicts = []
    for code, identities in sorted(by_code.items()):
        if len(identities) > 1:
            conflicts.append({
                "icao_type_designator": code,
                "records": sorted(identities.values(), key=lambda item: (_normal(item.get("manufacturer")), _normal(item.get("model")))),
                "review_required": True,
            })
    return {
        "report_type": "aircraft_catalog_review",
        "records": len(catalog),
        "verification_statuses": dict(sorted(statuses.items())),
        "sources": dict(sorted(sources.items())),
        "conflicting_icao_type_codes": len(conflicts),
        "conflicts": conflicts,
        "note": "Conflicts are review flags, not proof of error. Imported metadata remains unverified until an independent source is manually checked.",
    }


def write_review_report(report: dict[str, Any], path: str | Path) -> None:
    """Write a review report as UTF-8 JSON."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(output_path.name + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(report, file, indent=2, ensure_ascii=False)
            file.write("\n")
        temporary_path.replace(output_path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
