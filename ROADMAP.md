# Project Roadmap

This file is the source of truth for project phases, current progress, and phase-by-phase approval. Keep it updated so future contributors and AI coding sessions can recognize the project state without relying on chat history.

## Project goal

Build a maintainable aircraft catalog and explorer that supports searching by ICAO type designator, model, and manufacturer. The project includes a Python CLI, a static HTML/CSS/JavaScript website, a JSON catalog, and a repeatable GitHub Actions refresh/deployment workflow.

## Working rules

- Work only in `MehdiAnti/AircraftCode-Explorer`.
- Implement one phase at a time, on a dedicated branch.
- Group each phase into one pull request for review; do not commit phase changes directly to `main`.
- After each phase, report files changed, checks actually run, known limitations, and the pull request.
- Stop and ask the user to review and approve before starting the next phase.
- Never claim tests or workflows passed unless they were actually run and the result was observed.
- Prefer Python's standard library unless a dependency has a clear benefit.
- Never invent ICAO type designators. Preserve source/provenance information and distinguish source data from independently verified facts.
- Preserve source provenance and distinguish imported metadata from independently verified facts.
- Do not select a project license or create a license file without the repository owner's confirmation.

## Phase status

| Phase | Name | Status |
|---|---|---|
| 1 | Repository foundation and local catalog CLI | Complete; execution not yet independently verified |
| 2 | Unit tests and continuous integration | Verified — 14 tests passed on Python 3.10–3.13; user review status previously recorded |
| 3 | legacy source data refresh | Complete — verified and approved by user |
| 4 | Data quality, normalization, and provenance | Complete — verified and approved by user |
| 5 | Documentation and release readiness | Complete — PR #1 merged; CI status should be checked separately |
| 6.1–6.2 | CSV export, search, and sorting | Complete — PR #2 merged |
| 6.3 | Catalog status and freshness | Complete — PR #3 merged |
| 7–8 | Legacy candidate discovery and metadata cross-check | Retired in Phase 10 in favor of catalog-first review |

## Phase 1 — Repository foundation and local catalog CLI

**Goal:** Establish the initial package, data format, and command-line interface.

**Deliverables:** `README.md`, `.gitignore`, `aircraft_explorer/`, `data/aircraft.json`, search by text/manufacturer/model/designator, and basic statistics.

**Acceptance criteria:** The module can be invoked with `python -m aircraft_explorer`; search and statistics operate on the local JSON catalog; missing catalog files return an empty catalog and malformed data is reported clearly.

**Status:** Complete. The files were committed to `main`; execution has not been independently verified in this chat.

## Phase 2 — Unit tests and continuous integration

**Goal:** Add repeatable automated checks before introducing network-dependent data fetching.

**Implemented:** Standard-library unit tests; GitHub Actions on Python 3.10–3.13 for pushes, pull requests, and manual dispatch; documented local test command.

