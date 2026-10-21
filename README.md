# Academic Writing Forge (AWF)

**AWF Neural Engine** is an engineering and machine-learning project for traceable academic text revision in Spanish and English. The goal is to preserve meaning, citations, evidence, and author intent while comparing pretrained editors, fine-tuned models, and explicit verification policies.

**Status (2026-10-20):** PR #10–#31 are merged into `develop` (`6888a8f44a33`). Draft PR #32 binds private dossier evidence; draft PR #33 authorizes signed rule proposals; draft PR #34 verifies a separate credential-signed scientific assessment as a *recorded opinion*, not an adjudication. All three PRs passed their own CI but remain unmerged in order. `main` is unchanged. Sprint 2 is OPEN with 0/168 MUST adjudicated and 16 DEFERRED_LAB in `EVAL_ONLY`. No neural editor, training authorization, verified rights or independently completed scientific adjudication.

## Start here

- [Architecture specification v0.1](docs/architecture/ARCHITECTURE_SPEC_0_1.md) — authoritative proposed architecture, file ownership, interfaces, tests, datasets, and S0–S8 roadmap.
- [Decision lock](docs/architecture/DECISIONS_LOCK.yaml) — current proposals, invariants, and open decisions.
- [Agent instructions](AGENTS.md) — how to work here without losing the project history.
- [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md) — requirements, provenance, and verifiability plan.
- [Roadmap](docs/ROADMAP.md) and [current handoff](docs/AGENT_HANDOFF.md).
- [Revision replay profile (S2)](docs/REVISION_REPLAY_PROFILE_S2.md) — synthetic measurements of journal recovery; no validation shortcuts or production SLOs.
- [Durable revision transitions (S2)](docs/DURABLE_REVISION_S2.md) — atomic critic sweeps and external iterations, event ordering, recovery and academic limits.
- [Evidence and source registry](docs/SOURCE_REGISTRY.md) — status and limitations of external references.
- [Compute plan](docs/COMPUTE_AND_TRAINING.md) — RTX 4050, Qwen baseline, and optional Google-hosted GPU.

## Integration status and current limits

