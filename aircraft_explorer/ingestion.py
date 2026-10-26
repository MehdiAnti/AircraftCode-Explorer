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
    """Return reasons a candidate is not safe to promote into the main catalog.

    Every populated factual field must have at least one non-Wikidata evidence
    entry with a valid HTTPS URL and retrieval timestamp. A missing ICAO code is
    allowed; an unverified non-empty code is not.
    """
    issues: list[str] = []
    if record.get("verification_status") != "verified":
        issues.append("verification_status must be 'verified'")

    classification = record.get("candidate_classification")
    if "candidate_classification" in record and classification != "model_candidate":
        issues.append(
            f"candidate classification is '{classification}'; review and classify it as a model candidate before promotion"
        )

    model = record.get("model")
    if not isinstance(model, str) or not model.strip():
        issues.append("model is required before a candidate can be promoted")

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
                and source_name.strip().casefold() != "wikidata"
                and isinstance(source_url, str)
                and source_url.startswith("https://")
                and _valid_timestamp(retrieved_at)
            ):
                verified = True
                break
        if not verified:
            issues.append(
                f"{field} needs independent non-Wikidata evidence with an HTTPS URL and retrieval timestamp"
            )
    return issues


def verified_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split candidates into promotable records and rejected records with reasons."""
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