**Verification:** GitHub Actions run [#3](https://github.com/MehdiAnti/AircraftCode-Explorer/actions/runs/40335663823) passed all four matrix jobs; the Python 3.10 log confirmed 14 tests and `OK`.

## Phase 3 — legacy source data refresh

**Historical goal:** Provide a network refresh command. This workflow was retired in Phase 10; the supported data-ingestion path is now the local CSV importer.

**Implemented:** SPARQL refresh command, timeout/User-Agent/retries, atomic writes, empty-result protection, provenance fields, mocked tests, and documentation.

**Verification:** GitHub Actions run [#14](https://github.com/MehdiAnti/AircraftCode-Explorer/actions/runs/40339675455) passed all four Python 3.10–3.13 jobs with 27 tests each. Tests used mocked responses; no live legacy source refresh was run.

**Status:** Historical implementation completed; the network refresh command was retired in Phase 10.

## Phase 4 — Data quality, normalization, and provenance

**Goal:** Make refreshed records easier to trust and maintain.

**Implemented:** Whitespace normalization, uppercase designators, deterministic deduplication, source identity preservation, conservative fallback identity, catalog field validation, safe handling and diagnostics for malformed legacy source rows, regression tests, and provenance documentation.

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
- **Phase 3:** legacy source refresh, provenance, CLI options, mocked tests, and documentation committed; run #14 passed 27 tests on Python 3.10–3.13; user approved.
- **Phase 4:** Normalization, deterministic deduplication, validation, diagnostics, tests, and provenance docs committed; run #27 passed 34 tests on Python 3.10–3.13; user approved.
- **Phase 5:** Documentation and release-readiness guidance merged in PR #1. No license has been selected and no release tag has been created.
- **Phase 6.1–6.2:** CSV export and selectable search sorting merged in PR #2. No aircraft data was added or changed.
- **Phase 6.3:** Catalog status and freshness reporting merged in PR #3. No aircraft data was added or changed.
- **Phases 7–8:** Legacy candidate-discovery workflow has been retired in Phase 10; local catalog import, review, and manual verification are now the documented path.




## Phase 10 — OpenSky-first workflow and catalog review

**Scope:** retire legacy network discovery/refresh commands; make local CSV import the documented ingestion path; add detailed verification-state and type-code conflict reports; make repeated imports update freshness without duplicating records or provenance; add deliberate manual verification based on independent source evidence.

**Boundaries:** importing or matching CSV data does not verify facts. The manual verification command records source details supplied by the user and cannot authenticate a source or prove that it supports the fields. Conflicting codes remain review-required unless the user explicitly confirms a manually resolved conflict. No dataset is downloaded or bundled.

**Status:** implementation on branch `phase-10-opensky-review-no-wikidata`; PR and CI pending.


## Phase 11 — Static web explorer and automated OpenSky refresh

**Goal:** Provide a polished static aircraft-search website and a repeatable weekly catalog refresh.

**Scope:**
- Add responsive HTML/CSS/JavaScript UI with search, sorting, pagination, catalog counts, source/provenance details, and a refresh button that reloads the latest published JSON.
- Add a GitHub Pages deployment workflow that publishes the site and `data/aircraft.json`.
- Add a scheduled workflow for Sunday 06:00 UTC plus manual dispatch. It downloads OpenSky CSV to temporary runner storage, uses the existing Python importer, validates the generated JSON, commits only the JSON when changed, and deploys the refreshed website.
- Keep source CSV out of Git history and never expose a GitHub token in frontend JavaScript.
- Preserve the rule that imported records remain unverified.

**Setup note:** Repository Settings → Pages must use GitHub Actions. Check the repository plan and site visibility before enabling Pages, because a Pages site may be publicly accessible even when the source repository is private.

**Status:** Merged in PR #9. Initial live Pages deployment and scheduled refresh should be confirmed in GitHub Actions; no successful live OpenSky run is assumed from the merge alone.


## Phase 12 — Search performance and individual-aircraft registry

**Goal:** Keep the existing website design while making large-catalog search responsive and adding useful individual-aircraft lookup.

**Scope:**
- Precompute searchable text and sort order once; debounce model-catalog input.
- Add separate search modes for the model catalog, registration, ICAO type code, and operator.
- Generate compressed JSON registry shards from the OpenSky CSV using the existing Python importer. Shards are partitioned by two-character field prefixes and contain available aircraft-level details such as ICAO24, registration, manufacturer, model, type code, serial/line number, operator/callsign, owner, dates, equipment flags, notes, and source provenance.
- Load registry shards on demand, cache loaded shards in the browser session, and keep the existing compact result cards. Clicking a card expands its details.
- Keep individual aircraft records separate from grouped model records in `data/aircraft.json`.
- Generate registry shards as part of the Pages artifact rather than committing them to Git history, preventing large binary registry updates from accumulating every week.
- Update tests, README, WEB.md, and workflow documentation.

**Search behavior:** Registry search accepts at least two letters or digits and matches prefixes, ignoring case and punctuation. The browser fetches only the matching field-specific shard. The Refresh data button continues to reload the latest model catalog JSON; it does not trigger Actions.

**Status:** Implementation in PR #10; awaiting review and CI. The live OpenSky download and GitHub Pages deployment still need to be checked after merge.
