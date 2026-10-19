"""Transactional, adversarial evidence ledger tests with synthetic local bytes."""

from __future__ import annotations

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.domain.evidence import (
    GENESIS_DIGEST,
    MAX_EVIDENCE_BYTES,
    EvidenceIntegrityError,
    EvidenceKind,
    event_digest,
    sha256_bytes,
)


def store(tmp_path: Path) -> SQLiteEvidenceLedger:
    ledger = SQLiteEvidenceLedger(tmp_path / "private" / "evidence.sqlite")
    ledger.initialize()
    return ledger


def append(ledger: SQLiteEvidenceLedger, raw: bytes = b"synthetic review evidence"):
    return ledger.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-001",
        subject_id="DSR-001",
        content=raw,
    )


def test_append_roundtrip_restart_and_checkpoint(tmp_path: Path) -> None:
    db = tmp_path / "private" / "evidence.sqlite"
    ledger = store(tmp_path)
    first = append(ledger)
    assert first.sequence == 1
    assert first.previous_digest == GENESIS_DIGEST
    assert first.evidence_sha256 == sha256_bytes(b"synthetic review evidence")
    assert ledger.retrieve(first.evidence_sha256) == b"synthetic review evidence"
    after_restart = SQLiteEvidenceLedger(db)
    audit = after_restart.verify(expected_head=first.digest)
    assert audit.events_checked == 1
    assert audit.evidence_objects_checked == 1
    assert audit.head_digest == first.digest
    assert audit.valid is True


