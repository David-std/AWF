"""LoRA smoke data admission is not a real academic gold/rights authorization."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from awf.ml.lora_smoke import LoRASmokePlan, prepare_smoke_run, train_synthetic_lora
from awf.ml.smoke_dataset import load_synthetic_smoke_dataset

from awf.cli.main import main


def _item(number: int, split: str) -> dict[str, str]:
    return {
        "example_id": f"synthetic-{number:02d}",
        "source_group_id": f"separate-document-{number}",
        "language": "es" if number % 2 else "en",
        "split": split,
        "prompt": f"Correct this fictional sample {number}: A sentence have issue.",
        "completion": f"Fictional sample {number}: A sentence has an issue.",
        "annotation_provenance": "DEVELOPER_SYNTHETIC",
    }


def _fixture() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "dataset_role": "LOCAL_SYNTHETIC_SMOKE_ONLY",
        "examples": [_item(1, "train"), _item(2, "train"), _item(3, "eval")],
    }


def _write(tmp_path: Path, dataset: dict[str, object]) -> tuple[Path, str]:
    path = tmp_path / "private-synthetic.json"
    raw = json.dumps(dataset, ensure_ascii=False, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    return path, hashlib.sha256(raw).hexdigest()


def test_preflight_reports_only_digest_counts_and_denies_promotion(tmp_path: Path):
    path, sha = _write(tmp_path, _fixture())
    data, result = prepare_smoke_run(path, sha, LoRASmokePlan())
    assert len(data.train) == 2 and len(data.evaluation) == 1
    assert result["loss_scope"] == "COMPLETION_ONLY"
    assert result["model_training_executed"] is False
    assert result["promotion"] == "DENIED"
    assert result["training_scope"] == "SYNTHETIC_SMOKE_ONLY"
    assert result["independent_gold_verified"] is False
    assert result["rights_independently_verified"] is False
    assert result["model_revision_requested"] == "7ae557604adf67be50417f59c2c2f167def9a775"
    report_text = json.dumps(result)
    assert "A sentence" not in report_text


def test_mutated_source_hash_fails_before_training(tmp_path: Path):
    path, sha = _write(tmp_path, _fixture())
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_synthetic_smoke_dataset(path, sha)


def test_declared_reviewer_gold_is_not_training_permission(tmp_path: Path):
    fixture = _fixture()
    fixture["dataset_role"] = "REVIEWED_GOLD"
    path, sha = _write(tmp_path, fixture)
    with pytest.raises(ValueError, match="role cannot authorize"):
        load_synthetic_smoke_dataset(path, sha)


@pytest.mark.parametrize("role", ["REVIEWED_HUMAN", "AI_LABELLED", "", None])
def test_refuses_non_synthetic_annotation(tmp_path: Path, role: object):
    fixture = _fixture()
    fixture["examples"][0]["annotation_provenance"] = role
    path, sha = _write(tmp_path, fixture)
    with pytest.raises(ValueError, match="synthetic smoke cannot claim"):
        load_synthetic_smoke_dataset(path, sha)


def test_group_leakage_rejected(tmp_path: Path):
    fixture = _fixture()
    fixture["examples"][2]["source_group_id"] = fixture["examples"][0]["source_group_id"]
    path, sha = _write(tmp_path, fixture)
    with pytest.raises(ValueError, match="source group leakage"):
        load_synthetic_smoke_dataset(path, sha)


def test_cross_split_exact_duplicate_rejected(tmp_path: Path):
    fixture = _fixture()
    fixture["examples"][2]["prompt"] = fixture["examples"][0]["prompt"]
    fixture["examples"][2]["completion"] = fixture["examples"][0]["completion"]
    path, sha = _write(tmp_path, fixture)
    with pytest.raises(ValueError, match="duplicate prompt/completion"):
        load_synthetic_smoke_dataset(path, sha)


def test_duplicate_identity_and_unknown_field_rejected(tmp_path: Path):
    fixture = _fixture()
    fixture["examples"][2]["example_id"] = fixture["examples"][0]["example_id"]
    path, sha = _write(tmp_path, fixture)
    with pytest.raises(ValueError, match="duplicate training example ID"):
        load_synthetic_smoke_dataset(path, sha)
    fixture = _fixture()
    fixture["examples"][0]["gold_verified"] = True
    path, sha = _write(tmp_path, fixture)
    with pytest.raises(ValueError, match="unexpected training example keys"):
        load_synthetic_smoke_dataset(path, sha)


@pytest.mark.parametrize(
    "overrides",
    [
        {"revision": "main"},
        {"model_id": "other/model"},
        {"max_steps": 0},
        {"max_steps": 50},
        {"max_length": 20},
        {"rank": 3},
        {"alpha": 1},
        {"learning_rate": 0.5},
        {"seed": -1},
    ],
)
def test_invalid_training_plan_fails_closed(overrides: dict[str, object]):
    settings = {
        "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        "revision": "7ae557604adf67be50417f59c2c2f167def9a775",
        "seed": 42,
        "max_steps": 2,
        "max_length": 256,
        "rank": 8,
        "alpha": 16,
        "learning_rate": 1e-4,
    }
    settings.update(overrides)
    with pytest.raises(ValueError):
        LoRASmokePlan(**settings)


def test_training_refuses_unapproved_output_directory_before_model_import(tmp_path):
    path, sha = _write(tmp_path, _fixture())
    with pytest.raises(ValueError, match="restricted to"):
        train_synthetic_lora(
            path, expected_sha256=sha, plan=LoRASmokePlan(), output_root=tmp_path / "public-weights"
        )


def test_cli_is_dry_run_by_default_without_ml_deps(tmp_path: Path, capsys):
    path, sha = _write(tmp_path, _fixture())
    assert main(["ml-smoke", str(path), "--expected-sha256", sha]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["model_training_executed"] is False
    assert "A sentence" not in output
    assert main(["ml-smoke", str(path), "--expected-sha256", "f" * 64]) == 2
    assert "AWF_ERROR" in capsys.readouterr().err


def test_cli_training_opt_in_rejected_when_dataset_invalid(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    source = _fixture()
    source["dataset_role"] = "REVIEWED_GOLD"
    path, sha = _write(tmp_path, source)
    assert (
        main(["ml-smoke", str(path), "--expected-sha256", sha, "--allow-synthetic-training"]) == 2
    )
    assert "AWF_ERROR" in capsys.readouterr().err
    assert not (tmp_path / ".awf").exists()


def test_private_symlink_dataset_is_rejected(tmp_path: Path):
    path, sha = _write(tmp_path, _fixture())
    link = tmp_path / "reference.json"
    try:
        link.symlink_to(path)
    except OSError:
        pytest.skip("symlink unavailable")
    with pytest.raises(ValueError, match="non-symlinked"):
        load_synthetic_smoke_dataset(link, sha)
