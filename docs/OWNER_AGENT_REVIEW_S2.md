# S2 owner-led AI agent review — private prototype API

This path is usable for a solo researcher **without requiring an independent university or hired external authority to approve a pilot**. It is **not a replacement for independent scientific certification** or source rights.

## Actors

- **Project owner**: defines tasks, externally pins source/task and reviewer-policy hashes, operates or holds the Ed25519 project-owner key, explicitly signs `APPROVE_PILOT_EVALUATION`, `REQUEST_REVISION` or `REJECT`. May also be the original rule proposer.
- **Reviewer agents A and B**: separately run language models or a code-based reviewer on a shared, pinned task. For now their `agent_id`, `execution_id`, and `model_id` are **self-reported metadata**; code can verify uniqueness and integrity of recorded bytes but cannot attest real inference by Qwen/Gemini.
- **AWF**: verifies externally retained ledger head, exact event references, canonical bytes, source/rule SHA, timestamps/roles, two reports, cited `RULE_SUPPORT` ledger events, and the owner's existing scoped Ed25519 authorization.

## Required workflow

1. Keep AWS historical ZIP and private source documents local. Pin original source SHA, task SHA, reviewer-policy SHA and ledger head independently from the mutable database.
2. Reuse a source-bound `KNOWLEDGE_REVIEW_PROPOSAL` with a `KNOWLEDGE_REVIEWER` signed attestation, then append two `AGENT_REVIEW_REPORT` events using `agent_report_payload`.
3. Append one `OWNER_EVALUATION_DECISION` event using `owner_review_decision_payload` referencing **both** report event IDs in order. Sign only with a scoped `PROJECT_OWNER` claim using the preexisting Ed25519 `append_signed_review_claim` implementation.
4. Invoke `verify_owner_review` using the exact externally pinned head/source/task/policy SHA, proposal and review refs. The response can be `pilot_evaluation_approved=true` only for the owner's *evaluation-only* action.
5. Do not treat this as model execution, an observed experiment, a dataset rights grant, independent scientific truth, historical requirement acceptance, or training authorization.

## Result contracts

The output includes verified report count, verdicts, distinct claimed model IDs, signed owner action and `pilot_evaluation_approved`. It also explicitly returns `independent_scientific_adjudication=false`, `scientific_adjudications=0`, `training_authorized=false`, `source_rights_verified=false` and `historical_rule_disposition_changed=false`.

Both reports must reference actual `RULE_SUPPORT` events of the same run/subject that predate each report. This verifies **ledger links**, not source validity. The decision signer may be the original proposer because the output is labelled OWNER-GOVERNED rather than EXTERNALLY INDEPENDENT. A different signer, duplicate execution, cross-task ref, stale head, altered hashes or mismatched owner grant fails closed.

## Follow-on changes

**Do not add further ceremonial roles or approvals as the next sprint.** Build a real source/claim checking adapter and an instrumented model runner with immutable input/output hashes, then evaluate individual historical rules. The owner signs a result only after inspecting that experimental evidence and source-rights restrictions.

See [ADR-0032](adr/0032-owner-governed-agent-evaluation.md).
