# ADR-0006 — Bootstrap CLI without runtime framework dependencies

- **Status:** Accepted for Sprint 0
- **Date:** 2026-10-17
- **Context:** The AWF blueprint proposes Typer and a fully pinned tooling stack. Sprint 0 must run offline for core commands, avoid cloud subscriptions and be reproducible on both Windows and Linux. The source environment can generate a project-only `uv.lock` without network access, but cannot resolve all development tools offline.
- **Decision:** Start the installed `awf` command with standard-library `argparse` and no required runtime dependencies. Defer adding Typer until the CLI's nested command structure justifies it. Keep the `main(argv)` entrypoint and tests provider-independent; the public command name remains `awf`.
- **Quality tooling:** CI invokes explicitly versioned Ruff, Pyright, pytest and Hypothesis through uv's ephemeral environments. Project runtime dependencies are locked; **developer tools are version-pinned in CI but not yet recorded in `uv.lock`**. Add a locked `dev` dependency group once dependency resolution is available and justify any changed tool versions. This deviation is visible technical debt, not full end-to-end supply-chain reproducibility.
- **Consequences:** Small auditable S0 binary and no network in the runtime. Contributors need an online environment for first-time installation of CI tooling and setuptools wheel. Future Typer migration needs CLI compatibility tests; no silent command or exit-code changes.
- **Rejected:** Building a fake Typer adapter or marking an unexecuted toolchain as tested; adding React/API/model dependencies in Sprint 0.
