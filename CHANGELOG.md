# Changelog

## Unreleased — independent scientific assessment receipts (S2 candidate)

- Propose a separately granted SCIENTIFIC_REVIEWER role and signed per-rule SCIENTIFIC_RULE_ASSESSMENT event verified after the exact authenticated proposal.
- Preserve the rights/independence/epistemic boundary: no automatic REVIEW_ATTESTED, TRAIN or resolution of historical rules. Functional SHA `86f71659` and final documentation SHA `34b192a3` passed 4/4 GitHub Actions (final push 39531777710 and final PR 39531782917); independent scientific/legal/code review and merge remain outstanding.



## Unreleased — S2 signed historical-rule proposals (draft PR #33)

- Add `KNOWLEDGE_REVIEWER` role and `KNOWLEDGE_REVIEW_PROPOSAL` event, reusing existing Ed25519 reviewer grants, signature envelopes and verified SQLite snapshots.
- Bind full review-template SHA and source/rule identity to the proposal before validating a scoped, revocable signed statement. Optional private CLI inventory and policy gate; no scientific review or `REVIEW_ATTESTED`.
- Add synthetic adversarial and CLI tests, ADR-0026, AWF-R035, handoff and guide. Draft stacked on unmerged PR #32; no training authorization.



## Unreleased — S2 dossier evidence links

- Add optional read-only binding of private dossier `evidence_ids` to source- and rule-scoped ledger events, with one verified SQLite snapshot and externally supplied head.
- Reject missing/wrong scope, kind, run, source or rule SHA; retain all scientific-review and training restrictions.
- Document ADR-0025 and PR #31 handoff corrections. Functional commit `5f10015` passed four-platform CI; this remains an unmerged PR and **not** a completed knowledge adjudication.


## Unreleased — signed authorization of durable critic sweeps (Sprint 2)

- Extend the canonical Ed25519 reviewer-role contract with CRITIC, restricted to CRITIC_OBSERVATION ledger events and an externally SHA-pinned trust policy.
- Add an application-level authorization gate that loads committed CLEAN_SWEEP intents, checks the exact document and convergence, requires a complete attestation inventory, binds each signature to its original observation and actor, and re-audits the exact head in one verified snapshot.
- Reject missing/swapped/forged/stale/revoked or scope-mismatched signatures, changed documents, concurrent ledger growth and incompatible causal evidence. Add integration tests, ADR-0023 and AWF-R032.
- This gate is opt-in for consumers and does not prove reviewer independence, academic correctness or any formal adjudication of the 168 historical MUST rules.

## Unreleased — durable critic sweeps and external iterations (Sprint 2)

- Persist `CLEAN_SWEEP` and `EXTERNAL_ITERATION` as typed, versioned SQLite intent/commit/snapshot transitions; replays preserve domain gates, idempotency and rollback.
- Bind observations to actual, properly typed ledger events for the same run and revision, written after the preceding commit. Reject stale, swapped or reused context across critics and cycles.
- Replay current-scope audit prerequisites from committed hashes without storing document text. Add synthetic failure, concurrency, recovery and tamper-path integration tests (ADR-0022 / AWF-R031).
- Local state convergence is not scholarly acceptance; no historical rule is newly adjudicated and no critic independence is verified.
- The initial code SHA `4aa5d5e8` passed 329 Linux tests, 4/4 GitHub Actions quality-gate matrix and 327 Windows ASUS tests (+2 documented platform skips); the final documentation commit is subject to the same CI gate before merge.

## Unreleased — revision recovery profiling (Sprint 2)

- Add a temporary-data benchmark that separates one-revision replay from verified `load` and database-wide recovery, with operation counts, traced memory, latency ranges and Python/SQLite metadata.
- Record synthetic scaling observations and defer unsafe cache/skip-validation changes pending a real workload and adversarial equivalence tests (ADR-0021). Durable critic sweeps and external iterations remain pending; no historical rule is adjudicated.

## Unreleased — atomic batched evidence writes (Sprint 2)

- Append ordered bounded evidence batches after one full audit under `BEGIN IMMEDIATE`; check SQLite schema within the locked transaction and roll back every event on any failure or interruption. Single `append` uses the same safe path; revision writes/recovery and direct evidence reads also validate DDL within their snapshots.
- Bind observed source chunks to their canonical manifest before storing, while preserving separate full-coverage and reviewer gates; reject stale externally supplied heads and retain payload deduplication.
- Add synthetic concurrency, corruption, interruption, property and performance tests, ADR-0020 and a reproducible append benchmark. No persistent trusted-head cache, external custody, auto-idempotent retry or academic adjudication is claimed.

