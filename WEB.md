# Web explorer and automated refresh

The static HTML/CSS/JavaScript website is deployed through GitHub Pages. It supports model-catalog search and separate individual-aircraft lookup by registration, ICAO24 address, ICAO type code, or operator. Search results are expandable cards, keeping the current compact design while exposing available airframe metadata only when opened.

The **Refresh data** button reloads the latest published model catalog JSON. It does not trigger a workflow and does not need a GitHub token.

## First-time setup

1. In repository Settings → Pages, select **GitHub Actions** as the build and deployment source.
2. Merge the website and workflow changes into `main`.
3. Check the **Deploy aircraft explorer website** workflow for the deployment.
4. Open the Pages URL shown in the deployment summary.

A GitHub Pages site may be publicly accessible even when its source repository is private. Confirm repository plan and intended website visibility before enabling Pages.

## Weekly data refresh

The **Refresh OpenSky aircraft catalog and registry** workflow runs every Sunday at 06:00 UTC and also supports manual dispatch. It downloads the official OpenSky metadata CSV to temporary runner storage, runs the Python importer, validates the model JSON and registry shards, commits only `data/aircraft.json` when that catalog changes, and deploys the generated site.

The CSV is not committed to the repository. Individual-aircraft registry shards are generated as compressed JSON files for the Pages artifact only, avoiding repeated large binary files in Git history. The registry is split by the first two normalized characters of ICAO24 address, registration, type code, or operator. The website loads a shard on demand and caches it for the current page session.

## Search behavior

- **Aircraft catalog:** searches the model-level catalog and retains sorting and pagination.
- **Registration:** finds individual airframes by registration prefix.
- **ICAO24 address:** finds an individual aircraft by its six-character ICAO24 address prefix.
- **ICAO type code:** finds individual airframes by type-code prefix.
- **Operator:** finds individual airframes by operator-name prefix.
- Registry lookup requires at least two letters or digits. Search ignores case and removes punctuation for registry matching.
- Click a result card to expand it and view all available source fields, including registration, ICAO24, manufacturer, model, type code, serial/line number, operator/callsign, ownership, registration dates, build/first-flight dates, equipment flags, notes, source, and retrieval time.
- Imported records remain `imported_unverified`. Data availability does not imply independent verification.

## Local checks

Run the Python test suite from the repository root:

    python -m unittest discover -s tests -v

To generate the registry shards locally from an already downloaded CSV:

    python -m aircraft_explorer import-opensky --metadata /path/to/aircraftDatabase.csv --registry-dir /tmp/aircraft-registry

The command also updates the selected model catalog unless you use `--dry-run`. Keep local CSV files and generated shards out of commits unless their distribution and repository-size implications have been deliberately reviewed.
