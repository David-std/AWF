# AWF — PR #45 / real local LoRA training and artifact verification

Date: 2026-10-21 (America/Lima). [PR #45](https://github.com/David-std/AWF/pull/45) `feat/s3-peft-training-foundation`, directly based on draft PR #43 (`feat/s3-synthetic-scope-benchmark`). PR #44 `feat/s4-lora-smoke-pipeline` is a separate, parallel draft based on #43, **not a parent of #45**. Do not merge, retarget, delete or overwrite either branch without a reconciliation. Main/develop left unchanged.

## Verified code and local results

- Prior code SHA `68a7a3143415672faafb7f908ae44e8d790825c8`, [push CI 39683381527](https://github.com/David-std/AWF/actions/runs/39683381527) and [PR CI 39683389762](https://github.com/David-std/AWF/actions/runs/39683389762), **4/4 SUCCESS each** (Ubuntu/Windows, Python 3.12/3.13), 546 tests Ubuntu 3.12, Pyright 0, Ruff/build pass.
- User-authorized RTX 4050 laptop, isolated neural venv (not global Python): PyTorch 2.9.1+cu130 CUDA true, Transformers 5.0.0, PEFT 0.20.0, TRL 0.29.1.
- Actual `python -m awf.training.runner --manifest ... --manifest-sha256 73c1c93971dcdfecd783bd16c747f70a77b04158e05e54af00a9716958770fda --profile config/training/local_lora_0_5b.json --allow-synthetic-smoke --execute`, exact SHA above, **exit 0**. Eight optimizer steps, train loss `0.9749333038926125`, training-only runtime 15.36 s, total process 81.95 s, max CUDA allocated 1,268,997,632 bytes. Privately stored adapter under `.awf/model-runs/a39d4d23782d4cd79ee94325b0566696/adapter`.
- The saved receipt's 7 artifact file SHA-256s match the original bytes, including `adapter_model.safetensors` 2,175,168 bytes. **Independent direct offline reload** via `PeftModel.from_pretrained` and a model loaded from the pinned local cache succeeded. 96 adapter tensor entries were all nonzero; an 8-new-token synthetic generation succeeded; loaded LoRA parameters frozen for inference (trainable count 0).
- Not a semantic experiment: dataset is 8 fictional train + 2 fictional validation examples and a sealed fake holdout descriptor (no actual gold holdout text). Training loss is not proof that rewriting improves. No output text, private synthetic dataset, manuscripts or weights were uploaded to GitHub.
- **Reproducibility issue found:** earlier saved PEFT config had `revision:null` while the receipt pinned model revision. This new code passes `revision=MODEL_REVISION` to `LoraConfig`, and adds a separate stdlib verifier CLI to compare saved file SHA256 and metadata. The old adapter and receipt stay **unchanged**; the checker reports `base_revision_saved_in_adapter_config=false` for it. Check new commit CI and new-run behavior before claiming fully corrected serialization.

## Source ownership, limitations, next steps

The base is Qwen2.5-0.5B-Instruct, HF revision `7ae557604adf67be50417f59c2c2f167def9a775`, Apache-2.0. AWF owns the newly trained LoRA **delta**, not the pretraining weights. Owner attestation and the dataset's own SHA-256s are not independent proof of source rights, scientific annotation, plagiarism provenance, or out-of-distribution generalization. 168 historical MUST remain unadjudicated and 16 DEFERRED_LAB remain EVAL_ONLY.

Next execute the new `python -m awf.training.verify_adapter RUN_DIR --expected-receipt-sha256 HASH` against both old and post-fix saved adapter; verify no false `revision` attestation. Add independently reviewed, rights-cleared claim-preserving source pairs before benchmarking baseline versus adapted generation; group-split by source/document to prevent leakage. Colab QLoRA notebook remains **untested on Colab**; it is a reproducible recipe, not a demonstrated result. Training should never optimize detector scores while sacrificing truth fidelity.

Read [neural training guide](../NEURAL_TRAINING_S3.md), [ADR-0036](../adr/0036-peft-adapter-training.md), [S3 #43 handoff](2026-10-21-S3-PR43-SYNTHETIC-SCOPE.md), and repository `AGENTS.md`.
