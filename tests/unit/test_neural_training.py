"""Data rights, split isolation, pinned base and default-no-train regression tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from awf.training.manifest import MODEL_REVISION, load_training_dataset
from awf.training.runner import load_profile, main, run_training
from awf.training.synthetic_smoke import make_private_smoke_dataset

PROFILE = Path(__file__).resolve().parents[2] / "config" / "training" / "local_lora_0_5b.json"


def _generated(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "private"
    digest = make_private_smoke_dataset(root)
    return root / "manifest.json", digest


def _rewrite(path: Path, object_value: dict) -> str:
    raw = (json.dumps(object_value, sort_keys=True, ensure_ascii=False) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_generated_dataset_and_preflight_without_ml_import(tmp_path: Path) -> None:
    manifest, digest = _generated(tmp_path)
    dataset = load_training_dataset(
        manifest,
        expected_sha256=digest,
        allow_synthetic_smoke=True,
        owner_authorized=False,
    )
    assert len(dataset.train) == 8
    assert len(dataset.validation) == 2
    assert dataset.role == "SYNTHETIC_SMOKE"
    assert dataset.independently_reviewed is False
    assert not (manifest.parent / "holdout.jsonl").exists()
    config = load_profile(PROFILE)
    assert config["model_revision"] == MODEL_REVISION
    result = run_training(
        dataset, config, workspace=tmp_path / "no_created_training", execute=False
    )
    assert result["status"] == "PREFLIGHT_ONLY"
    assert result["gradient_updates_observed"] == 0
    assert result["holdout_opened"] is False
    assert result["model_quality_certified"] is False
    assert not (tmp_path / "no_created_training").exists()


def test_training_defaults_to_opt_in(tmp_path: Path) -> None:
    manifest, digest = _generated(tmp_path)
    with pytest.raises(ValueError, match="explicit opt-in"):
        load_training_dataset(
            manifest, expected_sha256=digest, allow_synthetic_smoke=False, owner_authorized=True
        )
    assert (
        main(["--manifest", str(manifest), "--manifest-sha256", digest, "--profile", str(PROFILE)])
        == 2
    )


def test_manifest_external_hash_mismatch_rejected(tmp_path: Path) -> None:
    manifest, _ = _generated(tmp_path)
    with pytest.raises(ValueError, match="content hash mismatch"):
        load_training_dataset(
            manifest, expected_sha256="0" * 64, allow_synthetic_smoke=True, owner_authorized=False
        )


def test_split_tamper_is_rejected(tmp_path: Path) -> None:
    manifest, digest = _generated(tmp_path)
    (manifest.parent / "train.jsonl").write_bytes(b"modified")
    with pytest.raises(ValueError, match="content hash mismatch"):
        load_training_dataset(
            manifest,
            expected_sha256=digest,
            allow_synthetic_smoke=True,
            owner_authorized=False,
        )


def test_group_leakage_across_holdout_rejected(tmp_path: Path) -> None:
    manifest, _ = _generated(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["splits"]["holdout"]["group_ids"].append(payload["splits"]["train"]["group_ids"][0])
    digest = _rewrite(manifest, payload)
    with pytest.raises(ValueError, match="group leakage"):
        load_training_dataset(
            manifest, expected_sha256=digest, allow_synthetic_smoke=True, owner_authorized=False
        )


def test_owner_attestation_not_accepted_as_independent_review(tmp_path: Path) -> None:
    manifest, _ = _generated(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["dataset_role"] = "OWNER_AUTHORED"
    payload["source_rights"]["origin"] = "OWNER_AUTHORED"
    digest = _rewrite(manifest, payload)
    with pytest.raises(ValueError, match="owner-authored training requires"):
        load_training_dataset(
            manifest,
            expected_sha256=digest,
            allow_synthetic_smoke=True,
            owner_authorized=False,
        )
    dataset = load_training_dataset(
        manifest,
        expected_sha256=digest,
        allow_synthetic_smoke=False,
        owner_authorized=True,
    )
    assert dataset.independently_reviewed is False
    assert dataset.rights_claim["owner_attestation"] is True


def test_explicit_rights_assertion_must_not_be_missing(tmp_path: Path) -> None:
    manifest, _ = _generated(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["source_rights"]["training_permitted"] = False
    digest = _rewrite(manifest, payload)
    with pytest.raises(ValueError, match="training rights"):
        load_training_dataset(
            manifest,
            expected_sha256=digest,
            allow_synthetic_smoke=True,
            owner_authorized=False,
        )


def test_untrusted_relative_path_and_duplicate_id_rejected(tmp_path: Path) -> None:
    manifest, _ = _generated(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["splits"]["train"]["file"] = "../elsewhere.jsonl"
    digest = _rewrite(manifest, payload)
    with pytest.raises(ValueError, match="split path"):
        load_training_dataset(
            manifest,
            expected_sha256=digest,
            allow_synthetic_smoke=True,
            owner_authorized=False,
        )


def test_unverified_model_revision_and_learning_rate_rejected(tmp_path: Path) -> None:
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    target = tmp_path / "profile.json"
    profile["model_revision"] = "main"
    target.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(ValueError, match="bound to reviewed"):
        load_profile(target)
    profile["model_revision"] = MODEL_REVISION
    profile["learning_rate"] = -1
    target.write_text(json.dumps(profile), encoding="utf-8")
    with pytest.raises(ValueError, match="optimization parameters"):
        load_profile(target)


def test_cli_preflight_hides_training_text_and_creates_no_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, digest = _generated(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(
        [
            "--manifest",
            str(manifest),
            "--manifest-sha256",
            digest,
            "--profile",
            str(PROFILE),
            "--allow-synthetic-smoke",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["status"] == "PREFLIGHT_ONLY"
    assert "The sample contained" not in captured.out
    assert "La muestra" not in captured.out
    assert not (tmp_path / ".awf").exists()


def test_symlink_manifest_denied(tmp_path: Path) -> None:
    manifest, digest = _generated(tmp_path)
    symlink = tmp_path / "alias.json"
    try:
        symlink.symlink_to(manifest)
    except OSError:
        pytest.skip("symlinks disabled")
    with pytest.raises(ValueError, match="non-symlink"):
        load_training_dataset(
            symlink, expected_sha256=digest, allow_synthetic_smoke=True, owner_authorized=False
        )


def test_synthetic_dataset_generation_will_not_overwrite(tmp_path: Path) -> None:
    root = tmp_path / "data"
    make_private_smoke_dataset(root)
    with pytest.raises(ValueError, match="must not exist"):
        make_private_smoke_dataset(root)
