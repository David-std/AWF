# AWF — handoff after Sprint 0 bootstrap (implementation branch)

Updated 2026-10-17. This document describes **`feat/s0-bootstrap`**, not yet merged into main.

- **Current sprint:** S0.
- **Baseline:** architecture PR #10 (must be merged before this dependent implementation PR).
- **Issue:** [#1](https://github.com/David-std/AWF/issues/1).
- **Change:** installable Python package, `awf --version`, lockfile, unit tests, CI quality workflow and ADR-0006.
- **Local/CI verification:** see PR checks and recorded outputs; do not assume pending workflow jobs have passed.
- **Known limitation:** development tools pinned in CI, not locked in `uv.lock`; runtime is intentionally free of third-party dependencies. This is a declared temporary exception in ADR-0006.
- **Not implemented:** DocumentIR/ingestion (S1), knowledge compiler (S2), semantic verifier (S3), model inference (S4), fine-tuning (S5) and DPO (S6).
- **Source governance:** AWS 3.19.1 archive stays outside public Git; no corpus or proprietary outputs pushed.
- **Next step:** verify PR S0 gates, merge the architecture baseline and bootstrap PR, then begin S1 with immutable DocumentIR and Markdown parser.

Do not mark S0 complete until the CI matrix is confirmed green and the built CLI is smoke-tested.
