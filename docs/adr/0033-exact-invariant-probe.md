# ADR-0033 — Narrow exact-invariant probe before model execution

Date: 2026-10-21. Status: provisional, verification-first engineering prototype, draft PR stacked on #39.

## Context

PR #39 authenticates owner/agent reports but not whether model edits preserve quantities, citations, literal quotations or source identifiers. Green CI and owner approval cannot fill this gap. AWS 3.19.1 is retained as a private legacy source and its rules remain unadjudicated.

## Decision

Implement a small, pure `verification/exact_checks.py` probe with explicitly pinned baseline SHA and contract file SHA supplied from outside the candidate. Every assertion includes a literal and its exact left/right anchoring context. Compare actual UTF-8 bytes before interpreting anything. Report tri-state status and review signals for changes to numeric or modal/causal marker inventories. Preserve a separate `document_acceptance=NEEDS_REVIEW`, irrespective of local PASS. Keep input material out of emitted evidence and Git; use a CLI entrypoint and synthetic adversarial tests.

There is no new trust role, data store, model service, remote API, or permission grant. A caller asserting checks is not thereby a source-rights holder or verifier of semantic equivalence. Fail closed on source/contract checksum mismatch, duplicate check IDs and ambiguous original anchors.

## Alternatives rejected

* Automatic acceptance whenever the numeric strings are unchanged: fails on attribution/context and ignores omitted safeguards.
* Generic numeric/citation regex that rewrites or blesses prose: errors on locale, identifiers, semantics and scope.
* Two LLMs voting on a candidate: opaque circularity, model correlation, no independent ground truth.
* Importing the legacy ZIP or creating public real-source fixtures: unnecessary licensing/corpus exposure.

## Limitations and exit criteria

This only checks selected literals and finite risk signals. It does not demonstrate language understanding or effectiveness on 184 source rules. Before promotion, evaluate with rights-cleared real documents, independently reviewed annotations, and false-positive/negative analyses. Future agent execution must remain a separate port and cannot reinterpret `scope_status=PASS` as scholarly approval.
