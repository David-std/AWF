# ADR-0036 — SHA-pinned Qwen LoRA training with explicit data-rights boundary

**Date:** 2026-10-21. **Status:** experimental / draft PR #44, stacked on #43.

**Decision:** Fine-tune a small, Apache-2.0 Qwen2.5-Instruct base using PEFT LoRA, completion-only supervised TRL training, a documented initial local 6-GB GPU profile, and an optional NF4 4-bit Colab profile. Base model and dataset bytes are pinned by SHA; downstream inference never treats an adapter as a trustworthy scholarly judge. The model revision and tokenizer are fixed together. No full pretraining.

**Architecture:** `awf.training` is offline and separate from runtime `AgentExecutionPort`; the base domain has no torch imports. A stdlib validation module owns dataset source/gate and split checks. The runner imports ML packages lazily only after preflight and explicit `--execute`. The public repository contains *no* training dataset, unlicensed third-party text, tokens or model weights.

**Rights:** Owner attestation is not third-party proof. Training sources require separate affirmative rights and an authorization flag. Synthetic smoke is strictly marked fictional. The holdout is sealed and never opened by training; synthetic placeholder holdout is not independently reviewed.

**Alternatives:** training from scratch (cost/data), detector reward optimization (invalid proxy), automatic LLM self-labelling as gold (circular), unpinned `main` branch model revisions (unreproducible), automatic public publishing (rights/privacy), and shared global Python package installation (environment interference) rejected.

**Exit:** A verified saved adapter and one reproducible gradient run are engineering evidence. Quality claims require independently reviewed, source-licensed document-group holdouts and baseline/adapter comparisons. Report resource usage and failure/abstention cases; do not assert that a detector score authenticates human writing.
