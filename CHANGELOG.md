# Changelog

## Unreleased — AWF 0.1.0 (Sprint 0)

- Introduce the installable Python package `academic-writing-forge`, an `awf` CLI and a project-only `uv.lock`.
- Add an explicit, tested CLI version contract; unknown flags exit with code 2.
- Add quality-gate workflow for Linux/Windows, Python 3.12/3.13, Ruff, Pyright, pytest, Hypothesis availability and wheel/sdist build.
- Document ADR-0006: stdlib CLI bootstrap and separately pinned development toolchain.
- Preserve AWS 3.19.1 **locally**; only metadata and cryptographic provenance are stored in the public repository.

No revision engine, model training or document ingestion is claimed as implemented.
