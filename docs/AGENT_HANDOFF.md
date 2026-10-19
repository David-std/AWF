# AWF — handoff after Sprint 1 implementation branch

Updated 2026-10-17. Scope is `feat/s1-document-ir`, dependent on Sprint 0 PR #11 and architecture PR #10.

- **Current sprint:** S1 implemented in PR #12; awaiting code review/merge. Latest *code* SHA tested: `cbd05e9ba242c40eb3de0f6477a313342286860d`.
- **Issues:** [S0 #1](https://github.com/David-std/AWF/issues/1), [S1 #2](https://github.com/David-std/AWF/issues/2).
- **Changed functionality:** `awf ingest file.md [--store private-dir] [--output output.json]`; typed immutable `DocumentIR`, Markdown parser, content-addressed storage and negative tests.
- **Tests:** [PR workflow 39076453243](https://github.com/David-std/AWF/actions/runs/39076453243) and [push workflow 39076450574](https://github.com/David-std/AWF/actions/runs/39076450574) both concluded SUCCESS for SHA `cbd05e9ba242c40eb3de0f6477a313342286860d` (Ubuntu/Windows × Python 3.12/3.13, four successful matrix jobs). Any later documentation-only commit must still be checked separately.
- **Contracts:** SHA-256 references original bytes including BOM/newlines; block locations are 1-based inclusive line numbers. No inference of citations, scientific meaning or revision acceptance.
- **Known limitations:** parser only handles ATX headings, fenced code and generic paragraphs; not full CommonMark. Blob creation uses exclusive writes but does not implement production-grade multihost transaction/isolation.
- **Not implemented:** AWS knowledge compiler, semantic/source gate, neural editor/model port, training or API. No GPU required for S1.
- **Source governance:** AWS archive is local-only, not in Git.
- **Next step:** verify checks on final documentation commit, integrate stacked PRs in order, then begin S2 via a source-licensed knowledge manifest and exhaustive historical rule-ID mapping.

Changes in architecture must update ADR and tests; do not represent an unrun command as verified.
