"""Boundary tests for a metadata-only blind academic gold intake."""

import hashlib
import json
from copy import deepcopy

import pytest

from awf.evaluation.gold_intake import _read_pinned, audit_candidate_gold


def _case(id_, split, author, source, language="es"):
    return {
        "case_id": id_,
        "document_group": id_,
        "author_group": author,
        "source_group": source,
        "language": language,
        "genre": "academic",
        "split": split,
        "risk_families": ["negation", "quantity"],
        "blind_conditions": ["A", "B"],
        "original_sha256": hashlib.sha256(id_.encode()).hexdigest(),
        "source_evidence_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "rights_evidence_sha256": "c" * 64,
        "rights_basis": "SYNTHETIC_FIXTURE",
    }


def _manifest():
    return {
        "schema_version": "1.0.0",
        "dataset_role": "SYNTHETIC_DEVELOPMENT",
        "cases": [
            _case("case_a", "validation", "author_one", "source_one"),
            _case("case_b", "test_sealed", "author_two", "source_two", "en"),
        ],
    }


def _vote(case, condition, family, reviewer, label, code="SUPPORTED"):
    return {
        "case_id": case,
        "blind_condition": condition,
        "risk_family": family,
        "reviewer_id": reviewer,
        "label": label,
        "rationale_code": code,
        "evidence_sha256": "d" * 64,
    }


def _reviews():
    annotations = []
    for family in ("negation", "quantity"):
        for condition in ("A", "B"):
            for reviewer in ("reviewer_1", "reviewer_2"):
                annotations.append(
                    _vote(
                        "case_a",
                        condition,
                        family,
                        reviewer,
                        "DRIFT" if condition == "A" else "PRESERVED",
                    )
                )
    return {
        "schema_version": "1.0.0",
        "review_role": "BLIND_CANDIDATE_ANNOTATIONS",
        "annotations": annotations,
    }


def test_diagnostic_counts_never_promote_scientific_gold():
    report = audit_candidate_gold(_manifest(), review=_reviews())
    assert report["split_counts"] == {"test_sealed": 1, "validation": 1}
    assert report["paired_discordance"]["condition_a_only_drift"] == 1
    assert report["review_coverage"]["distinct_declared_reviewer_ids"] == 2
    assert report["independent_gold_verified"] is False
    assert report["source_rights_independently_verified"] is False
    assert report["model_quality_certified"] is False
    assert report["test_holdout_opened"] is False
    assert "reviewer_1" not in json.dumps(report)


def test_disagreement_is_unknown_and_not_majority_vote():
    rows = _reviews()
    rows["annotations"][0]["label"] = "PRESERVED"
    rows["annotations"][1]["label"] = "PRESERVED"
    rows["annotations"][4]["label"] = "PRESERVED"
    result = audit_candidate_gold(_manifest(), review=rows)
    assert result["review_coverage"]["discordant_double_reviews"] == 1
    assert result["paired_discordance"]["unknown_pair"] == 1


def test_confirmed_drift_takes_precedence_over_other_unknown():
    rows = _reviews()
    rows["annotations"][0]["label"] = "PRESERVED"
    report = audit_candidate_gold(_manifest(), review=rows)
    assert report["review_coverage"]["discordant_double_reviews"] == 1
    assert report["paired_discordance"]["condition_a_only_drift"] == 1


@pytest.mark.parametrize("field", ["original_sha256", "source_evidence_sha256"])
def test_content_hash_leakage_rejected(field):
    manifest = _manifest()
    manifest["cases"][1][field] = manifest["cases"][0][field]
    with pytest.raises(ValueError, match="leakage"):
        audit_candidate_gold(manifest)


def test_missing_review_is_unknown():
    result = audit_candidate_gold(_manifest())
    assert result["review_coverage"]["missing_double_reviews"] == 4
    assert result["paired_discordance"]["unknown_pair"] == 1


@pytest.mark.parametrize("dimension", ["document_group", "author_group", "source_group"])
def test_group_leakage_rejected(dimension):
    manifest = _manifest()
    manifest["cases"][1][dimension] = manifest["cases"][0][dimension]
    with pytest.raises(ValueError, match="leakage"):
        audit_candidate_gold(manifest)


def test_sealed_case_cannot_be_reviewed():
    manifest = _manifest()
    reviews = _reviews()
    reviews["annotations"].append(_vote("case_b", "A", "negation", "reviewer_3", "DRIFT"))
    with pytest.raises(ValueError, match="sealed"):
        audit_candidate_gold(manifest, review=reviews)


def test_duplicate_reviewer_cannot_vote_twice():
    reviews = _reviews()
    reviews["annotations"].append(deepcopy(reviews["annotations"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        audit_candidate_gold(_manifest(), review=reviews)


def test_rights_role_and_self_certified_gold_rejected():
    manifest = _manifest()
    manifest["dataset_role"] = "INDEPENDENT_GOLD"
    with pytest.raises(ValueError, match="reviewed gold"):
        audit_candidate_gold(manifest)
    manifest = _manifest()
    manifest["cases"][0]["rights_basis"] = "THIRD_PARTY_PERMISSION_CLAIM"
    with pytest.raises(ValueError, match="synthetic rights"):
        audit_candidate_gold(manifest)


def test_duplicate_json_keys_and_modified_bytes_rejected(tmp_path):
    path = tmp_path / "manifest.json"
    raw = b'{"a":1,"a":2}'
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="duplicate JSON"):
        _read_pinned(path, digest, max_size=1000)
    with pytest.raises(ValueError, match="mismatch"):
        _read_pinned(path, "0" * 64, max_size=1000)


def test_no_prose_or_annotator_ids_exported():
    report = audit_candidate_gold(_manifest(), review=_reviews())
    output = json.dumps(report)
    assert "case_a" not in output
    assert "author_one" not in output
    assert "source_one" not in output
    assert "reviewer_1" not in output
    assert "Apenas" not in output
