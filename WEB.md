# Web Explorer and Data Refresh

## Overview

Aircraft Explorer is a static HTML/CSS/JavaScript website published through GitHub Pages. It separates model-level catalog records from individual-aircraft records so a registration or operator does not overwrite a model record.

## Website behavior

- **Aircraft catalog:** search model-level records by model name, manufacturer, description, or ICAO type designator. Catalog results support sorting and pagination.
- **Registration:** search individual aircraft by registration prefix.
- **ICAO24:** search individual aircraft by ICAO24 address prefix.
- **ICAO type code:** search individual aircraft by type-code prefix.
- **Operator:** search individual aircraft by operator-name prefix.
- Registry searches require at least two letters or digits, ignore case, and normalize punctuation for matching.
- Expand a result to inspect the source fields available for that record, such as registration, ICAO24, manufacturer, model, type code, serial/line number, operator/callsign, ownership, dates, equipment flags, notes, source, and retrieval metadata.

The browser loads the model catalog from `data/aircraft.json`. It does not fetch the full individual-aircraft registry on initial page load. Individual-aircraft search fetches only relevant compressed lookup shards and caches loaded shard data for the page session. The browser decompresses gzip data using the built-in `DecompressionStream` API.

## Published data layout

| Published path | Purpose |
| --- | --- |
| `data/aircraft.json` | Model/manufacturer/type-code catalog used for catalog search and the website's Refresh data button |
| `data/airframes.json.gz` | Full gzip-compressed individual-aircraft registry |
| `data/registry/icao24/*.json.gz` | Lookup shards indexed by ICAO24 |
| `data/registry/registration/*.json.gz` | Lookup shards indexed by registration |
| `data/registry/typecode/*.json.gz` | Lookup shards indexed by ICAO type code |
| `data/registry/operator/*.json.gz` | Lookup shards indexed by operator |

The full registry and lookup shards are kept compressed to avoid duplicate plain-text registry copies. `data/aircraft.json` intentionally remains ordinary JSON because it is the smaller model catalog consumed directly by the website.

## Data source and freshness

Both workflows currently use this fixed OpenSky metadata snapshot:

`https://s3.opensky-network.org/data-samples/metadata/aircraft-database-complete-2024-05.csv`

This is a **May 2024 snapshot**, not a live feed. Running a workflow again rebuilds outputs from that same source; it does not make the source data more recent.

Imported records are not automatically independently verified. Treat absent fields as unknown and check important facts against authoritative evidence before relying on them.

## Refresh behavior

### Website Refresh data button

The **Refresh data** button reloads the published model catalog at `data/aircraft.json`. It does not start GitHub Actions and does not require a GitHub token.

### Refresh OpenSky aircraft catalog and registry workflow

This workflow is manual-only. To run it:

1. Open the repository's **Actions** tab.
2. Select **Refresh OpenSky aircraft catalog and registry**.
3. Choose **Run workflow** on the `main` branch.
4. Wait for the tests, source download, import, generated-data validation, commit step, and Pages deployment to finish.
5. Inspect the workflow summary and deployed website.

The workflow downloads the CSV to temporary runner storage, rebuilds `data/aircraft.json`, the full `data/airframes.json.gz` registry, and the compressed lookup shards, validates the outputs, commits changed data files, and prepares the site for deployment. The workflow is configured to reject unexpected uncompressed files in the registry output.

### Deploy aircraft explorer website workflow

The Pages workflow deploys the static application and generates compressed registry data for the Pages artifact using the configured source snapshot. It runs on relevant pushes to `main` and can also be dispatched manually.

Check the actual Actions run before assuming a workflow succeeded. A workflow definition or successful commit alone does not prove that the live Pages site is working.

## First-time Pages setup

1. Open repository **Settings → Pages**.
2. Set the build and deployment source to **GitHub Actions**.
3. Run the **Deploy aircraft explorer website** workflow or merge the relevant website/workflow changes into `main`.
4. Open the Pages URL shown in the successful deployment summary.

Confirm the repository plan and intended site visibility before enabling Pages: the published website may be publicly accessible even when the source repository is private.

## Local maintenance and checks

Python is needed for repository maintenance and data import, not for ordinary use of the deployed website. From the repository root, run tests with:

```bash
python -m unittest discover -s tests -v
```

To generate catalog and registry outputs from a CSV already downloaded locally:

```bash
python -m aircraft_explorer import-opensky \
  --metadata /path/to/aircraft-database-complete-2024-05.csv \
  --output data/aircraft.json \
  --registry-dir data/registry
```

The importer writes the full registry as `aircraft-registry.json.gz` inside the selected registry directory, along with the compressed lookup shards. The refresh workflow moves that full gzip file to `data/airframes.json.gz`. Do not add plain JSON registry copies or the source CSV to Git unless their distribution and repository-size implications have been deliberately reviewed.
