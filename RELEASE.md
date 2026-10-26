# Versioning and release guidance

This project is not yet packaged for installation and does not currently have a selected license. Treat releases as source-checkout releases until packaging is deliberately added.

## Versioning

Before the first public release:

1. Confirm the project's license with the repository owner and add the corresponding license file.
2. Confirm the supported Python versions and ensure the CI matrix covers them.
3. Review the README, command help, data-source caveats, and the complete test results.
4. Decide whether the release is ready to be tagged.

Until version 1.0.0, use a pre-1.0 version such as `0.2.0` for a backward-compatible feature release, `0.2.1` for a backward-compatible fix, and `0.3.0` for a change that expands or changes the interface. These are project conventions, not a promise of a stable API. Once 1.0.0 is declared, use Semantic Versioning: patch for compatible fixes, minor for backward-compatible functionality, and major for incompatible public-interface changes.

The package currently declares its version in `aircraft_explorer/__init__.py`. Keep that value aligned with the release tag and release notes.

## Release checklist

- [ ] Confirm and document the license; add a license file only after the owner chooses it.
- [ ] Review the README commands against `python -m aircraft_explorer --help` and each subcommand's help output.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Confirm GitHub Actions passes on every supported Python version.
- [ ] Inspect the final diff and ensure no test fixtures, credentials, temporary files, or unintended catalog changes are included.
- [ ] Confirm catalog changes have source provenance and do not invent or infer ICAO designators.
- [ ] Update `aircraft_explorer/__init__.py` if the version changes.
- [ ] Add concise release notes describing user-visible changes, known limitations, and any migration steps.
- [ ] Create a Git tag matching the version (for example, `v0.2.0`) and publish GitHub release notes from that tag.

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

Do not create a release tag or choose a license as part of routine documentation changes without explicit owner approval.
