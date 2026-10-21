# S3 — Bounded synthetic checker-scope benchmark (AWF-R045)

**Status:** provisional engineering experiment, draft PR stacked on #42. This is not a human-adjudicated scholarly benchmark. It is a reproducible audit of **what the current deterministic checker actually returns** when exposed to developer-labelled counterexamples.

## Execution

```powershell
# Store a locally created synthetic-only JSON file outside tracked Git paths.
$sha = (Get-FileHash -Algorithm SHA256 .awf\private\synthetic-benchmark.json).Hash.ToLowerInvariant()
awf evaluate-synthetic .awf\private\synthetic-benchmark.json --expected-sha256 $sha
```

Input is SHA-256-bound to the exact UTF-8 bytes and must be a regular file, ≤2 MiB. Contract schema is strict, `dataset_role=SYNTHETIC_DEVELOPMENT` **only**, 2–128 cases, ES/EN. Each case contains a `baseline`, `candidate`, original independently bound exact-invariant `contract`, developer-synthetic label `DRIFT`/`PRESERVED`, `risk_family`, language and document ID. The evaluator invokes the real `verify_exact_invariants` with the actual case bytes. It never accepts model/self-supplied verdicts or a claimed independent-gold status.

Data is read locally and original/candidate text is **not printed in reports**. The report includes identifiers, text hashes, recorded syntactic decisions, status counts and grouped metrics. No model weights, external API, private AWS ZIP or research paper is used. The source and annotations are not licensed for model training by this operation.

## Three-valued accounting

Treat `FAIL` as a **detected syntactic problem**, `PASS` as a **syntactically unflagged** candidate, and `NEEDS_REVIEW` as **abstention/escalation**. Even `PASS` never means academic approval.

| Synthetic developer label | FAIL | PASS | NEEDS_REVIEW |
|---|---|---|---|
| DRIFT | detected (`fail_on_drift`) | false-clear (`false_clear_on_drift`) | review on drift |
| PRESERVED | false rejection (`fail_on_preserved`) | unflagged preserved (`pass_on_preserved`) | review on preserved |

- `strict_drift_detection_rate = FAIL_on_DRIFT / all_DRIFT`, including abstentions in the denominator.
- `false_clear_rate_on_drift = PASS_on_DRIFT / all_DRIFT`.
- `review_escalation_rate = all_NEEDS_REVIEW / all_cases`.
- `failure_precision_excluding_abstentions = FAIL_on_DRIFT / all_FAIL`; explicitly excludes reviewed cases.
- Empty denominators are `null`, never 1.0. Results are separated by ES and EN, never blended to establish cross-language generalizability.

### Synthetic engineering fixture

The unit-test fixture has eight fully fictional short pairs: four ES, four EN; includes protected metric alteration, unlisted numeric addition, contextual qualification and an appended distant contradiction while preserving an exact anchor. Expected on current checker: 2 FAIL-on-DRIFT, 2 false-clears-on-DRIFT, 1 review-on-DRIFT, 2 PASS-on-PRESERVED and 1 review-on-PRESERVED. **These values are assertions about the software fixture, not empirical generalization to real papers.**

## Scope and next milestone

No `REVIEWED_GOLD`, `HOLDOUT` or training-labelled input is accepted. That deliberate restriction prevents a caller from claiming independent annotation merely by setting a JSON field. Real gold ingestion will require separate source-rights evidence, reviewer provenance, document-group separation, disagreement tracking and holdout isolation, followed by external annotation and statistical confidence intervals. The 168 historic AWS MUST requirements remain UNRESOLVED and 16 DEFERRED_LAB remain EVAL_ONLY; PR #43 issues no rule ratifications.

Related: [ADR-0035](adr/0035-synthetic-evaluation-boundary.md), [PR #41 historical probe](HISTORICAL_RULE_PILOT_S2.md), [PR #42 measured inference](LOCAL_AGENT_EXECUTION_S2.md).
