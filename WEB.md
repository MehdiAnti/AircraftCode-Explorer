# Web explorer and automated refresh

The static HTML/CSS/JavaScript website is deployed through GitHub Pages. It keeps model-level catalog data separate from individual-aircraft registry data, so registrations and operators never overwrite or conflict with model records.

## Data files

| Published path | Purpose |
| --- | --- |
| `data/aircraft.json` | Existing model/manufacturer/type-code catalog used by the website's catalog search and refresh button |
| `data/airframes.json.gz` | Tracked gzip-compressed full individual-aircraft registry |
| `data/registry/` | Tracked compressed search shards for fast lookup by ICAO24, registration, type code, and operator |
| Published `data/airframes.json` | Uncompressed full registry generated in the Pages artifact for direct access and download |

The website loads only `data/aircraft.json` for model-level catalog search. It does **not** download the full individual-aircraft JSON on initial page load; individual-aircraft search fetches only the relevant compressed shard and caches it for the current page session. The full airframe JSON files are published for direct data access and download.

## Refresh behavior

The **Refresh data** button reloads the latest published model catalog JSON at `data/aircraft.json`. It does not trigger a workflow and does not need a GitHub token.

The **Refresh OpenSky aircraft catalog and registry** workflow runs on the first day of each month at 06:00 UTC and also supports manual dispatch. It downloads the OpenSky metadata CSV to temporary runner storage, updates and validates the model catalog in `data/aircraft.json`, rebuilds the individual-aircraft registry and search shards directly under `data/`, validates the outputs, commits changed catalog and registry files, and deploys the generated site. Old search shards are removed before each refresh.

The source CSV and uncompressed full registry are not committed. The compressed full registry and search shards are committed under `data/`. The workflow stops before committing if the compressed registry reaches 90 MiB, leaving a margin below GitHub's 100 MB per-file limit.

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

The command also writes `data/registry/aircraft-registry.json.gz`; move that file to `data/airframes.json.gz` to match the automated workflow layout.

The command also updates the selected model catalog unless you use `--dry-run`. Keep local CSV files and generated shards out of commits unless their distribution and repository-size implications have been deliberately reviewed.
