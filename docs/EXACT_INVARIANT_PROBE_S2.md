# AWF-R042 — First verification-first probe (experimental, deterministic)

Status: **ENGINEERING PROTOTYPE**, independent review pending. Stacked on draft PR #39; never substitutes for scientific assessment or training authorization.

## Actual capability

`awf verify-exact BASELINE.md CANDIDATE.md --contract CONTRACT.json --expected-contract-sha256 SHA` checks UTF-8 bytes against a caller-reviewed SHA-pinned contract with up to 128 named literals. A protected literal is bound to exact nonempty left/right source context. Categories: `QUANTITY`, `CITATION`, `QUOTE`, `SOURCE_ID`. The baseline must contain exactly one complete anchor, and its original SHA must match the contract. Outputs contain IDs, hashes, decision codes, counts, **not original/candidate prose**.

- **PASS**: each listed literal has unchanged context, with no change to global numeric inventory or known causal/modal marker inventory. **This is local syntactic preservation only**, not a pass for the document as a whole.
- **FAIL**: an explicitly protected literal has been removed or occurs fewer times than in the baseline.
- **NEEDS_REVIEW**: an anchor was moved or its context changed, a literal was duplicated, or the global numeric / causal / modal marker inventory changed. Heuristics are review signals, not semantic judgments.
- Invalid/missing/ambiguous baseline anchors, bad input hashes, unsupported schema, symlinks or oversized input fail closed with CLI code 2. CLI code 1 means a failed or inconclusive local check, 0 means listed checks PASS.
- **Always** `document_acceptance=NEEDS_REVIEW`, even on PASS. This tool cannot prove citation/source-grounding, unlisted drift, semantics, licensing or human/model independence.

### Reproducible public synthetic example

Baseline (`base.md`):

```text
El análisis registró 18 % de casos (Autor, 2024).
```

Candidate (`candidate.md`):

```text
El análisis registró 19 % de casos (Autor, 2024).
```

Contract (`contract.json`; replace `<actual SHA>` with SHA-256 of the exact UTF-8 bytes of base.md):

```json
{
  "schema_version": "1.0.0",
  "baseline_sha256": "<actual SHA>",
  "checks": [
    {
      "id": "metric-1",
      "kind": "QUANTITY",
      "value": "18 %",
      "left_context": "registró ",
      "right_context": " de casos"
    }
  ]
}
```

Compute an **independently retained** SHA-256 of the contract JSON file and pass it via `--expected-contract-sha256`. This demonstrates an explicit `FAIL` for the 18→19 mutation. No private manuscript or AWS ZIP is uploaded or required.

## Deliberate bounds and future evidence

A literal kept in its original local context may still become misleading because of edits elsewhere. A moved literal could be perfectly justified, so `NEEDS_REVIEW` is not a scientific rejection. Multisets of numbers and finite marker lexica are imperfect sensors; they are deliberately conservative. Source rights and historical rule mapping stay separate: none of 168 MUST have become `REVIEW_ATTESTED`. Before claiming real-source validation, generate PRIVATE contracts from exact AWS ledger/span sources, adjudicate applicability and licenses, then measure error rates against a reviewed gold set with held-out documents. No authorisation for training is implied.
