"""WAL-aware backups and create-only recovery, bound to synthetic signed witnesses."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import awf.adapters.persistence.sqlite_snapshots as snapshots_adapter
from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.persistence.sqlite_revision import SQLiteRevisionJournal
from awf.adapters.persistence.sqlite_snapshots import SQLiteSnapshotWriter
from awf.adapters.security.ed25519_reviewer import Ed25519Verifier
from awf.application.commands.checkpoints import propose_checkpoint
from awf.application.commands.verified_snapshot import create_verified_snapshot
from awf.cli.main import main
from awf.domain.checkpoints import SignedLedgerCheckpoint, parse_checkpoint_policy
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.revision_audit import AuditSlot, AuditStatus
from awf.domain.signed_documents import canonical_json_bytes


def _setup(tmp_path: Path):
    source = tmp_path / "live" / "ledger.sqlite"
    ledger = SQLiteEvidenceLedger(source)
    ledger.initialize()
    ledger.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-a",
        subject_id="subject-a",
        content=b"synthetic private evidence",
    )
    key = Ed25519PrivateKey.generate()
    now = int(time.time())
    public = (
        key.public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        .hex()
    )
    policy_bytes = canonical_json_bytes(
        {
            "schema": 1,
            "grants": [
                {
                    "key_id": "custodian-a",
                    "ledger_ids": ["ledger-a"],
                    "public_key_hex": public,
                    "valid_from": now - 3600,
                    "valid_until": now + 3600,
                    "revoked": False,
                }
            ],
        }
    )
    policy = parse_checkpoint_policy(policy_bytes, expected_sha256=sha256_bytes(policy_bytes))
    claim = propose_checkpoint(
        store=ledger,
        ledger_id="ledger-a",
        key_id="custodian-a",
        issued_at=now - 1,
    )
    signed = SignedLedgerCheckpoint(claim, key.sign(claim.signing_bytes).hex())
    return source, signed, policy, policy_bytes, now


def _copy(source: Path, dest: Path, signed, policy, now: int):
    return create_verified_snapshot(
        store=SQLiteEvidenceLedger(source),
        writer=SQLiteSnapshotWriter(source),
        destination=dest,
        signed=signed,
        expected_signed_sha256=signed.sha256,
        policy=policy,
        verifier=Ed25519Verifier(),
        now=now,
    )


def test_backup_and_restore_to_fresh_path_preserve_signed_head_and_bytes(tmp_path: Path):
    source, signed, policy, _, now = _setup(tmp_path)
    backup = tmp_path / "backups" / "snapshot.sqlite"
    receipt = _copy(source, backup, signed, policy, now)
    assert backup.exists()
    assert receipt.event_count == 1
    assert receipt.head_digest == signed.claim.head_digest
    assert receipt.file_sha256 == sha256_bytes(backup.read_bytes())
    assert not receipt.independently_custodied
    restored = tmp_path / "restore" / "new.sqlite"
    restoration = _copy(backup, restored, signed, policy, now)
    assert restoration.head_digest == receipt.head_digest
    assert restoration.event_count == receipt.event_count
    assert SQLiteEvidenceLedger(restored).verify().head_digest == signed.claim.head_digest
    assert SQLiteEvidenceLedger(source).verify().head_digest == signed.claim.head_digest


def test_live_wal_uncheckpointed_event_is_included(tmp_path: Path):
    source, _, policy, _, now = _setup(tmp_path)
    # A pinned reader prevents checkpointing the newest WAL frames.
    with sqlite3.connect(source) as reader:
        reader.execute("PRAGMA journal_mode=WAL")
        reader.execute("BEGIN")
        assert reader.execute("SELECT count(*) FROM events").fetchone()[0] == 1
        store = SQLiteEvidenceLedger(source)
        store.append(
            kind=EvidenceKind.SOURCE_CHUNK,
            run_id="run-a",
            subject_id="chunk-2",
            content=b"latest committed WAL event",
        )
        assert Path(str(source) + "-wal").exists()
        key = Ed25519PrivateKey.generate()
        # Make an explicit independent grant for the newly observed source head.
        public = (
            key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
            )
            .hex()
        )
        policy_bytes = canonical_json_bytes(
            {
                "schema": 1,
                "grants": [
                    {
                        "key_id": "custodian-a",
                        "ledger_ids": ["ledger-a"],
                        "public_key_hex": public,
                        "valid_from": now - 3600,
                        "valid_until": now + 3600,
                        "revoked": False,
                    }
                ],
            }
        )
        policy = parse_checkpoint_policy(policy_bytes, expected_sha256=sha256_bytes(policy_bytes))
        claim = propose_checkpoint(
            store=store,
            ledger_id="ledger-a",
            key_id="custodian-a",
            issued_at=now - 1,
        )
        signed = SignedLedgerCheckpoint(claim, key.sign(claim.signing_bytes).hex())
        snapshot = tmp_path / "snapshot.sqlite"
        receipt = _copy(source, snapshot, signed, policy, now)
        assert receipt.event_count == 2
        assert SQLiteEvidenceLedger(snapshot).verify().events_checked == 2


def test_append_after_signature_blocks_backup_and_leaves_no_destination(tmp_path: Path):
    source, signed, policy, _, now = _setup(tmp_path)
    SQLiteEvidenceLedger(source).append(
        kind=EvidenceKind.SOURCE_CHUNK,
        run_id="run-a",
        subject_id="new",
        content=b"unsigned next event",
    )
    target = tmp_path / "not-created.sqlite"
    with pytest.raises(EvidenceIntegrityError, match="current ledger head"):
        _copy(source, target, signed, policy, now)
    assert not target.exists()


def test_concurrent_append_between_verification_and_copy_never_publishes_unsafe_backup(
    tmp_path: Path,
):
    source, signed, policy, _, now = _setup(tmp_path)
    target = tmp_path / "no-racy-snapshot.sqlite"

    class InterleavingWriter:
        def create_new(self, *, destination: Path, expected_head: str, expected_events: int):
            SQLiteEvidenceLedger(source).append(
                kind=EvidenceKind.SOURCE_CHUNK,
                run_id="run-a",
                subject_id="race",
                content=b"append between authorization and snapshot",
            )
            return SQLiteSnapshotWriter(source).create_new(
                destination=destination,
                expected_head=expected_head,
                expected_events=expected_events,
            )

    with pytest.raises(EvidenceIntegrityError, match="trusted head"):
        create_verified_snapshot(
            store=SQLiteEvidenceLedger(source),
            writer=InterleavingWriter(),
            destination=target,
            signed=signed,
            expected_signed_sha256=signed.sha256,
            policy=policy,
            verifier=Ed25519Verifier(),
            now=now,
        )
    assert not target.exists()
    assert SQLiteEvidenceLedger(source).verify().events_checked == 2


def test_changed_or_truncated_source_fails_before_backup(tmp_path: Path):
    source, signed, policy, _, now = _setup(tmp_path)
    rebuilt = tmp_path / "different.sqlite"
    ledger = SQLiteEvidenceLedger(rebuilt)
    ledger.initialize()
    ledger.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-a",
        subject_id="subject-a",
        content=b"other bytes at same event index",
    )
    target = tmp_path / "not-created.sqlite"
    with pytest.raises(EvidenceIntegrityError):
        _copy(rebuilt, target, signed, policy, now)
    assert not target.exists()
    with sqlite3.connect(source) as conn:
        conn.execute("DROP TRIGGER event_immutable_delete")
    with pytest.raises(EvidenceIntegrityError):
        _copy(source, target, signed, policy, now)
    assert not target.exists()


def test_duplicate_destination_cannot_be_overwritten_on_backup_or_restore(tmp_path: Path):
    source, signed, policy, _, now = _setup(tmp_path)
    target = tmp_path / "existing.sqlite"
    target.write_bytes(b"preserve these existing bytes")
    with pytest.raises(FileExistsError):
        _copy(source, target, signed, policy, now)
    assert target.read_bytes() == b"preserve these existing bytes"
    assert SQLiteEvidenceLedger(source).verify().events_checked == 1


def test_refuses_source_destination_alias_or_dangling_symlink(tmp_path: Path):
    source, signed, policy, _, now = _setup(tmp_path)
    with pytest.raises(ValueError):
        _copy(source, source, signed, policy, now)
    assert SQLiteEvidenceLedger(source).verify().events_checked == 1
    symlink = tmp_path / "symlink.sqlite"
    try:
        symlink.symlink_to(tmp_path / "absent.sqlite")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable on this platform")
    with pytest.raises(ValueError):
        _copy(source, symlink, signed, policy, now)
    assert symlink.is_symlink()


def test_atomic_publish_failure_cleans_staging_without_touching_original(
    tmp_path: Path,
    monkeypatch,
):
    source, signed, policy, _, now = _setup(tmp_path)
    target = tmp_path / "unpublished.sqlite"

    def fail_link(_src: Path, _target: Path) -> None:
        raise PermissionError("synthetic atomic publish failure")

    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(PermissionError, match="synthetic"):
        _copy(source, target, signed, policy, now)
    assert not target.exists()
    assert not tuple(tmp_path.glob(".unpublished.awf-snapshot-*"))
    assert SQLiteEvidenceLedger(source).verify().head_digest == signed.claim.head_digest


@pytest.mark.parametrize("value", [0.0, -1.0, float("inf"), float("nan"), 3601.0])
def test_snapshot_writer_rejects_invalid_transfer_timeouts(tmp_path: Path, value: float):
    with pytest.raises(ValueError, match="timeout"):
        SQLiteSnapshotWriter(tmp_path / "source.sqlite", timeout_seconds=value)


def test_transfer_timeout_aborts_without_publishing_partial_database(
    tmp_path: Path,
    monkeypatch,
):
    source, signed, policy, _, now = _setup(tmp_path)
    target = tmp_path / "timeout.sqlite"
    ticks = iter([0.0, 121.0, 121.0, 121.0])
    monkeypatch.setattr(snapshots_adapter.time, "monotonic", lambda: next(ticks, 121.0))
    with pytest.raises(TimeoutError, match="deadline"):
        create_verified_snapshot(
            store=SQLiteEvidenceLedger(source),
            writer=SQLiteSnapshotWriter(source),
            destination=target,
            signed=signed,
            expected_signed_sha256=signed.sha256,
            policy=policy,
            verifier=Ed25519Verifier(),
            now=now,
        )
    assert not target.exists()
    assert not tuple(tmp_path.glob(".timeout.awf-snapshot-*"))


@pytest.mark.parametrize("damage", ["forged_state", "missing_commit"])
def test_backup_rejects_corrupted_revision_snapshot_even_with_valid_signed_event_chain(
    tmp_path: Path,
    damage: str,
):
    db = tmp_path / "revision.sqlite"
    journal = SQLiteRevisionJournal(db)
    journal.initialize()
    doc = MarkdownAdapter().parse(b"synthetic claim with source.\n", source_name="sample.md")
    slot = AuditSlot(doc.blocks[0].block_id, "claims", 2)
    journal.create(
        revision_id="revision-a",
        operation_id="start",
        run_id="run-a",
        document=doc,
        slots=(slot,),
    )
    journal.record_audit(
        revision_id="revision-a",
        operation_id="audit",
        run_id="run-a",
        document=doc,
        expected_version=0,
        slot_key=slot.key,
        status=AuditStatus.CLEAN,
        checks_executed=2,
        observation_ref="synthetic-note",
    )
    now = int(time.time())
    # Obtain trust for the actual revision ledger's current head, using the
    # custodian policy and matching key from a fresh, self-contained fixture.
    key = Ed25519PrivateKey.generate()
    public = (
        key.public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        .hex()
    )
    raw = canonical_json_bytes(
        {
            "schema": 1,
            "grants": [
                {
                    "key_id": "custodian-a",
                    "ledger_ids": ["ledger-a"],
                    "public_key_hex": public,
                    "valid_from": now - 3600,
                    "valid_until": now + 3600,
                    "revoked": False,
                }
            ],
        }
    )
    policy = parse_checkpoint_policy(raw, expected_sha256=sha256_bytes(raw))
    claim = propose_checkpoint(
        store=journal.ledger,
        ledger_id="ledger-a",
        key_id="custodian-a",
        issued_at=now - 1,
    )
    signed = SignedLedgerCheckpoint(claim, key.sign(claim.signing_bytes).hex())
    assert journal.ledger.verify().events_checked == 3
    # A privileged attacker briefly drops a trigger, tampers with the
    # snapshots and recreates the *exact* trigger, so schema checks pass.
    # It is the typed journal replay that must catch this violation.
    with sqlite3.connect(db) as conn:
        if damage == "forged_state":
            conn.execute("DROP TRIGGER revision_snapshot_immutable_update")
            conn.execute("UPDATE revision_snapshots SET state_bytes=? WHERE version=0", (b"{}",))
            conn.execute(
                """CREATE TRIGGER revision_snapshot_immutable_update
                BEFORE UPDATE ON revision_snapshots
                BEGIN SELECT RAISE(ABORT, 'revision snapshots immutable'); END"""
            )
        else:
            conn.execute("DROP TRIGGER revision_snapshot_immutable_delete")
            conn.execute("DELETE FROM revision_snapshots WHERE version=1")
            conn.execute(
                """CREATE TRIGGER revision_snapshot_immutable_delete
                BEFORE DELETE ON revision_snapshots
                BEGIN SELECT RAISE(ABORT, 'revision snapshots immutable'); END"""
            )
    with journal.ledger._open() as connection:
        journal._check_schema(connection)
    assert journal.ledger.verify().head_digest == signed.claim.head_digest
    target = tmp_path / "should-not-exist.sqlite"
    with pytest.raises(EvidenceIntegrityError, match="snapshot|revision"):
        _copy(db, target, signed, policy, now)
    assert not target.exists()


def test_restore_rejects_tampered_backup_before_creating_any_file(tmp_path: Path):
    source, signed, policy, _, now = _setup(tmp_path)
    backup = tmp_path / "backup.sqlite"
    _copy(source, backup, signed, policy, now)
    with sqlite3.connect(backup) as conn:
        conn.execute("DROP TRIGGER event_immutable_update")
    target = tmp_path / "restore.sqlite"
    with pytest.raises(EvidenceIntegrityError):
        _copy(backup, target, signed, policy, now)
    assert not target.exists()


def test_cli_backup_restore_and_bad_external_digest(tmp_path: Path, capsys):
    source, signed, _, policy_raw, _ = _setup(tmp_path)
    checkpoint_file = tmp_path / "signed.json"
    checkpoint_file.write_bytes(signed.to_bytes())
    policy_file = tmp_path / "custodians.json"
    policy_file.write_bytes(policy_raw)
    destination = tmp_path / "backup.sqlite"
    flags = [
        "--checkpoint-file",
        str(checkpoint_file),
        "--expected-checkpoint-sha256",
        signed.sha256,
        "--policy-file",
        str(policy_file),
        "--expected-policy-sha256",
        sha256_bytes(policy_raw),
    ]
    assert main(["evidence", "snapshot-create", str(source), str(destination), *flags]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "SNAPSHOT_BACKUP_CREATED"
    assert result["external_custody_proven"] is False
    restored = tmp_path / "recovered.sqlite"
    assert main(["evidence", "snapshot-restore", str(destination), str(restored), *flags]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "SNAPSHOT_RESTORED_TO_NEW_PATH"
    assert result["event_count"] == 1
    assert main(["evidence", "snapshot-restore", str(destination), str(restored), *flags]) == 2
    assert "destination already exists" in capsys.readouterr().err
    wrong = list(flags)
    wrong[3] = "f" * 64
    not_created = tmp_path / "no-restore.sqlite"
    assert main(["evidence", "snapshot-restore", str(destination), str(not_created), *wrong]) == 2
    assert "SNAPSHOT_FAILED" in capsys.readouterr().err
    assert not not_created.exists()
