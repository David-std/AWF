"""CLI reads local synthetic evidence; no document contents in stdout or Git."""

from __future__ import annotations

import json
from pathlib import Path

from awf.cli.main import main


def test_cli_append_and_verify_with_head_checkpoint(
    tmp_path: Path, capsys
) -> None:
    evidence = tmp_path / "private-evidence.txt"
    secret = "synthetic private paragraph: not for stdout"
    evidence.write_text(secret, encoding="utf-8")
    db = tmp_path / "private" / "ledger.sqlite"
    assert main([
        "evidence", "append", str(evidence), "--kind", "AUDIT_RECEIPT",
        "--run-id", "session-1", "--subject-id", "DSR-019",
        "--database", str(db),
    ]) == 0
    output = capsys.readouterr().out
    assert secret not in output
    receipt = json.loads(output)
    assert receipt["status"] == "EVIDENCE_RECORDED"
    assert receipt["claims_independently_verified"] is False
    assert evidence.read_text(encoding="utf-8") == secret
    assert main([
        "evidence", "verify", "--database", str(db),
        "--expected-head", receipt["head_digest"],
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "LEDGER_INTEGRITY_VALID"
    assert result["events_checked"] == 1
    assert result["external_authenticity_proven"] is False


def test_cli_rejects_false_checkpoint(tmp_path: Path, capsys) -> None:
    path = tmp_path / "data.txt"
    path.write_text("synthetic", encoding="utf-8")
    db = tmp_path / "ledger.sqlite"
    assert main([
        "evidence", "append", str(path),
        "--kind", "SOURCE_CHUNK", "--run-id", "test", "--subject-id", "chunk-1",
        "--database", str(db),
    ]) == 0
    capsys.readouterr()
    assert main([
        "evidence", "verify", "--database", str(db), "--expected-head", "1" * 64
    ]) == 2
    assert "trusted head" in capsys.readouterr().err


def test_cli_never_overwrites_source_even_if_database_matches(
    tmp_path: Path, capsys
) -> None:
    path = tmp_path / "source.sqlite"
    original = b"actual source bytes"
    path.write_bytes(original)
    assert main([
        "evidence", "append", str(path),
        "--kind", "AUDIT_RECEIPT", "--run-id", "test", "--subject-id", "item",
        "--database", str(path),
    ]) == 2
    assert "cannot be the ledger" in capsys.readouterr().err
    assert path.read_bytes() == original


def test_cli_missing_source_does_not_claim_recorded(
    tmp_path: Path, capsys
) -> None:
    assert main([
        "evidence", "append", str(tmp_path / "absent.txt"),
        "--kind", "AUDIT_RECEIPT", "--run-id", "test", "--subject-id", "item",
        "--database", str(tmp_path / "ledger.sqlite"),
    ]) == 2
    assert "EVIDENCE_APPEND_FAILED" in capsys.readouterr().err
