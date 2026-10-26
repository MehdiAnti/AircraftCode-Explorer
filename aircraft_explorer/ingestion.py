"""Validation and promotion helpers for independently verified aircraft data."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

FACTUAL_FIELDS = (
    "model",
    "manufacturer",
    "description",
    "icao_type_designator",
)


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(
            value.strip()[:-1] + "+00:00" if value.strip().endswith("Z") else value.strip()
        )
    except ValueError:
        return False
    return True


def verification_issues(record: dict[str, Any]) -> list[str]:
    """Return reasons a candidate is not safe to mark verified in the main catalog.

    Every populated factual field must have independent source evidence
    with a valid HTTPS URL and retrieval timestamp. A missing ICAO code is
    allowed; an unverified non-empty code is not.
    """
    issues: list[str] = []
    if record.get("verification_status") != "verified":
        issues.append("verification_status must be 'verified'")

    model = record.get("model")
    if not isinstance(model, str) or not model.strip():
        issues.append("model is required before a record can be verified")

    evidence = record.get("field_evidence")
    if not isinstance(evidence, dict):
        evidence = {}

    for field in FACTUAL_FIELDS:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        entries = evidence.get(field)
        if not isinstance(entries, list):
            issues.append(f"{field} has no field-level evidence")
            continue

        verified = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source_name = entry.get("source_name")
            source_url = entry.get("source_url")
            retrieved_at = entry.get("retrieved_at")
            if (
                isinstance(source_name, str)
                and source_name.strip()
                and source_name.strip().casefold() != "opensky aircraft metadata"
                and source_name.strip().casefold() != str(record.get("source") or "").strip().casefold()
                and isinstance(source_url, str)
                and source_url.startswith("https://")
                and _valid_timestamp(retrieved_at)
            ):
                verified = True
                break
        if not verified:
            issues.append(
                f"{field} needs independent evidence from a source other than the record's import source, with an HTTPS URL and retrieval timestamp"
            )
    return issues


def verified_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split records into verified records and rejected records with reasons."""
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for original in records:
        record = dict(original)
        issues = verification_issues(record)
        if issues:
            rejected.append({"source_id": record.get("source_id"), "issues": issues})
            continue
        record.pop("candidate_kind", None)
        record["verification_status"] = "verified"
        accepted.append(record)
    return accepted, rejected


def verify_record(record: dict[str, Any], *, source_name: str, source_url: str, retrieved_at: str) -> dict[str, Any]:
    """Mark a record verified only after explicit manual source review."""
    verified = dict(record)
    evidence_entry = {
        "source_name": source_name.strip(),
        "source_url": source_url.strip(),
        "retrieved_at": retrieved_at.strip(),
    }
    verified["verification_status"] = "verified"
    current_evidence = verified.get("field_evidence")
    evidence = {
        field: list(entries) if isinstance(entries, list) else []
        for field, entries in current_evidence.items()
    } if isinstance(current_evidence, dict) else {}
    for field in FACTUAL_FIELDS:
        value = verified.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        entries = evidence.setdefault(field, [])
        if evidence_entry not in entries:
            entries.append(dict(evidence_entry))
    verified["field_evidence"] = evidence
    issues = verification_issues(verified)
    if issues:
        raise ValueError("Record cannot be marked verified: " + "; ".join(issues))
    return verified
