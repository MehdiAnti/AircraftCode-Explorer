# Web explorer and automated refresh

The static HTML/CSS/JavaScript website is deployed through GitHub Pages. It keeps model-level catalog data separate from individual-aircraft registry data, so registrations and operators never overwrite or conflict with model records.

## Data files

| Published path | Purpose |
| --- | --- |
| `data/aircraft.json` | Existing model/manufacturer/type-code catalog used by the website's catalog search and refresh button |
| `data/airframes.json.gz` | Gzip-compressed full individual-aircraft registry |
| `data/registry/` | Gzip-compressed search shards, grouped by lookup category and two-character prefix |

The website loads only `data/aircraft.json` for model-level catalog search. It does **not** download the full individual-aircraft registry on initial page load; individual-aircraft search fetches only the relevant compressed shard and caches it for the current page session. JavaScript decompresses each `.json.gz` shard using the browser's `DecompressionStream` API. The full compressed registry is also published for direct data access and download.

## Refresh behavior

The **Refresh data** button reloads the latest published model catalog JSON at `data/aircraft.json`. It does not trigger a workflow and does not need a GitHub token.

The **Refresh OpenSky aircraft catalog and registry** workflow is manual-only because the configured source is a fixed May 2024 snapshot. It downloads the source CSV to temporary runner storage, updates and validates the model catalog in `data/aircraft.json`, rebuilds the full compressed registry and compressed search shards in the workflow workspace, validates their contents and shard prefixes, commits the model catalog and compressed registry files, and deploys the generated site. Old generated files are removed before each refresh.

The source CSV and uncompressed registry copies are never committed. The compressed full registry and compressed search shards are tracked in Git and published to GitHub Pages. The workflow does not create or publish uncompressed JSON copies.

## Search behavior

- **Aircraft catalog:** searches model-level records and retains sorting and pagination.
- **Registration:** finds individual airframes by registration prefix.
- **ICAO24 address:** finds individual airframes by their six-character ICAO24 address prefix.
- **ICAO type code:** finds individual airframes by type-code prefix.
- **Operator:** finds individual airframes by operator-name prefix.
- Registry lookup requires at least two letters or digits. Search ignores case and removes punctuation for registry matching.
- Expand a result card to view available source fields, including registration, ICAO24, manufacturer, model, type code, serial/line number, operator/callsign, ownership, registration dates, build/first-flight dates, equipment flags, notes, source, and retrieval time.
- Imported records remain `imported_unverified`. Data availability does not imply independent verification.

## First-time setup

1. In repository Settings → Pages, select **GitHub Actions** as the build and deployment source.
2. Merge the website and workflow changes into `main`.
3. Check the **Deploy aircraft explorer website** workflow for the deployment.
4. Open the Pages URL shown in the deployment summary.

A GitHub Pages site may be publicly accessible even when its source repository is private. Confirm repository plan and intended website visibility before enabling Pages.

## Local checks

Run the Python test suite from the repository root:

    python -m unittest discover -s tests -v

To generate the registry locally from an already downloaded CSV:

    python -m aircraft_explorer import-opensky --metadata /path/to/aircraftDatabase.csv --registry-dir data/registry

The command writes compressed shards and `data/registry/aircraft-registry.json.gz`. The automated workflow moves the full compressed registry to the Pages artifact as `data/airframes.json.gz`. It does not generate plain JSON counterparts.

The command also updates the selected model catalog unless you use `--dry-run`. Keep local CSV files and generated shards out of commits unless their distribution and repository-size implications have been deliberately reviewed.
