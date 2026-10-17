# ADR-0007 — Sprint 1 conservative immutable Markdown IR

- **Status:** Accepted for the Sprint 1 implementation branch
- **Motivation:** Early ML experiments require stable source lineage before integrating DOCX/PDF parsers or models.
- **Decision:** The public `awf ingest` command reads original UTF-8 Markdown bytes, computes SHA-256 from **those exact bytes**, and emits a typed `DocumentIR` that contains heading/paragraph/code blocks and 1-based inclusive line positions.
- **Scope limits:** The first parser does not claim full CommonMark compliance, extract citations, normalize text for round-trip reconstruction, or parse DOCX/PDF. Markdown lists/tables remain paragraph content. Unclosed code fences are rejected rather than guessed. Source max 4 MiB, no NUL and no invalid UTF-8.
- **Storage:** `--store <dir>` optionally preserves source bytes by SHA under a user-selected private local path. It is idempotent and validates existing content. CLI rejects `--output` equal to the source filename to avoid accidental overwrite. The default is read-only analysis with JSON printed to stdout.
- **Safety model:** `DocumentIR` is an immutable view, **not** an accepted revision; no model is invoked. Semantic/source verification remains S3. Explicitly prohibit using this IR as proof of scientific correctness.
- **Tradeoff:** Content-addressed identity changes when even metadata line breaks or BOM change; this is intentional. Semantic equivalence is assessed separately.
- **Future:** Extend parser with source byte-span coordinates, CommonMark-compatible parsing and DOCX/PDF adapters only with evidence/tests. Add atomic JSON output and storage concurrency tests before production-facing deployment.