PRs [#10–#29](https://github.com/David-std/AWF/pulls?q=is%3Apr+is%3Amerged+base%3Adevelop) were reviewed and merged **in sequence into `develop`**, preserving their merge commits. [PR #29](https://github.com/David-std/AWF/pull/29) merged as `2275d0018f17de8559a72d8c6cae4e248a1627c0`, with 329 Linux tests, 327 Windows ASUS tests (+2 platform skips) and 4/4 GitHub Actions checks ([run 39377697531](https://github.com/David-std/AWF/actions/runs/39377697531)). [PR #30](https://github.com/David-std/AWF/pull/30) adds an [application-level signed-critic gate](docs/REVIEWER_AUTH_S2.md) with 4/4 CI on the first code SHA, without claiming proof of independence. See [the current handoff](docs/AGENT_HANDOFF.md).

Integrity is **not** independent scholarly assessment: externally verified independence, actual external checkpoint custody, policy-backed reviewer authority and the 168 rule adjudications remain incomplete. The synthetic recovery profile is not an operational SLO. Do not promote `REVIEW_ATTESTED`, publish the historical ZIP or authorize model training based on these infrastructure tests.

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

The `SQLiteRevisionJournal` Python API persists versioned `RevisionState` snapshots and their evidence events together in **one local SQLite transaction**. A stable operation ID supports idempotent retry; stale writers fail closed, and recovery checks the event/snapshot chain. Durable edits, findings, critic sweeps and external iterations use exact event-bound intentions, compatible with previous commits. Sweep context/observation events are checked for type, run, revision and causal freshness. **Scientific acceptance is not implemented.** See [ADR-0014](docs/adr/0014-atomic-revision-journal.md), [ADR-0015](docs/adr/0015-durable-edit-and-finding-transitions.md), [ADR-0022](docs/adr/0022-durable-critic-and-external-iterations.md) and [the recovery guide](docs/DURABLE_REVISION_S2.md).

No historical requirement is automatically adjudicated by this infrastructure, and no locally stored audit is independent proof of academic accuracy or evaluator authority. The original AWS archive stays private.

## Reviewer signatures and role authorization — Sprint 2 prototype

The application can now verify detached Ed25519 reviewer statements over **one exact ledger event** against an externally SHA-pinned reviewer allowlist (actor/key, roles, run/subject, expiry, revocation). The `awf evidence attest` and `attest-verify` commands do not generate or hold reviewer private keys. Audit and knowledge-stage gates can require signed statements in addition to local integrity; legacy receipts are not silently upgraded. See [ADR-0016](docs/adr/0016-signed-reviewer-authorization.md) and [the authorization guide](docs/REVIEWER_AUTH_S2.md).

This is **cryptographic key/role authorization only**, not third-party identity vetting, independent human judgment, trustworthy timestamping, or permission to accept a manuscript. Durable sweep events do not automatically require signed independent assessors.

## Verified evidence reads and scaling — Sprint 2 integrated increment

Source-chunk coverage, audit receipt checks and knowledge-stage verification can share **one fully audited SQLite read transaction** across their receipts, avoiding repeated full-ledger audits while preserving exact event/run/subject/bytes checks. [ADR-0019](docs/adr/0019-verified-evidence-read-snapshots.md) and the [benchmark guide](docs/EVIDENCE_READ_SCALING_S2.md) document concurrency, negative tests, reproducible synthetic measurements and the remaining `O(n)` per-operation cost. No signature, custody or academic truth is inferred from higher throughput.

## Atomic evidence append batches — Sprint 2 integrated increment

`SQLiteEvidenceLedger.append_batch` accepts a bounded, ordered group of new
evidence events and commits them in **one** SQLite write transaction after a
complete integrity audit. The schema check is now performed under the write
lock, including for legacy `append`. An application helper binds observed
source chunks to their canonical manifest before writing; full coverage
must still pass a separate gate. [ADR-0020](docs/adr/0020-atomic-batched-evidence-append.md)
and the [write benchmark guide](docs/EVIDENCE_BATCH_APPEND_S2.md) explain
failure/rollback behavior, limits and measured synthetic throughput. This
increment is integrated in [PR #26](https://github.com/David-std/AWF/pull/26),
but not academically adjudicated by this description.

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

## Dossier evidence links — optional Sprint 2 gate

[ADR-0025](docs/adr/0025-dossier-evidence-links.md) documents the opt-in `awf knowledge inspect-review --evidence-database ... --review-run-id ... --expected-head ...` integrity gate. It verifies stored event bytes, bound source/rule identity and one trusted ledger snapshot, without granting reviewer authority or scientific acceptance. See [usage](docs/DOSSIER_EVIDENCE_LINKS_S2.md).

## Signed dossier proposal review — stacked Sprint 2 increment

A separate `KNOWLEDGE_REVIEWER` role can sign the exact immutable snapshot of a documented private rule proposal, with per-rule/run grants, expiry and revocation. `awf knowledge inspect-review` can optionally verify this signed inventory under an externally pinned policy and ledger head. This is **credential authorization only**, never `REVIEW_ATTESTED` or scientific acceptance. See [ADR-0026](docs/adr/0026-signed-knowledge-review-proposals.md) and [private usage guide](docs/SIGNED_KNOWLEDGE_PROPOSALS_S2.md). Draft [PR #33](https://github.com/David-std/AWF/pull/33) depends on draft PR #32.

## Independent scientific assessment receipts (S2 draft candidate)

The optional Python application service `verify_independent_scientific_assessments` authenticates an actor-distinct, role-scoped, Ed25519-signed assessment following an already signed rule proposal. Assessment notes remain in the private ledger. Credential and event integrity do not prove research correctness or source rights. No historical rule is thereby adjudicated or usable for training. See [ADR-0027](docs/adr/0027-independent-scientific-assessment-receipts.md).

Verified final [PR #34 CI](https://github.com/David-std/AWF/actions/runs/39531782917) at `34b192a3` (4/4); the corresponding authoritative [handoff section](docs/AGENT_HANDOFF.md) includes SHA, architecture, preserved limits, and next requirements. See [ADR-0027](docs/adr/0027-independent-scientific-assessment-receipts.md). No physical ASUS full-suite tests are claimed.

## Source-specific rights/provenance gate (S2 stacked draft PR #35)

A private, canonical source-rights inventory distinguishes READ, EVALUATE, TRANSFORM,
REDISTRIBUTE and TRAIN for exact source files and byte segments. `parse_source_rights`
requires an independently retained expected SHA-256 and exact archive/file identity.
`check_source_right` fails closed on denial, revocation, expired or contradictory
grants, incomplete scope, missing original bytes or evidence. The **default** is
`UNKNOWN`: no implementation of a real legal authority verifier is included in
this PR. A future externally trusted rights authority must verify underlying
evidence and issuer scope before any conditional positive rights conclusion.
`TRAIN_ALLOWED` never sets the separate system-level `training_authorized` flag.
No ZIP or private evidence is committed. See [ADR-0028](docs/adr/0028-source-rights-evidence-gate.md)
and [guide](docs/SOURCE_RIGHTS_GATE_S2.md).

**PR #35 code verification:** `cd6c2c8` passed [push CI 39540058673](https://github.com/David-std/AWF/actions/runs/39540058673), 4/4 matrix jobs (Ubuntu/Windows × Python 3.12/3.13), 440 tests passed on Ubuntu 3.12 and Pyright 0 errors. This does not establish external legal authority or scientific acceptance.

## Signed scientific disagreement triage (S2 stacked draft PR #36)

The `verify_disagreement_protocol` application service compares **two distinct,
role-scoped, Ed25519-signed** scientific assessments of the same exact proposal,
reusing PR #34's signed-review gates and the same externally pinned ledger head.
Opposing or inconclusive verdicts require a private, canonical, SHA-pinned case
plan recording the issue, missing evidence, methodological divergence and next
action. It does not perform a third-party scientific adjudication, accept a rule,
grant source rights or enable model training. No extra signature role or key
system is introduced. See [ADR-0029](docs/adr/0029-scientific-disagreement-triage.md)
and [private guide](docs/SCIENTIFIC_DISAGREEMENTS_S2.md).

**PR #36 code CI checkpoint:** `55f1c03`, both [push 39542413641](https://github.com/David-std/AWF/actions/runs/39542413641) and [PR 39542418761](https://github.com/David-std/AWF/actions/runs/39542418761) SUCCESS (4/4 each); Ubuntu 3.12 449 tests PASS, Pyright zero errors. This proves an engineering test outcome only, never human scientific independence or final adjudication.

## Third-party scientific arbitration / reconsideration (S2 draft PR #37)

A dedicated `SCIENTIFIC_ARBITER` role **reuses the existing Ed25519 reviewer
trust policy and event signatures**. The application verifies a PR #36 open
disagreement, source/proposal/two assessments, evidence-event references,
signed decision records and append-only reconsideration decisions citing
fresh recorded evidence. An independently pinned, externally qualified
reviewer/COI authority must be supplied to verify *procedural competence*.
No such real authority exists in the shipped code: valid signatures alone
return `procedure_verified=false`. Even with a synthetic verifier in tests,
`scientific_adjudications=0` and all training/right/disposition
authorizations stay false. See [ADR-0030](docs/adr/0030-third-party-scientific-arbitration.md)
and the [private API guide](docs/SCIENTIFIC_ARBITRATION_S2.md).

**PR #37 engineering checkpoint:** `0205780d` passed both
[push CI 39544667960](https://github.com/David-std/AWF/actions/runs/39544667960)
and [PR CI 39544672301](https://github.com/David-std/AWF/actions/runs/39544672301),
4/4 matrix jobs each. Ubuntu Python 3.12 recorded 459 pytest PASS and
Pyright 0 errors/0 warnings. Engineering verification is not a scientific
adjudication or qualification of an actual human arbitrator.

## Reversible scientific governance (S2 stacked draft PR #38)

A private, externally SHA-pinned governance policy (two-to-five-person quorum)
binds exact `SCIENTIFIC_GOVERNANCE` intent events to the prior validated
arbitration case. Distinct `GOVERNANCE_APPROVER` keys sign **the same** event
with the existing reviewer Ed25519 infrastructure; conflicts with proposer,
scientific evaluators, arbitrators and prior governors are rejected. The
reversible procedural projection is `OPEN → RATIFIED_PROCEDURAL → SUSPENDED →
OPEN`, with fresh evidence mandatory for suspension/reopening.

Critically, **no actual governance/qualification authority adapter has been
appointed or implemented**. Signed intents are recorded but not applied
without both externally qualified arbitration and a separately trusted
`ExternalGovernanceAuthorityPort`. In default deployment the state remains
OPEN. Even test-only synthetic ratification never changes the 184 historic
requirements, source rights, scientific truth or model-training access.
See [ADR-0031](docs/adr/0031-scientific-governance-register.md)
and [private API guide](docs/SCIENTIFIC_GOVERNANCE_S2.md).

**PR #38 code checkpoint:** `edd2301e235c2f0214ab56666dbae30d179c214e`,
[push CI 39623798093](https://github.com/David-std/AWF/actions/runs/39623798093)
4/4 PASS; Ubuntu Python 3.12 **472 pytest PASS** and Pyright zero errors.
[PR CI 39623808300](https://github.com/David-std/AWF/actions/runs/39623808300)
should be verified independently at the code SHA; this documentation
follow-up requires another CI run on its own SHA.

## Owner-governed AI review for EVAL_ONLY pilots (S2 draft PR #39)

An AWF project owner may **authorize their own internal evaluation experiments**
without an external institution, by signing an exact `OWNER_EVALUATION_DECISION`
using the existing Ed25519 trust system. Two `AGENT_REVIEW_REPORT` records bind
the same source/rule/task, claimed model runs and existing ledger source-support
events. AWF verifies distinct agent/run labels, signatures and canonical hashes.
The owner **may be the original proposer** because this mode does NOT claim an
independent scientific adjudication, third-party qualification or publication
review. No trained-model access, rights grant, historic rule disposition or
`RATIFIED_PROCEDURAL` state follows. See [ADR-0032](docs/adr/0032-owner-governed-agent-evaluation.md)
and [owner workflow](docs/OWNER_AGENT_REVIEW_S2.md).
