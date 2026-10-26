# AircraftCode-Explorer

AircraftCode-Explorer is a small Python command-line tool for searching a local aircraft catalog by ICAO type designator, model, manufacturer, or description. It can discover broad aircraft candidates from Wikidata, track field-level verification evidence, and promote only independently supported records into a separate catalog.

> **Data caution:** Wikidata is community-maintained and is not an authoritative ICAO register. This tool does not independently verify designators or infer missing codes. Verify data against an authoritative source before operational use.

## Requirements

- Python 3.10 or newer
- Git, if you are cloning the repository
- No third-party Python packages are required

## Get started

Clone the repository and change into its directory:

```bash
git clone https://github.com/MehdiAnti/AircraftCode-Explorer.git
cd AircraftCode-Explorer
```

Run commands from the repository root. There is no package installation step yet; the project can be run directly from the checkout.

Check basic catalog statistics and the more detailed quality/freshness status:

```bash
python -m aircraft_explorer stats
python -m aircraft_explorer status
```

Search the local catalog:

```bash
python -m aircraft_explorer search C172
python -m aircraft_explorer search --manufacturer Cessna
python -m aircraft_explorer search --model "Skyhawk"
python -m aircraft_explorer search --icao C172
python -m aircraft_explorer search --sort-by model
python -m aircraft_explorer search --sort-by icao --descending
```

Export the local catalog as CSV, either to the terminal or to a file:

```bash
python -m aircraft_explorer export
python -m aircraft_explorer export --output aircraft.csv
```

The CSV export includes the known catalog fields in a stable order, followed by any additional source-specific fields. Missing values are empty cells; nested values in extra fields are JSON-encoded. CSV quoting and embedded commas/newlines are handled by Python's standard CSV library.

The current checked-in catalog may be empty. An empty catalog is valid during development, so searches may return no results until data is added or refreshed.

## Command reference

### Global option

- `--data PATH`: read or write a catalog at a different path. Put this option **before** the subcommand.

For example:

```bash
python -m aircraft_explorer --data /tmp/aircraft.json stats
python -m aircraft_explorer --data /tmp/aircraft.json search C172
python -m aircraft_explorer --data /tmp/aircraft.json update
```

### `search`

Searches the local JSON catalog only; it does not make network requests.

```bash
python -m aircraft_explorer search [QUERY] [--manufacturer NAME] [--model NAME] [--icao CODE] [--json]
```

- `QUERY`: optional case-insensitive substring searched across designator, model, manufacturer, and description.
- `--manufacturer NAME`: restrict results to matching manufacturer text.
- `--model NAME`: restrict results to matching model text.
- `--icao CODE`: restrict results to matching ICAO type designator text.
- `--sort-by FIELD`: sort by `manufacturer` (default), `model`, `icao`, or `description`.
- `--descending`: reverse the selected sort order. Records with a missing sort value remain last.
- `--json`: print results as JSON instead of the human-readable list.

When multiple filters are supplied, all supplied filters must match. Missing designators do not prevent a record from being searched by model, manufacturer, or description.

### `export`

Writes the local catalog as CSV. By default, CSV is written to standard output; use `--output PATH` to write a file. The output path is created or overwritten, so choose it carefully.

```bash
python -m aircraft_explorer export
python -m aircraft_explorer export --output aircraft.csv
```

The export uses only the local catalog and makes no network requests. Known fields appear first in a stable order; any additional fields present in records are included as extra columns. Missing values are represented by empty cells, and nested extra-field values are encoded as JSON text. An empty catalog still produces a CSV header.

### `stats`

Shows the number of records, records with a designator, and distinct non-empty manufacturers.

```bash
python -m aircraft_explorer stats
python -m aircraft_explorer stats --json
```

### `status`

Reports catalog quality and provenance without making network requests:

- Total records, records with/missing ICAO designators, and distinct manufacturers.
- Record counts by source, with missing source labels grouped as `Unknown`.
- Counts of valid, missing, and invalid retrieval timestamps.
- Oldest and latest valid retrieval timestamps in UTC, plus the age in days of the latest timestamp.

Retrieval timestamps are metadata supplied by the source. If none are valid, freshness is reported as unknown rather than inferred. A timestamp without a timezone is interpreted as UTC; malformed timestamps are counted as invalid and excluded from freshness calculations.

