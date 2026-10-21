# ADR-0032 — Owner-governed agent evaluation without third-party dependency

Date: 2026-10-21. Status: provisional engineering design, stacked draft PR #39 on #38 → #37 → #36 → #35 → #34 → #33 → #32 → develop. AWF-R041.

## Problem

PR #35–#38 established trustworthy *credential and procedural boundaries*, but progressively demanded an externally appointed independent human scientific/governance body as a prerequisite. For a personally owned research/ML engineering project, requiring a paid academic committee simply to experiment creates a bottleneck without demonstrating better model or writing quality. Conversely, permitting a language model to self-approve its own generated content would create circular evidence. **A project owner is the legitimate authority for internal experiment scope and priority, but cannot truthfully present their own approval as independent external scientific certification.**

## Decision: two explicitly separate paths

1. **Owner-governed pilot evaluation — implemented.** The project owner may propose the rule, commission distinct AI-agent reviewer runs and sign a specific `OWNER_EVALUATION_DECISION` using existing Ed25519 reviewer trust infrastructure and new scoped role `PROJECT_OWNER`. This permits only `APPROVE_PILOT_EVALUATION`, `REQUEST_REVISION` or `REJECT` on a specific task. The owner can act as proposer *because* this is not an independent scientific adjudication.
2. **Third-party scientific/governance certification — preserved unchanged.** Existing PR #35–#38 strict ports, roles, quorum and externally qualified identity remain separate for future formal claims. Owner approval must NEVER call those ports pretending to be an independent institution or cause `RATIFIED_PROCEDURAL` in the original governance register.

## Implemented evidence flow

`signed historical proposal → agent report A → agent report B → source/task and ledger hash checks → explicit owner decision event → scoped project-owner Ed25519 signature → EVAL_ONLY authorization receipt`.

Each agent report `AGENT_REVIEW_REPORT` binds the exact source ID/archive SHA, requirement ID/requirement SHA, proposal ledger ref, task SHA and unique *claimed* agent and execution IDs, model ID, verdict, written analysis, limitations and source-support event references. Two reports must be distinct events with different agent IDs and execution IDs and valid `RULE_SUPPORT` references within the same subject/run and ledger head. Shared model IDs are permitted (affordable local Qwen pilots), but the result exposes `distinct_model_ids` and does NOT label them independent models. Different IDs do not prove real task execution, inference provenance or epistemic independence. Those require an independently instrumented execution adapter, logs, dataset/control comparisons and blind holdout testing as a later incremental delivery.

An owner's private canonical `OWNER_EVALUATION_DECISION` binds both reports in exact order, plus the same source/rule/task/proposal SHAs, owner actor ID, action and reason. The existing signature machinery authenticates the owner under a separately held, SHA-pinned `ReviewerTrustPolicy`; the ledger head must also be pinned outside the mutable database. No private keys, private notes or historical AWS ZIP enter the public repo.

Outputs never set `scientific_adjudications>0`, `training_authorized=true`, `source_rights_verified=true` or `historical_rule_disposition_changed=true`. Approval means only **a plan is eligible for EVAL_ONLY evaluation** on synthetic, otherwise lawfully available, or separately right-cleared data. It does not license or automatically commence model training.

## Why not assert 'AI is more objective' as a fact?

AI reviewers can be faster and more repeatable for controlled criteria, but repeatability is not validity. [Sebo & Wang (2026)](https://doi.org/10.1007/s11606-026-10806-8) studied 50 clinical research abstracts/800 AI reviews and reported high repeatability without a human gold standard establishing reviewer accuracy. [AI in scholarly peer review: scoping review (2026)](https://doi.org/10.1016/j.ijmedinf.2026.106418) mapped 189 sources, supporting transparent *assisted* peer review while identifying autonomous-assessment limitations. [NIST AI RMF 600-1](https://doi.org/10.6028/NIST.AI.600-1) recommends measurement validity and error/bias evaluation. These are evidence for **testing agent judgments against independent ground truth**, not for relying on vote counts or privately invented expertise.

## Threats and known limitations

- The owner may be interested in a particular outcome. This is disclosed by the **OWNER-GOVERNED** classification instead of mislabeling as external impartiality.
- Two prompt variants or models can share training data, failure modes or unverified claims; disagreement must remain visible, not averaged into certainty.
- Exact SHA-pinned events and valid model IDs do not establish that Gemini/Qwen/Claude was actually executed. Agent execution instrumentation and provider provenance are future work.
- A `RULE_SUPPORT` event can contain a correctly hashed but false claim; cryptographic checks establish custody and context, not scholarly truth. External source checking and a held-out benchmark are required.
- Neither the pilot nor the project owner's signature authorizes ingestion, redistribution or training on unlicensed publications. Rights controls in PR #35 still apply.
- Never delete or weaken the PR #35–#38 interfaces or signatures; do not reuse the term `RATIFIED_PROCEDURAL` for a pilot experiment.

## Next milestone: empirical per-rule validation, not another signature layer

1. Read historical AWS 3.19.1 locally and map the 184 requirement IDs to exact clauses, source evidence, rule test fixtures and versioned applicability.
2. Select a small initial group of machine-checkable rules (e.g. immutable quantities, source references, protected quotes), add executable controls and negative cases. Preserve remaining rules as `NEEDS_REVIEW`.
3. Run two context-isolated reviewer agents on the same pinned task + source snapshot. Compare claims with the executable checks, disputed cases and independent source evidence, not just opinions.
4. Have the owner sign the narrow pilot decision. Evaluate false-positive/false-negative rates on held-out Spanish/English academic examples before any upgrade.
5. Keep source rights, formal scientific certification and training eligibility separate.

Status: **engineering path only; no model training or historical MUST adjudication**.

## Engineering implementation checkpoint

Code SHA `b72de165412759e62737a0c64afb3cdc276e675a`
passed [push CI 39630505998](https://github.com/David-std/AWF/actions/runs/39630505998)
and [PR CI 39630513081](https://github.com/David-std/AWF/actions/runs/39630513081),
both SUCCESS 4/4 on Ubuntu/Windows × Python 3.12/3.13. Ubuntu Python
3.12 ran 482 tests PASS, Pyright 0 errors/0 warnings, Ruff lint/format
and build PASS. These tests use synthetic keys and agent receipt metadata,
NOT real independently instrumented Qwen/Gemini execution or primary-source
scientific adjudication. The subsequent documentation commit is subject
to another SHA-specific CI check.
