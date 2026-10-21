# Verify private dossier evidence links — S2

After creating a local review workbench and editing the `review_template` fields, run the normal `inspect-review` first. This new opt-in gate checks event identity and stored bytes but does not adjudicate an academic rule.

The reviewer supplies `event:<digest>` in each `evidence_ids` list, where the digest is the returned `head_digest` of that specific ledger event (not the content SHA). Create a JSON source file for a synthetic experiment containing exactly:

```json
{
  "schema_version": "1.0.0",
  "purpose": "knowledge_review_support",
  "archive_sha256": "<actual ZIP SHA-256>",
  "source_id": "aws-3.19.1",
  "requirement_id": "DSR-001",
  "requirement_sha256": "<canonical per-rule SHA-256>"
}
```

The values must be read from the pinned manifest and canonical packet, not invented. Add this JSON as `RULE_SUPPORT` evidence using `awf evidence append`, with `--subject-id DSR-001` and a chosen `--run-id`. Do not write private source descriptions in this JSON unless you have explicitly authorized local processing of that material.

```shell
awf knowledge inspect-review /private/aws.zip --batch-size 12 \
  --evidence-database .awf/evidence/ledger.sqlite \
  --review-run-id knowledge-run-001 \
  --expected-head SHA256_HEAD_SAVED_OUTSIDE_THE_DATABASE
```

Both the JSON source and SQLite file must stay under the protected, Git-ignored local workspace. The `--expected-head` checkpoint must be independently retained; printing and copying the current database head does not establish external trust. A new append after the checkpoint requires a newly trusted head.

Without these three flags, `inspect-review` keeps its PR #31 metadata-only behavior. When flags are supplied, missing/invalid links return exit code 2; the output adds only evidence counts, affected public rule IDs and hardcoded false for reviewer authorization, external adjudication, training and private-text inclusion. `--require-documented` still enforces PR #31's separate metadata gate.

This verifies **provenance of declared records**, not the scientific quality of the claims, temporal precedence over the review, legal permission, an actual person's identity or authorization to use material for model training.
