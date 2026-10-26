# AircraftCode-Explorer

A small Python command-line tool for exploring aircraft by ICAO type designator, model, and manufacturer.

## Project status and roadmap

The project is developed in reviewable phases. See [ROADMAP.md](ROADMAP.md) for the full plan, current phase statuses, acceptance criteria, working rules, and completion log. Each phase is reviewed with the user before the next phase begins.

## Requirements

- Python 3.10 or newer
- No third-party Python packages required

## Usage

Run commands from the repository root:

```bash
python -m aircraft_explorer stats
python -m aircraft_explorer search C172
python -m aircraft_explorer search --manufacturer Cessna
```

### Refresh the local catalog

Run the refresh explicitly; ordinary searches do not access the network:

```bash
python -m aircraft_explorer update
```

Options:

- `--timeout 20`: request timeout in seconds (default 20).
- `--retries 3`: retries after transient errors (default 3; maximum 5).
- `--allow-empty`: explicitly allow an empty result to replace the catalog. By default, an empty response leaves the existing catalog untouched.
- Global `--data PATH`: use a different catalog file, for example `python -m aircraft_explorer --data /tmp/aircraft.json update`.

The update command queries Wikidata's SPARQL endpoint for items with an ICAO aircraft type designator. Requests use a timeout, a descriptive User-Agent, and bounded exponential backoff for transient network errors and HTTP 429/5xx responses. The catalog is replaced atomically only after a valid response has been parsed.

## Data format and provenance

Records may include:

- `icao_type_designator`: designator supplied by Wikidata (not independently verified by this tool)
- `model`: item label
- `manufacturer`: manufacturer label, when available
- `description`: Wikidata description, when available
- `source`: source name
- `source_id`: stable Wikidata entity identifier
- `source_url`: link to the source entity
- `source_retrieved_at`: UTC timestamp for when the response was retrieved

Wikidata is community-maintained and is not a guarantee of complete or authoritative ICAO data. This initial query includes only items that have the Wikidata ICAO type designator property; aircraft without that property are not returned. Verify designators against an authoritative source before operational use.

## Development and tests

Run the tests without network access:

```bash
python -m unittest discover -s tests -v
```

The Wikidata client and update command are tested with mocked responses; tests do not query the live SPARQL endpoint.
