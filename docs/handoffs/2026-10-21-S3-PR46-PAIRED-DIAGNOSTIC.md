# AWF Sprint 3 — PR #46 continuation, 2026-10-21

**Current working branch:** `feat/s3-paired-adapter-evaluation`, [draft PR #46](https://github.com/David-std/AWF/pull/46), stacked directly on draft PR #45 (base `feat/s3-peft-training-foundation`), **not** on experimental parallel PR #44. Do not merge, retarget or repeat training.

## Critical historical anchor

Read [full PR #45 transfer](2026-10-21-S3-PR45-CONTINUATION-COMPLETE.md) first for exact model revision, run IDs, hardware, adapter bytes and hashes, source permissions and known limits. The post-fix LoRA trained eight real gradient updates; no new training was run in PR #46.

## Private preservation completed

On the authorized Windows machine, copied both historical model runs and the original synthetic manifest/train/validation files to a durable user-private `Documents/AWF-Private-Evidence/PR45-2026-10-21/` folder. Rehashed **19/19 files** against their untouched originals. Canonical receipt SHA-256 `2b37cc7f8376be93ade5da3429f1445a8298fb33cf28c9de849e45a80b7c28e1`, adapter weights SHA `8261a513e3a2fa517f13814bf422669d4763f62b5ff1f3fcacbf94a3dd26f319`. No deletions or in-place modifications.

## Paired synthetic evaluation

Code: `src/awf/evaluation/paired_lora.py`; tests: `tests/unit/test_paired_lora.py`; [ADR-0037](../adr/0037-paired-adapter-diagnostic.md) and [evaluation instructions](../PAIRED_LORA_EVALUATION_S3.md).

- Actual GPU execution on ASUS_ROG_STRIX, local Qwen2.5-0.5B-Instruct pinned revision `7ae557604adf67be50417f59c2c2f167def9a775`, previously trained LoRA run `f4e66e7e8e3b420d8dd74dfab79536fc`.
- Original manifest SHA `73c1c93971dcdfecd783bd16c747f70a77b04158e05e54af00a9716958770fda` and verified original adapter receipt SHA pinned externally. Same tokenizer/system message/user prompt; greedy decoding, 64 token cap, same GPU for both variants.
- **2/2 synthetic validation prompts processed; 1 changed output, 1 identical.** Exit code 0, SHA-bound private receipt `c340de7458b9898749a226b23759d2ba43d46d3b054aa2f656ad603d062559aa`.
- The final version explicitly supplies `attention_mask`; second execution had the **same metadata receipt digest** as the previous execution and did not emit the mask ambiguity warning. A benign Transformers flag warning remains.
- Saved private outputs/receipt to durable `Documents/AWF-Private-Evidence/PR46-2026-10-21/masked-run` without overwriting. Both files SHA-verified against the scratch output; private outputs SHA `f802bcfffa6ed4193f13aed85d80fde1e3562096655f6ed60370676c2c426819`. No private contents uploaded.
- Negative attempt retained conceptually: the first inference failed after weight load because Transformers 5 `BatchEncoding` was passed instead of the `input_ids` tensor. Corrected and re-executed; no fake success or relabeling of that attempt.
- No third-party rights, gold independence, academic improvement, text meaning preservation or citation validation has been established.

## Validation and CI

The PR code must pass Ubuntu and Windows × Python 3.12/3.13, Ruff, Pyright, pytest and build for the **final commit**. Earlier code commits encountered Ruff formatting failures and a mistakenly copied terminal footer; both were fixed without claiming them as green. A prior commit `88cdcad486d4347e3083356b3b934c1ba5420ca4` passed branch and PR CI, but later commits require their own checks. Latest code commit before this handoff: `676511c795f5a6873ecd9cc68850f11bef38a442`; check CI status for its run and for the subsequent documentation commit.

Local neural environment did not include `pytest`; use GitHub CI for the unit suite rather than claiming it passed locally. GPU runs are not part of normal CI.

## Next action

Follow [gold protocol](../INDEPENDENT_GOLD_PROTOCOL_S3.md). Acquire rights-cleared independent source-grounded cases, freeze document/author/source split, blind reviewers and labels before any quality claims. Do **not** use synthetic train/validation or sealed placeholder as independent gold; never optimize on detector percentages.
