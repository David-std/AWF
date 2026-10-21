"""Synthetic-only diagnostic matrix; independently reviewed gold is NOT supplied."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from awf.cli.main import main
from awf.evaluation.synthetic_scope import run_synthetic_scope_benchmark

EN = "The fictional study reported 18 % under one narrow condition."
ES = "El estudio ficticio reportó 18 % bajo una condición limitada."


def _case(
    identity: str,
    original: str,
    candidate: str,
    label: str,
    *,
    language: str,
    family: str,
    document_id: str | None = None,
) -> dict[str, object]:
    start = original.index("18 %")
    left = original[max(0, start - 12) : start]
    right = original[start + 4 : start + 16]
    return {
        "case_id": identity,
        "document_id": document_id or identity,
        "language": language,
        "risk_family": family,
        "gold_label": label,
        "gold_provenance": "DEVELOPER_SYNTHETIC",
        "baseline": original,
        "candidate": candidate,
        "contract": {
            "schema_version": "1.0.0",
            "baseline_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            "checks": [
                {
                    "id": "protected-metric",
                    "kind": "QUANTITY",
                    "value": "18 %",
                    "left_context": left,
                    "right_context": right,
                }
            ],
        },
    }


def _fixture() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "dataset_role": "SYNTHETIC_DEVELOPMENT",
        "cases": [
            _case("en_ok", EN, EN, "PRESERVED", language="en", family="quantity"),
            _case(
                "en_metric",
                EN,
                EN.replace("18 %", "19 %"),
                "DRIFT",
                language="en",
                family="quantity",
            ),
            _case(
                "en_distant",
                EN,
                EN + " This conclusion is false.",
                "DRIFT",
                language="en",
                family="negation",
            ),
            _case(
                "en_context",
                EN,
                EN.replace("reported ", "reported approximately "),
                "PRESERVED",
                language="en",
                family="modality",
            ),
            _case("es_ok", ES, ES, "PRESERVED", language="es", family="quantity"),
            _case(
                "es_metric",
                ES,
                ES.replace("18 %", "19 %"),
                "DRIFT",
                language="es",
                family="quantity",
            ),
            _case(
                "es_distant",
                ES,
                ES + " Esta conclusión es falsa.",
                "DRIFT",
                language="es",
                family="negation",
            ),
            _case(
                "es_added",
                ES,
                ES + " Otro valor fue 42 %.",
                "DRIFT",
                language="es",
                family="quantity",
            ),
        ],
    }


def _write(tmp_path: Path, fixture: dict[str, object]) -> tuple[Path, str]:
    target = tmp_path / "synthetic.json"
    raw = json.dumps(fixture, ensure_ascii=False, sort_keys=True).encode("utf-8")
    target.write_bytes(raw)
    return target, hashlib.sha256(raw).hexdigest()


def test_actual_checker_scores_synthetic_es_en_and_preserves_abstentions(tmp_path):
    path, digest = _write(tmp_path, _fixture())
    report = run_synthetic_scope_benchmark(path, expected_sha256=digest)
    counts = report["evaluation"]
    assert counts["cases"] == 8
    assert counts["drift_cases"] == 5
    assert counts["preserved_cases"] == 3
    assert counts["fail_on_drift"] == 2
    assert counts["false_clear_on_drift"] == 2
    assert counts["review_on_drift"] == 1
    assert counts["pass_on_preserved"] == 2
    assert counts["review_on_preserved"] == 1
    assert counts["fail_on_preserved"] == 0
    assert counts["strict_drift_detection_rate"] == 0.4
    assert counts["false_clear_rate_on_drift"] == 0.4
    assert counts["review_escalation_rate"] == 0.25
    assert set(report["by_language"]) == {"es", "en"}
    assert report["independent_gold_verified"] is False
    assert report["semantic_equivalence_verified"] is False
    assert report["document_acceptance"] == "NEEDS_REVIEW"
    assert report["training_authorized"] is False
    assert EN not in json.dumps(report, ensure_ascii=False)
    assert ES not in json.dumps(report, ensure_ascii=False)


def test_hash_tamper_fails_closed(tmp_path):
    path, digest = _write(tmp_path, _fixture())
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)


@pytest.mark.parametrize("role", ["HOLDOUT", "TRAIN", "REVIEWED_GOLD", ""])
def test_disallows_any_claim_of_real_gold_without_proof(tmp_path, role):
    corpus = _fixture()
    corpus["dataset_role"] = role
    path, digest = _write(tmp_path, corpus)
    with pytest.raises(ValueError, match="only explicitly synthetic"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)


def test_rejects_fake_independent_annotation(tmp_path):
    corpus = _fixture()
    corpus["cases"][0]["gold_provenance"] = "INDEPENDENT_REVIEWED"
    path, digest = _write(tmp_path, corpus)
    with pytest.raises(ValueError, match="marked synthetic"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)


def test_rejects_duplicate_case_identity_and_document_cross_language(tmp_path):
    corpus = _fixture()
    corpus["cases"][1]["case_id"] = "en_ok"
    path, digest = _write(tmp_path, corpus)
    with pytest.raises(ValueError, match="duplicate"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)
    corpus = _fixture()
    corpus["cases"][4]["document_id"] = "en_ok"
    path, digest = _write(tmp_path, corpus)
    with pytest.raises(ValueError, match="crosses"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)


def test_rejects_unknown_status_fields_and_false_drift(tmp_path):
    corpus = _fixture()
    corpus["cases"][0]["scope_status"] = "FAIL"
    path, digest = _write(tmp_path, corpus)
    with pytest.raises(ValueError, match="unexpected synthetic case fields"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)
    corpus = _fixture()
    corpus["cases"][0]["gold_label"] = "DRIFT"
    path, digest = _write(tmp_path, corpus)
    with pytest.raises(ValueError, match="unchanged text"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)


def test_contract_cannot_be_changed_to_fake_new_source(tmp_path):
    corpus = _fixture()
    corpus["cases"][1]["contract"]["baseline_sha256"] = "0" * 64
    path, digest = _write(tmp_path, corpus)
    with pytest.raises(ValueError, match="baseline bytes"):
        run_synthetic_scope_benchmark(path, expected_sha256=digest)


def test_cli_synthetic_success_failure_and_private_text_not_printed(tmp_path, capsys):
    path, digest = _write(tmp_path, _fixture())
    assert main(["evaluate-synthetic", str(path), "--expected-sha256", digest]) == 0
    result = capsys.readouterr()
    payload = json.loads(result.out)
    assert payload["evaluation"]["cases"] == 8
    assert EN not in result.out and ES not in result.out
    assert main(["evaluate-synthetic", str(path), "--expected-sha256", "0" * 64]) == 2
    assert "AWF_ERROR" in capsys.readouterr().err


def test_symlink_dataset_refused(tmp_path):
    path, digest = _write(tmp_path, _fixture())
    link = tmp_path / "linked.json"
    try:
        link.symlink_to(path)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="non-symlinked"):
        run_synthetic_scope_benchmark(link, expected_sha256=digest)
