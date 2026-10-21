"""CLI supports opt-in verified links without altering dossier adjudication."""

from __future__ import annotations

import json
from pathlib import Path

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.cli.main import main
from awf.domain.evidence import EvidenceKind

SOURCE_SHA = "a" * 64
RULE_SHA = "b" * 64
RUN_ID = "review-run-001"


def test_private_cli_evidence_links_remain_unadjudicated(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest_path = tmp_path / "provenance" / "source-manifest.json"
    manifest_path.parent.mkdir()
    manifest = {"archive_sha256": SOURCE_SHA, "source_id": "aws-3.19.1"}
    template = {
        "reviewer": None,
        "reason": None,
        "evidence_ids": [],
        "conflicting_rule_ids": [],
        "desired_disposition": None,
        "proposed_tests": [],
        "source_rights_status": "NOT_EVALUATED",
        "current_model_or_version_evidence": None,
    }
    canonical_rule = {
        "id": "DSR-001",
        "priority": "MUST",
        "requirement_sha256": RULE_SHA,
        "review_template": template,
    }
    packet = {"batch_id": "AWF-REVIEW-001", "rules": [canonical_rule]}
    expected = {"batch-001.json": packet}
    monkeypatch.setattr("awf.cli.main.prepare_review", lambda **_: (manifest, expected))

    support = {
        "schema_version": "1.0.0",
        "purpose": "knowledge_review_support",
        "archive_sha256": SOURCE_SHA,
        "source_id": "aws-3.19.1",
        "requirement_id": "DSR-001",
        "requirement_sha256": RULE_SHA,
    }
    database = tmp_path / ".awf" / "evidence" / "ledger.sqlite"
    ledger = SQLiteEvidenceLedger(database)
    ledger.initialize()
    event = ledger.append(
        kind=EvidenceKind.RULE_SUPPORT,
        run_id=RUN_ID,
        subject_id="DSR-001",
        content=json.dumps(support).encode("utf-8"),
    )
    review_dir = tmp_path / ".awf" / "knowledge" / f"review-{SOURCE_SHA[:12]}-b12"
    review_dir.mkdir(parents=True)
    (review_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    proposal = {
        **canonical_rule,
        "review_template": {
            **template,
            "reviewer": "declared person, not authenticated",
            "reason": "A sufficiently detailed but unverified scientific claim.",
            "evidence_ids": [f"event:{event.digest}"],
            "desired_disposition": "KEEP_AS_CONTEXT",
            "proposed_tests": ["synthetic unit check"],
            "source_rights_status": "NOT_APPLICABLE",
            "current_model_or_version_evidence": "test snapshot",
        },
    }
    (review_dir / "batch-001.json").write_text(
        json.dumps({**packet, "rules": [proposal]}), encoding="utf-8"
    )
    base = [
        "knowledge",
        "inspect-review",
        str(tmp_path / "aws-private.zip"),
        "--manifest",
        str(manifest_path),
    ]
    assert main(base) == 0
    standard = json.loads(capsys.readouterr().out)
    assert "evidence_links" not in standard

    args = base + [
        "--evidence-database",
        str(database),
        "--review-run-id",
        RUN_ID,
        "--expected-head",
        event.digest,
        "--require-documented",
    ]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status_counts"]["PROPOSAL_DOCUMENTED"] == 1
    assert result["evidence_links"]["all_declared_links_verified"] is True
    assert result["review_attestation_authorized"] is False
    assert result["training_authorized"] is False
    assert "sufficiently detailed" not in json.dumps(result)
    assert "declared person" not in json.dumps(result)

    assert main(args[:-3]) == 2  # incomplete evidence configuration
    capsys.readouterr()
    assert main([*args[:-1], "--expected-head", "f" * 64]) == 2
    assert "DOSSIER_INSPECTION_FAILED" in capsys.readouterr().err
