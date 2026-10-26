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
| 1 | Repository foundation and local catalog CLI | Complete; execution not yet independently verified |
| 2 | Unit tests and continuous integration | Verified — 14 tests passed on Python 3.10–3.13; awaiting user review |
| 3 | Wikidata data refresh | Implemented; CI verification in progress |
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

**Implemented:**
- `tests/test_core.py` covers loading, missing files, invalid JSON shapes/records, case-insensitive search, description search, filters, combined filters, no matches, and statistics.
- `.github/workflows/tests.yml` runs the standard-library unittest suite on Python 3.10–3.13 for pushes to `main`, pull requests, and manual dispatch.
- `README.md` documents the test command and links this roadmap.

**Acceptance criteria:**
- Tests cover successful loads, missing files, invalid top-level JSON shape, invalid records, search matching, filtering, and statistics.
- CI uses supported Python versions and runs without third-party runtime dependencies.
- Report the actual test result. If tests cannot be executed in the current environment, state that clearly.

**Verification results (2026-10-26):** GitHub Actions run [#3](https://github.com/MehdiAnti/AircraftCode-Explorer/actions/runs/40335663823) completed successfully for commit `9cdb7b47ef5643762c52d3e5e39b13e14a8ec2eb`. All four matrix jobs (Python 3.10, 3.11, 3.12, and 3.13) completed successfully. The Python 3.10 job log confirms `Ran 14 tests` and `OK`; the other three jobs also report the test step succeeded. The tests were run by GitHub Actions on the committed repository, not in this chat's local runtime.

**Status:** Implementation and CI verification complete. Awaiting user review/approval before Phase 3.

## Phase 3 — Wikidata data refresh

**Goal:** Provide an explicit command that fetches candidate aircraft records from Wikidata and writes a local catalog.

**Implemented:**
- `aircraft_explorer/wikidata.py` queries Wikidata SPARQL for entities with the P239 ICAO type designator property.
- The request has a 20-second default timeout, a descriptive User-Agent, bounded exponential backoff, and up to three retries for network errors and HTTP 429/5xx responses.
- The `update` CLI command accepts `--timeout`, `--retries` (0–5), `--allow-empty`, and global `--data`.
- Catalog output is serialized to a temporary file and atomically replaced only after a successful response and parse. Empty results are refused by default.
- Records retain Wikidata source name, entity ID, source URL, retrieval timestamp, labels, manufacturer, description, and the supplied designator.
- The parser deduplicates by Wikidata entity ID and rejects malformed designators rather than importing them.
- Mocked tests cover parsing/provenance, retry behavior, retry limits, input validation, successful update, network-failure preservation, and empty-result protection.
- `README.md` documents refresh usage and source limitations.

**Acceptance criteria:**
- The refresh command is separate from ordinary local searches.
- Network failures leave the existing catalog intact.
- Results include source provenance.
- Mocked tests do not depend on live network access.

**Verification status:** The first CI run exposed one malformed-designator fixture being accepted; the parser was tightened to reject it. The corrected CI run is in progress. Do not mark Phase 3 complete until the final GitHub Actions result is confirmed.

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
- **Phase 2:** Test suite, CI workflow, README roadmap link, and roadmap status update committed. GitHub Actions run #3 passed all 14 tests across Python 3.10–3.13; user approved Phase 3.
- **Phase 3:** Wikidata refresh, atomic catalog replacement, provenance, CLI options, mocked tests, and documentation committed. Initial CI exposed one parser validation failure; parser fix committed and verification is pending on GitHub Actions run #11.
