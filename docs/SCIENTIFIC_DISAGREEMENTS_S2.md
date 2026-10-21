# Scientific disagreement protocol — S2 private API

This is **structured disagreement triage**, not final adjudication. It extends the separately signed `SCIENTIFIC_RULE_ASSESSMENT` receipts from [PR #34](https://github.com/David-std/AWF/pull/34) with a **second independently authorized and signed assessment** for each documented historical rule proposal.

## Inputs and responsibilities

Application API `verify_disagreement_protocol` consumes canonical/observed dossier packets, an exact proposal inventory, *left* and *right* signed scientific-assessment inventories, a private dispute-case map and a map of **externally retained** expected case hashes. The caller supplies one SQLite evidence store, the run, a trusted current ledger head, an externally pinned reviewer policy, signature verifier and trustworthy verification time.

Neither the rule-proposing actor nor the other scientific reviewer can substitute for the second independent reviewer. The verifier checks two separately signed `SCIENTIFIC_REVIEWER` assessments and refuses same-actor or same-event pairs. Actors/keys are credential-level claims, not confirmed natural-person identities.

## Case plan

A canonical JSON payload returned by `disagreement_case_payload` has a fixed schema, source/archive/rule SHA, exact signed proposal reference, both assessment references, substantive *claim_in_dispute*, *evidence_gaps*, *methodological_divergence*, and one `proposed_next_action`:

- `REQUEST_EVIDENCE`: seek verifiable additional primary evidence.
- `REPLICATE_EXPERIMENT`: reproduce methods and test controls.
- `ESCALATE_PANEL`: send the documented dispute to an appropriately independent third reviewer/panel.
- `RETAIN_DISAGREEMENT`: record that the available evidence does not decide the matter.

Use the local file's SHA-256 as an externally retained expected hash. A digest pinned only **inside the same editable file** does not establish integrity. The case plan must remain confidential; the output returns **only public DSR IDs, classification, counts and explicit non-authorization flags**.

## Possible outcomes

`CONCORDANT_SUPPORT`, `CONCORDANT_CONTEST`, `DIVERGENT`, `INCONCLUSIVE`. Divergent or inconclusive cases without a verified docket are reported as open. A complete docket means that the issue and next action were **documented**, not that a panel met or resolved the disagreement.

Result invariants: `scientific_adjudications=0`, `training_authorized=false`, `review_attestation_authorized=false` and `source_rights_verified=false`. A matching `SUPPORT` pair cannot bypass copyright, source validity, dataset permissions, model verification or the remaining 168 undecided MUST items.

This pilot reuses the original ledger, reviewer roles and signed envelopes; it does **not** introduce another signature protocol. A later implementation can support independently authorized panels and appeal/revision, but must have explicit governance and tests first. See [ADR-0029](adr/0029-scientific-disagreement-triage.md).
