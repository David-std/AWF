# Independent academic-fidelity evaluation protocol — S3

**Status:** specification for a future evidence collection and review workflow, NOT an approved dataset and NOT a completed independent scientific benchmark. Supersedes no source-rights controls. Applies to English and Spanish separately.

## Purpose and separation of datasets

The current AWF synthetic smoke fixture (8 train / 2 validation / sealed placeholder) establishes only engineering function. It is unsuitable as an independent academic test. Never use that placeholder as gold, treat an author/agent's `gold_provenance` string as a reviewer, or open the sealed test set during model/prompt/threshold selection.

A future study must maintain immutable group and source bindings across (a) development/train, (b) validation/model selection and (c) final sealed independent test. Group at minimum by original document and source, with author grouping when possible. Near-duplicates, translations and derivatives of the same underlying document must be assigned to the same group. Record hashes before split assignment and independently audit leakage.

## Admission to the candidate-gold pool

Each prospective case needs:

- Unique `case_id`, `document_group_id`, source/work identifier, language, discipline, genre and timestamp/version.
- Document and source provenance, license/permission evidence (evidence location and reviewer), authorized processing scope and confidentiality classification. An owner claim is an attestation, not third-party rights.
- Original excerpt (kept in private storage), candidate edit, linked claims and citations, exact byte SHA-256 for each content snapshot and evidence-span locator(s).
- Risks explicitly in scope: proposition identity, **negation**, quantities/units, population/sample, inclusion/exclusion, temporal bounds, **causality vs association**, epistemic modality, citation identity and whether each claim is supported by the cited source.
- A known comparison unit and stable model/prompt/decoding snapshot; do not mix different task instructions in a single paired comparison.

Reject case admission if rights, source identity or original content integrity cannot be established. Store texts and annotation notes privately; reports may share only aggregate counts/hashes when disclosure rights allow.

## Annotation workflow and independence

1. Freeze the source, intended task, case identity, protocol and sampling plan **before** showing candidates to reviewers.
2. Assign at least two qualified reviewers, blinded to the model condition and to one another's scores. Record a stable reviewer credential/role, domain qualification, review environment and review timestamp, without asserting independence solely from a JSON field or signed self-claim.
3. Ask each reviewer to inspect original and source evidence, and label **each specified risk dimension** with `PRESERVED`, `DRIFT` or `UNKNOWN`; record short rationale, source span ID, and discrepancy type. Unsupported source claims are not `PRESERVED`.
4. Capture all disagreement records unchanged. An adjudicator with independent source access resolves disagreements or leaves `UNKNOWN`; maintain pre/post-adjudication labels and reviewer provenance.
5. Separate case-level factual/semantic acceptance from readability, academic register and rhetorical appropriateness. Surface grammatical quality does not override an unsupported citation or critical semantic drift. A model must not award itself PASS.
6. Freeze the reconciled test labels and record an externally held digest before final model comparison. Any post-test change requires a visible amendment, not silent relabeling.

### Required per-case annotation fields (conceptual schema)

`case_id`, `document_group_sha256`, `original_sha256`, `candidate_sha256`, `source_evidence_ids`, `rights_evidence_id`, `language`, `genre`, `risk_family`, `blind_condition_id`, `reviewer_id`, `reviewer_conflict_attestation`, `review_timestamp`, `label(PRESERVED|DRIFT|UNKNOWN)`, `evidence_span_ids`, `reason`, `adjudication_status`, `adjudicator_id`, `protocol_version`.

Credentials must be checked by a **separate** attestation/authorization process; fields alone cannot authenticate qualifications or independent review. Do not make a public case file containing proprietary source passages.

## Evaluation and stopping rules

For each frozen case, run identical instructions, original evidence, tokenizer, base revision, decoding settings, length limit and timing method across pinned BASE and BASE+LoRA. Store private raw outputs with hashes and identify model condition only after blinded review. Paired cases and document groups remain linked; no cross-split adaptation after unsealing final gold.

Primary outcome: **critical semantic drift proportion** per arm, counting `UNKNOWN` separately and conservatively (never as PASS), plus paired discordance (base-only fail, adapter-only fail, both fail, neither fail), with document-cluster-aware uncertainty intervals when sample size supports them. Secondary: citation grounding/attribution, quantitative preservation, false clears, abstention rate, functional edit utility and reviewer-rated academic clarity; report ES/EN and risk-family strata separately. Record reviewer agreement and unresolved disagreements. Include all attempted samples and inference failures in denominators, not just successful outputs.

Define the study sample size/precision and stop criteria in a pre-registered evaluation plan based on feasible licensed data. Do not invent a target improvement, effect size or statistical significance before data exist. A two-case synthetic smoke run has no meaningful statistical power for scholarly claims.

**Quality gate:** `critical FAIL → REJECTED`, `critical UNKNOWN → NEEDS_REVIEW`, and no independent source-grounded gold → `MODEL_QUALITY_UNVERIFIED`. Detector percentages are separate observations and cannot certify authorship, scholarly fidelity or acceptability.

## Evidence state as of 2026-10-21

- Two fictional validation cases underwent genuine local inference on pinned Qwen2.5-0.5B-Instruct and the PEFT LoRA adapter, **one output changed**, one unchanged, zero substantive labels.
- No source-grounded third-party reviewed case has been admitted; no annotator or gold labels were fabricated. Existing training validation was not exposed to the optimizer, but it is a development fixture and not a blind independent holdout.
- The separate fictitious placeholder remains sealed. `independent_gold_verified=false`, `semantic_equivalence_verified=false` and `model_quality_certified=false`.

## Engineering increment: PR #47 candidate intake (not independent gold)

A standalone [metadata-only diagnostic](GOLD_INTAKE_S3.md) now checks SHA-pinned manifest and optional blinded annotations, grouped isolation including source/content hashes, and missing or conflicting two-reviewer opinions. It never reads the sealed test split or source text, does **not** independently verify rights or reviewer identity, and always returns `independent_gold_verified=false` and `document_acceptance=NEEDS_REVIEW`. The [external reviewer instructions](GOLD_REVIEWER_INSTRUCTIONS_S3.md) specify the work that remains outside the software: access to source evidence, authorized use, blinded genuine expert judgement and independent adjudication. This is engineering readiness, not a new scholarly finding.
