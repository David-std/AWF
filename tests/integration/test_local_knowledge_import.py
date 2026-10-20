"""Synthetic ZIP tests: actual AWS corpus is private and never checked into Git."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

from awf.adapters.knowledge.pinned_archive import PinnedAwsArchive
from awf.adapters.knowledge.review_file import JsonReviewReader
from awf.adapters.knowledge.zip_archive import LEDGER_PATH, read_requirement_ledger
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


def test_import_does_not_change_original_archive(
    local_source: tuple[Path, Path, str],
) -> None:
    archive, manifest, digest = local_source
    _ = import_test_knowledge(archive_path=archive, manifest_path=manifest)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest


@pytest.mark.skipif(sys.platform == "win32", reason="Windows locks open ZIP files")
def test_zip_path_replacement_after_checksum_does_not_change_verified_bytes(
    local_source: tuple[Path, Path, str], tmp_path: Path, monkeypatch
) -> None:
    archive, _, trusted_sha = local_source
    replacement = tmp_path / "replacement.zip"
    with zipfile.ZipFile(replacement, mode="w") as output:
        output.writestr(
            LEDGER_PATH,
            json.dumps(
                {
                    "suite_version": "3.19.1",
                    "requirements": [
                        {
                            "id": "DSR-001",
                            "domain": "structural",
                            "priority": "MUST",
                            "requirement": "Different untrusted source text",
                            "source_ids": ["deep-1"],
                        },
                        {
                            "id": "DSR-002",
                            "domain": "detector",
                            "priority": "DEFERRED_LAB",
                            "requirement": "Different laboratory text",
                            "source_ids": ["deep-2"],
                        },
                    ],
                }
            ),
        )
    original_zipfile = zipfile.ZipFile
    was_replaced = False

    def replace_path_before_zip_open(file, *args, **kwargs):
        nonlocal was_replaced
        if not was_replaced:
            os.replace(replacement, archive)
            was_replaced = True
        return original_zipfile(file, *args, **kwargs)

    monkeypatch.setattr(zipfile, "ZipFile", replace_path_before_zip_open)
    rows = read_requirement_ledger(
        archive,
        expected_sha256=trusted_sha,
        expected_version="3.19.1",
        expected_count=2,
    )
    assert was_replaced
    assert rows[0]["requirement"] == "Preserve provenance."


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


def test_audit_detects_mismatched_report_totals(
    local_source: tuple[Path, Path, str],
) -> None:
    archive, manifest, _ = local_source
    report = import_test_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
    report["requirements_count"] = 184
    assert audit_registry(report)["valid"] is False


def test_overlay_creates_proposal_not_executable_attestation(
    local_source: tuple[Path, Path, str], tmp_path: Path
) -> None:
    archive, manifest, digest = local_source
    overlay = tmp_path / "review.json"
    overlay.write_text(
        json.dumps(
            {
                "source_sha256": digest,
                "decisions": [
                    {
                        "id": "DSR-001",
                        "disposition": "KEEP_AS_CODE",
                        "reviewer": "Researcher",
                        "reason": "Prototype only: the mechanical source check is not attested.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = import_test_knowledge(
        archive_path=archive, manifest_path=manifest, review_path=overlay
    ).to_dict()
    assert report["records"][0]["review_status"] == "REVIEW_PROPOSED"
    assert report["unreviewed_count"] == 2
    assert audit_registry(report)["valid"] is True


def test_audit_rejects_forged_attestation_even_with_plausible_identity(
    local_source: tuple[Path, Path, str],
) -> None:
    archive, manifest, _ = local_source
    report = import_test_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
    report["records"][0].update(
        disposition="KEEP_AS_CODE",
        review_status="REVIEW_ATTESTED",
        reviewer="Claimed evaluator",
        decision_reason="The code supposedly passed a private source audit.",
    )
    report["disposition_counts"].update(UNRESOLVED=0, KEEP_AS_CODE=1)
    report["unreviewed_count"] = 1
    verdict = audit_registry(report)
    assert verdict["valid"] is False
    assert any("self-attested" in msg for msg in verdict["errors"])


def test_audit_rejects_deferred_lab_promotion_even_with_proposal(
    local_source: tuple[Path, Path, str],
) -> None:
    archive, manifest, _ = local_source
    report = import_test_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
    report["records"][1].update(
        disposition="TRAIN",
        review_status="REVIEW_PROPOSED",
        reviewer="Researcher",
        decision_reason="This is only a proposal; no valid training permission is present.",
    )
    report["disposition_counts"].update(EVAL_ONLY=0, TRAIN=1)
    verdict = audit_registry(report)
    assert verdict["valid"] is False
    assert any("deferred lab promotion" in msg for msg in verdict["errors"])


@pytest.mark.parametrize("value", ["REVIEW_APPROVED", None, 1])
def test_audit_rejects_undeclared_review_status(
    local_source: tuple[Path, Path, str], value: object
) -> None:
    archive, manifest, _ = local_source
    report = import_test_knowledge(archive_path=archive, manifest_path=manifest).to_dict()
    report["records"][0]["review_status"] = value
    verdict = audit_registry(report)
    assert verdict["valid"] is False
    assert any("unknown review status" in msg for msg in verdict["errors"])


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


def test_review_plan_never_overwrites_local_human_annotations(
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
        "1",
    ]
    assert main(args) == 0
    overview_path = Path(json.loads(capsys.readouterr().out)["manifest"])
    overview = json.loads(overview_path.read_text(encoding="utf-8"))
    packet_path = overview_path.parent / overview["batches"][0]["file"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["rules"][0]["review_template"]["reason"] = "Unfinished private annotation"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    annotated_bytes = packet_path.read_bytes()
    prior_manifest = overview_path.read_bytes()

    assert main(args) == 2
    assert "local changes" in capsys.readouterr().err
    assert packet_path.read_bytes() == annotated_bytes
    assert overview_path.read_bytes() == prior_manifest


def test_review_plan_resumes_incomplete_write_without_changing_existing_packets(
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
        "1",
    ]
    assert main(args) == 0
    overview_path = Path(json.loads(capsys.readouterr().out)["manifest"])
    overview = json.loads(overview_path.read_text(encoding="utf-8"))
    first = overview_path.parent / overview["batches"][0]["file"]
    second = overview_path.parent / overview["batches"][1]["file"]
    first_bytes = first.read_bytes()
    second.unlink()
    overview_path.unlink()

    assert main(args) == 0
    capsys.readouterr()
    assert first.read_bytes() == first_bytes
    assert second.exists() and overview_path.exists()


def test_review_plan_rejects_modified_manifest(
    local_source: tuple[Path, Path, str], capsys
) -> None:
    archive, manifest, _ = local_source
    args = ["knowledge", "plan-review", str(archive), "--manifest", str(manifest)]
    assert main(args) == 0
    overview_path = Path(json.loads(capsys.readouterr().out)["manifest"])
    overview_path.write_text("manual review summary\n", encoding="utf-8")
    assert main(args) == 2
    assert "manifest.json" in capsys.readouterr().err
    assert overview_path.read_text(encoding="utf-8") == "manual review summary\n"


def test_private_review_inspection_does_not_attest_open_rules(
    local_source: tuple[Path, Path, str], capsys
) -> None:
    archive, manifest, _ = local_source
    params = [str(archive), "--manifest", str(manifest), "--batch-size", "1"]
    assert main(["knowledge", "plan-review", *params]) == 0
    capsys.readouterr()
    assert main(["knowledge", "inspect-review", *params]) == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["requirements_count"] == 2
    assert summary["status_counts"] == {"OPEN": 2}
    assert summary["review_attestation_authorized"] is False
    assert summary["independent_evidence_verified"] is False
    assert "Preserve provenance" not in str(summary)
    assert main(["knowledge", "inspect-review", *params, "--require-documented"]) == 2


def test_private_review_inspector_rejects_modified_source_bound_rule(
    local_source: tuple[Path, Path, str], capsys
) -> None:
    archive, manifest, _ = local_source
    params = [str(archive), "--manifest", str(manifest), "--batch-size", "1"]
    assert main(["knowledge", "plan-review", *params]) == 0
    output = json.loads(capsys.readouterr().out)
    location = Path(output["manifest"])
    overview = json.loads(location.read_text(encoding="utf-8"))
    batch = location.parent / overview["batches"][0]["file"]
    packet = json.loads(batch.read_text(encoding="utf-8"))
    packet["rules"][0]["review_status"] = "REVIEW_ATTESTED"
    batch.write_text(json.dumps(packet), encoding="utf-8")
    assert main(["knowledge", "inspect-review", *params]) == 2
    stderr = capsys.readouterr().err
    assert "immutable source-bound" in stderr
    assert "Preserve provenance" not in stderr


def test_private_review_inspector_rejects_missing_batch(
    local_source: tuple[Path, Path, str], capsys
) -> None:
    archive, manifest, _ = local_source
    params = [str(archive), "--manifest", str(manifest), "--batch-size", "1"]
    assert main(["knowledge", "plan-review", *params]) == 0
    output = json.loads(capsys.readouterr().out)
    location = Path(output["manifest"])
    overview = json.loads(location.read_text(encoding="utf-8"))
    (location.parent / overview["batches"][0]["file"]).unlink()
    assert main(["knowledge", "inspect-review", *params]) == 2
    assert "DOSSIER_INSPECTION_FAILED" in capsys.readouterr().err
