# ADR-0035 — Separate synthetic checker diagnostics from scholarly gold evaluation

**Date:** 2026-10-21. **Status:** provisional S3 implementation, stacked draft PR #43 above #42.

## Problem

PR #41 observed six syntactic false-clears on deliberately contradictory edits; PR #42 instrumented a real local Qwen call, but neither can quantify academic semantic fidelity or adjudicate research sources. Running a neural model and asking the same model to approve the edit would be circular, whereas collecting ad hoc PASS/FAIL arrays from developer claims would not prove the checker executed.

## Decision

Add a **strict synthetic-development** benchmark that invokes the actual SHA-pinned exact-invariant checker for every case and counts synthetic developer labels without upgrading those labels to independent human gold. Keep original and candidate texts private; export only metadata, SHA-256 hashes, statuses, error categories and rates. Explicitly separate `FAIL`, `PASS` and `NEEDS_REVIEW` and include abstentions in denominators of conservative detection rates; disallow `HOLDOUT`, `TRAIN` and `REVIEWED_GOLD` roles until source rights and reviewer evidence can be independently checked. Require caller-supplied SHA-256 from outside the dataset file. Do not treat a local syntactic PASS as editorial acceptance.

## Alternatives

- Hard-coded synthetic PASS/FAIL counts: rejected; no actual tool execution.
- Self-attested `gold_provenance=INDEPENDENT`: rejected; identity string is not independent evidence.
- Counting `NEEDS_REVIEW` as automatically detected drift: rejected; artificially inflates recall.
- Using private AWS rules or real manuscripts as publicly committed labelled samples: rejected; rights, epistemic ground truth and data leakage not resolved.
- Training/evaluating on the same tiny synthetic set: rejected; severe contamination and misleading outcome.
- Introducing MLflow, vector database or NLI threshold at this step: rejected; no independent gold to calibrate it.

## Consequences and release conditions

New `awf evaluate-synthetic` CLI and `evaluation/synthetic_scope.py` with adversarial tests, ES/EN groups, no data in stdout and fail-closed source hash. Future gold evaluator must be a **separate** reviewed-source port with immutable group splits, independent labels and out-of-sample measurement, not a rename of this dataset role. No rule disposition, training authorization, rights determination or semantic truth claim is changed.