def test_duplicate_payload_is_single_object_but_distinct_events(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    a = append(ledger, b"identical")
    b = append(ledger, b"identical")
    report = ledger.verify(expected_head=b.digest)
    assert b.sequence == 2
    assert b.previous_digest == a.digest
    assert a.digest != b.digest
    assert report.evidence_objects_checked == 1
    assert report.events_checked == 2


def test_empty_oversize_invalid_identity_and_kind_fail_closed(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    for data in (b"", b"X" * (MAX_EVIDENCE_BYTES + 1)):
        with pytest.raises(ValueError, match="nonempty"):
            append(ledger, data)
    with pytest.raises(ValueError, match="run identifier"):
        ledger.append(
            kind=EvidenceKind.SOURCE_CHUNK,
            run_id="private personal data",
            subject_id="chunk",
            content=b"x",
        )
    with pytest.raises(ValueError, match="unknown evidence kind"):
        ledger.append(
            kind="SOURCE_CHUNK",  # type: ignore[arg-type]
            run_id="test",
            subject_id="chunk",
            content=b"x",
        )
    assert ledger.verify().events_checked == 0


def test_database_triggers_reject_mutation(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    append(ledger)
    with sqlite3.connect(ledger.database) as db:
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            db.execute("UPDATE events SET subject_id='faked'")
        with pytest.raises(sqlite3.DatabaseError, match="immutable"):
            db.execute("DELETE FROM evidence_objects")
    assert ledger.verify().events_checked == 1


def test_changed_payload_bytes_are_detected(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    event = append(ledger)
    with sqlite3.connect(ledger.database) as db:
        db.execute("DROP TRIGGER evidence_immutable_update")
        db.execute(
            "UPDATE evidence_objects SET payload=? WHERE sha256=?",
            (b"forged payload", event.evidence_sha256),
        )
        db.execute(
            """CREATE TRIGGER evidence_immutable_update
            BEFORE UPDATE ON evidence_objects
            BEGIN SELECT RAISE(ABORT, 'evidence immutable'); END"""
        )
    with pytest.raises(EvidenceIntegrityError, match="bytes/hash"):
        ledger.verify()
    with pytest.raises(EvidenceIntegrityError):
        append(ledger, b"another event")


def test_forged_event_digest_is_detected(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    event = append(ledger)
    with sqlite3.connect(ledger.database) as db:
        db.execute("DROP TRIGGER event_immutable_update")
        db.execute(
            "UPDATE events SET digest=? WHERE sequence=1",
            ("a" * 64,),
        )
        db.execute(
            """CREATE TRIGGER event_immutable_update
            BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT, 'events immutable'); END"""
        )
    with pytest.raises(EvidenceIntegrityError, match="digest mismatch"):
        ledger.verify(expected_head=event.digest)


def test_missing_immutability_trigger_blocks_verification(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    append(ledger)
    with sqlite3.connect(ledger.database) as db:
        db.execute("DROP TRIGGER event_immutable_delete")
    with pytest.raises(EvidenceIntegrityError, match="trigger"):
        ledger.verify()


@pytest.mark.parametrize(
    ("trigger", "table", "operation"),
    [
        ("event_immutable_update", "events", "UPDATE"),
        ("evidence_immutable_delete", "evidence_objects", "DELETE"),
    ],
)
def test_counterfeit_immutable_trigger_with_same_name_is_rejected(
    tmp_path: Path, trigger: str, table: str, operation: str
) -> None:
    ledger = store(tmp_path)
    append(ledger)
    with sqlite3.connect(ledger.database) as db:
        db.execute(f"DROP TRIGGER {trigger}")
        db.execute(f"CREATE TRIGGER {trigger} BEFORE {operation} ON {table} BEGIN SELECT 1; END")
    with pytest.raises(EvidenceIntegrityError, match="schema definition changed"):
        ledger.verify()
    with pytest.raises(EvidenceIntegrityError, match="schema definition changed"):
        append(ledger, b"must not append into unprotected database")
    with pytest.raises(EvidenceIntegrityError, match="schema definition changed"):
        ledger.initialize()


def test_missing_evidence_payload_detected(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    append(ledger)
    with sqlite3.connect(ledger.database) as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("DROP TRIGGER evidence_immutable_delete")
        db.execute("DELETE FROM evidence_objects")
        db.execute(
            """CREATE TRIGGER evidence_immutable_delete
            BEFORE DELETE ON evidence_objects
            BEGIN SELECT RAISE(ABORT, 'evidence immutable'); END"""
        )
    with pytest.raises(EvidenceIntegrityError, match="orphan"):
        ledger.verify()


def test_truncated_consistent_prefix_requires_independent_checkpoint(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    a = append(ledger, b"first")
    b = append(ledger, b"second")
    with sqlite3.connect(ledger.database) as db:
        db.execute("DROP TRIGGER event_immutable_delete")
        db.execute("DROP TRIGGER evidence_immutable_delete")
        db.execute("DELETE FROM events WHERE sequence=2")
        db.execute("DELETE FROM evidence_objects WHERE sha256=?", (b.evidence_sha256,))
        db.execute(
            """CREATE TRIGGER event_immutable_delete
            BEFORE DELETE ON events
            BEGIN SELECT RAISE(ABORT, 'events immutable'); END"""
        )
        db.execute(
            """CREATE TRIGGER evidence_immutable_delete
            BEFORE DELETE ON evidence_objects
            BEGIN SELECT RAISE(ABORT, 'evidence immutable'); END"""
        )
    # Prefixes cannot be proved nontruncated using an internal hash alone.
    assert ledger.verify().head_digest == a.digest
    with pytest.raises(EvidenceIntegrityError, match="trusted head"):
        ledger.verify(expected_head=b.digest)


def test_atomicity_on_aborted_event_insert(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    existing = append(ledger, b"committed")
    with sqlite3.connect(ledger.database) as db:
        db.execute(
            """CREATE TRIGGER deliberately_abort_new_event
            BEFORE INSERT ON events
            BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END"""
        )
    with pytest.raises(sqlite3.DatabaseError, match="simulated write failure"):
        append(ledger, b"should roll back")
    assert ledger.verify(expected_head=existing.digest).events_checked == 1
    assert ledger.verify().evidence_objects_checked == 1


def test_wal_concurrent_writers_have_contiguous_chain(tmp_path: Path) -> None:
    ledger = store(tmp_path)

    def write(index: int) -> int:
        return append(SQLiteEvidenceLedger(ledger.database), f"item-{index}".encode()).sequence

    with ThreadPoolExecutor(max_workers=3) as pool:
        numbers = list(pool.map(write, range(6)))
    assert sorted(numbers) == list(range(1, 7))
    assert ledger.verify().events_checked == 6


def test_missing_database_verification_does_not_initialize(tmp_path: Path) -> None:
    path = tmp_path / "new" / "never.sqlite"
    ledger = SQLiteEvidenceLedger(path)
    assert not path.exists()
    with pytest.raises(FileNotFoundError):
        ledger.verify()
    assert not path.exists()


def test_unknown_database_version_is_rejected(tmp_path: Path) -> None:
    ledger = store(tmp_path)
    with sqlite3.connect(ledger.database) as db:
        db.execute("PRAGMA user_version=72")
    with pytest.raises(EvidenceIntegrityError, match="schema"):
        ledger.initialize()
    with pytest.raises(EvidenceIntegrityError, match="schema"):
        ledger.verify()


def test_database_path_symlinks_are_rejected(tmp_path: Path) -> None:
    target = tmp_path / "actual.sqlite"
    alias = tmp_path / "alias.sqlite"
    try:
        alias.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("host cannot create a test symlink")
    with pytest.raises(ValueError, match="symlink"):
        SQLiteEvidenceLedger(alias)


def test_existing_parent_permissions_not_mutated(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("POSIX permission test")
    folder = tmp_path / "existing"
    folder.mkdir(mode=0o755)
    before = folder.stat().st_mode & 0o777
    SQLiteEvidenceLedger(folder / "evidence.sqlite")
    assert folder.stat().st_mode & 0o777 == before


def test_event_digest_binds_metadata_and_length() -> None:
    raw = b"proof"
    values = dict(
        sequence=1,
        kind=EvidenceKind.REVIEW_DECISION,
        run_id="run",
        subject_id="DSR-001",
        evidence_sha256=sha256_bytes(raw),
        evidence_bytes=len(raw),
        recorded_at="2026-10-17T12:00:00+00:00",
        previous_digest=GENESIS_DIGEST,
    )
    first = event_digest(**values)
    assert first != event_digest(**{**values, "subject_id": "DSR-002"})
    assert first != event_digest(**{**values, "previous_digest": "f" * 64})
