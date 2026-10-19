# Changelog

## Unreleased — AWF 0.1.0 (Sprint 1 branch)

- Implement `awf ingest <file.md>` with deterministic UTF-8 parsing, immutable DocumentIR and SHA-256 of original bytes.
- Support optional local content-addressed original preservation with integrity checks, repeatable output and a guarded `--output` path.
- Add unit/integration/property tests for idempotency, malformed inputs, fenced code, BOM, attempted source overwrite and corrupt stored blobs.
- Record ADR-0007's strict scope and remaining improvements; does not claim full CommonMark support or semantic validation.

## Sprint 0 foundation

- Introduce installable Python package `academic-writing-forge`, `awf --version`, project-only `uv.lock` and cross-platform quality workflow.
- Record ADR-0006 on dependency-free CLI and temporary dev-tool lock gap.
- AWS 3.19.1 stays local; public Git contains provenance metadata only.
