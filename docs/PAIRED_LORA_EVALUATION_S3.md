# Paired baseline vs LoRA, local smoke diagnostic

This experimental code is stacked on PR #45 and intentionally does **not**
repeat the previous training. It requires the owner-preserved run with the
exact SHA-verified receipt, the original SHA-pinned synthetic manifest and a
local CUDA installation. It reads **only the two validation rows**, never
the sealed holdout. The training/validation separation is structural;
the development fixture is not independent scholarly gold.

Example from the private PR #45 checkout (replace private paths):

```powershell
$env:PYTHONPATH="C:\path\AWF\src"
python -m awf.evaluation.paired_lora `
  --manifest "C:\private\neural-smoke\manifest.json" `
  --manifest-sha256 73c1c93971dcdfecd783bd16c747f70a77b04158e05e54af00a9716958770fda `
  --run-directory "C:\private\model-runs\f4e66e7e8e3b420d8dd74dfab79536fc" `
  --receipt-sha256 2b37cc7f8376be93ade5da3429f1445a8298fb33cf28c9de849e45a80b7c28e1 `
  --output "C:\private\.awf\paired\first-run" `
  --allow-synthetic-smoke
```

**Output**: private `private_outputs.json` and metadata-only `receipt.json`.
A distinct, unused output path is required for each run. No model inference
or CUDA execution is performed during CI. Until actual GPU execution and
an independently reviewed, legally usable gold set, **all scientific
quality conclusions must remain UNKNOWN**.

Preserved originals live in the owner's separate private evidence archive;
never publish exact machine paths, training data, outputs, or model weights.

## Verified local paired inference (2026-10-21)

On the authorized RTX 4050 host, two synthetic **validation** prompts were run through the pinned base and the post-fix adapter. The first attempt failed on Transformers 5 `BatchEncoding` handling (exit 1; no completed comparison); after passing `input_ids` explicitly, two prompts completed with exit 0 and one different output. A final rerun used an explicit attention mask and produced the same metadata digest `c340de7458b9898749a226b23759d2ba43d46d3b054aa2f656ad603d062559aa` (two cases, one changed). Both private files were preserved and verified in a durable user-private folder, with the originals retained.

**Measured only:** successful pinned inference and output hashes. **Not measured:** validation loss, correct meaning, citations, academic quality, independent gold or statistically meaningful LoRA lift. Do not treat one changed response as improvement; all semantic flags remain false.

A separate [independent gold protocol](INDEPENDENT_GOLD_PROTOCOL_S3.md) specifies rights evidence, grouped leakage prevention, source-bounded annotation and blind review. It is not yet an implemented scientifically reviewed dataset.
