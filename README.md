# Academic Writing Forge (AWF)

**AWF Neural Engine** is an engineering and machine-learning project for traceable academic text revision in Spanish and English. The goal is to preserve meaning, citations, evidence, and author intent while comparing pretrained editors, fine-tuned models, and explicit verification policies.

**Status on `develop` (2026-10-20): architecture, S0, S1 and S2 increments through PR #24 are merged and verified.** This feature branch proposes one-audit verified evidence reads and a reproducible scaling benchmark. `main` remains at its pre-integration baseline; Sprint 2 is still open. None of the 168 mandatory historic rules has been formally adjudicated. The neural editor, independent semantic verifier, training and external API are **not implemented**. This repository maintains research provenance without claiming detector performance.

## Start here

- [Architecture specification v0.1](docs/architecture/ARCHITECTURE_SPEC_0_1.md) — authoritative proposed architecture, file ownership, interfaces, tests, datasets, and S0–S8 roadmap.
- [Decision lock](docs/architecture/DECISIONS_LOCK.yaml) — current proposals, invariants, and open decisions.
- [Agent instructions](AGENTS.md) — how to work here without losing the project history.
- [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md) — requirements, provenance, and verifiability plan.
- [Roadmap](docs/ROADMAP.md) and [current handoff](docs/AGENT_HANDOFF.md).
- [Evidence and source registry](docs/SOURCE_REGISTRY.md) — status and limitations of external references.
- [Compute plan](docs/COMPUTE_AND_TRAINING.md) — RTX 4050, Qwen baseline, and optional Google-hosted GPU.

## Integration status and current limits

