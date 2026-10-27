# Aircraft Explorer

A lightweight, static aircraft-search website built with HTML, CSS, and JavaScript, backed by a model catalog and a compressed individual-aircraft registry.

## The website

The browser lets you:

- Search aircraft models by model name, manufacturer, description, or ICAO type designator.
- Look up individual aircraft by registration, ICAO24 address, ICAO type code, or operator.
- Sort and paginate model results, view catalog statistics, and expand records for available aircraft details.
- Search large registry data efficiently: the browser fetches only the relevant compressed `.json.gz` shard for an individual-aircraft lookup.

The **Refresh data** button reloads the published model catalog. It does not start a GitHub Actions workflow.

### Data files

- `data/aircraft.json` — model-level catalog used by the website.
- `data/airframes.json.gz` — full compressed individual-aircraft registry.
- `data/registry/` — compressed lookup shards for ICAO24, registration, type code, and operator.

Registry JSON is kept compressed to avoid storing duplicate plain-text copies. The website decompresses requested shards in the browser using the built-in `DecompressionStream` API.

### Data freshness and verification

The refresh workflow currently uses a **fixed May 2024 OpenSky metadata snapshot**. It is not a live feed. The workflow is run manually from **GitHub → Actions → Refresh OpenSky aircraft catalog and registry → Run workflow**. It rebuilds and validates the catalog and compressed registry, then deploys the website through GitHub Pages.

Imported source data is not automatically verified. Treat missing fields as unknown and independently check records before relying on them operationally.

### Publish the website

1. Open repository **Settings → Pages** and select **GitHub Actions** as the build and deployment source.
2. Run the **Deploy aircraft explorer website** workflow, or merge the website changes into `main` if they are still in a pull request.
3. Open the Pages URL shown in the deployment summary.

Check the repository plan and intended visibility before enabling Pages: a published site may be publicly accessible even if its source repository is private.

## Project documentation

- [Web explorer and refresh details](WEB.md)
- [Roadmap](ROADMAP.md)
- [Release guidance](RELEASE.md)

<details>
<summary><strong>Optional: Python CLI, imports, and developer commands</strong></summary>

The Python tools support maintainers who import, inspect, compare, or verify catalog data. You do not need to run Python just to use the deployed website.

### Requirements

- Python 3.10 or newer
- Git, if cloning the repository
- No third-party Python packages are required

### Run locally

```bash
git clone https://github.com/MehdiAnti/AircraftCode-Explorer.git
cd AircraftCode-Explorer
python -m aircraft_explorer stats
python -m aircraft_explorer status
```

Run commands from the repository root. The project can be run directly from the checkout; there is no package installation step.

### Common commands

```bash
# Search the local model catalog
python -m aircraft_explorer search C172
python -m aircraft_explorer search --manufacturer Cessna
python -m aircraft_explorer search --model "Skyhawk"
python -m aircraft_explorer search --icao C172

# Export the catalog as CSV
python -m aircraft_explorer export
python -m aircraft_explorer export --output aircraft.csv

# Review possible identity/type-code conflicts
python -m aircraft_explorer review

# Check catalog quality and provenance
python -m aircraft_explorer status

# Run tests
python -m unittest discover -s tests -v
```

### Importing OpenSky metadata

The importer reads a CSV already available on your machine; it does not download data itself.

```bash
python -m aircraft_explorer import-opensky --metadata /path/to/aircraft.csv --dry-run
python -m aircraft_explorer import-opensky --metadata /path/to/aircraft.csv --registry-dir /tmp/aircraft-registry
```

- The model catalog is written to `data/aircraft.json` by default; use `--data PATH` before the subcommand or `--output PATH` to choose another destination.
- `--dry-run` reports proposed counts without writing.
- `--registry-dir PATH` also writes the full registry as `aircraft-registry.json.gz` and compressed lookup shards.
- Individual aircraft stay separate from model-level records. Conflicting records are retained for review; ICAO codes are not inferred.
- Imported records are marked `imported_unverified`. Verification requires independent evidence and explicit manual confirmation.

### Other data-review commands

```bash
python -m aircraft_explorer verify --model "Cessna 172 Skyhawk" --icao C172 --source-name "FAA Aircraft Registry" --source-url "https://www.faa.gov/aircraft" --retrieved-at "2026-10-27T12:00:00Z" --confirm

python -m aircraft_explorer cross-check --metadata /path/to/aircraft-metadata.csv
```

`verify` records evidence you supply; it cannot independently authenticate the cited page. `cross-check` compares local records with a separately obtained CSV and does not modify the catalog.

For the complete command options and data-field details, see the Python package help and [WEB.md](WEB.md).

</details>

## License

The project code is licensed under the [MIT License](LICENSE). Unless a separate notice says otherwise, this applies to the project's original code and accompanying documentation—not to third-party datasets.

### Aircraft data

The aircraft registry is generated from an OpenSky aircraft metadata snapshot. The OpenSky aircraft database page states that the database is unlicensed and outside its general Terms of Use. Permission to redistribute the source data and generated registry through this repository and the public website has not been confirmed. The MIT code license does not grant rights to that data; see [ROADMAP.md](ROADMAP.md) for the outstanding data-permission question.
