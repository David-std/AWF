# ADR-0030 — Third-party arbitration records and append-only reconsideration

Date: 2026-10-20. Status: **engineering candidate**, review pending. Stacked S2 draft PR #37 on #36 → #35 → #34 → #33 → #32 → `develop`. Requirement AWF-R039.

## Scientific-method basis and explicit limits

JBI's *Manual for Evidence Synthesis* recommends two independent critical appraisals, discussion of discrepancies and a third reviewer if consensus is impossible ([JBI section 7.3.6.3](https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355598976/7.3.6.3%2BAssessment%2Bof%2Bmethodological%2Bquality)). PRISMA 2020 items 8–9 ask researchers to report reviewer independence, collection methods and disagreement resolution ([PRISMA expanded checklist](https://www.prisma-statement.org/s/PRISMA_2020_expanded_checklist-yc78.pdf)). These are **methodological analogies**, not standards certifying this application, its reviewers or any historical AWS rule. The distinction between a third-person credential, verified professional competence, and scientific correctness is mandatory.

## Architectural decision

1. Add `EvidenceKind.SCIENTIFIC_ARBITRATION` and `ReviewerRole.SCIENTIFIC_ARBITER`, extending the **existing** reviewer trust-policy and Ed25519 event signature machinery. The role is separate because the prior `SCIENTIFIC_REVIEWER` may not arbitrate its own evidence. No new key-management, signing service or backend is created.
2. Start only from PR #36's **verified divergent or inconclusive case**, including canonical proposal, both signed scientific assessments, independently held ledger head and a separate SHA-pinned private case plan. A concordant pair is not automatically elevated to scientific truth; no arbitrary review can bypass the prior evidence checks.
3. Record one private, canonical `scientific_arbitration` event with exact source and requirement SHA, proposal ref, two assessment refs, case digest, actor, evidence-event refs, structured position `SUPPORT/CONTEST/DEFER/UNRESOLVED`, substantive reasoning and limitations. Append a separately signed `REVIEW_ATTESTATION`, reusing the existing `ReviewerRole.SCIENTIFIC_ARBITER`. The signed credential proves control of a policy-bound key, not identity or credentials of a physical person.
4. The arbitrator may not equal the rule proposer, either of the two scientific reviewers, or a prior arbitrator in the same reconsideration chain. Each evidence ref must bind `RULE_SUPPORT`, exact run/subject, verified chain and precede the signed decision.
5. An appeal is another immutable event with `supersedes_ref` to the previous decision, an explicit reconsideration basis, a **new actor**, and at least one newly recorded support event after the previous signed ruling. Appeals do not rewrite prior events; chains are bounded to 5 decisions (initial + up to four reconsiderations), until volume and governance justify an alternative. No time-based appeals deadlines or legal rights are assumed.
6. A separate `ExternalQualificationPort` is a mandatory **outside authority** for procedural qualification: it must evaluate appropriate expertise, verified distinct-person identity, conflicts of interest, institutional independence, and an externally pinned policy/evidence instrument against the actual rule/case and excluded actors. A checksum plus declared role is insufficient. No real external qualification adapter is included. Without one, result: `independently_qualified=false`, `procedure_verified=false`, even when all receipts authenticate.
7. With an injected verifier whose external authority is independently trusted, the prototype may report `procedure_verified=true`; that means the **procedural evidence gate** was verified under the provided policy, not scientific truth. Even then `scientific_adjudications=0`, `review_attestation_authorized=false`, `training_authorized=false`, `source_rights_verified=false`, and `historical_rule_disposition_changed=false`. This is an intentional separation until a formal, independently governed acceptance and reversible state-transition policy exists.
8. Leave original ZIP, unpublished source texts, arbitration notes, keys, qualification evidence and reviewer identities in local private storage, not in GitHub, logs, model prompts or corpus training. No new CLI that silently grants dispositions or writes to the 184-rule registry.

## Negative cases and threat model

- Same actor with a second key or promoted role cannot arbitrate themselves.
- Swapped signatures, changed source/proposal/case, missing original dispute, revoked/expired signer, stale chain head, changed raw records, wrong event types, wrong chronological order, contradictory/ambiguous refs fail closed.
- Mere self-asserted degree, ORCID, university profile or user-controlled qualification JSON must not substitute for an independent verified qualification/COI chain.
- Reconsideration referencing an old evidentiary record rather than fresh recorded support is rejected; novel argument with no fresh support stays an unresolved case, not an accepted appeal under this pilot.
- A reviewer can be biased even if two keys and the data signatures verify; the software does not infer statistical independence or truth.

## Limitations and deferred increments

This PR is a credential- and source-bound procedural record pipeline only. It does NOT decide final scientific claims, empirically validate legal/ethical reviewer qualifications, settle licensing, support actual jury quorum, implement inter-institution conflict disclosure, or authorize data/ML training. A separate future governance ADR must define panel size, independent appointment, appeal criteria, recusal, a real evidence examiner, revocation/withdrawal and an explicit, reversible adjudication authority before raising `scientific_adjudications` above 0. Do not reinterpret `procedure_verified` as approval to train.

## Verification

Synthetic SQLite event chain, authentic test Ed25519 signatures, adversarial role promotion, revoked key, bounded chain, new evidence chronology, tampering and externally pinned fake qualification authority. Run locked Ruff/Pyright/pytest/build on Linux/Windows Python 3.12/3.13; record final SHA after CI, not before.
