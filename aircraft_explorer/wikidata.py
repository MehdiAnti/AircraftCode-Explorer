"""Wikidata SPARQL client and aircraft-record normalization."""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from typing import Any, Callable

from .core import deduplicate_records, normalize_record

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "AircraftCode-Explorer/0.1 (https://github.com/MehdiAnti/AircraftCode-Explorer)"
DEFAULT_TIMEOUT = 20.0
DEFAULT_RETRIES = 3

SPARQL_QUERY = """
SELECT DISTINCT ?item ?itemLabel ?itemDescription ?manufacturer ?manufacturerLabel ?icao
WHERE {
  ?item wdt:P239 ?icao.
  OPTIONAL { ?item wdt:P176 ?manufacturer. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?icao
LIMIT 5000
"""


class WikidataError(RuntimeError):
    """Raised when Wikidata cannot provide a valid aircraft catalog."""


def _binding_value(binding: dict[str, Any], key: str) -> str | None:
    entry = binding.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return value if isinstance(value, str) and value.strip() else None


def _request_json(
    *,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = 0.5,
    opener: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Request SPARQL JSON with a bounded retry count for transient errors."""
    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")
    if retries < 0:
        raise ValueError("retries cannot be negative")

    params = urlencode({"query": SPARQL_QUERY, "format": "json"})
    request = Request(
        f"{ENDPOINT}?{params}",
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": USER_AGENT,
        },
    )
    open_request = opener or urlopen
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            with open_request(request, timeout=timeout) as response:
                raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise WikidataError("Wikidata returned an unexpected JSON structure")
            return payload
        except HTTPError as exc:
            last_error = exc
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable or attempt >= retries:
                break
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                break
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WikidataError(f"Wikidata returned invalid JSON: {exc}") from exc

        sleep(retry_delay * (2 ** attempt))

    raise WikidataError(
        f"Wikidata request failed after {attempt + 1} attempt(s): {last_error}"
    ) from last_error


def parse_wikidata_response(
    payload: dict[str, Any],
    *,
    retrieved_at: str | None = None,
    diagnostics: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Convert SPARQL JSON bindings into catalog records with provenance."""
    try:
        bindings = payload["results"]["bindings"]
    except (KeyError, TypeError) as exc:
        raise WikidataError("Wikidata response is missing results.bindings") from exc

    if not isinstance(bindings, list):
        raise WikidataError("Wikidata results.bindings must be a list")

    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []
    skipped = 0

    for binding in bindings:
        if not isinstance(binding, dict):
            skipped += 1
            continue

        item_uri = _binding_value(binding, "item")
        if not item_uri:
            skipped += 1
            continue
        try:
            parsed_uri = urlsplit(item_uri)
        except ValueError:
            skipped += 1
            continue
        source_id = parsed_uri.path.rstrip("/").rsplit("/", 1)[-1]
        if (
            parsed_uri.scheme not in {"http", "https"}
            or parsed_uri.hostname not in {"wikidata.org", "www.wikidata.org"}
            or not parsed_uri.path.startswith("/entity/")
            or not source_id.startswith("Q")
            or not source_id[1:].isdigit()
        ):
            skipped += 1
            continue

        designator = _binding_value(binding, "icao")
        if not designator or not re.fullmatch(r"[A-Za-z0-9]{2,4}", designator.strip()):
            skipped += 1
            continue
        model = _binding_value(binding, "itemLabel")
        manufacturer = _binding_value(binding, "manufacturerLabel")
        description = _binding_value(binding, "itemDescription")

        record: dict[str, Any] = {
            "source": "Wikidata",
            "source_id": source_id,
            "source_url": f"https://www.wikidata.org/wiki/{source_id}",
            "source_retrieved_at": timestamp,
        }
        record["icao_type_designator"] = designator
        if model:
            record["model"] = model.strip()
        if manufacturer:
            record["manufacturer"] = manufacturer.strip()
        if description:
            record["description"] = description.strip()

        records.append(normalize_record(record))

    if diagnostics is not None and skipped:
        diagnostics.append(
            f"Skipped {skipped} malformed or incomplete Wikidata row(s)."
        )

    return sorted(
        deduplicate_records(records),
        key=lambda item: (
            (item.get("icao_type_designator") or "").casefold(),
            (item.get("manufacturer") or "").casefold(),
            (item.get("model") or "").casefold(),
        ),
    )


def fetch_wikidata_aircraft(
    *,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = 0.5,
    opener: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    diagnostics: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch candidate aircraft records that have a Wikidata ICAO designator."""
    payload = _request_json(
        timeout=timeout,
        retries=retries,
        retry_delay=retry_delay,
        opener=opener,
        sleep=sleep,
    )
    return parse_wikidata_response(payload, diagnostics=diagnostics)
