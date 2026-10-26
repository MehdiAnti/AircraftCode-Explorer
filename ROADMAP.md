# Project Roadmap

This file is the source of truth for project phases, current progress, and phase-by-phase approval. Keep it updated so future contributors and AI coding sessions can recognize the project state without relying on chat history.

## Project goal

Build a maintainable aircraft catalog and explorer that supports searching by ICAO type designator, model, and manufacturer. Start with a simple Python command-line interface and a local JSON catalog, then add a repeatable data refresh workflow.

## Working rules

- Work only in `MehdiAnti/AircraftCode-Explorer`.
- Implement one phase at a time, on a dedicated branch.
- Group each phase into one pull request for review; do not commit phase changes directly to `main`.
- After each phase, report files changed, checks actually run, known limitations, and the pull request.
- Stop and ask the user to review and approve before starting the next phase.
- Never claim tests or workflows passed unless they were actually run and the result was observed.
- Prefer Python's standard library unless a dependency has a clear benefit.
- Never invent ICAO type designators. Preserve source/provenance information and distinguish source data from independently verified facts.
- Treat Wikidata as a useful community-maintained source, not as a complete or authoritative ICAO register.
- Do not select a project license or create a license file without the repository owner's confirmation.

## Phase status

| Phase | Name | Status |
|---|---|---|
| 1 | Repository foundation and local catalog CLI | Complete; execution not yet independently verified |
| 2 | Unit tests and continuous integration | Verified — 14 tests passed on Python 3.10–3.13; user review status previously recorded |
| 3 | Wikidata data refresh | Complete — verified and approved by user |
| 4 | Data quality, normalization, and provenance | Complete — verified and approved by user |
| 5 | Documentation and release readiness | Complete — PR #1 merged; CI status should be checked separately |
| 6.1–6.2 | CSV export, search, and sorting | Complete — PR #2 merged |
| 6.3 | Catalog status and freshness | Complete — PR #3 merged |
| 7 | Broad aircraft discovery, field-level verification, and safe promotion | Complete — PR #4 merged; classification refinements merged in PR #5 |\n| 8 | Local metadata cross-check and conflict reporting | Implemented in review PR; no API, automatic download, or catalog mutation |

## Phase 1 — Repository foundation and local catalog CLI

**Goal:** Establish the initial package, data format, and command-line interface.

**Deliverables:** `README.md`, `.gitignore`, `aircraft_explorer/`, `data/aircraft.json`, search by text/manufacturer/model/designator, and basic statistics.

**Acceptance criteria:** The module can be invoked with `python -m aircraft_explorer`; search and statistics operate on the local JSON catalog; missing catalog files return an empty catalog and malformed data is reported clearly.

**Status:** Complete. The files were committed to `main`; execution has not been independently verified in this chat.

## Phase 2 — Unit tests and continuous integration

**Goal:** Add repeatable automated checks before introducing network-dependent data fetching.

**Implemented:** Standard-library unit tests; GitHub Actions on Python 3.10–3.13 for pushes, pull requests, and manual dispatch; documented local test command.

