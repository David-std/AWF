# ADR-0029 — Reproducible scientific disagreement triage, not adjudication

- Date: 2026-10-20.
- Status: provisional S2 implementation, pending independent scientific/code review.
- Dependency: draft PR #35 `feat/s2-source-rights-provenance`, HEAD `895e9a39fc8415e41263a5dfafdba7ef10247275`; PR #35 remains stacked on #34 → #33 → #32.
- Requirement: AWF-R038.

## Research basis and limits

JBI's evidence-synthesis manual recommends that independent reviewers discuss disagreements and use a third reviewer when necessary. PRISMA 2020 requires explicit reporting of the number and independence of reviewers and how disagreements were resolved. **AWF adapts this governance principle as a design choice; neither guideline validates AWF's implementation, nor does it establish a numerical agreement metric or prove reviewer independence.**

- JBI, *Critical appraisal*, 2024: https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355828247/4.2.7%2BCritical%2Bappraisal
- JBI, *Assessment of methodological quality*, revised guidance: https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355598976/7.3.6.3%2BAssessment%2Bof%2Bmethodological%2Bquality
- PRISMA 2020 expanded checklist, items 8–9: https://www.prisma-statement.org/s/PRISMA_2020_expanded_checklist-yc78.pdf

These are methodological references, not legal rights or formal AWF acceptance criteria.

## Decision

1. Compare **two separately signed scientific assessments** of the exact same signed historical-rule proposal. Reuse PR #34's `SCIENTIFIC_REVIEWER`, `SCIENTIFIC_RULE_ASSESSMENT`, `verify_independent_scientific_assessments`, existing Ed25519 verifier and external pinned reviewer policy. Do not invent a new signer role, signature format or key material.
2. Both assessment inventories must independently pass PR #34's complete per-dossier verification using **the same independently held ledger head**, source SHA, trusted time and scoped reviewer policy. All `PROPOSAL_DOCUMENTED` IDs are required: omission is failure, not an implicit negative.
3. Read both exact events in one additional fully audited, immutable SQLite snapshot under the **same** head; require distinct assessment event digests, distinct signed actor IDs, the same proposal ref and source/run/rule scope. Different credential IDs do **not** prove different human beings or meaningful scientific independence.
4. Deterministic comparisons yield `CONCORDANT_SUPPORT`, `CONCORDANT_CONTEST`, `DIVERGENT` or `INCONCLUSIVE`. A matching opinion is not an adjudicated truth, and `INCONCLUSIVE` is never silently treated as agreement or a negative.
5. `DIVERGENT` and `INCONCLUSIVE` require a **private, canonical, externally SHA-pinned case plan**. It binds the same source/proposal/two assessments, with the question at issue, missing evidence, methodological divergence and a declared next action: `REQUEST_EVIDENCE`, `REPLICATE_EXPERIMENT`, `ESCALATE_PANEL` or `RETAIN_DISAGREEMENT`. If absent, it is reported as missing and `evidence_links_verified=false`.
6. Case notes are evidence-planning declarations, **not independently authenticated arbitration**. An editable note or even a matching hash cannot establish expert competence, a third actor, an actual meeting, a result, conflict-of-interest disclosure or a decisive resolution.
7. No matter how many assessments agree, **scientific_adjudications=0, review_attestation_authorized=false, training_authorized=false**. Neither a favorable verdict nor `evidence_links_verified=true` changes the historical registry, a rights inventory, rule dispositions or application acceptance.
8. No new CLI mutation path, database migration, actor grant, model inference, private-source download or proprietary dataset publication. This is an **application service** pilot.

## Workflow and fail-closed gates

`proposal → signed assessment A → signed assessment B → verify paired snapshots → compare → open private case if divergence/uncertainty → human-led follow-up (not implemented)`.

Reject: missing/extra/surrogate review inventory, same signed actor, same event twice, swapped attestations, changed proposal, revoked role, stale external head, source/rule/run mismatch, malformed notes, duplicated JSON keys, unpinned or modified case bytes, extra unsolicited cases, inaccessible evidence. A valid case documents the question and a possible next step, *not that the next step occurred*.

## Design tradeoffs

The first cut intentionally calls PR #34's full authorization verification **twice**, then makes one more fully audited read for paired comparison. This is expensive but traceable. Replacing it with a shared snapshot requires equivalent negative regression coverage and performance measurements, not an untested optimization. Dual reports with the same verdict need not be independent observations in the statistical sense; no kappa, validity coefficient or confidence score is invented.

A genuine final adjudication protocol requires separate independent identity/qualification and conflict-of-interest checks, published criteria for deciding unresolved questions, controlled third-reviewer authority, signed resolution referencing source evidence and all dissent, durable reconsideration/revocation semantics, and integration with both rights and downstream scientific validation gates. **Those are deferred**, not hidden inside `REVIEW_ATTESTED`.

## Verification

Only synthetic private ledger events and cryptographic keys are used in tests. Required outcomes include two distinct real Ed25519 credentials, positive/negative consensus, opposing verdicts, inconclusive, absent docket, modified externally pinned bytes, reordered/mismatched references, revoked reviewers and stale chain head. Run the locked Ubuntu/Windows × Python 3.12/3.13 pipeline and report actual SHA-specific results. Keep PR draft until independent review and source-rights design assessment.

## Verified engineering checkpoint

The code SHA `55f1c03a1904148e7c7360da4a2dd05ee695f49b` completed [push CI 39542413641](https://github.com/David-std/AWF/actions/runs/39542413641) and [PR CI 39542418761](https://github.com/David-std/AWF/actions/runs/39542418761), each 4/4 SUCCESS on Ubuntu/Windows × Python 3.12/3.13. Ubuntu Python 3.12 recorded 449 pytest PASS, Pyright 0 errors/0 warnings, Ruff lint/format and package build PASS. This describes a source-controlled engineering baseline, not a reviewed research outcome. A final documentation commit must be checked at its own exact SHA.
