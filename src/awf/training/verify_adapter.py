"""Verify a saved AWF LoRA artifact without importing ML libraries.

Checks stored bytes and the declared model identity, not academic quality.
The saved receipt is self-reported metadata unless pinned externally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from awf.training.manifest import BASE_MODEL, MODEL_REVISION

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_FILE = re.compile(r"[A-Za-z0-9_.-]+\Z")
_MAX_FILES = 32
_MAX_FILE_BYTES = 512 * 1024 * 1024


def _read_json(path: Path, limit: int) -> tuple[bytes, dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("artifact metadata must be a regular non-symlink file")
    with path.open("rb") as handle:
        raw = handle.read(limit + 1)
    if not 0 < len(raw) <= limit:
        raise ValueError("artifact metadata exceeds size bounds")

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON metadata field")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 artifact metadata") from exc
    if not isinstance(value, dict):
        raise ValueError("artifact metadata must be an object")
    return raw, value


def _hash_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("adapter file is not a regular non-symlink file")
    if not 0 < path.stat().st_size <= _MAX_FILE_BYTES:
        raise ValueError("adapter file exceeds size bounds")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_saved_adapter(
    run_directory: Path,
    *,
    expected_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify a receipt-bound adapter snapshot without opening any training data.

    Hash pinning proves byte consistency with this receipt, not that a model
    trained honestly or that data use and scholarly claims are authorized.
    """
    if run_directory.is_symlink() or not run_directory.is_dir():
        raise ValueError("run directory must be a regular non-symlink directory")
    receipt_bytes, receipt = _read_json(run_directory / "receipt.json", 128 * 1024)
    receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()
    if expected_receipt_sha256 is not None:
        if _SHA.fullmatch(expected_receipt_sha256) is None:
            raise ValueError("invalid externally supplied receipt SHA")
        if receipt_hash != expected_receipt_sha256:
            raise ValueError("receipt SHA mismatch")
    if (
        receipt.get("schema_version") != "1.0.0"
        or receipt.get("status") != "SFT_ADAPTER_TRAINED"
        or receipt.get("model_id") != BASE_MODEL
        or receipt.get("model_revision") != MODEL_REVISION
        or receipt.get("document_acceptance") != "NEEDS_REVIEW"
        or receipt.get("holdout_opened") is not False
        or receipt.get("holdout_evaluated") is not False
        or receipt.get("model_quality_certified") is not False
        or receipt.get("semantic_equivalence_verified") is not False
        or receipt.get("training_output_private") is not True
    ):
        raise ValueError("receipt is incompatible with the experimental AWF contract")
    steps = receipt.get("gradient_updates_observed")
    planned = receipt.get("optimizer_steps_planned")
    if type(steps) is not int or type(planned) is not int or not 1 <= steps <= planned <= 2500:
        raise ValueError("receipt does not report bounded positive optimizer steps")
    expected = receipt.get("adapter_files_sha256")
    if not isinstance(expected, dict) or not 2 <= len(expected) <= _MAX_FILES:
        raise ValueError("invalid receipt adapter-file inventory")
    adapter_dir = run_directory / "adapter"
    if adapter_dir.is_symlink() or not adapter_dir.is_dir():
        raise ValueError("adapter directory is missing or a symlink")
    found: set[str] = set()
    for path in adapter_dir.iterdir():
        if path.is_symlink() or not path.is_file():
            raise ValueError("unexpected directory or link in saved adapter")
        found.add(path.name)
    if found != set(expected):
        raise ValueError("adapter inventory differs from receipt")
    for name, expected_digest in expected.items():
        if (
            not isinstance(name, str)
            or _FILE.fullmatch(name) is None
            or not isinstance(expected_digest, str)
            or _SHA.fullmatch(expected_digest) is None
        ):
            raise ValueError("invalid adapter inventory entry")
        if _hash_file(adapter_dir / name) != expected_digest:
            raise ValueError("saved adapter content hash mismatch")
    required = {"adapter_config.json", "adapter_model.safetensors"}
    if not required <= found:
        raise ValueError("required PEFT adapter files are missing")
    _, config = _read_json(adapter_dir / "adapter_config.json", 128 * 1024)
    if (
        config.get("base_model_name_or_path") != BASE_MODEL
        or config.get("peft_type") != "LORA"
        or set(config.get("target_modules", [])) != {"q_proj", "v_proj"}
    ):
        raise ValueError("saved PEFT configuration differs from planned LoRA")
    pinned = config.get("revision") == MODEL_REVISION
    if config.get("revision") not in {None, MODEL_REVISION}:
        raise ValueError("saved adapter contains a conflicting base revision")
    return {
        "status": "VERIFIED_SAVED_ADAPTER_BYTES",
        "receipt_sha256": receipt_hash,
        "receipt_external_sha_pinned": expected_receipt_sha256 is not None,
        "adapter_file_count": len(found),
        "adapter_weights_sha256": expected["adapter_model.safetensors"],
        "base_model": BASE_MODEL,
        "base_revision": MODEL_REVISION,
        "base_revision_saved_in_adapter_config": pinned,
        "gradient_updates_reported": steps,
        "parameter_reload_executed": False,
        "model_quality_certified": False,
        "independent_gold_verified": False,
        "source_rights_independently_verified": False,
        "training_content_exported": False,
        "document_acceptance": "NEEDS_REVIEW",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="awf-verify-adapter")
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--expected-receipt-sha256")
    args = parser.parse_args(argv)
    try:
        result = verify_saved_adapter(
            args.run_directory,
            expected_receipt_sha256=args.expected_receipt_sha256,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"AWF_ERROR [ADAPTER_VERIFICATION_FAILED] {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
