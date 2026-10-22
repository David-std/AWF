"""Private LoRA weight receipt verification must fail closed on corrupted files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from awf.training.manifest import BASE_MODEL, MODEL_REVISION
from awf.training.verify_adapter import main, verify_saved_adapter


def _json(data: object) -> bytes:
    return (json.dumps(data, sort_keys=True) + "\n").encode()


def _fixture(folder: Path, revision: str | None = MODEL_REVISION) -> tuple[Path, str]:
    adapter = folder / "adapter"
    adapter.mkdir(parents=True)
    payloads = {
        "adapter_model.safetensors": b"synthetic weights - NOT a real safetensors object",
        "adapter_config.json": _json(
            {
                "base_model_name_or_path": BASE_MODEL,
                "peft_type": "LORA",
                "target_modules": ["q_proj", "v_proj"],
                "revision": revision,
            }
        ),
    }
    for name, data in payloads.items():
        (adapter / name).write_bytes(data)
    report = {
        "schema_version": "1.0.0",
        "status": "SFT_ADAPTER_TRAINED",
        "model_id": BASE_MODEL,
        "model_revision": MODEL_REVISION,
        "gradient_updates_observed": 8,
        "optimizer_steps_planned": 8,
        "document_acceptance": "NEEDS_REVIEW",
        "holdout_opened": False,
        "holdout_evaluated": False,
        "model_quality_certified": False,
        "semantic_equivalence_verified": False,
        "training_output_private": True,
        "adapter_files_sha256": {
            key: hashlib.sha256(value).hexdigest() for key, value in payloads.items()
        },
    }
    raw = _json(report)
    (folder / "receipt.json").write_bytes(raw)
    return folder, hashlib.sha256(raw).hexdigest()


def test_verifier_checks_actual_bytes_without_ml_imports(tmp_path: Path):
    folder, digest = _fixture(tmp_path / "run")
    report = verify_saved_adapter(folder, expected_receipt_sha256=digest)
    assert report["status"] == "VERIFIED_SAVED_ADAPTER_BYTES"
    assert report["adapter_file_count"] == 2
    assert report["receipt_external_sha_pinned"] is True
    assert report["base_revision_saved_in_adapter_config"] is True
    assert report["parameter_reload_executed"] is False
    assert report["model_quality_certified"] is False
    assert "synthetic weights" not in json.dumps(report)


def test_legacy_null_revision_is_reported_not_invented(tmp_path: Path):
    folder, _ = _fixture(tmp_path / "run", revision=None)
    report = verify_saved_adapter(folder)
    assert report["base_revision_saved_in_adapter_config"] is False
    assert report["receipt_external_sha_pinned"] is False


def test_tampered_weights_fail(tmp_path: Path):
    folder, digest = _fixture(tmp_path / "run")
    (folder / "adapter" / "adapter_model.safetensors").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_saved_adapter(folder, expected_receipt_sha256=digest)


def test_tampered_receipt_fails(tmp_path: Path):
    folder, digest = _fixture(tmp_path / "run")
    receipt = folder / "receipt.json"
    receipt.write_bytes(receipt.read_bytes() + b" ")
    with pytest.raises(ValueError, match="receipt SHA mismatch"):
        verify_saved_adapter(folder, expected_receipt_sha256=digest)


def test_extra_unrecorded_file_denied(tmp_path: Path):
    folder, _ = _fixture(tmp_path / "run")
    (folder / "adapter" / "unrecorded.txt").write_text("extra")
    with pytest.raises(ValueError, match="inventory differs"):
        verify_saved_adapter(folder)


def test_conflicting_base_revision_denied(tmp_path: Path):
    folder, _ = _fixture(tmp_path / "run", revision="wrong-sha")
    with pytest.raises(ValueError, match="conflicting base revision"):
        verify_saved_adapter(folder)


def test_no_positive_gradient_claim_denied(tmp_path: Path):
    folder, _ = _fixture(tmp_path / "run")
    receipt = folder / "receipt.json"
    info = json.loads(receipt.read_text())
    info["gradient_updates_observed"] = 0
    receipt.write_bytes(_json(info))
    with pytest.raises(ValueError, match="positive optimizer"):
        verify_saved_adapter(folder)


def test_cli_only_emits_metadata(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    folder, digest = _fixture(tmp_path / "run")
    assert main([str(folder), "--expected-receipt-sha256", digest]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "VERIFIED_SAVED_ADAPTER_BYTES"
    assert "synthetic weights" not in captured.out
    assert main([str(folder), "--expected-receipt-sha256", "0" * 64]) == 2
    assert "AWF_ERROR" in capsys.readouterr().err


def test_symlink_file_refused(tmp_path: Path):
    folder, _ = _fixture(tmp_path / "run")
    target = folder / "adapter" / "adapter_model.safetensors"
    link = folder / "adapter" / "link"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(ValueError, match="unexpected directory or link"):
        verify_saved_adapter(folder)
