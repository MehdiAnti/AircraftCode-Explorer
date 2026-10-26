# AircraftCode-Explorer

A small Python command-line tool for exploring aircraft by ICAO type designator, model, and manufacturer.

## Status

The project is being built in phases. The initial implementation uses a local JSON catalog; data refresh from Wikidata will be added in a later phase. Wikidata is a community-maintained source, so its records are not a guarantee of official or complete ICAO data.

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
