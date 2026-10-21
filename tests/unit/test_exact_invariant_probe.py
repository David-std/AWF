"""Adversarial tests: checks actual bytes, not provenance/semantic claims."""

from __future__ import annotations

import hashlib
import json

import pytest

from awf.cli.main import main
from awf.verification.exact_checks import (
    parse_contract,
    verify_exact_invariants,
)

BASE = "Fuente A dice que el 18 % mejoró; véase (López, 2024)."
LEFT = "que el "
VALUE = "18 %"
RIGHT = " mejoró;"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _contract(raw: str = BASE, *, value: str = VALUE) -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "baseline_sha256": _sha(raw.encode("utf-8")),
        "checks": [
            {
                "id": "frozen-quantity-1",
                "kind": "QUANTITY",
                "left_context": LEFT,
                "value": value,
                "right_context": RIGHT,
            }
        ],
    }


def _run(candidate: str, *, source: str = BASE) -> dict[str, object]:
    return verify_exact_invariants(
        source.encode("utf-8"), candidate.encode("utf-8"), parse_contract(_contract(source))
    )


def test_unrelated_edit_preserves_protected_literal_but_not_semantic_approval() -> None:
    result = _run(BASE + " Otra nota.")
    assert result["scope_status"] == "PASS"
    assert result["document_acceptance"] == "NEEDS_REVIEW"
    assert result["semantic_equivalence_verified"] is False
    assert result["training_authorized"] is False
    assert result["checks"][0]["reason_code"] == "EXACT_ANCHOR_UNCHANGED"
    assert VALUE not in json.dumps(result, ensure_ascii=False)


def test_quantity_change_blocks() -> None:
    result = _run(BASE.replace("18 %", "19 %"))
    assert result["scope_status"] == "FAIL"
    assert result["checks"][0]["reason_code"] == "PROTECTED_LITERAL_REMOVED"
    assert "NUMERIC_INVENTORY_DRIFT" in result["review_signals"]


def test_same_number_different_context_needs_review() -> None:
    result = _run(BASE.replace("que el ", "que aproximadamente el "))
    assert result["scope_status"] == "NEEDS_REVIEW"
    assert result["checks"][0]["reason_code"] == "CHANGED_CONTEXT_OR_DUPLICATE_LITERAL"


def test_insertion_of_duplicate_protected_number_needs_review() -> None:
    result = _run(BASE + " En otra frase: 18 %.")
    assert result["scope_status"] == "NEEDS_REVIEW"


def test_unlisted_numeric_change_does_not_silently_pass() -> None:
    candidate = BASE + " El plazo fue 2 días."
    assert _run(candidate)["scope_status"] == "NEEDS_REVIEW"


def test_causal_force_changes_trigger_review_not_fake_failure() -> None:
    source = BASE + " Esto causó un cambio."
    candidate = BASE + " Esto se asoció con un cambio."
    result = _run(candidate, source=source)
    assert result["scope_status"] == "NEEDS_REVIEW"
    assert "MODAL_CAUSAL_MARKER_DRIFT" in result["review_signals"]


def test_wrong_baseline_fails_closed() -> None:
    contract = parse_contract(_contract())
    with pytest.raises(ValueError, match="baseline bytes"):
        verify_exact_invariants(b"otra fuente", BASE.encode("utf-8"), contract)


def test_missing_or_ambiguous_anchor_fails_closed() -> None:
    raw = BASE + " " + BASE
    with pytest.raises(ValueError, match="ambiguous/missing baseline anchor"):
        _run(raw, source=raw)


def test_contract_schema_and_duplicate_rejected() -> None:
    c = _contract()
    c["extra"] = True
    with pytest.raises(ValueError, match="contract keys"):
        parse_contract(c)
    c.pop("extra")
    c["checks"] = [c["checks"][0], c["checks"][0]]
    with pytest.raises(ValueError, match="duplicate check"):
        parse_contract(c)


@pytest.mark.parametrize("kind", ["EXE", "SEMANTIC", "", "quantity"])
def test_unrecognized_kind_rejected(kind: str) -> None:
    c = _contract()
    c["checks"][0]["kind"] = kind
    with pytest.raises(ValueError, match="unsupported.*kind"):
        parse_contract(c)


def test_citation_literal_is_not_citation_grounding() -> None:
    text = "Según (López, 2024), el método puede servir."
    c = {
        "schema_version": "1.0.0",
        "baseline_sha256": _sha(text.encode()),
        "checks": [{
            "id": "citation",
            "kind": "CITATION",
            "left_context": "Según ",
            "value": "(López, 2024)",
            "right_context": ", el método",
        }],
    }
    result = verify_exact_invariants(text.encode(), text.encode(), parse_contract(c))
    assert result["scope_status"] == "PASS"
    assert result["source_truth_verified"] is False


def test_cli_private_files_and_external_contract_hash(tmp_path, capsys) -> None:
    a, b, policy = [tmp_path / name for name in ("original.md", "candidate.md", "contract.json")]
    a.write_text(BASE, encoding="utf-8")
    b.write_text(BASE.replace(VALUE, "19 %"), encoding="utf-8")
    policy.write_text(json.dumps(_contract(), ensure_ascii=False), encoding="utf-8")
    h = _sha(policy.read_bytes())
    command = [
        "verify-exact", str(a), str(b), "--contract", str(policy),
        "--expected-contract-sha256", h,
    ]
    assert main(command) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["scope_status"] == "FAIL"
    assert VALUE not in json.dumps(report, ensure_ascii=False)
    assert main(command[:-1] + ["a" * 64]) == 2
    assert "AWF_ERROR" in capsys.readouterr().err
    b.write_text(BASE, encoding="utf-8")
    assert main(command) == 0
    assert json.loads(capsys.readouterr().out)["scope_status"] == "PASS"


def test_cli_symlink_refused(tmp_path, capsys) -> None:
    original = tmp_path / "original.md"
    original.write_text(BASE, encoding="utf-8")
    link = tmp_path / "link.md"
    try:
        link.symlink_to(original)
    except OSError:
        pytest.skip("symlink creation unavailable on this runner")
    candidate = tmp_path / "candidate.md"
    candidate.write_text(BASE, encoding="utf-8")
    policy = tmp_path / "contract.json"
    policy.write_text(json.dumps(_contract()), encoding="utf-8")
    assert main([
        "verify-exact", str(link), str(candidate), "--contract", str(policy),
        "--expected-contract-sha256", _sha(policy.read_bytes()),
    ]) == 2
    assert "AWF_ERROR" in capsys.readouterr().err
