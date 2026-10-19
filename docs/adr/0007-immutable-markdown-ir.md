# ADR-0007 — Sprint 1 conservative immutable Markdown IR

- **Status:** Accepted for the Sprint 1 implementation branch
- **Motivation:** Early ML experiments require stable source lineage before integrating DOCX/PDF parsers or models.
- **Decision:** The public `awf ingest` command reads original UTF-8 Markdown bytes, computes SHA-256 from **those exact bytes**, and emits a typed `DocumentIR` that contains heading/paragraph/code blocks and 1-based inclusive line positions.
- **Scope limits:** The first parser does not claim full CommonMark compliance, extract citations, normalize text for round-trip reconstruction, or parse DOCX/PDF. Markdown lists/tables remain paragraph content. Unclosed code fences are rejected rather than guessed. Source max 4 MiB, no NUL and no invalid UTF-8.
- **Storage:** `--store <dir>` optionally preserves source bytes by SHA under a user-selected private local path. It is idempotent and validates existing content. CLI rejects `--output` equal to the source filename to avoid accidental overwrite. The default is read-only analysis with JSON printed to stdout.
- **Safety model:** `DocumentIR` is an immutable view, **not** an accepted revision; no model is invoked. Semantic/source verification remains S3. Explicitly prohibit using this IR as proof of scientific correctness.
- **Tradeoff:** Content-addressed identity changes when even metadata line breaks or BOM change; this is intentional. Semantic equivalence is assessed separately.
- **Future:** Extend parser with source byte-span coordinates, CommonMark-compatible parsing and DOCX/PDF adapters only with evidence/tests. Before production-facing deployment, evaluate hostile concurrent directory replacement and filesystems without hard-link support.

### Pre-merge review hardening (2026-10-19)

- `--output` now refuses hard-link aliases of the source, and publishes JSON via a same-directory temporary file and atomic replacement; failed output publication leaves the previous result intact.
- Content-addressed originals are flushed to private temporary files and published through exclusive, atomic hard-link creation. Competing writers see the previous complete blob or a complete new blob, never a partially written final path. Filesystems lacking local hard-link support fail closed.
- A symlinked hash-prefix directory or an existing symlink at the digest path is rejected to avoid redirecting private bytes outside the selected store. These checks are not a substitute for process-level sandboxing against a malicious actor who can actively swap directories.
- Negative integration tests cover hard-link source aliases, output-write interruption, symlink redirection, swapped digest path and concurrent writers. No source text is committed in the tests.
