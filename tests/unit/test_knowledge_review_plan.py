"""Review preparation must preserve every ID and never confer rule authority."""

from __future__ import annotations

import pytest

from awf.domain.knowledge import Disposition
from awf.knowledge.compiler import compile_knowledge
from awf.knowledge.review_plan import make_review_packets


def _source():
    rows = [
        {
            "id": "DSR-001",
            "domain": "stateful_runtime",
            "priority": "MUST",
            "requirement": "Preserve original hashes during candidate review.",
            "source_ids": ["deep-01"],
            "implementation_paths": ["runtime/artifact_ledger.py"],
            "verification": ["stateful_selftest"],
            "status": "IMPLEMENTED",
            "second_pass_class": "ROBUST_MECHANICAL_CONTRACT",
            "verification_strength": "MECHANICAL_OR_DETERMINISTIC",
            "acceptance_metric": "negative tests reject stale artifacts",
            "residual_uncertainty": "mechanical status does not prove academic accuracy",
        },
        {
            "id": "R319-CAP-01",
            "domain": "generation_control_3_19",
            "priority": "MUST",
            "requirement": "Require explicit model capability evidence.",
            "source_ids": ["deep-02"],
            "implementation_paths": ["runtime/capability.py"],
            "verification": ["capability_selftest"],
            "status": "IMPLEMENTED",
            "second_pass_class": "STRUCTURAL_ENFORCED_BOUNDED",
        },
        {
            "id": "DSR-DEF-01",
            "domain": "detector_semantics",
            "priority": "DEFERRED_LAB",
            "requirement": "Test Spanish detector behavior only with controlled data.",
            "source_ids": ["deep-03"],
            "second_pass_class": "DEFERRED_EMPIRICAL",
        },
    ]
    registry = compile_knowledge(
        rows,
        source_id="aws-3.19.1",
        archive_sha256="a" * 64,
        suite_version="3.19.1",
    )
    return rows, registry


def test_complete_manifest_and_private_packets() -> None:
    rows, registry = _source()
    manifest, packets = make_review_packets(rows, registry=registry, batch_size=1)
    assert manifest["requirements_count"] == 3
    assert manifest["open_count"] == 3
    assert manifest["reviewed_count"] == 0
    assert manifest["source_text_in_manifest"] is False
    assert manifest["legacy_verification_class_counts"] == {
        "DEFERRED_EMPIRICAL": 1,
        "ROBUST_MECHANICAL_CONTRACT": 1,
        "STRUCTURAL_ENFORCED_BOUNDED": 1,
    }
    assert len(packets) == 3
    assert sum(len(packet["rules"]) for packet in packets.values()) == 3
    assert "Preserve original hashes" not in str(manifest)
    rule = next(r for p in packets.values() for r in p["rules"] if r["id"] == "DSR-001")
    assert rule["legacy_status_claim"] == "IMPLEMENTED"
    assert rule["review_status"] == "OPEN"
    assert rule["awf_disposition"] == Disposition.UNRESOLVED.value
    assert rule["legacy_implementation_paths"] == ["runtime/artifact_ledger.py"]
    assert rule["review_template"]["source_rights_status"] == "NOT_EVALUATED"
    assert rule["review_template"]["desired_disposition"] is None


def test_repeated_plan_identical_and_no_omitted_rules() -> None:
    rows, registry = _source()
    first = make_review_packets(rows, registry=registry)
    assert first == make_review_packets(rows, registry=registry)
    with pytest.raises(ValueError, match="missing 1"):
        make_review_packets(rows[:-1], registry=registry)


def test_changed_text_blocked() -> None:
    rows, registry = _source()
    rows[0]["requirement"] = "False new claim"
    with pytest.raises(ValueError, match="hash changed"):
        make_review_packets(rows, registry=registry)


def test_unsupported_verification_strength_fails() -> None:
    rows, registry = _source()
    rows[0]["second_pass_class"] = "EVIDENCE_FREE"
    with pytest.raises(ValueError, match="unknown verification boundary"):
        make_review_packets(rows, registry=registry)


@pytest.mark.parametrize("size", [0, 51])
def test_invalid_batch_size_rejected(size: int) -> None:
    rows, registry = _source()
    with pytest.raises(ValueError, match="batch_size"):
        make_review_packets(rows, registry=registry, batch_size=size)
