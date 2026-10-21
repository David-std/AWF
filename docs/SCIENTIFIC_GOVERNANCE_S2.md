# S2 — reversible scientific governance register

This module is a **separate procedural projection over a cryptographically audited local ledger**. It does not amend the legacy 184-rule corpus, scientific facts, model-training rights or legal ownership. All examples in CI are synthetic.

## API

- `GovernanceState`, `GovernanceAction`, `next_governance_state`, `parse_governance_policy` in `awf.domain.scientific_governance`.
- `governance_transition_payload`, `ArbitrationContext`, `ExternalGovernanceAuthorityPort`, `verify_governance_register` in `awf.application.commands.scientific_governance`.

## Strict input sequence

1. Start from a privately held canonical/observed dossier and PR #37's two-reviewer disagreement evidence, exactly bound to the rule and external ledger head.
2. Verify the independent scientific arbitration chain, signed with the existing Ed25519 reviewer role, and the external arbitrator qualification port.
3. Load canonical governance policy `{"schema":1,"quorum":2,"max_transitions":5}` from a private file with its SHA kept externally. The example values **do not certify organizational legality**. Quorum can be 2–5, max transitions 1–16.
4. An appointed governing actor appends an `SCIENTIFIC_GOVERNANCE` **intent** naming exactly one legal `from_state/action` pair. Distinct governors independently sign **that same ledger event** using their scoped `GOVERNANCE_APPROVER` grants.
5. Supply independently retained SHA-pinned qualification evidence for every actor and an **actual, externally trusted governance verifier**. The verifer must check appointment, real-person identity, competence, independence and conflicts against the excluded proposer/scientists/arbitrators/other approvers and the rule/case/policy; there is no production verifier in PR #38.
6. Call `verify_governance_register`: it first re-verifies the complete arbitration chain, signatures, quorum, state and chronology, then invokes the external authority if present. With no real authority, it returns `OPEN` with zero `applied_actions`.
7. Later `SUSPEND` and `REOPEN` actions must cite a new `RULE_SUPPORT` record created after the predecessor's final signature. The original ratification is never deleted; the state is deterministically projected over the full authorized chain.

## Explicit state semantics

- `OPEN`: no accepted procedural ratification, or the original case was reopened.
- `RATIFIED_PROCEDURAL`: this register's source/receipt and governance gates passed under the provided external verifiers. It is **not a scientific-truth determination** and is impossible with only the shipped adapters.
- `SUSPENDED`: a previously procedurally ratified case was suspended with subsequent evidence; it can be reopened.

A signed intent without a verified independent governing authority is **not applied**. Even with a test-only authority, every result has `scientific_adjudications=0`, `training_authorized=false`, `source_rights_verified=false`, `historical_rule_disposition_changed=false` and `review_attestation_authorized=false`.

## Operator boundaries

The private ledger must be subject to restricted access controls. Never commit private credentials, policy anchors, human identities, case files or historical ZIP to GitHub. Do not treat an Ed25519 key as proof of a natural person. A later integration requires a genuine appointment mandate, independent verifier, authenticated policy updates, complete audit/revocation criteria and an authorized transition writer. There is no CLI flag that grants training or final scientific acceptance.

Read [ADR-0031](adr/0031-scientific-governance-register.md) and the source repository's existing reviewer-authentication ADRs before integrating.
