# S2 — third-party arbitration and reconsideration (private API)

`awf.application.commands.scientific_arbitration` provides:

- `arbitration_payload(...)`: canonical private event bytes binding source/rule/proposal, both signed assessment references, original SHA-pinned disagreement case, an arbitrator ID, supported position, reasoned findings, limitations, and exact primary evidence references.
- `verify_scientific_arbitration(...)`: verifies **the full preceding PR #36 disagreement protocol** before checking one or more chained Ed25519-signed arbitration receipts against the same externally retained ledger head. A new signed reviewer role (`SCIENTIFIC_ARBITER`) uses existing reviewer grant/signature mechanisms.
- `ExternalQualificationPort`: optional injection point for an **independently qualified external authority**. The actual implementation is **absent**; no self-asserted licence, resume or different public key is enough. It must assess real-person distinction, expertise, conflicts of interest and governing policy with separately trusted evidence bytes.

## Lifecycle

1. Proposal authenticated by a knowledge reviewer (PR #33).
2. Two independent assessment receipts authenticated (PR #34).
3. Divergence or uncertainty case documented and integrity checked (PR #36).
4. Third actor writes a canonical decision event, cites exact source-support ledger events, and signs it with its scoped `SCIENTIFIC_ARBITER` grant.
5. Optional reconsideration cites `supersedes_ref`, a substantive basis and fresh evidence recorded **after** the previous ruling; a different arbiter signs the new event. Earlier acts remain immutable.
6. A qualified external authority must then inspect independently pinned evidence, human expertise, conflicts and person identity for every arbiter. Without that check, the result is **not** procedurally validated.

The application returns only metadata: `authenticated_decisions`, `latest_position`, `appeal_count`, `independently_qualified`, and `procedure_verified`.

**Permanent non-authorization for this slice:** `scientific_adjudications=0`, `training_authorized=false`, `source_rights_verified=false`, `review_attestation_authorized=false`, `historical_rule_disposition_changed=false`. Even a `SUPPORT` position does not mutate a rule or license machine learning.

All examples in tests are invented and synthetic. Real reviewer credentials, private case notes, evidence bytes and the AWS historical ZIP must stay outside GitHub and CI. This is an **engineering prototype for procedural traceability**, not an operational human-review board or an externally certified scientific ruling.

References and decisions: [ADR-0030](adr/0030-third-party-scientific-arbitration.md), [ADR-0029](adr/0029-scientific-disagreement-triage.md).
