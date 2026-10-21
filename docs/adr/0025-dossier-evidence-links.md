# ADR-0025 — Source-bound dossier evidence links (S2)

- **Status:** prototype pending independent review; no scientific adjudication.
- **Date:** 2026-10-20.
- **Base:** `develop` after PR #31 (`6888a8f44a3342c61e0d31dc93374ef44a21c174`).
- **Scope:** verify that a declared private dossier `evidence_id` corresponds to an existing event and unchanged bytes under one coherent, fully audited SQLite read snapshot. Preserve all 184 legacy dispositions.

## Decision

1. Add `EvidenceKind.RULE_SUPPORT` for supporting review material; **do not** interpret it as `REVIEW_ATTESTATION` or a reviewer signature.
2. Use `event:<lowercase SHA-256 event digest>`, not a bare content SHA-256 or an arbitrary URL. Each event must have the expected `run_id` and `subject_id = DSR-nnn`.
3. Require a JSON evidence payload with **exactly** `schema_version=1.0.0`, `purpose=knowledge_review_support`, `archive_sha256`, `source_id`, `requirement_id` and `requirement_sha256`. Compare all fields against the *canonical ZIP-derived review plan*, not against mutable dossier text.
4. Keep PR #31's existing `audit_private_dossiers` structural gate first. Optional CLI flags `--evidence-database`, `--review-run-id`, `--expected-head` must be supplied together. The SHA-256 head must be independently retained; never derive trust from the database under audit.
5. Reuse `EvidenceStorePort.verified_read()`: one full database audit and a single SQLite snapshot shared by every link lookup. Do not call `resolve_event()` on the store afresh for each link.
6. An invalid/missing link adds the public DSR ID to `affected_rule_ids` and makes the optional CLI gate exit 2. Ledger corruption, schema violation or a stale external head raises an error. No review fields, evidence content, names or reasons are returned.
7. Keep `PROPOSAL_DOCUMENTED` as a metadata status. `all_declared_links_verified` is a **narrow integrity claim**, not all rules reviewed, author identity, independence, legal permission, factual accuracy or `REVIEW_ATTESTED`.

## Compatibility and security boundaries

Default `inspect-review` behavior without opt-in flags is unchanged. Existing private JSON batches retain schema 1.0.0 and are read-only; old `evidence_ids` that are arbitrary strings still pass metadata inspection but **fail** the new evidence-link gate until recorded and bound. The new event kind does not alter the SQLite storage schema.

No raw AWS ZIP, rule description, manuscript, private evidence payload, key material or user-provided reviewer identity is committed or printed. The caller is responsible for input confidentiality and independent storage of the trusted head digest.

A malicious writer with database write permissions can generate a new event with plausible self-declared metadata. Matching hashes proves only content binding. External custody, trusted timestamp, event authority, revocation and actual reviewer adjudication are separate later increments. This gate cannot establish that evidence existed *before* a proposal was written because old dossier templates have no trusted signed review timestamp. Do not infer that from SQLite's recorded_at.

## Tests / acceptance

- Good event belongs to correct source digest, rule digest, run, subject, event kind and JSON purpose.
- Wrong-kind, wrong-run, wrong-subject, cross-source, wrong-rule, wrong-rule-SHA, malformed JSON, stray keys, arbitrary URI and missing event fail closed.
- Duplicate IDs are rejected by the existing dossier inspector.
- A changed ledger head invalidates the verification transaction even if a referenced event still exists.
- No-reference dossiers do not yield a vacuous valid-evidence claim.
- Source-bound dossier inspection remains prior gate; no training or `REVIEW_ATTESTED` at any point.
- CI Linux/Windows Python 3.12/3.13, locked Ruff, Pyright and build required before merge to `develop`.

## Deferred

A separately authorized **knowledge-review** role with signed, revocable, context-bound authority; trustworthy review timestamps; a rights/licensing attestation source; independent quality assessment; durable adjudication transactions; content-level evaluation and training approval. The existing signed CRITIC role is not elevated implicitly.
