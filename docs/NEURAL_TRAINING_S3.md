# S3 — AWF Neural Adapter, supervised LoRA pilot

**State:** training infrastructure, draft PR #44 stacked on #43. A saved adapter is an AWF-owned *parameter-efficient delta*, not a pre-trained-from-scratch model. The existing original neural base remains pinned. **Do not infer academic reliability or author authenticity from a training loss.**

## Grounded technical decisions

- Official [Qwen2.5 0.5B Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), Apache-2.0, 0.49B parameters. Immutable Hugging Face revision `7ae557604adf67be50417f59c2c2f167def9a775` observed from its metadata on 2026-10-21.
- [TRL SFTTrainer](https://huggingface.co/docs/trl/sft_trainer): conversational **prompt–completion** examples, `completion_only_loss=True`, `assistant_only_loss=False`, no sequence packing in the pilot. This prevents wasting training signal on re-predicting the user prompt. Semantically strong validation remains independent.
- [PEFT](https://huggingface.co/docs/peft/main/tutorial/peft_model_config): causal-LM `LoraConfig`, `q_proj` and `v_proj`, `r=8`, `alpha=16`. First local run: *unquantized LoRA* on RTX 4050 6 GB, 0.5B model, max 256 tokens, batch 1, grad accumulation 2. Profiles are bounded; memory fit is **measured, not guaranteed**.
- Optional [4-bit QLoRA / NF4](https://huggingface.co/docs/transformers/main/quantization/bitsandbytes?bnb=4-bit) `colab_qlora` profile with same SHA-pinned base. Colab runtime is not assumed to have any specific GPU or unlimited session; see [Colab FAQ](https://research.google.com/colaboratory/faq.html).
- The original ZIP AWS 3.19.1 (private) **is not a training dataset**, and no historical RULE is promoted to accepted merely by training.

## Data contract, rights, leakage prevention

`src/awf/training/manifest.py` accepts SHA-256-bound local UTF-8 JSON and JSONL only, with explicit `SYNTHETIC_SMOKE` or `OWNER_AUTHORED` roles, source-rights declaration, and **separate** `train`, `validation` and `holdout` groups. Only train/validation text is opened by the loader; the holdout descriptor is `SEALED_NOT_READ` and holds group IDs and SHA, not text. This prevents this trainer from reading the holdout, but **a hash and claimed permission are not independent scientific or legal certification**. Avoid any holdout-guided hyperparameter selection and preserve original group identity from first creation.

For real owner-authored source: a separate explicit `--owner-authorized` is required. It records owner attestation only. Third-party sources/unknown licenses, private AWS rules and external articles are **not automatically permitted** by this flag. The synthetic generator writes tiny fictional pairs *only to ignored `.awf/`*, not Git. It supplies a holdout placeholder to exercise split plumbing: **not a scientific unseen gold test**.

## Local reproducibility

Create an isolated Python 3.12 environment **outside global packages** and install a CUDA-enabled PyTorch build that matches your GPU/driver according to the official [PyTorch installer](https://pytorch.org/get-started/locally/). Then install `requirements-neural.txt`. ML dependencies are not imported by AWF's normal CLI or CI. Keep CUDA packages and model cache on local disk.

```bash
python -m awf.training.synthetic_smoke --output .awf/neural-smoke
# Copy manifest_sha256 from output; inspect and retain it.
python -m awf.training.runner \
  --manifest .awf/neural-smoke/manifest.json \
  --manifest-sha256 YOUR_RECORDED_SHA256 \
  --profile config/training/local_lora_0_5b.json \
  --allow-synthetic-smoke
# Preflight does not load torch/TRL or modify model weights.
python -m awf.training.runner \
  --manifest .awf/neural-smoke/manifest.json \
  --manifest-sha256 YOUR_RECORDED_SHA256 \
  --profile config/training/local_lora_0_5b.json \
  --allow-synthetic-smoke --execute
```

The only trainable model parameters should be the LoRA adapter matrices; the original Qwen base is frozen. Output goes under ignored `.awf/model-runs/<uuid>/adapter`, with hashes of each saved adapter file and a metadata-only receipt. Runtime reports model SHA/version, dataset hashes, optimizer updates, GPU allocation and training loss. Notebooks do not publish weights, upload text to GitHub, or push to Hugging Face.

For Google Colab open `notebooks/awf_s3_qlora_colab.ipynb`; the notebook demonstrates the same source/rights gates and requires explicit GPU, inputs and execution authorization. Running it on a paid or free runtime may involve quotas. Colab is a hosted third-party environment: **do not upload private manuscripts without separate permission and reviewing the provider's terms**.

## Exit criteria

A **true** local LoRA adapter exists only after observing `gradient_updates_observed > 0`, saved weights with hash manifest, successful reload and independent held-out evaluation. A toy synthetic smoke adapter may prove training infrastructure works, **not** source fidelity or detector efficacy. Before a scientific model comparison: obtain reviewed owner-authored or licensed source-grounded examples, immutable document/author-separated holdout, blind annotations and baseline vs adapter revision receipts; report metrics including critical semantic drift and abstentions. The 168 historic MUST remain UNRESOLVED; 16 DEFERRED_LAB remain EVAL_ONLY.

**Files:** `training/manifest.py`, `training/runner.py`, `training/synthetic_smoke.py`, `config/training/`, `requirements-neural.txt`, `tests/unit/test_neural_training.py`, and [ADR-0036](adr/0036-peft-adapter-training.md).