```bash
python -m aircraft_explorer status
python -m aircraft_explorer status --json
```

### `discover`

Discovers broad aircraft candidates, including entities with and without an ICAO designator, and writes them to a separate candidate JSON file. It does not modify `data/aircraft.json`.

```bash
python -m aircraft_explorer discover
python -m aircraft_explorer discover --output /tmp/aircraft-candidates.json
```

Discovery results are explicitly marked `verification_status: "discovered"` and classified as `model_candidate`, `individual_aircraft`, or `ambiguous`. Classification uses Wikidata class labels, descriptions, and identifier-shaped labels to flag likely serial numbers and registrations, and generic descriptions such as "aircraft" remain ambiguous. These are conservative heuristics, not proof of identity: review uncertain records against independent sources. All classes remain in `data/candidates.json` with classification reasons, while promotion blocks records classified as individual aircraft or ambiguous. The trusted `data/aircraft.json` catalog is not changed by discovery.

### `import-opensky`

Import a locally obtained OpenSky aircraft metadata CSV into the selected catalog. Unlike `discover` and `promote`, this command does not query Wikidata and does not require candidate verification metadata.

```bash
python -m aircraft_explorer import-opensky --metadata /path/to/aircraft.csv --dry-run
python -m aircraft_explorer import-opensky --metadata /path/to/aircraft.csv
```

- By default, the command merges into the selected catalog (normally `data/aircraft.json`). Use the global `--data PATH` option before the subcommand to select another catalog, or `--output PATH` to select the destination explicitly.
- `--dry-run` prints the proposed counts without writing the catalog.
- Aircraft-level rows are grouped into unique manufacturer/model/type-code records. Individual registrations are not copied into the catalog.
- Exact matches are retained and gain an additional `source_records` provenance entry. Conflicting records are preserved separately and reported for review; no ICAO designator is inferred.
- Imported records use `verification_status: "imported_unverified"`. This import is not independent verification and does not make records eligible for `promote`.
- The command reads a local CSV only; it does not download data.

**Data-use caution:** OpenSky's aircraft database page says the database is not up to date and is unlicensed, with no guarantees. Confirm that your intended use and redistribution of the particular file are permitted before committing imported records to a public repository. This project does not bundle the source CSV or automatically download it.

### `cross-check`

Compares the discovery candidate JSON against an aircraft metadata CSV that you obtained separately. It makes no network requests, requires no API key, and does not modify the trusted catalog or the input files.

```bash
python -m aircraft_explorer cross-check --metadata /path/to/aircraft-metadata.csv
python -m aircraft_explorer cross-check --input data/candidates.json --metadata /path/to/aircraft-metadata.csv --output /tmp/cross-check.json
```

The report marks candidates as `corroborated`, `model_match_code_unknown`, `code_match_model_unconfirmed`, `conflict`, `multiple_matches`, or `no_match`. Matching is conservative: normalized model labels and ICAO type designators are compared when available; registration/serial identifiers are not treated as aircraft model names. The report retains matching rows and the conflicting fields for manual review.

**Important:** a cross-check result is not a verified record and does not add evidence to `field_evidence` or enable promotion. OpenSky's aircraft metadata is described by OpenSky as unlicensed, potentially stale, and provided without guarantees. Check the dataset's current terms and permitted use before obtaining or using it. Do not commit or redistribute the dataset; provide a local CSV path yourself. The report records the CSV filename, not a dataset retrieval timestamp, because the tool cannot infer when the file was downloaded.

### `promote`

Validates candidate evidence and writes only records marked `verified` to an output catalog. Every populated model, manufacturer, description, or ICAO designator must have field-level evidence from a source other than Wikidata, with an HTTPS URL and retrieval timestamp. Missing ICAO designators are allowed when the other populated fields are supported.

```bash
python -m aircraft_explorer promote --input data/candidates.json --output data/verified-aircraft.json
```

Promotion defaults to `data/verified-aircraft.json`, not the main catalog. It refuses to write if no records pass validation. The current tool validates evidence metadata and does not independently crawl or authenticate the cited source; reviewers must check that each source actually supports its field.

### `update`

Refreshes the local catalog explicitly from Wikidata. Ordinary `search` and `stats` commands never access the network.

```bash
python -m aircraft_explorer update
python -m aircraft_explorer update --timeout 30 --retries 2
```

