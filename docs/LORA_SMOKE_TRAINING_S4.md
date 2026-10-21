# AWF S4 — LoRA adapter smoke pipeline (explicitly synthetic only)

**Status:** engineering prototype. This is a **trainable LoRA adapter**, not yet a reliable academic editor or a validated human-writing model. Draft PR #44 directly on #43. No historic AWS corpus, real manuscript, journal PDF, detected-AI text or third-party material is training input.

## Why this stack

- **Base:** `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775` (Hugging Face model API inspected 2026-10-21; metadata reports `apache-2.0`). This is a *small hardware/procedure smoke base*, **not** the final architecture's best quality model or a right-clearance certificate.
- **Method:** parameter-efficient **LoRA** (`q_proj`, `v_proj`, rank 8, alpha 16). Default 2 train steps, completion-only supervised loss. No DPO and no automatic inference-score optimization.
- **Libraries:** Hugging Face Transformers + PEFT + TRL SFTTrainer + datasets, loaded lazily. Nothing changes the existing lightweight AWF core install. Optional `pip install -e '.[train-smoke]'` goes into a **new isolated virtual environment** only. CUDA GPU is required for training.
- **Hardware discovered:** ASUS RTX 4050 Laptop, **6141 MiB total GPU memory** (~5920 MiB free when checked). This is plausible for a tiny FP16 base plus LoRA but **not proof it fits**; capture peak VRAM and any OOM on a real run. 7B FP16/QLoRA training is not assumed possible on this GPU. Future A100/T4/Colab is an optional independent training environment.

## Data contract: fail closed

Only a **SHA-256-pinned UTF-8 JSON** file at a private path outside tracked Git, at most 256 KiB, 3–128 rows. Required top-level keys: `schema_version=1.0.0`, `dataset_role=LOCAL_SYNTHETIC_SMOKE_ONLY`, `examples`. Each example: `example_id`, `source_group_id`, `language=es|en`, `split=train|eval`, `prompt`, `completion`, `annotation_provenance=DEVELOPER_SYNTHETIC`. At least 2 train and 1 eval. No ID reuse, no exact duplicated normalized prompt/completion, no source group may cross train/eval. Prompt/completion are capped at 4 KiB each. No training on `HOLDOUT`, `REVIEWED_GOLD`, `REAL_MANUSCRIPT` or any other role.

**Important caveat:** `DEVELOPER_SYNTHETIC` is a file assertion, not independent proof of authorship or rights. This prototype is intended solely for fictional examples authored specifically for software smoke tests. Real licensed corpora require the separate ADR-0028 rights authority and independent review. Merely renaming private content or setting a boolean does not confer training rights.

## Commands

Create your own synthetic JSON inside `.awf/private/` (never in Git), obtain the actual SHA from an independent command, and run a **dependency-free preflight**:

```powershell
$sha = (Get-FileHash .awf\private\lora-smoke.json -Algorithm SHA256).Hash.ToLowerInvariant()
awf ml-smoke .awf\private\lora-smoke.json --expected-sha256 $sha
```

Preflight prints metadata only: file SHA, counts, language, split-group isolation and intended base revision; it neither imports PyTorch nor loads model weights. Only after source inspection, install optional ML dependencies in a venv and run:

```powershell
awf ml-smoke .awf\private\lora-smoke.json --expected-sha256 $sha --max-steps 2 --allow-synthetic-training
```

This uses **locally cached** weights by default. If you explicitly authorize fetching the **fixed pinned revision** from Hugging Face, add `--allow-model-download`. No API key is required for this public model. Weights and training artifacts remain under ignored `.awf/ml/smoke/`; no uploads, no pushing to Hugging Face, no MLflow or external telemetry.

The receipt must contain actual adapter `adapter_model.safetensors` hash, installed versions, CUDA device, training loss if returned, counts, and `promotion=DENIED`. Validation/eval examples are not passed to the optimizer, and are not represented as scholarly gold/holdout. If a model fails to load, CUDA is unavailable or training fails, do **not** claim a trained adapter exists.

## External research basis

- Hugging Face TRL [SFT Trainer](https://huggingface.co/docs/trl/sft_trainer): completion-only loss on prompt/completion pairs and `peft_config` integration.
- Hugging Face PEFT [quantization integration](https://huggingface.co/docs/peft/developer_guides/quantization): 4-bit/NF4 and `prepare_model_for_kbit_training` for future QLoRA experiments.
- [Qwen2.5-0.5B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct): model weights/metadata. Record exact pinned commit; an HF license label is not independent chain-of-title verification.

## Next meaningful gates

1. **Synthetic adapter actual run** in isolated CUDA env, record peak GPU, steps, measured loss, output adapter sha and compare before/after on separate synthetic eval samples. An apparent improvement over 2 steps is neither scientific evidence nor useful academic training.
2. Independently annotated **rights-cleared document groups** and a sealed holdout before any real corpus training. Trust and rights claims must not be self-certified; preserve disagreement and reviewer provenance.
3. Reusable `ModelPort` inference for base + PEFT adapter with exact seed/revision and source-verifier gates, and baseline comparisons. Ollama Qwen2.5 7B is currently a separate inference endpoint; a new PEFT adapter for Qwen2.5 0.5B **cannot** be attached blindly to that 7B model.
4. Only after out-of-sample performance improvements should a real AWF editor adapter be named/promoted. `168 MUST` remain unresolved; `16 DEFERRED_LAB` remain EVAL_ONLY.
