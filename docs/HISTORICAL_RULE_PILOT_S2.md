# S2 — pilot on the SHA-bound historical AWS ledger

Status: **experimental, syntactic measurement only**, stacked over draft PR #40. No rule adjudication, no neural run, no external API call.

## Pinned input

Required archive: **AWS 3.19.1**, SHA-256 `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`. The ZIP is private; it must remain external to the Git repository. The existing `PinnedAwsArchive` verifies original archive bytes and the 184-entry ledger.

Select six authentic historical rules: `DSR-001` (hash-bound audit), `DSR-055` (changed spans and hashes), `DSR-059` (atomic semantic checks), `DSR-063` (magnitude not semantic permission), `DSR-065` (unsupported additions), `DSR-066` (claim preservation). These historical rule IDs are **not** independently approved. The pilot uses their exact original statement bytes privately, with no published statement strings.

## Reproduction

```bash
awf knowledge pilot /private/path/academic_writing_suite_v3_19_1_product.zip \
  --manifest provenance/source-manifest.json
```

Output is a source-text-free JSON summary, hash-bound and with per-rule synthetic mutation statuses. It is **not** permission to TRAIN, REVIEW_ATTESTED or KEEP_AS_CODE. The private ZIP is parsed, but historical executable code is never run.

For each source statement, choose a unique source-local anchor (literal plus nearby context) and measure five deterministic cases: original unchanged, protected literal mutation, immediate-context mutation, unlisted numeric addition, and a distant contradictory sentence. No external paper or human-composed research text is treated as a labelled gold corpus.

## Initial local result (2026-10-21)

From the original ZIP verified by SHA: **6 authentic rule statements, 30 mutations**. Syntactic statuses: **12 PASS, 12 NEEDS_REVIEW, 6 FAIL**. All **6 distant semantic overrides returned PASS** for the local syntactic scope despite an intentionally contradictory qualifier; all six retained `document_acceptance=NEEDS_REVIEW`. This is a measured **blind spot**, not a semantic recall statistic or safe document approval.

All source IDs and historical implementation pointers are inspected for presence in the private ZIP, but existence is not proof that their underlying code works or that claims are scientifically sound. The report deliberately includes no source excerpts.

## Exit criteria and next increment

Independent, rights-cleared text and gold labels are needed before evaluating true semantic precision/recall. Contrast source logic and historical self-tests separately, then instrument an `AgentExecutionPort` for actual provider calls and measured outputs, with offline fake adapters. None of the 168 MUST rules are adjudicated, and 16 DEFERRED_LAB remain EVAL_ONLY. This pilot must never be described as training validation or detector efficacy.
