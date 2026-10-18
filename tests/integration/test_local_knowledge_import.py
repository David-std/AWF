"""Synthetic ZIP tests: actual AWS corpus is private and never checked into Git."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from awf.adapters.knowledge.pinned_archive import PinnedAwsArchive
from awf.adapters.knowledge.review_file import JsonReviewReader
from awf.adapters.knowledge.zip_archive import LEDGER_PATH
from awf.application.commands.compile_knowledge import import_knowledge
from awf.cli.main import main
from awf.knowledge.audit import audit_registry


def import_test_knowledge(
    *, archive_path: Path, manifest_path: Path, review_path: Path | None = None
):
    return import_knowledge(
        archive_path=archive_path,
        manifest_path=manifest_path,
        archive_reader=PinnedAwsArchive(),
        review_path=review_path,
        review_reader=JsonReviewReader(),
    )


@pytest.fixture
def local_source(tmp_path: Path) -> tuple[Path, Path, str]:
    archive = tmp_path / "private.zip"
    ledger = {
        "suite_version": "3.19.1",
        "requirements": [
            {
                "id": "DSR-001",
                "domain": "structural",
                "priority": "MUST",
                "second_pass_class": "ROBUST_MECHANICAL_CONTRACT",
                "requirement": "Preserve provenance.",
                "source_ids": ["deep-1"],
            },
            {
                "id": "DSR-002",
                "domain": "detector",
                "priority": "DEFERRED_LAB",
                "second_pass_class": "DEFERRED_EMPIRICAL",
                "requirement": "Measure outcomes in a controlled study.",
                "source_ids": ["deep-2"],
            },
        ],
    }
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(LEDGER_PATH, json.dumps(ledger))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "id": "aws-3.19.1",
                        "sha256": digest,
                        "version": "3.19.1",
                        "requirements_count": 2,
                        "repo_committed": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return archive, manifest, digest


def test_local_compilation_is_metadata_only(
    local_source: tuple[Path, Path, str], tmp_path: Path, capsys
) -> None:
    archive, manifest, digest = local_source
    registry_path = tmp_path / "local.json"
    code = main(
        [
            "knowledge",
            "import",
            str(archive),
            "--manifest",
            str(manifest),
            "--output",
            str(registry_path),
        ]
    )
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


def test_archive_hash_mismatch_rejected(local_source: tuple[Path, Path, str], capsys) -> None:
    archive, manifest, _ = local_source
    archive.write_bytes(archive.read_bytes() + b"tampering")
    assert main(["knowledge", "import", str(archive), "--manifest", str(manifest)]) == 2
    assert "SHA-256" in capsys.readouterr().err


def test_output_cannot_overwrite_archive(local_source: tuple[Path, Path, str], capsys) -> None:
    archive, manifest, _ = local_source
    original = archive.read_bytes()
    assert (
        main(
            [
                "knowledge",
                "import",
                str(archive),
                "--manifest",
                str(manifest),
                "--output",
                str(archive),
            ]
        )
        == 2
    )
    assert archive.read_bytes() == original
    assert "SOURCE_PROTECTED" in capsys.readouterr().err


def test_import_does_not_change_original_archive(local_source: tuple[Path, Path, str]) -> None:
    archive, manifest, digest = local_source
    _ = import_test_knowledge(archive_path=archive, manifest_path=manifest)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest


def test_unreviewed_promotion_in_report_fails_audit(
    local_source: tuple[Path, Path, str],
) -> None:
    archive, manifest, _ = local_source
    report = import_test_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
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
    overlay.write_text(
        json.dumps(
            {
                "source_sha256": "b" * 64,
                "decisions": [
                    {
                        "id": "DSR-001",
                        "disposition": "KEEP_AS_CODE",
                        "reviewer": "Researcher",
                        "reason": "The requirement is a deterministic byte integrity check.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="bound"):
        import_test_knowledge(archive_path=archive, manifest_path=manifest, review_path=overlay)


def test_audit_detects_mismatched_report_totals(local_source: tuple[Path, Path, str]) -> None:
    archive, manifest, _ = local_source
    report = import_test_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
    report["requirements_count"] = 184
    assert audit_registry(report)["valid"] is False


def test_private_review_plan_has_complete_coverage_and_no_stdout_source_text(
    local_source: tuple[Path, Path, str], tmp_path: Path, capsys
) -> None:
    archive, manifest, digest = local_source
    args = [
        "knowledge",
        "plan-review",
        str(archive),
        "--manifest",
        str(manifest),
        "--batch-size",
        "1",
    ]
    assert main(args) == 0
    printed = capsys.readouterr().out
    assert "Preserve provenance" not in printed
    summary = json.loads(printed)
    assert summary["requirements_count"] == 2
    assert summary["open_count"] == 2
    path = Path(summary["manifest"])
    assert path.exists()
    assert path.parent.parent.parent.name == ".awf"
    overview = json.loads(path.read_text(encoding="utf-8"))
    assert overview["archive_sha256"] == digest
    assert overview["source_text_in_manifest"] is False
    assert len(overview["batches"]) == 2
    first = json.loads((path.parent / overview["batches"][0]["file"]).read_text("utf-8"))
    assert first["contains_private_source_text"] is True
    assert first["rules"][0]["review_status"] == "OPEN"
    assert first["rules"][0]["review_template"]["desired_disposition"] is None
    assert "Preserve provenance" not in path.read_text(encoding="utf-8")

    # Repeat import must produce the same private, SHA-bound bytes.
    before = {p.name: p.read_bytes() for p in path.parent.glob("*.json")}
    args = [
        "knowledge",
        "plan-review",
        str(archive),
        "--manifest",
        str(manifest),
        "--batch-size",
        "1",
    ]
    assert main(args) == 0
    assert before == {p.name: p.read_bytes() for p in path.parent.glob("*.json")}


def test_review_plan_rejects_invalid_batch_size(
    local_source: tuple[Path, Path, str], capsys
) -> None:
    archive, manifest, _ = local_source
    args = [
        "knowledge",
        "plan-review",
        str(archive),
        "--manifest",
        str(manifest),
        "--batch-size",
        "0",
    ]
    assert main(args) == 2
    assert "batch_size" in capsys.readouterr().err
