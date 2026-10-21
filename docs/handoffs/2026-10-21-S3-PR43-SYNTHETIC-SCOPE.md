# AWF — S3 PR #43 synthetic benchmark handoff

Cut: 2026-10-21 (America/Lima). Owner repository: `David-std/AWF`. This is a **technical continuation checkpoint**, not independent scientific certification.

## Stack and verified source

- [PR #43](https://github.com/David-std/AWF/pull/43) draft/open on `feat/s3-synthetic-scope-benchmark`, base `feat/s2-local-agent-execution` ([PR #42](https://github.com/David-std/AWF/pull/42)). #42 is stacked over #41 over #40; do **not** merge or retarget without an explicit plan. `main` / `develop` unchanged at checkout.
- Functional SHA: `d44b289b119891730e0a8ea08c31913e6f69477b`; [push CI #39666512041](https://github.com/David-std/AWF/actions/runs/39666512041) and [PR CI #39666522033](https://github.com/David-std/AWF/actions/runs/39666522033) started on exact SHA. Ubuntu/Python 3.12: **534 pytest PASS**, Ruff lint/format, Pyright 0 errors/warnings, build success. Check complete matrix before stating all four OS/Python combinations passed. The final doc commit requires its own verification.
- AWS 3.19.1 original remains **private and external**: SHA `ccff7d4f8c672a6ec1305faa128540893c44ee6c373941eece72a61880bb6d3c`. All 168 MUST remain UNRESOLVED and 16 DEFERRED_LAB EVAL_ONLY; source existence is not independent truth.
- Prior PR #42 final SHA: `31bdd663376d2077e6c9733da2e8c1f0533eac69`, both CI [39660442374](https://github.com/David-std/AWF/actions/runs/39660442374) and [39660448865](https://github.com/David-std/AWF/actions/runs/39660448865) **4/4 SUCCESS**. An isolated venv on authorized ASUS had only `cryptography` added (no global Python modification); full `awf agent-run` with local Qwen2.5 7B, synthetic arithmetic input and explicit opt-in exited **0**, client **10,994,833,900 ns**, 2 tokens reported; returned output sha `4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a`. Private receipt and candidate stored under ignored `.awf` scratch checkout, not Git.

## What PR #43 actually implements

- `src/awf/evaluation/synthetic_scope.py`: checks SHA-pinned local UTF-8 JSON dataset and strict `SYNTHETIC_DEVELOPMENT` role. Validates 2..128 cases, unique IDs, ES/EN, one language per document ID, development risk family and `DEVELOPER_SYNTHETIC` annotation provenance; controls data size and source symlinks. Rejects dataset/contract tampering.
- Each case supplies literal baseline/candidate **bytes** and a baseline-SHA-bound exact-invariant contract. The harness invokes real `verify_exact_invariants`; nobody can supply a PASS array in input. Output has IDs, SHA256 of actual texts, observed status, confusion counts and language strata; original/candidate prose not exported.
- `awf evaluate-synthetic LOCAL.json --expected-sha256 HASH` prints a metadata-only report and refuses invalid input; `tests/unit/test_synthetic_scope_benchmark.py` contains deliberately fictional 4 ES/4 EN cases plus tamper/provenance/duplicate IDs/format/CLI/symlink negatives.
- Case accounting: `FAIL`=syntactic rejection, `PASS`=no syntactic alert, `NEEDS_REVIEW`=abstention. Never promote `PASS` to scholarly acceptance. 8 cases: 2 FAIL-on-DRIFT, 2 PASS-on-DRIFT (false clear), 1 REVIEW-on-DRIFT, 2 PASS-on-PRESERVED, 1 REVIEW-on-PRESERVED. Strict synthetic drift detection 2/5=40%, false clear 2/5=40%, escalation 2/8=25%. All **example-only**, no confidence or generalization claim.
- [ADR-0035](../adr/0035-synthetic-evaluation-boundary.md) and [scope methodology](../SYNTHETIC_SCOPE_BENCHMARK_S3.md) explain false-clears, abstentions, why labels are synthetic, and why this is not gold.
- No training job, NLI, genuine external data, detector test, second real independent model, paper-authorship judgment or human reviewer provenance added here.

## Next smallest meaningful increments

1. Build separate reviewed-source adapter/protocol: verified source rights, provenance and **external** labels; annotator disagreements preserved. Do not let JSON strings self-certify reviewer identity; holdout sealed, grouped by document/author/source. Keep source text local.
2. For initial S3, compare predicted EDIT candidates with source-grounding and source-invariant checks. Only on approved source material; include mismatch, negation, causal, population and citation drift; use unknown/abstain for unsupported inferences.
3. Run paired real Qwen baseline vs non-generative checker with versioned model/task/generation controls, and per-group outputs retained locally. Measure errors on independent gold when available; do not pretend sample fixture equals precision/recall in a paper.
4. Preserve stacked PRs and exact CI, update handoff and append-only evidence, do not publish corpus. No 168 historical MUST adjudicated; DEFERRED_LAB stays EVAL_ONLY.

Read first: [S2 PR42 handoff](2026-10-21-S2-PR42-LOCAL-AGENT.md), ADR-0033 and ADR-0034, architecture specification, AGENTS.md and current GitHub Actions jobs.
