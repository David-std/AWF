"""Unit tests: conservative, non-self-certifying classification."""

from __future__ import annotations

import hashlib

import pytest

from awf.domain.knowledge import Applicability, Disposition
from awf.knowledge.applicability import applicability_for
from awf.knowledge.compiler import compile_knowledge
from awf.knowledge.dependency_graph import KnowledgeDependencyError, dependency_closure


def _rows() -> list[dict[str, object]]:
    return [
        {"id": "DSR-001", "domain": "semantics", "priority": "MUST",
         "requirement": "Preserve original causal force.", "source_ids": ["deep-01"]},
        {"id": "DSR-002", "domain": "semantics", "priority": "MUST",
         "requirement": "  Preserve original causal  force. ", "source_ids": ["deep-02"]},
        {"id": "DSR-003", "domain": "detector", "priority": "DEFERRED_LAB",
         "requirement": "Test detector transfer only in a future lab.", "source_ids": ["deep-03"]},
    ]


def _compile(*, reviews: dict[str, dict[str, object]] | None = None):
    return compile_knowledge(
        _rows(), source_id="test", archive_sha256="a" * 64,
        suite_version="3.19.1", review_decisions=reviews,
    )


def test_must_rules_are_not_automatically_executable() -> None:
    registry = _compile()
    assert len(registry.records) == 3
    assert registry.counts()[Disposition.UNRESOLVED] == 2
    assert registry.counts()[Disposition.EVAL_ONLY] == 1
    assert registry.to_dict()["unreviewed_count"] == 3
    assert registry.possible_duplicate_groups == (("DSR-001", "DSR-002"),)
    assert "Preserve original causal force" not in str(registry.to_dict())


def test_known_source_text_hash_is_stable() -> None:
    record = _compile().records[0]
    digest = hashlib.sha256(b"preserve original causal force.").hexdigest()
    assert record.source_text_sha256 == digest


def test_review_requires_source_and_reason() -> None:
    with pytest.raises(ValueError, match="substantive"):
        _compile(reviews={"DSR-001": {
            "disposition": "KEEP_AS_CODE", "reviewer": "Researcher", "reason": "yes"
        }})


def test_explicit_review_does_not_self_certify_applicability() -> None:
    approved = _compile(reviews={"DSR-001": {
        "disposition": "KEEP_AS_CODE", "reviewer": "HumanResearcher",
        "reason": "This is a mechanical hash dependency with explicit tests.",
    }})
    item = approved.records[0]
    assert item.review_status == "REVIEW_ATTESTED"
    assert applicability_for(item, context_verified=False) == Applicability.UNKNOWN
    assert applicability_for(item, context_verified=True) == Applicability.APPLICABLE


def test_deferred_lab_cannot_be_promoted_to_training() -> None:
    with pytest.raises(ValueError, match="lab-only"):
        _compile(reviews={"DSR-003": {
            "disposition": "TRAIN", "reviewer": "Researcher",
            "reason": "This proposed reward has not been independently tested.",
        }})


def test_duplicate_identifier_fails_closed() -> None:
    rows = _rows()
    rows[1]["id"] = "DSR-001"
    with pytest.raises(ValueError, match="duplicate historic"):
        compile_knowledge(rows, source_id="test", archive_sha256="a" * 64,
                          suite_version="3.19.1")


def test_unknown_review_identifier_fails() -> None:
    with pytest.raises(ValueError, match="missing IDs"):
        _compile(reviews={"UNKNOWN-ID": {
            "disposition": "EVAL_ONLY", "reviewer": "Researcher",
            "reason": "No matching historical requirement is available here.",
        }})


def test_dependency_graph_is_ordered_and_rejects_cycle() -> None:
    graph = {"A": {"B", "C"}, "B": {"C"}, "C": set()}
    assert dependency_closure({"A"}, graph) == ("C", "B", "A")
    with pytest.raises(KnowledgeDependencyError, match="cyclic"):
        dependency_closure({"A"}, {"A": {"B"}, "B": {"A"}})
    with pytest.raises(KnowledgeDependencyError, match="unknown"):
        dependency_closure({"A"}, {"A": {"MISSING"}})
