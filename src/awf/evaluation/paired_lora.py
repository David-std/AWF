"""Private paired BASE vs PEFT-adapter inference on pre-existing validation inputs.

Engineering diagnostic only. No gold labels, training, sealed holdout reads,
editorial acceptance or scholarly validity claims are produced.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from awf.training.manifest import BASE_MODEL, MODEL_REVISION, load_training_dataset
from awf.training.verify_adapter import verify_saved_adapter

_SYSTEM = (
    "Revise academic writing without altering claims, citations, "
    "quantities, conditions or the author's intent. "
    "If evidence is insufficient, state the uncertainty."
)
_MAX_NEW_TOKENS = 64


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _json_bytes(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def make_paired_diagnostic(
    rows: tuple[dict[str, str], ...],
    *,
    produce: Callable[[str, str], str],
    dataset_sha256: str,
    receipt_sha256: str,
    adapter_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run each prompt through two variants; export no source/output prose in receipt."""
    if not 1 <= len(rows) <= 128:
        raise ValueError("invalid paired validation count")
    seen: set[str] = set()
    cases: list[dict[str, Any]] = []
    private_cases: list[dict[str, str]] = []
    for row in rows:
        case_id = row["id"]
        if case_id in seen or row["language"] not in {"es", "en"}:
            raise ValueError("duplicate ID or unsupported language")
        seen.add(case_id)
        prompt = row["prompt"]
        a = produce("base", prompt)
        b = produce("adapter", prompt)
        if not isinstance(a, str) or not isinstance(b, str):
            raise ValueError("a model response is not text")
        cases.append(
            {
                "case_id": case_id,
                "document_group_sha256": _sha(row["group_id"]),
                "language": row["language"],
                "prompt_sha256": _sha(prompt),
                "base_output_sha256": _sha(a),
                "adapter_output_sha256": _sha(b),
                "base_output_chars": len(a),
                "adapter_output_chars": len(b),
                "identical_output": a == b,
                "base_empty": not bool(a.strip()),
                "adapter_empty": not bool(b.strip()),
                "semantic_status": "NOT_ASSESSED",
            }
        )
        private_cases.append(
            {
                "case_id": case_id,
                "group_id": row["group_id"],
                "language": row["language"],
                "prompt": prompt,
                "base_output": a,
                "adapter_output": b,
            }
        )
    report = {
        "schema_version": "1.0.0",
        "status": "PAIRED_VALIDATION_DIAGNOSTIC_ONLY",
        "model_id": BASE_MODEL,
        "model_revision": MODEL_REVISION,
        "adapter_receipt_sha256": receipt_sha256,
        "adapter_weights_sha256": adapter_sha256,
        "dataset_manifest_sha256": dataset_sha256,
        "prompt_template": "S3_TRAINING_SYSTEM_V1",
        "decoding": {"do_sample": False, "max_new_tokens": _MAX_NEW_TOKENS},
        "case_count": len(cases),
        "changed_output_count": sum(not c["identical_output"] for c in cases),
        "empty_output_count": sum(
            int(c["base_empty"]) + int(c["adapter_empty"]) for c in cases
        ),
        "cases": cases,
        "validation_used_in_training": False,
        "validation_available_during_training": True,
        "sealed_holdout_opened": False,
        "independent_gold_verified": False,
        "semantic_equivalence_verified": False,
        "citation_grounding_verified": False,
        "model_quality_certified": False,
        "document_acceptance": "NEEDS_REVIEW",
        "original_text_exported_in_receipt": False,
    }
    private = {"schema_version": "1.0.0", "cases": private_cases}
    return report, private


def run_paired_inference(
    *,
    manifest: Path,
    manifest_sha256: str,
    run_directory: Path,
    receipt_sha256: str,
    output_directory: Path,
    allow_synthetic_smoke: bool,
) -> dict[str, Any]:
    """Fail closed on unsigned inputs and pre-existing output; never touch holdout."""
    if output_directory.is_symlink() or output_directory.exists():
        raise ValueError("output directory already exists or is a symlink")
    if ".awf" not in output_directory.resolve().parts:
        raise ValueError("paired outputs must remain inside private .awf")
    dataset = load_training_dataset(
        manifest,
        expected_sha256=manifest_sha256,
        allow_synthetic_smoke=allow_synthetic_smoke,
        owner_authorized=False,
    )
    if dataset.role != "SYNTHETIC_SMOKE":
        raise ValueError("only synthetic validation data are permitted in this pilot")
    verified = verify_saved_adapter(
        run_directory, expected_receipt_sha256=receipt_sha256
    )
    if not verified["base_revision_saved_in_adapter_config"]:
        raise ValueError("adapter missing its pinned base revision")
    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    peft = importlib.import_module("peft")
    if not torch.cuda.is_available():
        raise ValueError("paired inference requires a local CUDA GPU")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=MODEL_REVISION, trust_remote_code=False
    )
    base = transformers.AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        revision=MODEL_REVISION,
        trust_remote_code=False,
        dtype=torch.float16,
    ).to("cuda")
    base.eval()

    def generate(model: Any, prompt: str) -> str:
        conversation = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ]
        ids = tokenizer.apply_chat_template(
            conversation, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to("cuda")
        with torch.inference_mode():
            generated = model.generate(
                ids,
                do_sample=False,
                max_new_tokens=_MAX_NEW_TOKENS,
                pad_token_id=tokenizer.eos_token_id,
            )
        return str(tokenizer.decode(generated[0][ids.shape[1] :], skip_special_tokens=True))

    base_results = {
        row["id"]: generate(base, row["prompt"]) for row in dataset.validation
    }
    adapter = peft.PeftModel.from_pretrained(
        base, str(run_directory / "adapter"), is_trainable=False
    )
    adapter.eval()
    adapter_results = {
        row["id"]: generate(adapter, row["prompt"]) for row in dataset.validation
    }

    def produce(which: str, prompt: str) -> str:
        # The prompt-to-ID mapping is unique in this immutable synthetic source.
        match = next(row for row in dataset.validation if row["prompt"] == prompt)
        return (base_results if which == "base" else adapter_results)[match["id"]]

    summary, private = make_paired_diagnostic(
        dataset.validation,
        produce=produce,
        dataset_sha256=manifest_sha256,
        receipt_sha256=receipt_sha256,
        adapter_sha256=str(verified["adapter_weights_sha256"]),
    )
    parent = output_directory.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("private output parent must already exist")
    staging = parent / f".paired-{uuid4().hex}"
    staging.mkdir(mode=0o700)
    try:
        (staging / "private_outputs.json").write_bytes(_json_bytes(private))
        (staging / "receipt.json").write_bytes(_json_bytes(summary))
        os.rename(staging, output_directory)
    except BaseException:
        # Preserve partial evidence for forensic recovery, never silently delete it.
        raise
    return {
        "status": summary["status"],
        "receipt_sha256": hashlib.sha256((output_directory / "receipt.json").read_bytes()).hexdigest(),
        "case_count": summary["case_count"],
        "changed_output_count": summary["changed_output_count"],
        "output_directory": str(output_directory),
        "text_exported_in_stdout": False,
        "independent_gold_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="awf-paired-lora")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-synthetic-smoke", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_paired_inference(
            manifest=args.manifest,
            manifest_sha256=args.manifest_sha256,
            run_directory=args.run_directory,
            receipt_sha256=args.receipt_sha256,
            output_directory=args.output,
            allow_synthetic_smoke=args.allow_synthetic_smoke,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"AWF_ERROR [PAIRED_EVALUATION_FAILED] {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
