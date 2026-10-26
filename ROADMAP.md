# Project Roadmap

This file is the source of truth for project phases, current progress, and phase-by-phase approval. Keep it updated as work is completed so future contributors and AI coding sessions can recognize the project state without relying on chat history.

## Project goal

Build a maintainable aircraft catalog and explorer that supports searching by ICAO type designator, model, and manufacturer. Start with a simple Python command-line interface and a local JSON catalog, then add a repeatable data refresh workflow.

## Working rules

- Work only in `MehdiAnti/AircraftCode-Explorer`.
- Implement one phase at a time.
- After each phase, report files changed, checks actually run, known limitations, and the relevant commit(s).
- Stop and ask the user to review and approve before starting the next phase.
- Never claim tests or workflows passed unless they were actually run and the result was observed.
- Prefer Python's standard library unless a dependency has a clear benefit.
- Never invent ICAO type designators. Preserve source/provenance information and distinguish source data from independently verified facts.
- Treat Wikidata as a useful community-maintained source, not as a complete or authoritative ICAO register.

## Phase status

| Phase | Name | Status |
|---|---|---|
| 1 | Repository foundation and local catalog CLI | Complete |
| 2 | Unit tests and continuous integration | In progress |
| 3 | Wikidata data refresh | Planned |
| 4 | Data quality, normalization, and provenance | Planned |
| 5 | Documentation and release readiness | Planned |
| 6 | Optional usability improvements | Planned |

## Phase 1 — Repository foundation and local catalog CLI

**Goal:** Establish the initial package, data format, and command-line interface.

Deliverables:
- `README.md` with setup and usage instructions.
- `.gitignore` for Python artifacts.
- `aircraft_explorer/` Python package.
- JSON catalog at `data/aircraft.json`.
- Search by general text, manufacturer, model, and ICAO type designator.
- Basic catalog statistics.

**Acceptance criteria:**
- The package can be invoked with `python -m aircraft_explorer`.
- Search and statistics operate on the local JSON catalog.
- Missing catalog files return an empty catalog; malformed data is reported clearly.

**Status:** Complete. The files were committed to the `main` branch. Execution has not yet been independently verified.

## Phase 2 — Unit tests and continuous integration

**Goal:** Add repeatable automated checks before introducing network-dependent data fetching.

Deliverables:
- Unit tests for catalog loading, validation, search filters, and statistics.
- GitHub Actions workflow that runs tests on pushes and pull requests.
- A documented local test command.

**Acceptance criteria:**
- Tests cover successful loads, missing files, invalid top-level JSON shape, invalid records, search matching, filtering, and statistics.
- CI uses a supported Python version and runs without third-party runtime dependencies.
- Report the actual test result. If tests cannot be executed in the current environment, state that clearly.

**Status:** In progress.

## Phase 3 — Wikidata data refresh

**Goal:** Provide an explicit command that fetches candidate aircraft records from Wikidata and writes a local catalog.

Planned deliverables:
- A separate data-source module for the SPARQL query and HTTP request.
- A CLI command such as `python -m aircraft_explorer update`.
- Request timeout, sensible user-agent, bounded retries for transient failures, and clear error messages.
- Parsing that tolerates optional/missing fields and avoids inventing designators.
- Safe output handling: do not overwrite the current catalog with an empty or clearly failed result unless the user explicitly requests it.
- Unit tests using mocked responses; tests must not depend on live network access.

**Acceptance criteria:**
- The refresh command is separate from ordinary local searches.
- Network failures leave the existing catalog intact.
- Results include provenance/source information where available.
- The project documents source coverage and limitations.

## Phase 4 — Data quality, normalization, and provenance

**Goal:** Make refreshed records easier to trust and maintain.

Planned deliverables:
- Normalize whitespace and comparison keys consistently.
- Deduplicate records using stable source identifiers where available, with cautious fallback rules.
- Preserve source URLs and source identifiers in each record.
- Validate expected field types and report skipped/ambiguous records.
- Add fixtures for duplicates, missing values, and unusual source responses.

**Acceptance criteria:**
- Duplicate handling is deterministic and tested.
- Records without a verified ICAO type designator remain searchable by model/manufacturer without a fabricated code.
- Documentation explains what is sourced, inferred, or unknown.

## Phase 5 — Documentation and release readiness

**Goal:** Make the project understandable and usable by a new contributor.

Planned deliverables:
- Complete install, usage, update, troubleshooting, and test instructions.
- Example commands and example JSON records.
- License decision and license file, only after the intended license is confirmed.
- Versioning/release notes guidance.
- Review of error messages and CLI help text.

**Acceptance criteria:**
- A new user can follow the README from a clean checkout.
- All documented commands match the implemented CLI.
- License and data-source attribution are explicit.

## Phase 6 — Optional usability improvements

**Goal:** Consider enhancements after the core catalog and refresh flow are reliable.

Possible items, prioritized with user approval:
- CSV export.
- More structured filters and sorting.
- Catalog freshness/status command.
- Optional desktop or web interface.
- Packaging for installation as a command.
- Additional source adapters, if licensing and data quality permit.

**Acceptance criteria:**
- Each enhancement is proposed before implementation.
- The project remains usable without optional features.
- Dependencies and maintenance costs are justified.

## Phase completion log

- **Phase 1:** Foundation files committed. Local execution not yet verified.
- **Phase 2:** Pending completion and user review.