- `--timeout SECONDS`: request timeout; defaults to 20 seconds and must be greater than zero.
- `--retries COUNT`: retry attempts for transient failures; defaults to 3 and accepts values from 0 through 5.
- `--allow-empty`: permit an empty result to replace the current catalog. Use this only when that replacement is intentional.

The updater queries Wikidata's SPARQL endpoint for items with the ICAO aircraft type designator property. Requests use a descriptive User-Agent, a timeout, and bounded exponential backoff for network errors and HTTP 429/5xx responses. Malformed or incomplete rows are skipped and summarized in a warning. A successful result is written through a temporary file and atomically replaces the target catalog. By default, a response with zero usable records is refused, leaving the existing catalog untouched.

**Back up any hand-maintained catalog before running `update`:** a successful update replaces the target file with the fetched result; it does not merge it with the previous catalog.

## Data format and provenance

The catalog file is `data/aircraft.json` by default and contains a JSON list of record objects. Known fields are strings or `null`:

- `icao_type_designator`: designator supplied by the source; not independently verified by this tool
- `model`: source item label
- `manufacturer`: manufacturer label, when available
- `description`: source description, when available
- `source`: source name
- `source_id`: stable identifier assigned by the source
- `source_url`: URL for the source entity
- `source_retrieved_at`: UTC retrieval timestamp
- `verification_status`: discovery/verification state (for example, `discovered` or `verified`)
- `field_evidence`: mapping of factual fields to source name, HTTPS URL, and retrieval timestamp; Wikidata-only evidence is not sufficient for promotion
- `candidate_classification`: discovery triage result (`model_candidate`, `individual_aircraft`, or `ambiguous`)
- `classification_reasons`: reasons for the discovery classification

An illustrative schema-only record is shown below. Its placeholder values are not real aircraft data and should not be copied into the catalog as a factual record:

```json
[
  {
    "icao_type_designator": null,
    "model": "Example model (placeholder only)",
    "manufacturer": null,
    "description": null,
    "source": "example-source",
    "source_id": "example-id",
    "source_url": "https://example.org/entity/example-id",
    "source_retrieved_at": null
  }
]
```

The loader normalizes whitespace in known text fields and uppercases designators. It validates the top-level list, record objects, and known field types. Records with the same source identity are deduplicated; a conservative fallback is used only when designator, model, and manufacturer are all present. Missing values remain unknown. Unknown source-specific fields are preserved.

The legacy `update` command only returns items that have the Wikidata ICAO type designator property. The separate `discover` command also searches aircraft entities without that property and writes candidates separately. Model, manufacturer, and description values are source labels, not independently verified facts. The application does not infer or fabricate ICAO codes.

## Development and tests

Run the standard-library test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests use mocked Wikidata responses and do not need live network access. GitHub Actions runs the suite on Python 3.10, 3.11, 3.12, and 3.13 for pushes to `main` and pull requests.

Before submitting a change, run the test command above and review the output. See [ROADMAP.md](ROADMAP.md) for phase status and [RELEASE.md](RELEASE.md) for versioning and release guidance.

## Troubleshooting

- **`No matching aircraft found.`** The local catalog may be empty, or no record matches the supplied text and filters. Check `python -m aircraft_explorer stats` and the selected `--data` path.
- **`Aircraft catalog must contain a JSON list`** The catalog's top level must be a JSON array (`[]` or a list of record objects).
- **A record field must be a string or null.** One of the known fields contains a number, boolean, array, or object. Correct the JSON value and try again.
- **`Wikidata returned zero usable records`** The updater intentionally protects the existing catalog. Check connectivity and the upstream response first. Only pass `--allow-empty` if replacing the catalog with an empty list is intended.
- **Network or HTTP errors during update.** The updater retries transient failures a limited number of times. Retry later if the endpoint is unavailable; the existing catalog is not replaced when fetching or parsing fails.
- **An update replaced local records.** The update command refreshes the target catalog rather than merging it. Restore a backup if needed, or use a separate file with `--data PATH` when testing a refresh.

## License status

No project license has been selected or included yet. Until the repository owner confirms the intended license and adds the corresponding license file, do not assume that the code is offered under a particular open-source license. See [RELEASE.md](RELEASE.md) for the pre-release checklist.
