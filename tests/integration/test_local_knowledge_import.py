"""Synthetic ZIP tests: actual AWS corpus is private and never checked into Git."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from awf.adapters.knowledge.zip_archive import LEDGER_PATH, KnowledgeSourceError
from awf.application.commands.compile_knowledge import import_knowledge
from awf.cli.main import main
from awf.knowledge.audit import audit_registry


@pytest.fixture
def local_source(tmp_path: Path) -> tuple[Path, Path, str]:
    archive = tmp_path / "private.zip"
    ledger = {
        "suite_version": "3.19.1",
        "requirements": [
            {
                "id": "DSR-001", "domain": "structural", "priority": "MUST",
                "requirement": "Preserve provenance.", "source_ids": ["deep-1"],
            },
            {
                "id": "DSR-002", "domain": "detector", "priority": "DEFERRED_LAB",
                "requirement": "Measure outcomes in a controlled study.",
                "source_ids": ["deep-2"],
            },
        ],
    }
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(LEDGER_PATH, json.dumps(ledger))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"artifacts": [{
        "id": "aws-3.19.1", "sha256": digest, "version": "3.19.1",
        "requirements_count": 2, "repo_committed": False,
    }]}), encoding="utf-8")
    return archive, manifest, digest


def test_local_compilation_is_metadata_only(local_source: tuple[Path, Path, str],
                                            tmp_path: Path, capsys) -> None:
    archive, manifest, digest = local_source
    registry_path = tmp_path / "local.json"
    code = main(["knowledge", "import", str(archive), "--manifest", str(manifest),
                 "--output", str(registry_path)])
    assert code == 0
    report = json.loads(registry_path.read_text(encoding="utf-8"))
    assert report["archive_sha256"] == digest
    assert report["requirements_count"] == 2
    assert report["unreviewed_count"] == 2
    assert report["disposition_counts"]["UNRESOLVED"] == 1
    assert report["disposition_counts"]["EVAL_ONLY"] == 1
    assert "Preserve provenance" not in registry_path.read_text(encoding="utf-8")
    assert registry_path.stat().st_size < 10_000
    assert json.loads(capsys.readouterr().out)["status"] == "IMPORTED_WITH_OPEN_REVIEWS"
    assert main(["knowledge", "audit", str(registry_path), "--archive", str(archive)]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True


def test_archive_hash_mismatch_rejected(local_source: tuple[Path, Path, str],
                                        capsys) -> None:
    archive, manifest, _ = local_source
    archive.write_bytes(archive.read_bytes() + b"tampering")
    assert main(["knowledge", "import", str(archive), "--manifest", str(manifest)]) == 2
    assert "SHA-256" in capsys.readouterr().err


def test_output_cannot_overwrite_archive(local_source: tuple[Path, Path, str],
                                         capsys) -> None:
    archive, manifest, _ = local_source
    original = archive.read_bytes()
    assert main(["knowledge", "import", str(archive), "--manifest", str(manifest),
                 "--output", str(archive)]) == 2
    assert archive.read_bytes() == original
    assert "SOURCE_PROTECTED" in capsys.readouterr().err


def test_import_does_not_change_original_archive(local_source: tuple[Path, Path, str]) -> None:
    archive, manifest, digest = local_source
    _ = import_knowledge(archive_path=archive, manifest_path=manifest)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest


def test_unreviewed_promotion_in_report_fails_audit(
    local_source: tuple[Path, Path, str],
) -> None:
    archive, manifest, _ = local_source
    report = import_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
    records = report["records"]
    assert isinstance(records, list)
    records[0]["disposition"] = "TRAIN"
    report["disposition_counts"]["TRAIN"] = 1
    report["disposition_counts"]["UNRESOLVED"] = 0
    verdict = audit_registry(report)
    assert verdict["valid"] is False
    assert any("unreviewed promotion" in msg for msg in verdict["errors"])


def test_review_overlay_fails_when_bound_to_wrong_archive(
    local_source: tuple[Path, Path, str], tmp_path: Path
) -> None:
    archive, manifest, _ = local_source
    overlay = tmp_path / "review.json"
    overlay.write_text(json.dumps({
        "source_sha256": "b" * 64, "decisions": [{
            "id": "DSR-001", "disposition": "KEEP_AS_CODE",
            "reviewer": "Researcher",
            "reason": "The requirement is a deterministic byte integrity check.",
        }],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="bound"):
        import_knowledge(archive_path=archive, manifest_path=manifest, review_path=overlay)


def test_audit_detects_mismatched_report_totals(local_source: tuple[Path, Path, str]) -> None:
    archive, manifest, _ = local_source
    report = import_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
    report["requirements_count"] = 184
    assert audit_registry(report)["valid"] is False
