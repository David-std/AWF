"""Explicit, offline-output PEFT/TRL runner. Optional ML imports occur after data gates.

This runner only performs SFT on completion tokens; it is not a semantic judge.
The sealed holdout is never loaded, read, or evaluated here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from awf.training.manifest import (
    BASE_MODEL,
    MODEL_REVISION,
    TrainingDataset,
    load_training_dataset,
)

_ALLOWED_PROFILES = {"local_lora", "colab_qlora"}
_SHA = re.compile(r"[a-f0-9]{64}\Z")


def load_profile(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 20_000:
        raise ValueError("profile must be a small regular file")
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict) or set(profile) != {
        "schema_version", "profile", "model_id", "model_revision",
        "max_length", "steps", "learning_rate", "lora_r",
        "lora_alpha", "lora_dropout", "gradient_accumulation_steps", "seed",
    }:
        raise ValueError("unexpected training profile schema")
    if profile["schema_version"] != "1.0.0" or profile["profile"] not in _ALLOWED_PROFILES:
        raise ValueError("training profile is not supported")
    if profile["model_id"] != BASE_MODEL or profile["model_revision"] != MODEL_REVISION:
        raise ValueError("training model must be bound to reviewed repository revision")
    for field, low, high in (
        ("max_length", 64, 1024), ("steps", 1, 2500), ("lora_r", 2, 64),
        ("lora_alpha", 2, 128), ("gradient_accumulation_steps", 1, 32),
        ("seed", 0, 2**32 - 1),
    ):
        value = profile[field]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"invalid {field} in training profile")
    rate = profile["learning_rate"]
    dropout = profile["lora_dropout"]
    if (type(rate) not in {int, float} or not 1e-7 <= rate <= 0.001
        or type(dropout) not in {int, float} or not 0 <= dropout <= 0.2):
        raise ValueError("invalid training optimization parameters")
    return profile


def _dataset_view(data: tuple[dict[str, str], ...]) -> list[dict[str, Any]]:
    """TRL prompt-completion formatting, not free-text model self-supervision."""
    return [
        {
            "prompt": [
                {
                    "role": "system",
                    "content": (
                        "Revise academic writing without altering claims, citations, "
                        "quantities, conditions or the author's intent. "
                        "If evidence is insufficient, state the uncertainty."
                    ),
                },
                {"role": "user", "content": row["prompt"]},
            ],
            "completion": [{"role": "assistant", "content": row["completion"]}],
        }
        for row in data
    ]


def _module_versions(modules: dict[str, Any]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for key, module in modules.items():
        version: object = getattr(module, "__version__", "UNKNOWN")
        versions[key] = str(version)
    return versions


def _hash_tree(folder: Path) -> dict[str, str]:
    digest_map: dict[str, str] = {}
    for file in sorted(folder.rglob("*")):
        if file.is_symlink():
            raise ValueError("training output cannot include symbolic links")
        if file.is_file():
            relative = str(file.relative_to(folder)).replace("\\", "/")
            digest_map[relative] = hashlib.sha256(file.read_bytes()).hexdigest()
    return digest_map


def run_training(
    dataset: TrainingDataset,
    profile: dict[str, Any],
    *,
    workspace: Path,
    execute: bool,
) -> dict[str, Any]:
    """Records actual work separately from planned execution and owner attestation."""
    if workspace.is_symlink():
        raise ValueError("model workspace cannot be a symbolic link")
    basic: dict[str, Any] = {
        "schema_version": "1.0.0",
        "dataset_role": dataset.role,
        "manifest_sha256": dataset.manifest_sha256,
        "train_sha256": dataset.train_sha256,
        "validation_sha256": dataset.validation_sha256,
        "sealed_holdout_sha256": dataset.holdout_sha256,
        "train_examples": len(dataset.train),
        "validation_examples": len(dataset.validation),
        "profile": profile["profile"],
        "model_id": profile["model_id"],
        "model_revision": profile["model_revision"],
        "optimizer_steps_planned": profile["steps"],
        "independent_rights_verified": False,
        "independent_gold_verified": False,
        "semantic_equivalence_verified": False,
        "holdout_opened": False,
        "holdout_evaluated": False,
        "training_authorization_basis": "OWNER_ATTESTATION_NOT_INDEPENDENT",
        "model_quality_certified": False,
        "document_acceptance": "NEEDS_REVIEW",
    }
    if not execute:
        return {**basic, "status": "PREFLIGHT_ONLY", "gradient_updates_observed": 0}

    torch = importlib.import_module("torch")
    trl = importlib.import_module("trl")
    peft = importlib.import_module("peft")
    transformers = importlib.import_module("transformers")
    datasets = importlib.import_module("datasets")

    if not torch.cuda.is_available():
        raise ValueError("training requires an explicitly detected CUDA GPU")
    bf16_supported = bool(torch.cuda.is_bf16_supported())
    use_bf16 = bf16_supported
    # Single-GPU compute. Keep base model unmodified by training.
    model_opts: dict[str, Any] = {
        "revision": MODEL_REVISION,
        "trust_remote_code": False,
        "dtype": torch.bfloat16 if use_bf16 else torch.float16,
    }
    if profile["profile"] == "colab_qlora":
        bnb = importlib.import_module("transformers").BitsAndBytesConfig
        model_opts["quantization_config"] = bnb(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
            bnb_4bit_use_double_quant=True,
        )
        model_opts["device_map"] = {"": torch.cuda.current_device()}

    run_id = uuid.uuid4().hex
    target = workspace / run_id
    # Output is intentionally untracked under .awf/model-runs/, never public Git.
    if not workspace.is_dir():
        workspace.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("training output path collision")
    target.mkdir(mode=0o700)
    model = transformers.AutoModelForCausalLM.from_pretrained(BASE_MODEL, **model_opts)
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        BASE_MODEL, revision=MODEL_REVISION, trust_remote_code=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    adapter = peft.LoraConfig(
        r=profile["lora_r"], lora_alpha=profile["lora_alpha"],
        lora_dropout=profile["lora_dropout"],
        target_modules=["q_proj", "v_proj"],
        bias="none", task_type="CAUSAL_LM",
    )
    train_data = datasets.Dataset.from_list(_dataset_view(dataset.train))
    validation_data = datasets.Dataset.from_list(_dataset_view(dataset.validation))
    options = trl.SFTConfig(
        output_dir=str(target / "checkpoints"),
        max_steps=profile["steps"], learning_rate=profile["learning_rate"],
        max_length=profile["max_length"], completion_only_loss=True,
        assistant_only_loss=False, packing=False,
        per_device_train_batch_size=1, per_device_eval_batch_size=1,
        gradient_accumulation_steps=profile["gradient_accumulation_steps"],
        gradient_checkpointing=True, fp16=not use_bf16, bf16=use_bf16,
        seed=profile["seed"], data_seed=profile["seed"],
        report_to="none", push_to_hub=False, save_strategy="no",
        eval_strategy="no", logging_steps=1,
        disable_tqdm=True,
    )
    trainer = trl.SFTTrainer(
        model=model,
        args=options,
        train_dataset=train_data,
        eval_dataset=validation_data,
        processing_class=tokenizer,
        peft_config=adapter,
    )
    output = trainer.train()
    actual_steps = int(trainer.state.global_step)
    if not 1 <= actual_steps <= profile["steps"]:
        raise ValueError("trainer failed to report observed gradient steps")
    adapter_dir = target / "adapter"
    trainer.save_model(str(adapter_dir))
    receipt = {
        **basic,
        "status": "SFT_ADAPTER_TRAINED",
        "gradient_updates_observed": actual_steps,
        "training_loss_reported": float(output.training_loss),
        "gpu_name": str(torch.cuda.get_device_name(0)),
        "gpu_memory_max_allocated_bytes": int(torch.cuda.max_memory_allocated(0)),
        "precision": "bf16" if use_bf16 else "fp16",
        "python_version": platform.python_version(),
        "library_versions": _module_versions({
            "torch": torch, "trl": trl, "peft": peft,
            "transformers": transformers, "datasets": datasets,
        }),
        "adapter_files_sha256": _hash_tree(adapter_dir),
        "training_output_private": True,
    }
    (target / "receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return {
        **basic, "status": receipt["status"],
        "gradient_updates_observed": actual_steps,
        "receipt_path": str(target / "receipt.json"),
        "adapter_directory": str(adapter_dir),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="awf-neural-train")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-synthetic-smoke", action="store_true")
    parser.add_argument("--owner-authorized", action="store_true")
    args = parser.parse_args(argv)
    try:
        source = load_training_dataset(
            args.manifest, expected_sha256=args.manifest_sha256,
            allow_synthetic_smoke=args.allow_synthetic_smoke,
            owner_authorized=args.owner_authorized,
        )
        profile = load_profile(args.profile)
        result = run_training(
            source, profile, workspace=Path(".awf") / "model-runs", execute=args.execute,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, ImportError, RuntimeError, TypeError) as exc:
        print(f"AWF_ERROR [NEURAL_TRAINING_FAILED] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
