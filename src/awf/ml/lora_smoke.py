"""Local LoRA smoke training; research claims and rights must stay unverified.

The input file may only carry developer-created synthetic examples. This is
not a production trainer for copyrighted/manuscript/gold corpora.
Heavy ML dependencies are lazy so AWF core remains lightweight.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from awf.ml.smoke_dataset import SmokeDataset, load_synthetic_smoke_dataset

_BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
_BASE_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
_SHA = re.compile(r"[0-9a-f]{40}\Z")


@dataclass(frozen=True, slots=True)
class LoRASmokePlan:
    model_id: str = _BASE_MODEL
    revision: str = _BASE_REVISION
    seed: int = 42
    max_steps: int = 2
    max_length: int = 256
    rank: int = 8
    alpha: int = 16
    learning_rate: float = 0.0001

    def __post_init__(self) -> None:
        if self.model_id != _BASE_MODEL or _SHA.fullmatch(self.revision) is None:
            raise ValueError("only the pinned smoke model is currently supported")
        if type(self.seed) is not int or not 0 <= self.seed <= 4294967295:
            raise ValueError("invalid training seed")
        if type(self.max_steps) is not int or not 1 <= self.max_steps <= 20:
            raise ValueError("smoke max_steps must be 1..20")
        if type(self.max_length) is not int or not 64 <= self.max_length <= 512:
            raise ValueError("invalid smoke sequence budget")
        if type(self.rank) is not int or self.rank not in {4, 8, 16}:
            raise ValueError("invalid LoRA rank")
        if type(self.alpha) is not int or not self.rank <= self.alpha <= self.rank * 4:
            raise ValueError("invalid LoRA alpha")
        if not isinstance(self.learning_rate, (float, int)) or not (
            math.isfinite(self.learning_rate) and 0 < self.learning_rate <= 0.001
        ):
            raise ValueError("invalid LoRA learning rate")


def prepare_smoke_run(
    dataset_path: Path, expected_sha256: str, plan: LoRASmokePlan
) -> tuple[SmokeDataset, dict[str, Any]]:
    """Read locally and produce a no-text, no-trust-escalation preflight."""
    data = load_synthetic_smoke_dataset(dataset_path, expected_sha256)
    report = data.summary()
    report.update({
        "model_id": plan.model_id,
        "model_revision_requested": plan.revision,
        "seed": plan.seed,
        "max_steps": plan.max_steps,
        "max_length": plan.max_length,
        "lora_rank": plan.rank,
        "lora_alpha": plan.alpha,
        "learning_rate": plan.learning_rate,
        "loss_scope": "COMPLETION_ONLY",
        "model_training_executed": False,
        "model_weights_independently_verified": False,
        "dataset_rights_independently_verified": False,
        "scientific_validation": "NOT_PERFORMED",
        "promotion": "DENIED",
    })
    return data, report


def _artifact_hashes(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for file in sorted(root.rglob("*")):
        if file.is_symlink():
            raise ValueError("symlink found in generated adapter files")
        if file.is_file():
            if file.stat().st_size > 1024 * 1024 * 1024:
                raise ValueError("unexpected oversized adapter artifact")
            items.append({
                "name": file.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "bytes": file.stat().st_size,
            })
    return items


def train_synthetic_lora(
    dataset_path: Path,
    *,
    expected_sha256: str,
    plan: LoRASmokePlan,
    output_root: Path,
    allow_model_download: bool = False,
) -> dict[str, Any]:
    """Train bounded smoke LoRA from pinned synthetic data. No publish/auto-approve.

    When dependencies, weights or GPU are missing, raise a clear error *before*
    accepting or promoting any model. Caller must use an ignored private root.
    """
    dataset, preflight = prepare_smoke_run(dataset_path, expected_sha256, plan)
    if output_root.is_symlink() or not str(output_root.resolve()).replace("\\", "/").endswith(
        "/.awf/ml/smoke"
    ):
        raise ValueError("smoke outputs are restricted to .awf/ml/smoke")
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError("smoke output root is already populated; do not overwrite")
    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    peft = importlib.import_module("peft")
    trl = importlib.import_module("trl")
    datasets = importlib.import_module("datasets")
    if not torch.cuda.is_available():
        raise ValueError("CUDA GPU required for this measured smoke training")
    torch.manual_seed(plan.seed)
    model = transformers.AutoModelForCausalLM.from_pretrained(
        plan.model_id,
        revision=plan.revision,
        trust_remote_code=False,
        local_files_only=not allow_model_download,
        torch_dtype=torch.float16,
    )
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        plan.model_id,
        revision=plan.revision,
        trust_remote_code=False,
        local_files_only=not allow_model_download,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    output_root.mkdir(parents=True, exist_ok=False)
    train_data = datasets.Dataset.from_list([
        {"prompt": sample.prompt, "completion": sample.completion}
        for sample in dataset.train
    ])
    # Evaluation examples stay outside the optimizer and checkpoint loss.
    adapter_config = peft.LoraConfig(
        r=plan.rank,
        lora_alpha=plan.alpha,
        lora_dropout=0.0,
        target_modules=["q_proj", "v_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )
    args = trl.SFTConfig(
        output_dir=str(output_root / "trainer"),
        seed=plan.seed,
        max_steps=plan.max_steps,
        max_length=plan.max_length,
        learning_rate=plan.learning_rate,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=1,
        completion_only_loss=True,
        gradient_checkpointing=True,
        save_strategy="no",
        eval_strategy="no",
        report_to="none",
        logging_steps=1,
        push_to_hub=False,
        fp16=True,
        bf16=False,
        optim="adamw_torch",
        dataset_num_proc=1,
    )
    trainer = trl.SFTTrainer(
        model=model,
        args=args,
        train_dataset=train_data,
        processing_class=tokenizer,
        peft_config=adapter_config,
    )
    result = trainer.train()
    adapter_dir = output_root / "adapter"
    trainer.model.save_pretrained(adapter_dir, safe_serialization=True)
    tokenizer.save_pretrained(adapter_dir)
    artifacts = _artifact_hashes(adapter_dir)
    if not any(x["name"] == "adapter_model.safetensors" for x in artifacts):
        raise ValueError("no LoRA weights produced by trainer")
    output = dict(preflight)
    loss = getattr(result, "training_loss", None)
    output.update({
        "model_training_executed": True,
        "training_loss": float(loss) if loss is not None and math.isfinite(float(loss)) else None,
        "adapter_files": artifacts,
        "adapter_output_relative": ".awf/ml/smoke/adapter",
        "torch_version": str(torch.__version__),
        "transformers_version": str(transformers.__version__),
        "peft_version": str(peft.__version__),
        "trl_version": str(trl.__version__),
        "cuda_name": str(torch.cuda.get_device_name(0)),
        "training_examples": len(dataset.train),
        "holdout_examples_not_used_for_optimizer": len(dataset.evaluation),
        "model_weights_independently_verified": False,
        "academic_quality_verified": False,
        "training_scope": "SYNTHETIC_SMOKE_ONLY",
        "promotion": "DENIED",
    })
    return output
