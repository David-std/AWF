# Changelog

## Unreleased — Sprint 2 atomic revision journal

- Persist `START` and `AUDIT` `RevisionState` snapshots together with evidence/transition events in the same SQLite transaction, without replacing the earlier in-memory APIs.
- Recover immutable version history with hash/event checks, optimistic version conflicts and stable idempotency keys; rejected writes and pre-commit process interruption leave no audit event orphan.
- Add synthetic failure, crash, restart, replay, tampering, legacy-schema and concurrent-writer tests. Document ADR-0014; keep external authority and the remaining state transitions out of scope.

## Unreleased — Sprint 2 receipt-to-ledger binding (PR #18)

- Bind audit receipts, source-chunk observations and epistemic-stage claims to exact event/run/subject/type/payload identities; bare content hashes cannot authorize a claim.
- Recalculate expected chunk and axis coverage from stored private bytes before recording READ; require separate typed local adjudication events for understanding/applicability rather than caller booleans.
- Validate current document audit slots and local-scope lineage; failure to persist does not mutate the pure state. Add 12 synthetic integration regressions against stale/swapped/forged/foreign or missing proofs.
- Document ADR-0013 and keep independent scientific/model adjudication explicitly unresolved.


## Unreleased — Sprint 2 local evidence ledger

- Add transactional SHA-256-linked evidence events with private SQLite content-addressed blobs and optional independently retained head checkpoints.
- Add `awf evidence append/verify` CLI with source-file protection, synthetic regression tests, and explicit limit: hashes are not signatures nor academic assessment.
- ADR-0012 distinguishes necessary transactional persistence from earlier metadata-only JSON exports.

## Unreleased — Sprint 2 knowledge-integrity prototype

- Add source-identity and chunk-to-EOF inventory, evidence-bound read coverage and debt reporting.
- Separate available, read, understood, applicable, applied and verified as explicitly evidenced transitions, without equating receipts to comprehension.
- Add four-family calibration checks and answer-key-free challenge packets; reject missing, duplicate or unresolved challenges.
- Preserve critical exceptions, historical negative knowledge, dependencies and reversible source pointers; reject style-template or implicit-training use.
- Track token efficiency separately from execution-fidelity evidence.
- Record DSR-016..032 technical transfer review and ADR-0011. No rule is automatically adjudicated.

## Unreleased — Sprint 2 private review workbench

- Add complete private review packets grouped by domain and deterministic batch number; read original rules only from pinned local ZIP.
- Preserve historical implementation claims, verification surfaces, acceptance metrics and residual uncertainty as evidence pointers without treating them as AWF passes.
- Add coverage/hash checks, fail-closed unsupported boundaries, synthetic positive/negative regression tests, and source-text-free CLI summaries.
- All 184 remain OPEN pending justified review; source archive stays local-only.


## Unreleased — AWF 0.1.0 (Sprint 2 knowledge-import branch)

- Add `awf knowledge import` and `knowledge audit` for a SHA-pinned, local-only AWS 3.19.1 archive; export metadata without text or source ZIP.
- Preserve all 184 requirement IDs conservatively: 168 unresolved MUST, 16 lab-only evaluation entries. No implicit training authorization or semantic contradiction claims.
- Add private atomic registry exports, reviewed decision overlays, duplicate-description inspection, strict ZIP guards and negative tests.
- ADR-0008 defers SQLAlchemy/SQLite until transaction/queries demonstrate need; S2 is explicitly still incomplete.

## Sprint 1 branch

- Implement `awf ingest <file.md>` with deterministic UTF-8 parsing, immutable DocumentIR and SHA-256 of original bytes.
- Support optional local content-addressed original preservation with integrity checks, repeatable output and a guarded `--output` path.
- Add unit/integration/property tests for idempotency, malformed inputs, fenced code, BOM, attempted source overwrite and corrupt stored blobs.
- Record ADR-0007's strict scope and remaining improvements; does not claim full CommonMark support or semantic validation.

## Sprint 0 foundation

- Introduce installable Python package `academic-writing-forge`, `awf --version`, project-only `uv.lock` and cross-platform quality workflow.
- Record ADR-0006 on dependency-free CLI and temporary dev-tool lock gap.
- AWS 3.19.1 stays local; public Git contains provenance metadata only.
