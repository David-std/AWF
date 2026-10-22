# ADR-0038 — Metadata-only candidate-gold and blind review diagnostic

**Status:** Experimental on draft PR #47, stacked directly on PR #46. No real scientific gold accepted.

### Context

AWF #46 compared the pinned 0.5B Qwen base with the authentic LoRA on **two synthetic development validation cases**. The result (one differing output) cannot establish academic fidelity. A real gold set requires rights-cleared sources, grouped splits and externally verified independent assessors. An ad hoc JSON field such as `independent_gold_verified: true` is insufficient evidence.

### Decision

Provide a standalone stdlib `python -m awf.evaluation.gold_intake` preflight, accepting only externally SHA-pinned **metadata** manifests with rights-evidence and source-evidence digests and opaque A/B conditions. It detects leakage across original document, author and source group, rejects model-name-bearing conditions, prevents developmental annotations on the sealed test split, and refuses self-declared `INDEPENDENT_GOLD` roles. Annotations require two distinct reviewer IDs for each pair/condition/risk family; missing or conflicting opinions become UNKNOWN. Per-condition and paired-discordance counts remain provisional and anonymous.

No text, sources, model outputs or held-out test content are read. Signer/human independence, evidence bytes, rights chain and adjudication have **not** been verified. The return value **always** retains `independent_gold_verified=false`, `document_acceptance=NEEDS_REVIEW`. This does not create a path to circumvent the rights and external reviewer gates.

### Alternatives

Auto-upgrade two matching anonymous reviewer IDs to gold: rejected, no identity/qualification proof. Treat `UNKNOWN` as preserved: rejected. Include a SHA of text in a public dataset: insufficient rights. Use model votes: circular and correlated. Publish model identities before blind scoring: rejected. Consume synthetic placeholder holdout: rejected.

### Exit gate

Only after a source-rights evidence audit and independently verified, sufficiently qualified, blinded reviewers/adjudicator: freeze signed externally held gold receipts, map A/B conditions after label freeze, and run genuinely unseen group-separated source-grounded tests. New ADR required for any automatic promotion from diagnostic to accepted gold.
