# AWF — candidate-gold preflight (not scholarly gold)

Run a metadata-only, offline preflight for blinded ES/EN document-group comparisons. This **does not load source passages or model responses**, and never opens the sealed holdout.

```bash
python -m awf.evaluation.gold_intake --manifest PRIVATE_MANIFEST.json \
  --manifest-sha256 SHA256_PINNED_OUTSIDE_MANIFEST \
  --reviews PRIVATE_BLIND_ANNOTATIONS.json \
  --reviews-sha256 REVIEWS_SHA256_PINNED_OUTSIDE_REVIEWS
```

Both input files must remain in private ignored `.awf/` storage (or another secure local owner-controlled location), never committed. The CLI prints anonymous aggregate counts only; no private text. Obtain their actual SHA-256 with the local OS **before** evaluation. Without `--reviews`, the command reports missing review coverage.

## Manifest contract

JSON `{"schema_version":"1.0.0","dataset_role":"SYNTHETIC_DEVELOPMENT","cases":[...]}`, or `"CANDIDATE_REVIEW"` for rights-controlled candidate material. Each case contains exact keys:
`case_id`, `document_group`, `author_group`, `source_group`, `language` (es/en), `genre`, `split` (train, validation or test_sealed), `risk_families` (list of supported families), `blind_conditions` (exactly ["A","B"]), `original_sha256`, `source_evidence_sha256`, `rights_evidence_sha256`, `rights_basis`.

Use `rights_basis="SYNTHETIC_FIXTURE"` only for synthetic; candidate roles may declare `OWNER_ATTESTED` or `THIRD_PARTY_PERMISSION_CLAIM`. These strings **do not prove a license**. A reviewer must inspect the external evidence before admission. Document, author and source groups cannot cross train/validation/holdout. Split `test_sealed` records metadata only and cannot appear in developmental annotations.

## Review contract

JSON `{"schema_version":"1.0.0","review_role":"BLIND_CANDIDATE_ANNOTATIONS","annotations":[...]}`. Each row has:
`case_id`, `blind_condition` (A/B), `risk_family`, `reviewer_id`, `label` (`PRESERVED`, `DRIFT`, `UNKNOWN`), `rationale_code`, `evidence_sha256`. Require two unique reviewer IDs per risk family and condition. A disagreement, missing reviewer or UNKNOWN remains UNKNOWN; otherwise report condition-specific labels. Neither agreement nor a cryptographic SHA authenticates the reviewers or confirms their access to underlying source evidence.

**Note:** The current implementation does not verify exact source-span bytes, annotation signatures, reviewer qualifications or licenses. It does not map blinded A/B to base/adapter or inspect raw model outputs. Distinguish automated structural validation from substantive academic judgement. A test containing only synthetic metadata is a software test, not a performance estimate for writing quality.

See [independent gold protocol](INDEPENDENT_GOLD_PROTOCOL_S3.md) and [ADR-0038](adr/0038-blind-gold-candidate-intake.md).
