# S2 — Instrumented local inference (Ollama) / AWF-R044

Status: **experimental engineering**, draft PR stacked on #41. This increment measures **an observed local HTTP model call**, not academic quality, source grounding, authorship or independently verified model weights.

## Architecture

- `domain/agent_execution.py`: immutable `AgentTask` (UTF-8 prompt ≤32 KiB; model ID; temperature; seed; generation budget ≤256 tokens), `ProviderObservation` (output ≤128 KiB, provider-reported metrics and digest).
- `application/ports.py`: `AgentExecutionPort.generate(task)`, a single provider-neutral protocol.
- `application/commands/run_agent.py`: invokes the port, measures monotonic client elapsed nanoseconds, checks returned model name and actual input/output hashes, produces a content-free receipt. Includes explicit unverified truth/rights/independence/semantic flags.
- `adapters/models/ollama_local.py`: **only** connects to fixed `127.0.0.1:11434`. Checks the Ollama-reported model digest before and after `POST /api/generate` (`stream:false`), accepts one bounded response and statistics. No arbitrary URL, other hosts, or external credentials. A server report is **not an independent proof** of weights or compute provenance.
- `adapters/models/offline_fake.py`: deterministic test-only fake; reports `OFFLINE_FAKE`, never a real inference.

## Opt-in local CLI

```powershell
awf agent-run .awf/private/sample-task.txt --model qwen2.5:7b-instruct \
  --seed 42 --temperature 0 --max-output-tokens 12 --allow-local-inference
```

Requires explicit `--allow-local-inference`. No candidate text is emitted to stdout. The generated output bytes are stored via `FileBlobStore` inside ignored `.awf/agent-execution/blobs/`, and a metadata-only receipt is atomically stored under `.awf/agent-execution/receipts/`. Fail closed on malformed UTF-8, unsafe paths, bounded-size violations, mismatched model, altered reported digest, invalid response, transport errors or excessive output. Store timestamps are independent of any server duration claims.

## What a receipt does and does not prove

An `execution_transport=LOCAL_OLLAMA_HTTP` receipt indicates this adapter executed a localhost HTTP request and received a response; the model ID, digest, token count and durations are **reported by that Ollama instance**. The client independently measures elapsed monotonic time and hashes prompt/candidate bytes. It cannot establish that weights are authentic, that outputs came from epistemically independent models/contexts, or that content is semantically sound. Even on a successful request, `document_acceptance=NEEDS_REVIEW`, `semantic_equivalence_verified=false`, `source_rights_verified=false` and `training_authorized=false`.

## Documentation grounding

Ollama documents `GET /api/tags`, `POST /api/generate` with `stream:false`, `options.temperature`/`seed`/`num_predict`, and `prompt_eval_count`, `eval_count`, `total_duration`, `load_duration` (nanoseconds): https://github.com/ollama/ollama/blob/main/docs/api.md. Its FAQ documents localhost bind and `OLLAMA_HOST`: https://github.com/ollama/ollama/blob/main/docs/faq.mdx.

## Tests and limits

CI must cover fake vs observed transport distinction, model mismatch, changed model digest, malformed inputs, explicit opt-in, private blob retention, content-free metadata and symlink rejection. A real local synthetic Qwen 2.5 7B inference is a **smoke test**, not an academic benchmark. AWS 3.19.1's 168 MUST stay UNRESOLVED and 16 DEFERRED_LAB stay EVAL_ONLY.

**Next:** create a genuinely rights-cleared and independently annotated document-level gold set; run side-by-side baselines (dummy vs local Qwen or comparable model) under matched tasks; record all candidate outputs and failures and measure false acceptance/false rejection with confidence intervals. Do not optimize AI detector scores at the expense of source fidelity.
