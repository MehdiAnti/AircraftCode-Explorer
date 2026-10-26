# AircraftCode-Explorer

AircraftCode-Explorer is a small Python command-line tool for searching a local aircraft catalog by ICAO type designator, model, manufacturer, or description. It can import local aircraft metadata, track provenance, report conflicts, and record manual verification based on independent source evidence.

Imported source data is not automatically verified. Review records against independent sources before relying on them operationally.

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

### `review`

Summarizes verification states and reports type codes associated with different model/manufacturer identities.

```bash
python -m aircraft_explorer review
python -m aircraft_explorer review --json
python -m aircraft_explorer review --output catalog-review.json
```

A conflict is a review flag, not proof that a record is wrong. Resolve conflicts against independent evidence before verifying a record.

### `verify`

After manually checking an independent source, attach its evidence to one catalog record and mark it verified.

```bash
python -m aircraft_explorer verify --model "Cessna 172 Skyhawk" --icao C172 --source-name "FAA Aircraft Registry" --source-url "https://www.faa.gov/aircraft" --retrieved-at "2026-10-27T12:00:00Z" --confirm
```

The `--confirm` flag confirms that you checked the source supports every populated factual field. The command requires an HTTPS URL and timestamp, rejects the same source used for the import, and refuses records with conflicting ICAO codes unless `--confirm-conflict` is supplied after manual conflict review. It records the evidence you provide; it cannot independently authenticate the cited page.

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

### `import-opensky`

Import a locally obtained OpenSky aircraft metadata CSV directly into the selected catalog, without a network request or a separate candidate workflow.

```bash
python -m aircraft_explorer import-opensky --metadata /path/to/aircraft.csv --dry-run
python -m aircraft_explorer import-opensky --metadata /path/to/aircraft.csv
```

- By default, the command merges into the selected catalog (normally `data/aircraft.json`). Use global `--data PATH` before the subcommand to choose a different catalog, or `--output PATH` to set the destination.
- `--dry-run` reports proposed counts without writing.
- Aircraft-level rows are grouped into unique manufacturer/model/type-code records; individual registrations are not copied.
- Exact matches retain existing fields and gain a `source_records` provenance entry. Conflicting records remain separate for review; no ICAO code is inferred.
- Imported records are marked `imported_unverified`; this does not make them verified.
- The command reads a local CSV only and never downloads it.

**Data-use caution:** confirm that the particular file and your intended use/redistribution are permitted before committing imported data to this public repository. This project does not bundle the CSV or automatically download it.

### `cross-check`

Compares the selected local catalog against a metadata CSV you obtained separately. It makes no network requests and does not modify the catalog.

```bash
python -m aircraft_explorer cross-check --metadata /path/to/aircraft-metadata.csv
python -m aircraft_explorer cross-check --input data/aircraft.json --metadata /path/to/aircraft-metadata.csv --output /tmp/cross-check.json
```

The report highlights corroborating matches, conflicts, multiple matches, and no-match records. A match is not verification evidence; inspect the source manually.

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
- `verification_status`: review state (for example, `imported_unverified` or `verified`)
- `field_evidence`: mapping of each populated factual field to an independent source name, HTTPS URL, and retrieval timestamp

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

The application does not infer or fabricate ICAO codes. Source labels and imported metadata are not independently verified facts.

## Development and tests

Run the standard-library test suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests use mocked independent source responses and do not need live network access. GitHub Actions runs the suite on Python 3.10, 3.11, 3.12, and 3.13 for pushes to `main` and pull requests.

Before submitting a change, run the test command above and review the output. See [ROADMAP.md](ROADMAP.md) for phase status and [RELEASE.md](RELEASE.md) for versioning and release guidance.

## Troubleshooting

- **`No matching aircraft found.`** The local catalog may be empty, or no record matches the supplied text and filters. Check `python -m aircraft_explorer stats` and the selected `--data` path.
- **`Aircraft catalog must contain a JSON list`** The catalog's top level must be a JSON array (`[]` or a list of record objects).
- **A record field must be a string or null.** One of the known fields contains a number, boolean, array, or object. Correct the JSON value and try again.

## License status

No project license has been selected or included yet. Until the repository owner confirms the intended license and adds the corresponding license file, do not assume that the code is offered under a particular open-source license. See [RELEASE.md](RELEASE.md) for the pre-release checklist.
