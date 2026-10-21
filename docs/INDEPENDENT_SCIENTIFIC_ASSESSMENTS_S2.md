# Independent scientific assessment receipts — S2 API prototype

This prototype builds on **draft PR #32 followed by draft PR #33**. It does not constitute completed scientific adjudication. The first stage is the existing private `plan-review`, `inspect-review`, `RULE_SUPPORT` evidence, signed `KNOWLEDGE_REVIEW_PROPOSAL` and Ed25519 `KNOWLEDGE_REVIEWER` attestation described in `docs/SIGNED_KNOWLEDGE_PROPOSALS_S2.md`.

The next stage is a **different** actor/credential, granted `SCIENTIFIC_REVIEWER` with the same run and DSR scope in an externally SHA-pinned `ReviewerTrustPolicy`:

1. In a Git-ignored private workspace, create an assessment using `scientific_assessment_payload(source_id=..., archive_sha256=..., requirement_id=..., requirement_sha256=..., proposal_ref=..., actor_id=..., verdict=..., method_notes=..., evidence_analysis=..., limitations=...)`. Notes contain actual locally reviewed arguments and limitations, not placeholders. The `verdict` is a *declared opinion*: `SUPPORT`, `CONTEST` or `INCONCLUSIVE`.
2. Append its exact canonical bytes as an `SCIENTIFIC_RULE_ASSESSMENT` event with the SAME `run_id` and `subject_id` as the proposal. Record `event:<digest>` (not the payload SHA).
3. The second key signs a `ReviewerClaim` targeting that exact event with role `SCIENTIFIC_REVIEWER`. Append through the existing `evidence attest` command. Capture a new externally retained trusted ledger head *after* both attestations.
4. Create a canonical private JSON inventory of **all** documented DSR rules:
   ```json
   {"assessments":{"DSR-001":{"assessment_ref":"event:<digest>","attestation_ref":"event:<digest>"}},"schema":1}
   ```
   Parse it using `parse_scientific_assessment_inventory`. This current increment exposes `verify_independent_scientific_assessments(...)` through Python application service, not yet through a new CLI switch. The caller supplies the same previously verified `proposal_refs`, canonical/observed private packets, expected head, independent policy and trusted time.

The outcome includes only checked/verified counts, public rule IDs and explicit false flags for scientific adjudication, `REVIEW_ATTESTED` and training. It never prints assessment notes or signature material. A clean return means provenance and scoped credential *consistency* only. Human identity/independence, academic validity, source-rights verification and permission to train are **not established**.

Store the AWS ZIP, private JSON packets, notes, SQLite ledger, private keys, policy and external trust anchor in authorized private storage. Never add them to Git, an Actions artifact or a public log. Do not claim a physical Windows run unless personally executed and recorded. See [ADR-0027](adr/0027-independent-scientific-assessment-receipts.md).
