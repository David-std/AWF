"""No fake gold, no text in receipts, negative cases for paired diagnostics."""

import hashlib
import json

import pytest

from awf.evaluation.paired_lora import make_paired_diagnostic


def _rows():
    return (
        {
            "id": "fictional_1",
            "group_id": "document_1",
            "language": "es",
            "prompt": "Transforma la oración ficticia A.",
        },
        {
            "id": "fictional_2",
            "group_id": "document_2",
            "language": "en",
            "prompt": "Transform fictional sentence B.",
        },
    )


def test_pairing_preserves_provenance_and_does_not_claim_quality():
    output = {
        ("base", "Transforma la oración ficticia A."): "El total es 12.",
        ("adapter", "Transforma la oración ficticia A."): "El total es 15.",
        ("base", "Transform fictional sentence B."): "Only group B.",
        ("adapter", "Transform fictional sentence B."): "Only group B.",
    }
    report, private = make_paired_diagnostic(
        _rows(),
        produce=lambda variant, prompt: output[variant, prompt],
        dataset_sha256="a" * 64,
        receipt_sha256="b" * 64,
        adapter_sha256="c" * 64,
    )
    assert report["case_count"] == 2
    assert report["changed_output_count"] == 1
    assert report["independent_gold_verified"] is False
    assert report["semantic_equivalence_verified"] is False
    assert report["document_acceptance"] == "NEEDS_REVIEW"
    assert report["cases"][0]["semantic_status"] == "NOT_ASSESSED"
    assert report["cases"][0]["base_output_sha256"] == hashlib.sha256(
        b"El total es 12."
    ).hexdigest()
    dumped = json.dumps(report, ensure_ascii=False)
    assert "El total" not in dumped and "Transforma" not in dumped
    assert "El total es 12." in json.dumps(private, ensure_ascii=False)


def test_duplicate_identifiers_fail_closed():
    a, _ = _rows()
    with pytest.raises(ValueError, match="duplicate"):
        make_paired_diagnostic(
            (a, a),
            produce=lambda variant, prompt: "value",
            dataset_sha256="a" * 64,
            receipt_sha256="b" * 64,
            adapter_sha256="c" * 64,
        )


def test_nontext_model_output_is_not_silently_accepted():
    with pytest.raises(ValueError, match="not text"):
        make_paired_diagnostic(
            _rows(),
            produce=lambda variant, prompt: None,
            dataset_sha256="a" * 64,
            receipt_sha256="b" * 64,
            adapter_sha256="c" * 64,
        )
