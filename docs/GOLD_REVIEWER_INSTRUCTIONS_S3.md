# AWF S3 — Independent blinded review instructions (prospective)

**Status:** recruitment/review instructions, not evidence that any person has reviewed an AWF example. Source excerpts, model responses, reviewer identity evidence and rights documents stay **private** and out of GitHub.

## What reviewers receive

For each future rights-cleared case: unchanged original passage, original cited source and exact evidence locations, the prescribed editorial operation, two anonymous candidate edits labelled **A** and **B**, and a checklist for the risks relevant to that case. Reviewers are not told model identity, hypothesis or other reviewers' conclusions. The experiment coordinator holds the A/B mapping separately, pinned externally before adjudication. Model responses are never called genuine human examples.

## Review of each risk dimension

Rate each blind edit against the unchanged original and the actual cited source:

- `PRESERVED`: the claim, scope, citation relationship and evidentiary strength required by this dimension are supported. A fluent sentence without source support does **not** qualify.
- `DRIFT`: meaning or attribution differs materially; record the concrete discrepancy and source span.
- `UNKNOWN`: evidence is inaccessible, ambiguous, insufficient or beyond the reviewer's expertise; **never** guess.

Dimensions: negation; quantity/unit; citation attribution; causality vs association; population/exclusion; modality/certainty; temporal scope; and source support. Record a short reason and immutable source-span SHA/locator. Each condition/family needs two independently completed reviews. Disagreements remain preserved as disagreements until a separate adjudicator assesses the same source; a vote count alone must not silently decide them.

### Artificial illustration (NOT research evidence)

Original fictional passage: "The hypothetical survey included **18** participants; no causal effect was established."

- Edit A: "The hypothetical survey included **81** participants and demonstrated a causal effect."  
  Quantity and causality are **DRIFT**, even if the wording is fluent.
- Edit B: "Eighteen participants were included in the hypothetical survey, which did not establish causality."  
  Quantity and causality are potentially **PRESERVED**, subject to verifying the original source.

Do not copy this illustration into the independent corpus, train set or scientific report as a sampled result.

## Reviewer recruitment/identity and rights prerequisites

Before treating labels as independent scientific gold, the coordinator must verify rights to inspect/process original text and cited evidence (owner-authored vs coauthored vs publisher-licensed), record the dated scope of permission and version of the cited source, and verify reviewers' expertise, identity, potential conflict of interest, access to source and actual independent performance. Two names in JSON do **not** prove two people; an Ed25519 signature proves key possession, not expertise or independence. Obtain informed and permitted participation before sharing private manuscript material.

Recommended operational sequence: small **development-only calibration pilot**, revise rubric and annotation clarity without accessing sealed final test, then freeze reviewed-label protocol and document/author/source group assignments. Sample size and effect precision for the final study must be justified separately. No specific number of cases or performance improvement is pre-certified.

## Current state

PR #47 provides **only structural/metadata validation** using the [candidate gold intake CLI](../GOLD_INTAKE_S3.md). It cannot review original passages, verify source rights, authenticate reviewer identities, or approve gold. `independent_gold_verified=false` and `model_quality_certified=false` remain mandatory. Annotations must not be applied to `test_sealed` via this development-only tool.
