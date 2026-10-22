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
