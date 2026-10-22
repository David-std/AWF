# ADR-0037 — Pinned paired inference is diagnostic, not gold

**Status:** Provisional, draft evaluation increment stacked on PR #45.

Base Qwen2.5-0.5B-Instruct and the authentic SHA-verified LoRA adapter
must be compared against the **same source revision**, tokenizer, system/user
prompt, deterministic greedy decoding and maximum output tokens. A paired
validation run is valuable to measure execution and differences in emitted
bytes, but training validation was visible to the training infrastructure and
these fictional pairs are not independently adjudicated.

A new local-only `python -m awf.evaluation.paired_lora` command loads
the original pinned manifest's **validation** rows, verifies the external
adapter receipt SHA and every adapter file, generates the unadapted baseline
first, then wraps that **same base** with PEFT for adapted inference.
Raw prompts and outputs are written only under an existing private `.awf`
directory. The metadata receipt contains SHA and lengths, not text;
stdout contains only receipt location and aggregate counts. A missing CUDA
device, modified source/adapter, reused output path or missing source opt-in
stops execution.

No detector score, reference fidelity score, factual correctness, human
authorship or academic validity can be inferred from this smoke test. All
semantic checks remain `NOT_ASSESSED` and all acceptance flags remain false.
The sealed holdout is not read. This study must not select training
hyperparameters or be presented as independent gold evidence.

**Rejected:** judging two variants with their own logits, copying private
weights to GitHub/Colab, treating differences as improvements, and
altering pre-existing trained receipts to suit evaluation.
