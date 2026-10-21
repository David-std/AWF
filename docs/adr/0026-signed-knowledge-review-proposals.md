# ADR-0026 — Signed, scope-bound historical-rule review proposals

- **Status:** experimental credential-authorization gate, pending independent review.
- **Date:** 2026-10-20.
- **Depends on:** ADR-0016, ADR-0019, ADR-0024, ADR-0025 (unmerged PR #32).
- **Branch:** `feat/s2-signed-knowledge-review-proposals` in draft PR #33, stacked on PR #32.
- **Requirement:** AWF-R035.

## Problem

Private review dossiers currently offer `PROPOSAL_DOCUMENTED` when metadata are structurally complete. PR #32 additionally resolves `evidence_ids` to source- and rule-bound immutable ledger events. A source hash and a declared `reviewer` string do not prove that any authorized reviewer signed the exact proposed decision. A signature over only an evidence ID would survive subsequent changes to the rule's disposition, reason, tests, rights declaration, conflicts or supporting evidence.

## Decision and trust boundary

1. Introduce **`ReviewerRole.KNOWLEDGE_REVIEWER`** and **`EvidenceKind.KNOWLEDGE_REVIEW_PROPOSAL`**. Map this role to that event kind only. Keep `CRITIC`, `CALIBRATOR`, `AUDITOR` and `APPLICABILITY_REVIEWER` separate; do not silently widen existing grants.
2. Use the existing `ReviewerClaim`, `SignedReviewerClaim`, Ed25519 verifier and SHA-pinned `ReviewerTrustPolicy`. The grant must permit the precise actor/key, `KNOWLEDGE_REVIEWER` role, review run, public rule ID and verification time; revocation/expiry are reevaluated on **every** inspection. A signed claim references an exact committed proposal event, not a raw rule or an uncommitted assertion.
3. A proposal event must carry canonical JSON containing `schema=1`, `type=private_dossier_review_proposal`, source ID and archive SHA-256, requirement ID and text SHA-256, declared reviewer actor ID, `review_status=PROPOSAL_DOCUMENTED` and SHA-256 of the **complete** private `review_template`. The complete template hash binds disposition, reasons, evidence IDs, conflicts, proposed tests, version reference and declared rights without publishing source prose.
4. The new opt-in `inspect-review` gate first runs the existing source-bound dossier inspection, requires an exact mapping for **every** `PROPOSAL_DOCUMENTED` rule (zero documented rules never passes), and checks source-bound `RULE_SUPPORT` events, proposal JSON, kind/run/subject and sequence ordering, then Ed25519 signature and trust policy in **one verified SQLite snapshot** pinned to an independently retained `expected_head`.
5. Expose private `--attestation-inventory`, `--reviewer-policy`, and `--expected-reviewer-policy-sha256` flags only with the PR #32 evidence database, run ID and external head. Inventory contains per-rule `proposal_ref` and `attestation_ref`. Require a canonical, bounded, duplicate-free JSON inventory; never print private annotations or signatures.
6. Return `credentials_authorized` for the exact submitted, documented proposal snapshots only; **never** produce `REVIEW_ATTESTED`, change original rule dispositions, grant `TRAIN`, mark conflicts resolved or increment 0/168 scientific adjudications. Unsigned/default inspector behavior remains unchanged.

## Alternatives rejected

- Reuse existing `APPLICABILITY_REVIEWER` or `CRITIC` as a historical-rule adjudicator: their grants govern different evidence types and causal scopes.
- Sign an editable `reviewer` label or `evidence_ids` alone: those references do not bind the full annotated decision.
- Write an attestation straight into the existing dossier JSON: allows replacement, makes a mutable file appear authoritative and bypasses ledger event order.
- Claim independent scholarly acceptance from an Ed25519 key: possession of a key does not establish identity, expertise, human independence or legal permission.
- Audit SQLite separately for every support reference and signature: slower and vulnerable to cross-snapshot drift.

## Failure behavior / boundary

A missing/extra inventory entry, swapped signature, revoked/expired grant, wrong role/run/rule/actor, forged signature, modified template, unbound source evidence, stale external ledger head or reordering fails closed. A broken trust policy SHA is a hard error. Evidence append sequence proves **recorded ordering inside this ledger only**, not trusted time or that a person actually read a document before signing; the signer may have signed without conducting a review.

This prototype authenticates credential-level **authorization of a proposal snapshot**, not the content of that proposal. The standalone `evidence attest` command only authenticates the narrower role/event; consumers seeking an authorized *dossier* must call this higher-level gate. In particular, `source_rights_status=PERMISSION_VERIFIED` remains self-declared and cannot enable training.

## Acceptance and deferred work

Synthetic tests must exercise real Ed25519 signatures, independent policy digest, run/rule scopes, revocation/expiry, changed dossier fields, prior support-event ordering, inventory completeness, explicit head, CLI, restarted SQLite and single full-ledger scan. Locked Ruff, Pyright, build, Ubuntu/Windows × Python 3.12/3.13 CI required. No baseline private ZIP, actual private reviewer dossiers, keys or real manuscripts enter Git.

Defer independent identity confirmation, scientific source/claim review, external rights grants, anti-collusion/dual-control review, trusted timestamp/custody and durable disposition transitions to later S2 increments. Keep Sprint 2 OPEN and 168 MUST unresolved.
