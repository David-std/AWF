# ADR-0031 — Reversible scientific governance register with external quorum authority

- Date: 2026-10-21.
- Status: provisional engineering implementation in stacked **draft PR #38**.
- Parent: PR #37 (HEAD `736b2786e3bf0908ee136226dbf330830d9833a6`), stacked #32 → #33 → #34 → #35 → #36 → #37.
- Requirement: AWF-R040. Previous AWF-R039 arbitration remains independent.
- This is a scientific **procedural** decision register, not a scientific truth oracle, a state change to the 184 historical requirements, or data-training authorization.

## Methodological and technical basis

- [PRISMA 2020 expanded checklist](https://www.prisma-statement.org/s/PRISMA_2020_expanded_checklist-yc78.pdf), items 8–9, requires transparent documentation of reviewers, independence and disagreement-handling processes. It does not prescribe an AWF board size.
- [COPE, Ethical guidelines for peer reviewers](https://doi.org/10.24318/2019.1.4) describes competence, confidentiality and competing-interest duties. It does not certify AWF reviewer identities.
- [NIST AI RMF, GOVERN 1.4–1.5, 2.1](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) recommends accountable governance policies, documented roles, ongoing monitoring and review. It is a risk-management framework, not an independent external approval.

A **minimum quorum of two approvers** is a conservative **AWF prototype policy choice** rather than an empirical optimal panel size or a rule dictated by PRISMA, COPE or NIST. The quorum is configured in a canonical JSON policy pinned by an expected SHA-256 retained outside the editable governance file.

## Architectural decision

1. Add `EvidenceKind.SCIENTIFIC_GOVERNANCE` and `ReviewerRole.GOVERNANCE_APPROVER` to the existing Ed25519 reviewer authorization implementation. No second signature protocol, mutable SQL status column or new model-based adjudicator.
2. Require complete re-verification of the upstream PR #37 source/proposal/two scientific assessments, SHA-pinned disagreement case, signed arbitration chain and role-scoped reviewer policy using one externally anchored head and trusted time.
3. Accept one governance **intent** only as a canonical event referencing exact source/archive/requirement SHA, case SHA, last arbitration event, current procedural state, action, predecessor governance event, documented reason, supporting ledger events and pinned governance-policy hash.
4. Require at least the policy quorum of distinct `GOVERNANCE_APPROVER` signed attestations of **the same exact intent event**; exclude proposer, both scientific reviewers, every prior arbiter and reused governance approvers across the whole chain. Valid signing keys alone still do not prove distinct real persons or independence.
5. Require an **injected independently trusted `ExternalGovernanceAuthorityPort`** with evidence bytes per approver, an externally held SHA per evidence item, external governance-policy SHA and trusted time. The port is responsible for verifiable appointment, subject competence, human identity, conflicts of interest, institutional independence, mandate and revocation. No production adapter/real governing body is designated here. If absent, the view remains `OPEN` with zero applied actions even with valid signatures.
6. Procedural states and actions are explicit and reversible: `OPEN —RATIFY→ RATIFIED_PROCEDURAL —SUSPEND→ SUSPENDED —REOPEN→ OPEN`. No invalid jumps, implicit acceptance, deletion or rewriting historical ledger records. A suspension and reopening must cite a newly recorded `RULE_SUPPORT` event **after the previous signed governance action**. Every event forms an append-only chain with exact `previous_decision_ref`.
7. `RATIFY` cannot be applied if the upstream last arbitration is `DEFER` or `UNRESOLVED` or its separate arbitrator qualification gate failed. Even a supported/contested qualified arbitration and formally qualified governor quorum produce only **procedural ratification**, never an epistemically guaranteed truth claim.
8. Source rights and training are separate. In **every** projection: `scientific_adjudications=0`, `review_attestation_authorized=false`, `training_authorized=false`, `source_rights_verified=false`, `historical_rule_disposition_changed=false`. No training dataset, historic rule disposition or graph contract changes. The snapshot can always be recomputed from the immutable evidence after revocation or policy updates.

## Authority admission checklist (future implementation, not self-attested)

An organization authorized by the project owner must establish, **outside Git/SQLite**: identities and credential chain of governors, subject-matter expertise, independent appointment and mandate, conflicts/financial interests, relationship to proposers/scientists/arbiters, exclusion/recusal, signatory and policy expiry, evidence handling/confidentiality, agreed criteria for a decision, appeal/suspension procedures, revocation and independent trusted anchors. A self-signed local policy, ORCID/DOI, or two differently named keys is not sufficient.

The `ExternalGovernanceAuthorityPort` is deliberately a boundary only. App logic cannot verify whether an actual institution is legally empowered, whether evidence is true, whether human independence is genuine, or whether a natural person has been compensated; such verification belongs to the externally designated reviewer and documented governance process.

## Threats, residual risks and testing

Test with synthetic Ed25519 signers and fake external arbitral/board verifiers: no external authority, missing approval quorum, duplicated signer, replay/role promotion, revoked credential, changed source/case/policy, stale ledger head, wrong event order, unsupported transition, failed qualification evidence and old support masquerading as fresh. A fake verifier can return a procedural `RATIFIED_PROCEDURAL` to exercise workflow without demonstrating any actual organizational acceptance.

**Important:** S2's 168 MUST requirements remain unadjudicated and 16 DEFERRED_LAB remain EVAL_ONLY. This module is not an authorization shortcut. Do not import private AWS ZIP, human credentials, source excerpts or legal attestations into the public repo.

## Deferred

Actual appointment and verification of a real external governing authority, verified custody and cross-key human identity, event-level quorum certificates recognized across institutions, expiration scheduling, practical appeals service, enforceable external revocation/withdrawal and deliberate promotion of any historical rule after empirical source-linked review. No silent version or state migration.

## Verified engineering checkpoint (not scientific authorization)

The code SHA `edd2301e235c2f0214ab56666dbae30d179c214e`
completed [push CI 39623798093](https://github.com/David-std/AWF/actions/runs/39623798093)
with 4/4 matrix jobs PASS (Ubuntu/Windows × Python 3.12/3.13).
Ubuntu Python 3.12 recorded 472 pytest PASS, Pyright zero errors/warnings,
Ruff 0.14 lint/format and build success. The corresponding
[PR CI 39623808300](https://github.com/David-std/AWF/actions/runs/39623808300)
must be independently checked at the same SHA and this documentation commit
will require another CI check. Synthetic verification of source-bound
procedures does not establish a real independent governing institution.
