# ADR-0027 — Independent scientific assessment receipts, not adjudications

- Date: 2026-10-20
- Status: CI-verified provisional engineering prototype; independent scientific/legal and code review remain outstanding (not merged).
- Base: draft PR #33 SHA `7fcd406189762e62ad2186f43f967b1dd4ec2661`; parent PR #32 is also unmerged. Do not merge out of stack.
- Purpose: authenticate a second, actor-distinct, source-bound scientific assessment of a signed historical-rule proposal without granting formal adjudication, licensing or training rights.

## Decision and guarantees

1. Add `SCIENTIFIC_RULE_ASSESSMENT` ledger event kind and separately grantable `SCIENTIFIC_REVIEWER` Ed25519 role. It is not a synonym for `KNOWLEDGE_REVIEWER`, `CRITIC`, `CALIBRATOR`, or `APPLICABILITY_REVIEWER`.
2. An assessment is a canonical, strictly parsed version-1 JSON ledger event with the canonical `archive_sha256`, `source_id`, `requirement_id`, `requirement_sha256`, the **exact** previously signed `proposal_ref`, an assessment actor ID, declared `verdict` among `SUPPORT|CONTEST|INCONCLUSIVE`, and bounded private method/evidence/limitations notes. Storing notes in the locally protected ledger (not Git) permits hash and byte verification; merely hashing nonexistent notes is insufficient.
3. The assessment event is signed with the existing `ReviewerClaim`/Ed25519 `REVIEW_ATTESTATION` workflow and independently SHA-pinned trust policy. Verifier requires valid role/run/subject/expiry/revocation and signatures.
4. Re-run PR #33's source-bound proposed-dossier/ledger authorization gate, then inspect the same externally pinned exact head in a fresh verified read snapshot: signed proposal must exist and precede the second assessment event, and its signing actor must differ from the new authorized signing actor, who must equal `assessment_actor_id`.
5. A complete private canonical inventory maps each `PROPOSAL_DOCUMENTED` DSR ID to `assessment_ref` and `attestation_ref`. Missing/extra/swapped records, malformed JSON, wrong kind, version, source SHA, proposal link, actor, role, chronology, policy pin and stale ledger head fail closed.
6. The gate is an **application service** pilot, not a new default `inspect-review` CLI mode, and never mutates a dossier, disposition, registry or rule status. Its `all_credentials_verified` means only authenticated links under the supplied externally held policy/head, not `REVIEW_ATTESTED`, genuine human independence, science, rights verification or permission to train.
7. This gate deliberately performs two full-ledger audits: PR #33 complete credential validation and second assessment validation. Both pin the identical externally provided head so a concurrent append invalidates either transaction. If profiling later justifies it, refactor to a shared read snapshot without relaxing checks.

## Why not approve a rule yet?

Cryptographic separation of **actor IDs** does not establish distinct people, expertise, impartiality, actual source reading, scientific correctness, a rights grant or permission for ML usage. This prototype accepts a `SUPPORT` label as *the contents of a signed opinion*, not a scientific truth. No model inference participates in this step. Legal rights depend on source-specific owners/licensing scopes, verified outside the signer's self-declarations. Approval needs additional independently reviewed procedures and a durable adjudication command with explicit preconditions, versioned evidence and appeal/revocation semantics.

## Alternatives rejected

- Reuse a single signer/role, or trust an editable `reviewer` string as independence: conflicts with role separation and non-self-review.
- Interpret a `source_rights_status: PERMISSION_VERIFIED` string as a license: unverifiable self-assertion.
- Write `REVIEW_ATTESTED` from a signed opinion: would conflate integrity with epistemic evaluation.
- Add external model or API judge in S2: no authorized gold evidence or calibrated evaluator.
- Store only a digest of a private assessment without immutable source bytes: does not prove those bytes exist.

## Verification and deferred work

Real-Ed25519 adversarial integration tests and locked Ruff/Pyright/pytest/build were verified on the final PR #34 SHA `34b192a32efd0841a6149d93493d3aa1b19147b3`: [push CI 39531777710](https://github.com/David-std/AWF/actions/runs/39531777710) and [PR CI 39531782917](https://github.com/David-std/AWF/actions/runs/39531782917), both 4/4 SUCCESS (Ubuntu/Windows × Python 3.12/3.13). Ubuntu Python 3.12: **420 PASS**, Pyright **0 errors/0 warnings**, Ruff/build PASS. No physical Windows full-suite reproduction is claimed. No AWS ZIP or private annotations in Git.

Next separately design: scientific evidence evaluation protocol (primary source review, conflicting evidence, applicability), licensed-source provenance/owner rights and explicit `UNKNOWN` handling, third-party independence/audit, eventual durable `REVIEW_ATTESTED` transition with no auto-TRAIN, and operator CLI. S2 remains OPEN, **0/168 MUST adjudicated**, 16 lab-only `EVAL_ONLY`.
