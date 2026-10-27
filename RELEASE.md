# Release and Versioning Guide

## Current release model

Aircraft Explorer currently consists of a static HTML/CSS/JavaScript website, a Python maintenance/import CLI, and generated aircraft data. It is not currently documented as a packaged Python application for installation from a package index. The website is deployed through GitHub Pages workflows.

The project's original code and accompanying documentation are licensed under the MIT License; see `LICENSE`.

## Before a website release or deployment

- [ ] Review the pull request diff and confirm only intended application, workflow, documentation, and data files changed.
- [ ] Confirm the model catalog and compressed registry outputs have the expected structure.
- [ ] Run the configured unit tests and inspect the actual GitHub Actions results.
- [ ] Confirm the refresh workflow's full-registry and shard validation succeeds when data is refreshed.
- [ ] Confirm the Pages workflow succeeds and inspect the deployed website.
- [ ] Test model catalog search, sorting/pagination, and individual-aircraft searches for registration, ICAO24, type code, and operator.
- [ ] Confirm the website loads compressed shards and does not require uncompressed registry copies.
- [ ] Check that the displayed data-source and freshness limitations are accurate; the configured OpenSky source is a fixed May 2024 snapshot.
- [ ] Check that no CSV source file, credentials, temporary files, or unintended data changes were committed.
- [ ] Confirm the intended website visibility, especially if the repository is private.

## Before a Python CLI/source release

- [ ] Review the supported Python versions and CI matrix.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Review command help and verify README examples against the current CLI.
- [ ] Check catalog provenance and ensure no ICAO type designators have been invented or inferred.
- [ ] Update the version in `aircraft_explorer/__init__.py` if a versioned source release is intended.
- [ ] Add concise release notes covering user-visible changes, known limitations, and any migration steps.

## Versioning

Until version 1.0.0, the repository may use pre-1.0 versions such as `0.2.0` for a backward-compatible feature release, `0.2.1` for a compatible fix, and `0.3.0` for an interface change. These are project conventions, not a guarantee of a stable API. If the project adopts Semantic Versioning after 1.0.0, use patch releases for compatible fixes, minor releases for backward-compatible features, and major releases for incompatible public-interface changes.

Do not create a version tag, publish a GitHub release, or claim a successful deployment unless the owner has approved the decision and the relevant action has actually been completed.

## Release notes template

```markdown
## [Version] — YYYY-MM-DD

### Added
-

### Changed
-

### Fixed
-

### Known limitations
-
```
