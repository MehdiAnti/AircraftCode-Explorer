# AircraftCode-Explorer

A small Python command-line tool for exploring aircraft by ICAO type designator, model, and manufacturer.

## Project status and roadmap

The project is developed in reviewable phases. See [ROADMAP.md](ROADMAP.md) for the full plan, current phase statuses, acceptance criteria, working rules, and completion log. Each phase is reviewed with the user before the next phase begins.

## Status

The initial implementation uses a local JSON catalog. Data refresh from Wikidata is planned for a later phase. Wikidata is community-maintained and is not a guarantee of complete or authoritative ICAO data.

## Requirements

- Python 3.10 or newer
- No third-party Python packages required for the basic CLI

## Usage

Run commands from the repository root:

```bash
python -m aircraft_explorer stats
python -m aircraft_explorer search C172
python -m aircraft_explorer search --manufacturer Cessna
```

The initial catalog lives at `data/aircraft.json`.

## Data format

Each aircraft record may include:

- `icao_type_designator`: type designator, when known
- `model`: aircraft model name
- `manufacturer`: manufacturer name
- `source`: provenance URL or source label
- `description`: optional notes

Unknown values should be omitted or set to `null`; the tool must not invent ICAO designators.

## Development

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Data and attribution

The planned refresh feature will query Wikidata. Data quality and coverage depend on the source and should be independently verified before operational use.
