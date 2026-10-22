# AWF — PR #47 blinded candidate-gold intake handoff (2026-10-21)

**Repo:** David-std/AWF. [Draft PR #47](https://github.com/David-std/AWF/pull/47) branch `feat/s3-blind-gold-intake`, base **PR #46** `feat/s3-paired-adapter-evaluation` → #45 → #43. **PR #44 remains a separate parallel experimental branch** and was neither merged nor copied.

## Predecessor status and private data

PR #46 final SHA `36a9a5f2aefa947f9424c91c671245716c7a3731` had independent CI push+PR completed **SUCCESS 4/4 each**. A real local RTX 4050 BASE vs post-fix LoRA comparison over **two synthetic validation prompts** completed; one output differed and the private paired receipt SHA was `c340de7458b9898749a226b23759d2ba43d46d3b054aa2f656ad603d062559aa`. Both LoRA runs, manifest/training splits and paired result were already copied into durable owner-private Documents storage with byte-level SHA checks; no training was repeated and no historical files overwritten during PR #47. Read the preceding [PR #46 handoff](2026-10-21-S3-PR46-PAIRED-DIAGNOSTIC.md).

## Implemented on PR #47

- `src/awf/evaluation/gold_intake.py`: standalone stdlib CLI with externally pinned SHA-256 metadata manifest and optional review annotations (also externally pinned). No raw source passage, candidate output, model weights or holdout bytes are read or exported.
- Enforces case schema, role, 2 opaque blind conditions A/B, supported risk families, unique identifiers, and disjoint train/validation/test-sealed groups by document, author, source, original-content SHA and source-evidence SHA.
- `test_sealed` cannot be annotated in this development tool. Exactly two distinct reviewer IDs per case/condition/family are provisionally tallied. Missing votes, disagreements and concordant UNKNOWN remain UNKNOWN; a confirmed DRIFT in another critical family dominates UNKNOWN at case level. Labels are never upgraded to independent academic gold on the basis of names or agreement alone.
- `tests/unit/test_gold_intake.py`: 15 focused synthetic unit tests passed locally using system Python 3.12, including CLI execution, hash tamper/duplicate JSON, leak prevention, reviewer disagreements, content-hash leakage and privacy properties.
- `docs/adr/0038-blind-gold-candidate-intake.md`, `docs/GOLD_INTAKE_S3.md`, [reviewer guide](../GOLD_REVIEWER_INSTRUCTIONS_S3.md) and updates to `AWF-R048` trace.

## CI and scientific boundaries

Initial commit `70deafbfbe75cb0690f765d235446eae53df4dc2` failed CI format; the failure was not hidden. Code + test corrections committed through `98b52c959ad1c747e5c8997c8597985ce1aaed91`. **Inspect the exact SHA's push and PR CI before claiming full green; this documentation commit has a later SHA requiring independent checks.** No quantitative academic claims or rights/human reviewer verifications exist yet.

`source_rights_independently_verified=false`, `human_gold_adjudicated=false`, `independent_gold_verified=false`, `semantic_equivalence_verified=false` and `document_acceptance=NEEDS_REVIEW` must remain false/needs review regardless of local unit or CI success.

## External prerequisites

1. A **rights-cleared**, originally sourced academic corpus with group IDs, original passage and cited source evidence, a permission/rights record and version pins; do not presume ownership of coauthored papers or publisher articles.
2. **Two qualified independent reviewers** with verifiable identities, actual access to the sources, conflict checks and genuinely blind evaluation; separate adjudication for disagreement.
3. A **prospectively frozen A/B mapping**, grouped split, source/rights audit and out-of-band holdout integrity attestation. Never use synthetic train/validation nor the placeholder holdout as scientific gold.

No review personnel or owner text has been silently substituted. Next integration should be explicit evidence-byte checks, verified external reviewer/rights authority and blinded adjudication receipts, rather than inventing a score or training another adapter.
