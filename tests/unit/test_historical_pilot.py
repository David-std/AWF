"""Synthetic regression tests for source-bound, non-adjudicating historical pilot."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from awf.adapters.knowledge.pilot_evidence import inspect_historical_evidence
from awf.verification.historical_pilot import PILOT_IDS, run_historical_pilot


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture():
    rows = [
        {
            "id": identity,
            "domain": "operation_semantics",
            "priority": "MUST",
            "requirement": (
                f"Every material change of {identity} preserves the originally recorded "
                "information and requires explicit review approval."
            ),
            "source_ids": ["deep_01"],
            "implementation_paths": ["runtime/prototype.py"],
            "status": "IMPLEMENTED",
        }
        for identity in PILOT_IDS
    ]
    return rows


def test_synthetic_pilot_counts_and_semantic_gap() -> None:
    rows = _fixture()
    report = run_historical_pilot(rows, source_sha256="a" * 64, suite_version="3.19.1")
    assert report["case_count"] == 30
    assert report["real_source_rule_count"] == 6
    assert report["counts_by_scope_status"] == {"FAIL": 6, "NEEDS_REVIEW": 12, "PASS": 12}
    assert report["synthetic_semantic_override_syntactic_pass_count"] == 6
    assert report["rule_adjudications_issued"] == 0
    assert report["training_authorized"] is False
    assert all(case["document_acceptance"] == "NEEDS_REVIEW" for case in report["cases"])
    assert all(rule["awf_review_status"] == "UNREVIEWED" for rule in report["selected"])
    assert "requires explicit review" not in json.dumps(report)


def test_changed_or_duplicate_source_fails_closed() -> None:
    rows = _fixture()
    with pytest.raises(ValueError, match="selected rule not present"):
        run_historical_pilot(rows[:-1], source_sha256="a" * 64, suite_version="3.19.1")
    with pytest.raises(ValueError, match="duplicate historical"):
        run_historical_pilot(rows + [rows[0]], source_sha256="a" * 64, suite_version="3.19.1")
    rows[0]["priority"] = "DEFERRED_LAB"
    with pytest.raises(ValueError, match="incomplete real"):
        run_historical_pilot(rows, source_sha256="a" * 64, suite_version="3.19.1")


def test_untrusted_version_and_duplicate_ids_rejected() -> None:
    rows = _fixture()
    with pytest.raises(ValueError, match="pinned AWS"):
        run_historical_pilot(rows, source_sha256="a" * 64, suite_version="3.18.1")
    with pytest.raises(ValueError, match="nonempty and distinct"):
        run_historical_pilot(rows, source_sha256="a" * 64, suite_version="3.19.1",
                             rule_ids=(PILOT_IDS[0], PILOT_IDS[0]))


def test_archive_evidence_paths_and_tamper(tmp_path: Path) -> None:
    archive = tmp_path / "historical.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("academic_writing_suite/runtime/prototype.py", "# synthetic")
        z.writestr("academic_writing_suite/docs/research_inputs/deep_01.md", "synthetic")
    digest = _digest(archive.read_bytes())
    subset = _fixture()[:1]
    result = inspect_historical_evidence(archive, expected_sha256=digest, rows=subset)
    assert result["historical_implementation_file_refs_resolved"] == 1
    assert result["historical_research_source_refs_resolved"] == 1
    assert result["independent_scientific_review"] is False
    with pytest.raises(ValueError, match="differs"):
        inspect_historical_evidence(archive, expected_sha256="b" * 64, rows=subset)
    subset[0]["implementation_paths"] = ["../../private.txt"]
    with pytest.raises(ValueError, match="invalid source-surface"):
        inspect_historical_evidence(archive, expected_sha256=digest, rows=subset)


def test_missing_historical_surface_fails_closed(tmp_path: Path) -> None:
    archive = tmp_path / "empty.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("academic_writing_suite/docs/research_inputs/deep_01.md", "synthetic")
    with pytest.raises(ValueError, match="historical implementation surface missing"):
        inspect_historical_evidence(
            archive, expected_sha256=_digest(archive.read_bytes()), rows=_fixture()[:1]
        )