**Verification:** GitHub Actions run [#3](https://github.com/MehdiAnti/AircraftCode-Explorer/actions/runs/40335663823) passed all four matrix jobs; the Python 3.10 log confirmed 14 tests and `OK`.

## Phase 3 — Wikidata data refresh

**Goal:** Provide an explicit command that fetches candidate aircraft records from Wikidata and writes a local catalog.

**Implemented:** SPARQL refresh command, timeout/User-Agent/retries, atomic writes, empty-result protection, provenance fields, mocked tests, and documentation.

**Verification:** GitHub Actions run [#14](https://github.com/MehdiAnti/AircraftCode-Explorer/actions/runs/40339675455) passed all four Python 3.10–3.13 jobs with 27 tests each. Tests used mocked responses; no live Wikidata refresh was run.

**Status:** Complete and user-approved.

## Phase 4 — Data quality, normalization, and provenance

**Goal:** Make refreshed records easier to trust and maintain.

**Implemented:** Whitespace normalization, uppercase designators, deterministic deduplication, source identity preservation, conservative fallback identity, catalog field validation, safe handling and diagnostics for malformed Wikidata rows, regression tests, and provenance documentation.

**Verification:** GitHub Actions run [#27](https://github.com/MehdiAnti/AircraftCode-Explorer/actions/runs/40342033600) passed all four Python 3.10–3.13 jobs; the Python 3.10 log confirmed 34 tests. Tests used mocked source responses; no live refresh was run. The checked-in `data/aircraft.json` remains `[]`, as requested.

**Status:** Complete and user-approved.

## Phase 5 — Documentation and release readiness

**Goal:** Make the project understandable and usable by a new contributor, and document release prerequisites without making owner-only decisions.

**Deliverables:**
- Clear checkout/setup instructions, command reference, examples, data format, and troubleshooting.
- A schema-only JSON example clearly marked as placeholders, not real aircraft data.
- Versioning and release notes guidance.
- A release checklist and explicit unresolved license decision.
- Review of CLI help text against documented behavior.

**Acceptance criteria:**
- A new user can follow the README from a clean checkout.
- Documented commands match the implemented CLI.
- License status and data-source attribution are explicit.
- CI passes for all supported Python versions.

**Status:** Complete. Documentation and release-readiness guidance were merged in PR [#1](https://github.com/MehdiAnti/AircraftCode-Explorer/pull/1). The merge was confirmed on 2026-10-26. Verify the associated workflow before claiming CI passed.

## Phase 6 — Usability improvements

**Goal:** Make the local catalog easier to export, search, and inspect while keeping the project dependency-free.

### Phase 6.1 — CSV export

**Scope:** Add an `export` command using Python's standard-library CSV support. Write to stdout by default or to a user-selected output path. Keep known columns in a stable order, include additional source-specific fields, represent missing values as empty cells, and safely encode nested values.

**Acceptance criteria:** Correct CSV quoting for commas and quotes; UTF-8 output; empty catalog emits headers; file and stdout modes work; JSON catalog remains unchanged.

### Phase 6.2 — Search and sorting

**Scope:** Add selectable sorting by manufacturer, model, ICAO designator, or description, plus descending order. Keep the existing default ordering and search filters. Missing sort values remain last in either direction.

**Acceptance criteria:** Sorting is case-insensitive and deterministic; filters still combine; records without designators remain searchable; CLI help and README match behavior.

**Status:** Complete. CSV export and selectable sorting were merged together in PR [#2](https://github.com/MehdiAnti/AircraftCode-Explorer/pull/2) on 2026-10-26.

### Phase 6.3 — Catalog status and freshness

**Scope:** Add a status view for total records, missing designators, source distribution, and available freshness/retrieval timestamps. Report unknown metadata as unknown; do not infer freshness when timestamps are absent.

**Acceptance criteria:**
- Counts are computed from the selected local catalog, without a network request.
- Source labels are grouped consistently; missing labels are explicitly shown as unknown.
- Valid retrieval timestamps are summarized in UTC; missing and invalid values are counted separately.
- If no valid timestamp exists, freshness and age are reported as unknown, not guessed.
- JSON output is machine-readable and human-readable output is clear.

**Status:** Implemented on `phase-6-3-catalog-status`; tests and CI are pending review.

Further possibilities, subject to explicit user approval: optional desktop or web interface, packaging, and additional source adapters if licensing and data quality permit.

## Completion log

- **Phase 1:** Foundation files committed; local execution not independently verified.
- **Phase 2:** Test suite and CI committed; run #3 passed 14 tests on Python 3.10–3.13.
- **Phase 3:** Wikidata refresh, provenance, CLI options, mocked tests, and documentation committed; run #14 passed 27 tests on Python 3.10–3.13; user approved.
- **Phase 4:** Normalization, deterministic deduplication, validation, diagnostics, tests, and provenance docs committed; run #27 passed 34 tests on Python 3.10–3.13; user approved.
- **Phase 5:** Documentation and release-readiness guidance merged in PR #1. No license has been selected and no release tag has been created.
- **Phase 6.1–6.2:** CSV export and selectable search sorting merged in PR #2. No aircraft data was added or changed.
- **Phase 6.3:** Catalog status and freshness reporting merged in PR #3. No aircraft data was added or changed.
- **Phase 7:** Discovery and verification workflow merged in PR #4. The trusted catalog remains unchanged; follow-up discovery-classification improvements are under review.


## Phase 7 — Broad aircraft data ingestion

**Goal:** Discover aircraft entities with and without ICAO designators, retain provenance, and prevent unverified candidates from silently entering the main catalog.

**Implemented:** a broad Wikidata discovery query for candidates with and without ICAO designators; field-level Wikidata provenance; heuristic candidate classification into model candidates, individual aircraft, and ambiguous records; reasons retained for each classification; promotion validation requiring independent non-Wikidata evidence; a separate output by default; mocked tests; and documentation.

**Important limitations:** classification is heuristic and can misclassify entities; it is a triage aid, not verification. The promotion command checks evidence metadata and classification status but does not crawl or authenticate cited pages. Reviewers must verify each source supports the associated field. No live refresh was run as part of the code change, and `data/aircraft.json` remains unchanged until records are independently verified and reviewed.

**Acceptance criteria:** candidates with and without designators can be discovered; unverified or Wikidata-only fields cannot be promoted; independently evidenced aircraft without designators are permitted; candidate discovery never overwrites the trusted catalog; failed or empty discovery does not overwrite existing output.

**Status:** Phase 7 implementation was merged in PR [#4](https://github.com/MehdiAnti/AircraftCode-Explorer/pull/4). Discovery classification refinements were merged in PR [#5](https://github.com/MehdiAnti/AircraftCode-Explorer/pull/5). The checked-in aircraft catalog remains unchanged until candidate evidence has been verified.


## Phase 8 — Local aircraft metadata cross-check

**Goal:** Add a dependency-free, API-free way to compare discovered candidates with a metadata CSV obtained separately, while preserving the existing verification gate.

**Implemented in the phase branch:** a `cross-check` CLI command, flexible CSV header handling for model/type-code fields, conservative normalized comparisons, explicit conflict and multiple-match statuses, a JSON report with source filename and check time, and mocked/local-file tests.

**Boundaries:** no automatic download, no API credentials, no dataset bundled in the repository, no change to `data/aircraft.json`, and no automatic promotion or addition to `field_evidence`. A local file's download date is not inferred. OpenSky metadata may be stale and has licensing/reuse limitations; the user must obtain and use a dataset only as permitted and manually inspect results.

**Acceptance criteria:** malformed CSV and candidate input fail safely; code/model matches are reported separately; disagreements and duplicate matches are visible; empty/no-match data is not treated as verification; report output is separate from the trusted catalog.

**Status:** Implementation is on `phase-8-local-metadata-cross-check`; review and CI pending.


## Phase 9 — OpenSky CSV import and safe catalog merge

**Goal:** Build the actual local catalog from a locally obtained OpenSky aircraft metadata CSV without routing through Wikidata discovery or the independent-evidence promotion gate.

**Scope:** dedicated `import-opensky` command; flexible CSV headers; model-level grouping; merge into the selected catalog (default `data/aircraft.json`); provenance history for exact matches; conflict preservation; dry-run support; and standard-library tests.

**Data-use boundary:** no automatic download or source dataset is committed. Confirm reuse and redistribution terms for the particular file before committing imported data to the public repository. Imported records remain marked unverified.

**Status:** Implementation under review in PR #7. No OpenSky dataset was downloaded or bundled.
