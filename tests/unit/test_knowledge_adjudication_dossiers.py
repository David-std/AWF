"""Adversarial checks for the non-authoritative private dossier inspector."""

from __future__ import annotations

import copy

import pytest

from awf.knowledge.adjudication_dossiers import audit_private_dossiers
from awf.knowledge.compiler import compile_knowledge
from awf.knowledge.review_plan import make_review_packets


def _workbench():
    rows = [
        {
            "id": "DSR-001",
            "domain": "knowledge_integrity",
            "priority": "MUST",
            "requirement": "Keep every original source identity bound to its digest.",
            "source_ids": ["deep-one"],
            "status": "IMPLEMENTED",
            "second_pass_class": "ROBUST_MECHANICAL_CONTRACT",
        },
        {
            "id": "DSR-002",
            "domain": "detector",
            "priority": "DEFERRED_LAB",
            "requirement": "Measure empirical outcomes using frozen detectors.",
            "source_ids": ["deep-two"],
            "status": "RESEARCH",
            "second_pass_class": "DEFERRED_EMPIRICAL",
        },
    ]
    registry = compile_knowledge(
        rows, source_id="aws", archive_sha256="a" * 64, suite_version="3.19.1"
    )
    manifest, packets = make_review_packets(rows, registry=registry, batch_size=1)
    return manifest, packets


def _checked(observed_manifest, observed_packets, manifest, packets):
    return audit_private_dossiers(
        canonical_manifest=manifest,
        canonical_packets=packets,
        observed_manifest=observed_manifest,
        observed_packets=observed_packets,
    )


def _rule(packets, identifier):
    for packet in packets.values():
        for rule in packet["rules"]:
            if rule["id"] == identifier:
                return rule
    raise AssertionError(identifier)


def _propose(packet, *, identifier, disposition):
    form = _rule(packet, identifier)["review_template"]
    form.update(
        reviewer="reviewer-A",
        reason="Comparative implementation reviewed with explicit counterexample evidence.",
        evidence_ids=["event:" + "a" * 64],
        proposed_tests=["test_rejects_wrong_digest"],
        desired_disposition=disposition,
        current_model_or_version_evidence="source snapshot 3.19.1 and AWF test run",
        source_rights_status="NOT_APPLICABLE",
    )


def test_unedited_workbench_remains_fully_open() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    report = _checked(manifest, actual, manifest, packets)
    assert report["status_counts"] == {"OPEN": 2}
    assert report["all_rules_adjudicated"] is False
    assert report["review_attestation_authorized"] is False


def test_documented_proposal_never_becomes_an_attestation() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _propose(actual, identifier="DSR-001", disposition="KEEP_AS_CODE")
    report = _checked(manifest, actual, manifest, packets)
    assert report["status_counts"] == {"OPEN": 1, "PROPOSAL_DOCUMENTED": 1}
    assert report["training_authorized"] is False
    assert report["independent_evidence_verified"] is False
    assert "source identity bound" not in str(report)


def test_forged_legacy_implementation_or_requirement_rejected() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _rule(actual, "DSR-001")["requirement"] = "A forged substitute"
    with pytest.raises(ValueError, match="immutable source-bound"):
        _checked(manifest, actual, manifest, packets)


def test_forged_review_status_rejected() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _rule(actual, "DSR-001")["review_status"] = "REVIEW_ATTESTED"
    with pytest.raises(ValueError, match="immutable source-bound"):
        _checked(manifest, actual, manifest, packets)


def test_swapped_or_missing_batch_rejected() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    keys = sorted(actual)
    actual[keys[0]], actual[keys[1]] = actual[keys[1]], actual[keys[0]]
    with pytest.raises(ValueError, match="metadata changed"):
        _checked(manifest, actual, manifest, packets)
    with pytest.raises(ValueError, match="inventory changed"):
        _checked(manifest, {keys[0]: packets[keys[0]]}, manifest, packets)


def test_modified_manifest_is_not_a_source_of_authority() -> None:
    manifest, packets = _workbench()
    altered = copy.deepcopy(manifest)
    altered["reviewed_count"] = 2
    with pytest.raises(ValueError, match="manifest differs"):
        _checked(altered, packets, manifest, packets)


def test_laboratory_rule_cannot_become_executable_or_training() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _propose(actual, identifier="DSR-002", disposition="TRAIN")
    with pytest.raises(ValueError, match="laboratory"):
        _checked(manifest, actual, manifest, packets)


def test_unverified_training_rights_block_structural_completeness() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _propose(actual, identifier="DSR-001", disposition="TRAIN")
    _rule(actual, "DSR-001")["review_template"]["source_rights_status"] = "PERMISSION_VERIFIED"
    report = _checked(manifest, actual, manifest, packets)
    row = next(r for r in report["rules"] if r["id"] == "DSR-001")
    assert row["status"] == "PROPOSAL_INCOMPLETE"
    assert "training_license_independently_verified" in row["missing"]


def test_pending_conflicts_and_missing_evidence_are_visible() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _propose(actual, identifier="DSR-001", disposition="KEEP_AS_CONTEXT")
    form = _rule(actual, "DSR-001")["review_template"]
    form["conflicting_rule_ids"] = ["DSR-002"]
    form["evidence_ids"] = []
    report = _checked(manifest, actual, manifest, packets)
    item = next(r for r in report["rules"] if r["id"] == "DSR-001")
    assert item["status"] == "PROPOSAL_INCOMPLETE"
    assert {"conflict_resolution", "evidence_ids"} <= set(item["missing"])


@pytest.mark.parametrize("bad", [["DSR-001"], ["missing"]])
def test_self_or_unknown_conflict_rejected(bad) -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _propose(actual, identifier="DSR-001", disposition="KEEP_AS_CODE")
    _rule(actual, "DSR-001")["review_template"]["conflicting_rule_ids"] = bad
    with pytest.raises(ValueError, match="conflict ID"):
        _checked(manifest, actual, manifest, packets)


def test_duplicate_evidence_and_unrecognized_fields_rejected() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _propose(actual, identifier="DSR-001", disposition="KEEP_AS_CODE")
    form = _rule(actual, "DSR-001")["review_template"]
    form["evidence_ids"] = ["same", "same"]
    with pytest.raises(ValueError, match="duplicate"):
        _checked(manifest, actual, manifest, packets)
    form["evidence_ids"] = ["same"]
    form["approved"] = True
    with pytest.raises(ValueError, match="unknown or missing"):
        _checked(manifest, actual, manifest, packets)


def test_partial_annotations_do_not_count_as_closed() -> None:
    manifest, packets = _workbench()
    actual = copy.deepcopy(packets)
    _rule(actual, "DSR-001")["review_template"]["reason"] = "still thinking"
    report = _checked(manifest, actual, manifest, packets)
    assert report["status_counts"] == {"OPEN": 1, "PARTIAL": 1}
