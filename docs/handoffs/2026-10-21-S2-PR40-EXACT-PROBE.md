# AWF — S2 incremental handoff after PR #40

Cut: 2026-10-21 (America/Lima). Project: Academic Writing Forge; account `David-std`.

## Verified baseline and current stack

- **PR #39**: `feat/s2-owner-agent-review`, draft/open, HEAD `29f29f9425880c6dfb291bb8868be42b4a345edc`. Push [39642297840](https://github.com/David-std/AWF/actions/runs/39642297840), PR [39642308164](https://github.com/David-std/AWF/actions/runs/39642308164): SUCCESS 4/4 each.
- PRs **#32–#39 remain draft/open and stacked** in exact dependent order. `main=a902135b80e96eea17ebb9c229eed065077e809d`, `develop=6888a8f44a3342c61e0d31dc93374ef44a21c174`; no merges at this checkpoint.
- **New PR #40**: [verification-first exact-invariant probe](https://github.com/David-std/AWF/pull/40), open/draft, `feat/s2-exact-invariant-probe` based directly on `feat/s2-owner-agent-review`; neither head nor base was retargeted.
- Functional code SHA `ea384f46d1312baf10961934738e43154d15425a`: push [39644665209](https://github.com/David-std/AWF/actions/runs/39644665209) and PR [39644672812](https://github.com/David-std/AWF/actions/runs/39644672812), **SUCCESS 4/4 EACH** (Ubuntu/Windows × Python 3.12/3.13). Ubuntu 3.12: **498 pytest PASS**, Pyright 0 errors/0 warnings; Ruff lint/format and Python package build PASS. These are synthetic engineering tests only, not an evaluation of a neural agent.
- This handoff is a later documentation commit: verify GitHub push/PR CI at its own exact new SHA before reporting docs-final CI PASS.

## Implementation delivered in PR #40 (AWF-R042)

- `src/awf/verification/exact_checks.py`: pure verification from actual baseline/candidate UTF-8 bytes; explicit externally pinned baseline SHA and 1–128 check IDs; each `QUANTITY/CITATION/QUOTE/SOURCE_ID` literal anchored to a unique left/right context in original bytes. Output reports hashes, counts, IDs, reason codes, no original prose.
- `src/awf/cli/main.py`: `awf verify-exact BASE.md CANDIDATE.md --contract CONTRACT.json --expected-contract-sha256 SHA`. CLI exit 0 means only declared syntactic checks PASS, exit 1 means FAIL or NEEDS_REVIEW, exit 2 means invalid/missing inputs and fail-closed contract.
- Missing protected literal → FAIL; moved/duplicated literal/context, numeric inventory change or modal/causal marker drift → NEEDS_REVIEW. Even if local scope PASS, `document_acceptance=NEEDS_REVIEW` and `semantic_equivalence_verified=false`.
- `tests/unit/test_exact_invariant_probe.py`: adversarial mutation tests (quantity alteration, extra number, changed causal force, duplicated literal, changed attribution context, wrong SHA, unsupported/ambiguous contract, CLI privacy and symlink rejection).
- `docs/EXACT_INVARIANT_PROBE_S2.md`, `docs/adr/0033-exact-invariant-probe.md`, `docs/REQUIREMENT_TRACEABILITY.md` explain scope, examples and AWF-R042.

## Unchanged security, evidence and research boundaries

- No actual LLM run, training job, or assessment of human/AI writing quality occurred. **0/168 historical MUST formally adjudicated**; 16 `DEFERRED_LAB` are `EVAL_ONLY`.
- `scope_status=PASS` is only exact anchoring/number-marker preservation: it cannot certify semantic equivalence, source support, non-hallucination, citation appropriateness or licensing.
- An exact SHA calculated only from an untrusted contract is **self-consistency**, not trusted approval; the expected contract SHA must come from independently retained custody for integrity assurance.
- This prototype does not exercise the original AWS 3.19.1 archive/corpus: it uses synthetic fixtures. Neither ZIP, any private review file, article, private manuscript, key, model weights, nor real-source excerpt was published.
- No changes to `SourceRightsGate`, formal governance, external authority adapters, Ed25519 roles, owner approval, `REVIEW_ATTESTED`, or `TRAIN`. Nothing was merged or force-pushed.
- The two Ruff formatting scratch copies live under the authorized ASUS machine's existing ignored `Downloads/AWF/.awf/` directory; no branch switch or tracked-user-file change was required. Full local tests were not run on that PC; GitHub CI was.
- Detector metrics remain subordinate to fidelity and academic correctness.

## Known limitations and next smallest testable step

1. Explicit checks cover only declared literals and local string contexts. A distant edit can change meaning while all protected anchors remain unchanged. The finite numeric/causal marker inventories detect some but not all changes, with possible false alarms; no `PASS` semantic result is ever produced.
2. **Next:** privately read the SHA-pinned original AWS archive; choose a rights-cleared pilot of authentic historical rule IDs, map evidence/source span and applicability, and measure on separately reviewed negative and positive cases. Publish only source-safe contract templates/hashes and aggregate results, no historic text.
3. **Then:** separately implement an `AgentExecutionPort` with offline fake and instrumented provider adapter (real, measured model execution only when available), sealed tasks, model/revision/seed metadata and independent comparison to this deterministic probe. Do not equate two submitted report identities with two actual model runs.
4. Preserve the stacked PR sequence. Keep #40 draft, review it, and do not automatically merge #32–#40, alter `main`/`develop`, or use a self-reported model PASS to bypass rights/semantic checks.

Read first: previous [PR #39 recovery](2026-10-21-S2-PR39-RECOVERY.md), [ADR-0032](../adr/0032-owner-governed-agent-evaluation.md), [ADR-0033](../adr/0033-exact-invariant-probe.md), [AWF architecture](../architecture/ARCHITECTURE_SPEC_0_1.md), `AGENTS.md`, and PR #40 diff/CI.