## Unreleased — single-snapshot verified evidence reads (Sprint 2)

- Add `VerifiedEvidenceReaderPort` and transaction-scoped `SQLiteEvidenceLedger.verified_read` to amortize a complete integrity audit across multiple receipt resolutions without caching trusted heads.
- Route chunk coverage, audit receipts and knowledge-stage adjudication (including nested READ coverage) through one consistent SQLite snapshot; individual `resolve_event` still audits before resolving and invalid event/run/subject/payloads remain unverified.
- Add synthetic count-based and WAL concurrency regressions, an offline timing benchmark, ADR-0019 and measurement guide. No assumption about academic adjudication, witness custody or production latency targets.

## Unreleased — WAL-aware signed backup and restore (Sprint 2)

- Add SQLite online backup creation and fresh-path restore guarded by the latest independently pinned Ed25519 signed checkpoint, without overwriting existing state or accessing custodian private keys.
- Verify the entire revision journal including replay and orphan transitions, not just event hashes, before publishing a staged copy with an atomic create-only hardlink.
- Cover active WAL frames, concurrent append, altered revision state, tampered backup, existing targets, symlinks, failed publication and CLI. ADR-0018 keeps automatic cutover, actual external custody and RPO/RTO outside the prototype.

## Unreleased — externally signed ledger checkpoints (Sprint 2)

- Add a separate Ed25519 custodian trust policy, canonical versioned checkpoint claims, an externally held latest-checkpoint hash and mandatory signed ancestry for detecting internally valid truncation/rollback.
- Audit all checkpoint prefixes, SQLite objects and immutable schema in one read snapshot through `EvidenceStorePort.verify_anchors`; expose `checkpoint-propose` (unsigned) and `checkpoint-verify` commands without handling custodian secrets.
- Add adversarial signed/forged/truncated/rebuilt/revoked/stale/lineage tests and ADR-0017. External custody, trusted timestamps, historic grant rotation and scientific adjudication remain outside the guarantee.

## Unreleased — reviewer authorization prototype (Sprint 2)

- Introduce Ed25519-signed review attestations bound to exact ledger event, role, run and subject, verified against an externally pinned allowlist with expiration/revocation.
- Add separate audit and knowledge-claim authorization gates, `awf evidence attest` and `attest-verify`, and adversarial signature, swap, scope and revocation tests.
- Preserve the distinction between key/role authorization and independent scholarly adjudication; neither legacy receipts nor the 168 MUST rules gain automatic approval.

## Unreleased — integration audit and continuity (2026-10-19)

- Merge PRs #10–#20 in order into the new `develop` branch from `main`, preserving all merge commits and leaving `main` unchanged.
- Close adversarial gaps found during independent review: schema/trigger replacement, audit state replay, mixed-run knowledge progress, idempotent private exports, and causal event ordering.
- Final integrated validation: 196 Linux tests, 194 Windows Python 3.12 tests plus 2 documented skips, and 4/4 Linux/Windows Python 3.12/3.13 Actions jobs on PR #20.
- Preserve historical decision boundaries: no formal adjudication of 168 MUST rules, no proof of independent reviewer authorization, no external checkpoint, no automatic scientific approval or training entitlement.

## Unreleased — Sprint 2 durable edit and finding transitions

- Coordinate `accept_edit`, `open_finding` and `resolve_finding` with immutable revision snapshots in one SQLite transaction.
- Add event-bound typed intents and schema-2 commits, retaining replay of original schema-1 START/AUDIT records.
- Verify conservative receipt invalidation, material finding lineage, crash rollback, concurrent writers and idempotence with synthetic tests. ADR-0015 documents the absence of external reviewer authority.

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


## Unreleased — S2 private historical dossier inspection (PR #31)

- Added `awf knowledge inspect-review` for exhaustive, read-only assessment of private annotations against the SHA-pinned historical archive and original review packets.
- Rejects source-field modifications, missing/swapped batches, invalid conflict references, deferred-lab promotion, and incomplete evidence.
- Preserves `OPEN`/`PARTIAL`/`PROPOSAL_INCOMPLETE`/`PROPOSAL_DOCUMENTED` as metadata states only; no automatic review attestation or training rights.
- Added adversarial tests, integration CLI tests, and ADR-0024. Historical archive and review annotations remain private.

