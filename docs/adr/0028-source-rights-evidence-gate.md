# ADR-0028 — Source-specific rights evidence and fail-closed external authority

- **Date:** 2026-10-20.
- **Status:** provisional engineering implementation in stacked draft PR #35; no legal review or adjudication.
- **Base:** PR #34 HEAD `1c8f729e75e9fdcb1a6e9054854baabdad8f8f24` (PRs #32–#34 remain open).
- **Requirement:** AWF-R037.
- **Decision:** create a local canonical, externally hash-pinned, source-and-byte-span rights inventory. It is not a licence, a judicial opinion or a valid grant merely because a record claims that it is one.

## Threat model and authority

An uploader can edit licence labels, owners, URLs, assertions, metadata, evidence hashes and local JSON. A checksum protects byte identity only against an **independently retained** expected hash; self-pinning does not show ownership. Evidence bytes plus their SHA prove byte consistency, not chain of title. A researcher, a scientific reviewer, a knowledge proposer and an LLM have no inherent capacity to grant intellectual-property rights. The current Python core therefore has **no default positive-authorizing adapter**. Positive decisions demand a separately trusted `RightsAuthorityPort`, pinned external authority policy, actual evidence bytes and a matching file/fragment hash. That port must eventually validate licence instrument, true licensor authorization, permitted act, geography/term, revocation, exceptions and chain of custody; its absence returns `UNKNOWN`.

## Contract

- Distinguish `READ`, `EVALUATE`, `TRANSFORM`, `REDISTRIBUTE`, `TRAIN` for individual files and 0-based half-open byte ranges. No automatic implication between operations.
- Distinguish `UNKNOWN`, `RESTRICTED`, `LICENSED_FOR_EVAL`, `TRAIN_ALLOWED`, `RIGHTS_SUPPORTED`. The latter three are conditional scope conclusions **only if** an independently supplied verifier succeeded; they are not software-wide permissions. Every decision reports `training_authorized=false`.
- Source identity binds source ID, exact archive SHA, file SHA and byte count, plus the requested segment digest. Snapshot metadata are accepted only if canonical JSON is hash pinned outside the file; no trusted sources are inferred from URLs.
- A denial, revoked claim, not-yet-valid claim or expired grant affecting the requested scope is a veto. Missing coverage/evidence/policy/authority is `UNKNOWN`. Invalid bytes, duplicate IDs, ambiguous fields and changed content raise errors. A later rights claim cannot silently override a negative existing claim.
- No training, redistribution of private datasets, source rewriting or advancement of `REVIEW_ATTESTED` is performed. Neither this gate nor PR #34 adjudicates scientific claims.
- A manifest may contain mixed rights for different byte spans and use purposes; rights need not be homogeneous even within one publication.
- Any positive rights outcome in synthetic tests uses a fake external verifier deliberately unavailable in production.

## Deferred and rationale

A real rights-verification adapter is **DEFERRED**, pending an identifiable external authority, verifiable legal documents, trust policy, privacy/access design, and independent legal assessment. Do not implement a `verify_license_by_name()` shortcut or infer ML rights from copyright/licence metadata.

The SPDX license list defines standard identifiers and expressions, **not proof that a specific asset carries the licence** (https://spdx.org/licenses/; https://spdx.github.io/spdx-spec/v3.0.1/annexes/spdx-license-expressions/). Creative Commons says the human-readable deed does not replace legal code and terms differ by commercial use/adaptations (https://wiki.creativecommons.org/wiki/Considerations_for_licensors_and_licensees/Licensees). Hugging Face dataset cards provide descriptive licence metadata but not independent ownership verification (https://huggingface.co/docs/hub/main/datasets-cards).

This decision preserves the existing modular monolith and ports/adapters boundary; no new Ed25519 signing role, SQLite table, training switch or network fetch is added. A scientific disagreement protocol is a **separate subsequent PR**; do not conflate a rights file with scientific rule adjudication.

## Verification

Tests use synthetic source bytes, fake external claims and fake authority; cover SHA mismatch, different-source claims, partial ranges, missing evidence, malicious owner, revocation, expiration, negative claims, unsupported operations, duplicates and conflicting scopes. CI matrix must validate locked Ruff 0.14.0/Pyright/pytest/build before declaring an implementation verified.
