# AWF — S2 checkpoint after PR #41: authentic historical rule pilot

Date: 2026-10-21 (America/Lima). **Scope:** engineering measurement, not scientific adjudication. Project `David-std/AWF`.

## Verified stack and source integrity

- Direct parent is draft/open [PR #40](https://github.com/David-std/AWF/pull/40) at `4d17a763e4bdbfbe935f76a52e3374e774e9818c`. No force push, merge, or retarget. [PR #41](https://github.com/David-std/AWF/pull/41) is `feat/s2-private-historical-pilot` directly over PR #40 and remains DRAFT.
- Last **code** SHA: `9f9d2467b0b7cabd88c3181d96dd12251cd1ddf8`. [Push CI 39656095522](https://github.com/David-std/AWF/actions/runs/39656095522) + [PR CI 39656102213](https://github.com/David-std/AWF/actions/runs/39656102213): **SUCCESS 4/4 each** (Ubuntu/Windows × Python 3.12/3.13). Ubuntu 3.12: **503 pytest PASS**, Ruff lint/format PASS, Pyright **0 errors/0 warnings**, wheel/sdist build PASS.
- Source artifact (private): `academic_writing_suite_v3_19_1_product.zip` on the ASUS Downloads, and identical-byte uploaded `academic_writing_suite_v3_19_1_product(2).zip`; SHA-256 `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`. 1,364 ZIP entries, integrity check clean; ledger `academic_writing_suite/runtime/deep_spec_requirement_ledger.json`, version 3.19.1, 184 records.
- ZIP is not part of the repository. No copyrighted/private source text, manuscript, model output, confidential keys, or original code was uploaded to GitHub.

## Functionality and results

- `src/awf/verification/historical_pilot.py`: chooses six genuine `MUST` rule IDs `DSR-001`, `DSR-055`, `DSR-059`, `DSR-063`, `DSR-065`, `DSR-066`; selects unique literal/context spans from their exact original text; constructs 5 controlled local mutations per source rule.
- `src/awf/adapters/knowledge/pilot_evidence.py`: local-only SHA-pinned ZIP traversal; verifies source implementation paths and mapped research file **presence**. Never imports or executes legacy Python, doesn't export source text. Six rules resolve 25 file refs, 10 directory refs and 14 research source refs, no missing paths.
- `awf knowledge pilot ORIGINAL.zip --manifest provenance/source-manifest.json`: uses the existing `PinnedAwsArchive`, reuses the exact-invariant checker, returns a metadata-only result and source-path counts without protected strings.
- Five cases per authentic statement: unchanged control, protected literal replaced, local context changed, unlisted numeric addition, distant contradictory sentence.
- **Real local execution with actual pinned archive on the authorized ASUS computer and in isolated container:** 30 cases total; **12 syntactic PASS, 12 NEEDS_REVIEW, 6 FAIL**. All six distant semantic overrides produced **syntactic PASS**, exposing an actual scope blind spot. Every case nevertheless has `document_acceptance=NEEDS_REVIEW`; no false scientific approval is emitted.
- The raw local CLI import on the authorized machine initially failed because the user's **global Python 3.12** lacked `cryptography` (a preexisting CLI dependency). The actual pilot modules were then invoked directly through that Python environment using `PinnedAwsArchive` and the original ZIP; the resulting summary matched container evaluation. No global packages were changed. Do not claim the CLI entrypoint was directly exercised on that PC.
- All runtime changes were CI validated with synthetic ZIPs and rule fixtures. This is an integration/engineering experiment, not scientifically validated real writing performance.

## Narrow research claim and limits

**Supported:** The deterministic syntax checker catches the six protected-literal mutations, refers local-context and added-number modifications for review, and *does not detect* six deliberately appended distant contradictions. The source and historical pointer inventories are structurally present.

**Not supported:** semantic precision/recall on research manuscripts; independent gold standard, citation truth, original historical implementation correctness, scientific independence, neural efficacy, Pangram/GPTZero/Turnitin performance, training authorization, or `REVIEW_ATTESTED` promotion. Six source IDs are **selected for experimentation, not adjudicated**. All **168 historical MUST remain UNRESOLVED; 16 DEFERRED_LAB remain EVAL_ONLY**.

## Follow-up (functional not ceremonial)

1. Use actual historical code and primary-source extracts **privately**, with rights clearance for each output. Match a source span and negative control to each rule ID. Avoid recasting the successful path check as evidence that the underlying claim is correct.
2. Design **held-out, independently reviewed** annotations for document-level semantic failures; report sensitivity, specificity and false alerts with denominators rather than claiming semantics from syntactic checks. Include deliberately distant negation and context shifts.
3. Implement instrumented `AgentExecutionPort` with an offline fake, deterministic input/output receipt hashing, model/provider/sampling parameters and measured elapsed durations. Real model use must record exact model/context, never infer independence from different agent IDs.
4. Preserve the PR stack, CI, ADR boundaries, rights metadata and `EVAL_ONLY` gates. Do not silently change `main` or `develop`.

Read first: [PR #40 handoff](2026-10-21-S2-PR40-EXACT-PROBE.md), [ADR-0033](../adr/0033-exact-invariant-probe.md), [pilot method](../HISTORICAL_RULE_PILOT_S2.md), [architecture](../architecture/ARCHITECTURE_SPEC_0_1.md), and `AGENTS.md`.
