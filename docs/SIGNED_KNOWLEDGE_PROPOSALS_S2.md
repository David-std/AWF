# Signed historical-rule proposals — Sprint 2 prototype

This workflow is **opt-in** and does not approve a historical knowledge rule. Complete PR #31's private dossier and PR #32's source-bound evidence links first. The AWS 3.19.1 ZIP, detailed rule descriptions, reviewer notes, private evidence and signing keys stay on the owner's machine.

## Canonical causal chain

```text
pinned ZIP + manifest
  -> private source-bound review packet (only review_template editable)
  -> one or more RULE_SUPPORT ledger events linked by evidence_ids
  -> KNOWLEDGE_REVIEW_PROPOSAL event containing SHA of the whole review_template
  -> offline Ed25519 KNOWLEDGE_REVIEWER signature over that proposal event
  -> REVIEW_ATTESTATION ledger event (existing evidence attest)
  -> private inspect-review with complete inventory + external policy/head
```

Generate the proposal payload with the pure `private_dossier_proposal_payload()` application function using the **canonical rule** from `prepare_review()`, the same immutable manifest and the observed private annotated rule. Do this only after `audit_private_dossiers()` has returned `PROPOSAL_DOCUMENTED` for that specific rule. The output is canonical JSON containing hashes and the actor ID, not the private reason text. Keep it in a Git-ignored local directory.

Append its exact bytes:

```shell
awf evidence append /private/rule-proposal.json \
  --kind KNOWLEDGE_REVIEW_PROPOSAL --run-id review-run-001 \
  --subject-id DSR-001 --database .awf/evidence/ledger.sqlite
```

Retain the resulting `event:<digest>` reference. The actor in the review template must be the **same actor ID** as the signer in a separately held SHA-pinned authorization policy. The policy's grant must include `KNOWLEDGE_REVIEWER`, the exact run and public DSR ID, valid dates and an unrevoked key.

Construct a `ReviewerClaim` with role `KNOWLEDGE_REVIEWER`, target event reference from the committed proposal, matching run/DSR ID, and an issued-at timestamp. The reviewer signs `claim.signing_bytes` **outside AWF** and shares only `SignedReviewerClaim.to_bytes()`. The existing `awf evidence attest` command validates that signature and appends the signed `REVIEW_ATTESTATION` event, returning a different event reference. Never put the signing key into an archive, CLI log, repository or ledger.

## Full private inspection

Prepare a bounded, canonical JSON inventory, with no duplicate keys, in this schema. These are placeholder values, **not real hashes or valid evidence**:

```json
{"attestations":{"DSR-001":{"attestation_ref":"event:<real-signed-event-digest>","proposal_ref":"event:<real-proposal-event-digest>"}},"schema":1}
```

The inventory must contain exactly every currently `PROPOSAL_DOCUMENTED` rule; rules still `OPEN` or `PROPOSAL_INCOMPLETE` are not silently promoted. Capture a new externally trusted ledger head **after** the attestation was committed. Then run:

```shell
awf knowledge inspect-review /private/aws.zip --batch-size 12 \
  --evidence-database .awf/evidence/ledger.sqlite \
  --review-run-id review-run-001 --expected-head TRUSTED_LEDGER_HEAD \
  --attestation-inventory /private/attestation-inventory.json \
  --reviewer-policy /private/reviewer-policy.json \
  --expected-reviewer-policy-sha256 TRUSTED_POLICY_SHA256
```

The output includes only public rule IDs, missing references and a boolean `credentials_authorized`. Exit 2 means invalid/incomplete inventory or insufficient authorization; independent ledger/policy corruption also fails. The legacy inspector without these flags behaves as before.

**These controls do not establish human identity, independence, expertise, scientific merit, source licensing, training rights, or `REVIEW_ATTESTED`.** The submitted actor and the evidence event are authenticated only as far as the independently pinned policy and head can be trusted. No 168 MUST rule is adjudicated by this operation.
