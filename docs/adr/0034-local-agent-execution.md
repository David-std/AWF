# ADR-0034 — Observed local execution, not agent self-attestation

- Date: 2026-10-21.
- State: provisional engineering, draft PR #42, stacked on #41 → #40 → #39.
- Problem: PR #39 validates signed report *claims* and PR #41 detects a semantic blind spot, but neither proves that actual model inference occurred. More identity/signature metadata would not solve this empirical problem.
- Decision: define `AgentExecutionPort` in the application boundary and a strict loopback-only Ollama adapter. Use immutable typed task/result DTOs, independently timed invocations, input and output SHA-256 hashes, narrowly interpreted provider metrics and a separately hashed stored candidate. Only an explicit CLI opt-in may initiate local HTTP inference. Provide an honest `OFFLINE_FAKE` adapter for synthetic tests, not as evidence of model execution.
- Model identity: request a named model and compare the service's reported name and digest before and after the request. This is a consistency check, not cryptographic proof of actual model weights, process isolation, uniqueness or independent scientific judgment.
- Data: retain output under the user's ignored local `.awf` only, do not publish inputs, outputs, prompts, source content, model weights or keys. No provider-independent claims without experimental comparison.
- Governance: source-rights and owner EVAL_ONLY gates are unaffected. The runtime output's content never becomes academic PASS or training permission from its receipt. Failure of transport/typing/digest checks aborts without evidentiary promotion.
- Alternatives rejected: a second fictional agent report, model vote counting, arbitrary URL external services, automatic academic acceptance from a model response, introducing a new event-store or UI just for model smoke testing.
- Future exit criteria: actual provider smoke test on public synthetic prompt, CI on 4 Python/OS combinations, control/error cases and independent labelled writing-source benchmark. `model_weights_verified=false`, `semantic_equivalence_verified=false` and `training_authorized=false` remain hard-coded for this increment.