PRs [#10–#24](https://github.com/David-std/AWF/pulls?q=is%3Apr+is%3Amerged+base%3Adevelop) were reviewed and merged **in sequence into `develop`**, preserving their merge commits. The last completed increment is [PR #24](https://github.com/David-std/AWF/pull/24), merged as `e32e0ea99e76640133d328548214f0efbae63cfc`: 279 Linux tests and 277 Windows tests (+2 platform-specific skips), with 4/4 GitHub Actions jobs Linux/Windows Python 3.12/3.13 passing, plus Ruff and Pyright ([run 39203570452](https://github.com/David-std/AWF/actions/runs/39203570452)). [PR #25](https://github.com/David-std/AWF/pull/25) passed its initial 4/4 CI ([run 39347741248](https://github.com/David-std/AWF/actions/runs/39347741248)) and isolated authorized Windows reproduction; it still requires verification of its final documentation SHA before merger. See [the current handoff](docs/AGENT_HANDOFF.md).

Integrity is **not** independent scholarly assessment: externally verified human independence, actual external checkpoint custody, full durable critic sweeps, recovery benchmarks and the 168 rule adjudications remain incomplete. Do not promote `REVIEW_ATTESTED`, publish the historical ZIP or authorize model training based on these infrastructure tests.

## Implemented core (S0–S1)

`develop` includes an installable Python package, CLI and deterministic Markdown ingestion. For example:

```shell
uv sync --locked
uv run awf --version
uv run awf ingest draft.md
uv run awf ingest draft.md --store .awf --output document-ir.json
```

The ingest command reads **original UTF-8 bytes** and returns a content-addressed DocumentIR (SHA-256, blocks, inclusive line positions). `--store` is opt-in private local storage; the original file is never modified. The initial parser recognizes ATX headings, paragraphs and fenced code only; it is not a full CommonMark parser or a semantic verifier.

S0: [PR #11](https://github.com/David-std/AWF/pull/11) · S1: [PR #12](https://github.com/David-std/AWF/pull/12), following [architecture PR #10](https://github.com/David-std/AWF/pull/10). All three are merged into `develop`, not `main`.

## Knowledge Compiler (Sprint 2, initial implementation)

```shell
uv run awf knowledge import "/private/path/academic_writing_suite_v3_19_1_product(1).zip" \\
  --manifest provenance/source-manifest.json \\
  --output .awf/knowledge/registry.json
uv run awf knowledge audit .awf/knowledge/registry.json \\
  --archive "/private/path/academic_writing_suite_v3_19_1_product(1).zip"
```

The source ZIP remains local. Only SHA-bound metadata is written to a private ignored directory, not the rule descriptions. The first import is deliberately conservative: **168 MUST → UNRESOLVED** and **16 DEFERRED_LAB → EVAL_ONLY**, with all 184 IDs retained. Rules are not silently made executable or admitted into training. [Read the S2 contract](docs/KNOWLEDGE_COMPILER_S2.md).

This is an initial S2 slice, **not** completed semantic adjudication. [Implementation PR #13](https://github.com/David-std/AWF/pull/13) was developed on [#12](https://github.com/David-std/AWF/pull/12), [#11](https://github.com/David-std/AWF/pull/11) and [#10](https://github.com/David-std/AWF/pull/10) and is now merged into `develop`.

## Engineering principles

1. **Verification before claims:** model output does not certify itself. A critical failure rejects the change; a critical unknown requires review.
2. **No destructive migration:** AWS 3.19.1 remains an immutable upstream research baseline, subject to provenance and licensing checks before import.
3. **Models are interchangeable:** start with a deterministic dummy adapter, measure pretrained baselines, then train PEFT adapters only when justified.
4. **Reproducible comparisons:** preserve document-level partitions, benchmark holdouts, source/model licenses, run manifests, adverse cases, and negative results.
5. **Scope first:** modular Python monolith with hexagonal boundaries and lightweight command/query separation; no premature distributed services.

## Planned development

S0: repository, CLI, tooling and CI → S1: immutable DocumentIR → S2: knowledge compiler → S3: independent verification → S4: model baselines → S5: SFT/QLoRA → S6: optional DPO/ablations → S7: API → S8: optional detector research.

No AI-detector bypass rate is claimed. Detector outputs, if studied, remain separate from the primary requirements of academic correctness, fidelity, and citation integrity.

## Research and licenses

Some research datasets, model checkpoints, academic texts, and commercial service outputs have use restrictions. No third-party corpus, provider outputs, model weights, proprietary suite archive, or user manuscript is committed here by default. The project's **code license is intentionally undecided** until reuse constraints are reviewed.

> Note: the GitHub repository slug is `David-std/AWF`; the display name is **Academic Writing Forge**. Internal package and command names are `awf` in the S0–S1 implementation.

## Stateful audit prototype (Sprint 2, not a production verifier)

[PR #15](https://github.com/David-std/AWF/pull/15) introduces a pure, model-independent revision-state prototype covering candidate transfers of historic DSR-001..015. It requires an explicit nonempty audit inventory, binds receipts to current hashes, invalidates dependent checks after edits, tracks open findings, and gates convergence on distinct documented clean sweeps and budgets. See the [15-rule review](docs/reviews/STATEFUL_RUNTIME_DSR001_015.md) and [ADR-0010](docs/adr/0010-revision-audit-prototype.md).

The prototype does **not** establish semantic correctness, genuine independent critic isolation, source permissions, a neural model, or finished migration of AWS rules. It was built on PRs #10–#14 and is now merged into `develop`; subsequent S2 PRs added persistent *local* audit proofs, not external attestation.

## Knowledge integrity gates — Sprint 2 prototype

[PR #16](https://github.com/David-std/AWF/pull/16) adds source-byte and chunk-to-EOF inventories, nonempty expected coverage, explicit AVAILABLE/READ/UNDERSTOOD/APPLICABLE/APPLIED/VERIFIED evidence stages, calibration with positive/near-miss/counterexample/holdout cases, source-pinned cards, critical dependency closure and separately reported token efficiency vs fidelity evidence. See [the 17-rule audit](docs/reviews/KNOWLEDGE_INTEGRITY_DSR016_032.md) and [ADR-0011](docs/adr/0011-knowledge-integrity-gates.md).

**Boundary:** a valid receipt is *not* proof that a person or model read and understood the material. Nor is it a license to reuse private texts, an academic-correctness certificate, a fine-tuned neural model, or a verified detector result. The historical corpus stays private.

## Local evidence ledger — Sprint 2

[ADR-0012](docs/adr/0012-local-evidence-ledger.md) introduces a private, transactional SQLite journal for evidence bytes and SHA-256-linked events. Use `awf evidence append` and `awf evidence verify` as documented in [the local evidence guide](docs/EVIDENCE_LEDGER_S2.md). This makes declared evidence *retrievable and locally integrity-checkable*, **not signed, externally authenticated, independently assessed, or a proof that a model understood its inputs**. PR #17 is merged into `develop`; it does not finish the ML engine.

## Evidence-bound revision and knowledge receipts — Sprint 2

[PR #18](https://github.com/David-std/AWF/pull/18) extends the local evidence ledger with exact event-bound receipt verification for document audits, source chunks, required coverage and knowledge stages. The [ADR-0013](docs/adr/0013-evidence-bound-receipts.md) explains event identity, expected-run/subject checks, carried-audit constraints and adversarial tests; [evidence binding guide](docs/EVIDENCE_BINDING_S2.md) lists application APIs.

**Important:** `local_integrity_passed` is not equivalent to a trustworthy assessment of the manuscript, the sources, reviewer independence or actual model comprehension; `independent_adjudication_proven` remains `false`. The entire S2 stack through #20 is integrated into `develop` but has no production editor or neural training. Historical AWS 3.19.1 files remain private.

## Atomic revision journal — Sprint 2 incremental prototype

The `SQLiteRevisionJournal` Python API persists versioned `RevisionState` snapshots and their evidence events together in **one local SQLite transaction**. A stable operation ID supports idempotent retry; stale writers fail closed, and recovery checks the event/snapshot chain. A subsequent S2 increment adds durable edits and finding open/resolution with exact event-bound intentions, compatible with previous commits. Critic sweeps and academic acceptance are not durable. See [ADR-0014](docs/adr/0014-atomic-revision-journal.md), [ADR-0015](docs/adr/0015-durable-edit-and-finding-transitions.md) and [the recovery guide](docs/DURABLE_REVISION_S2.md).

No historical requirement is automatically adjudicated by this infrastructure, and no locally stored audit is independent proof of academic accuracy or evaluator authority. The original AWS archive stays private.

## Reviewer signatures and role authorization — Sprint 2 prototype

The application can now verify detached Ed25519 reviewer statements over **one exact ledger event** against an externally SHA-pinned reviewer allowlist (actor/key, roles, run/subject, expiry, revocation). The `awf evidence attest` and `attest-verify` commands do not generate or hold reviewer private keys. Audit and knowledge-stage gates can require signed statements in addition to local integrity; legacy receipts are not silently upgraded. See [ADR-0016](docs/adr/0016-signed-reviewer-authorization.md) and [the authorization guide](docs/REVIEWER_AUTH_S2.md).

This is **cryptographic key/role authorization only**, not third-party identity vetting, independent human judgment, trustworthy timestamping, or permission to accept a manuscript. Durable critic sweeps remain open.

## Verified evidence reads and scaling — Sprint 2 proposed increment

Source-chunk coverage, audit receipt checks and knowledge-stage verification can share **one fully audited SQLite read transaction** across their receipts, avoiding repeated full-ledger audits while preserving exact event/run/subject/bytes checks. [ADR-0019](docs/adr/0019-verified-evidence-read-snapshots.md) and the [benchmark guide](docs/EVIDENCE_READ_SCALING_S2.md) document concurrency, negative tests, reproducible synthetic measurements and the remaining `O(n)` per-operation cost. No signature, custody or academic truth is inferred from higher throughput.

## Signed ledger checkpoints — Sprint 2 incremental prototype

The `awf evidence checkpoint-propose` command emits an **unsigned** Ed25519
claim for the current SQLite head, identified by sequence and event digest.
An offline custodian signs it outside AWF, and `checkpoint-verify` checks a
**separately retained SHA-256 of the signed checkpoint**, an independently
pinned authorization policy, the whole signature lineage and exact historical
prefixes in one SQLite read transaction. Internally valid database truncation
is detectable relative to the *most recent independently held checkpoint*.
No private key or remote publication is managed by this code. See
[ADR-0017](docs/adr/0017-externally-signed-ledger-checkpoints.md) and
[checkpoint guide](docs/SIGNED_CHECKPOINTS_S2.md).

If the newest digest was never independently retained, a prior valid signed
checkpoint may still be replayed: the program cannot prove custody, time,
independence or scientific merit. Real external backup custody and institutional
rotation are separate S2 deliverables.

## WAL-aware verified backups and restore — Sprint 2 incremental prototype

Use `awf evidence snapshot-create SOURCE.sqlite DESTINATION.sqlite` to produce
a coherent SQLite backup even when WAL has pending committed frames, and
`snapshot-restore BACKUP.sqlite NEW_LEDGER.sqlite` to recover into a **new**
location. Both require the latest independently pinned signed checkpoint,
its full signature history and policy; the restored copy must match the
signed head exactly. The recovery audit also reconstructs every saved
`RevisionState`, detects altered/missing snapshots and rejects compromised
revision triggers. Publishing never overwrites an existing file.

See [ADR-0018](docs/adr/0018-wal-aware-signed-backup-recovery.md) and
[the operational guide](docs/VERIFIED_SNAPSHOTS_S2.md). There is no remote
backup provider, scheduler, automatic cutover, proof of third-party custody
or RPO/RTO commitment. A backup does not authorize scholarly claims.
