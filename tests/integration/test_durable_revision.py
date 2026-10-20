"""S2 crash, replay, CAS and integrity tests with synthetic documents only."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

import awf.adapters.persistence.sqlite_revision as revision_adapter
from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.persistence.sqlite_revision import (
    RevisionConflictError,
    SQLiteRevisionJournal,
)
from awf.application.commands.bind_evidence import verify_audit_receipts
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.domain.revision_audit import AuditSlot, AuditStatus, RevisionVerdict, decision


def manuscript(text: str = "Citation and a controlled claim."):
    return MarkdownAdapter().parse(text.encode(), source_name="synthetic.md")


def journal(tmp_path: Path) -> SQLiteRevisionJournal:
    item = SQLiteRevisionJournal(tmp_path / "private" / "ledger.sqlite")
    item.initialize()
    return item


def begin(store: SQLiteRevisionJournal):
    doc = manuscript()
    slot = AuditSlot(doc.blocks[0].block_id, "attribution", 2)
    initial = store.create(
        revision_id="revision-1",
        operation_id="op-start",
        run_id="run-1",
        document=doc,
        slots=(slot,),
    )
    return doc, slot, initial


def audit(
    store: SQLiteRevisionJournal,
    *,
    operation_id: str = "op-audit",
    version: int = 0,
    observation_ref: str = "synthetic:observation",
    status: AuditStatus = AuditStatus.CLEAN,
):
    doc = manuscript()
    slot = AuditSlot(doc.blocks[0].block_id, "attribution", 2)
    return store.record_audit(
        revision_id="revision-1",
        operation_id=operation_id,
        run_id="run-1",
        document=doc,
        expected_version=version,
        slot_key=slot.key,
        status=status,
        checks_executed=2,
        observation_ref=observation_ref,
    )


def test_atomic_snapshot_evidence_and_restart(tmp_path: Path) -> None:
    store = journal(tmp_path)
    doc, slot, original = begin(store)
    assert original.version == 0
    assert original.state.dirty_keys == {slot.key}
    committed = audit(store)
    ledger = SQLiteEvidenceLedger(store.ledger.database)
    assert ledger.verify().events_checked == 3  # START, AUDIT_RECEIPT, COMMIT
    recovered = SQLiteRevisionJournal(store.ledger.database).load(
        revision_id="revision-1", expected_head=ledger.verify().head_digest
    )
    assert recovered.version == 1
    assert recovered.state == committed.state
    assert recovered.state.dirty_keys == frozenset()
    assert verify_audit_receipts(
        recovered.state, doc, store=ledger, run_id="run-1"
    ).local_integrity_passed
    assert decision(recovered.state, doc) == RevisionVerdict.FRESH_CRITIC_REQUIRED


def test_revision_write_and_recovery_validate_schema_inside_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = journal(tmp_path)
    ledger_check = SQLiteEvidenceLedger._check_schema
    revision_check = SQLiteRevisionJournal._check_schema
    observations: list[tuple[str, bool]] = []

    def watched_ledger(conn: sqlite3.Connection) -> None:
        observations.append(("ledger", conn.in_transaction))
        ledger_check(conn)

    def watched_revision(conn: sqlite3.Connection) -> None:
        observations.append(("revision", conn.in_transaction))
        revision_check(conn)

    monkeypatch.setattr(SQLiteEvidenceLedger, "_check_schema", staticmethod(watched_ledger))
    monkeypatch.setattr(SQLiteRevisionJournal, "_check_schema", staticmethod(watched_revision))
    begin(store)
    assert observations == [("ledger", True), ("revision", True)]
    observations.clear()
    store.load(revision_id="revision-1")
    assert observations == [("ledger", True), ("revision", True)]


def test_replay_after_lost_response_is_exactly_once(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)
    audit(store)  # Simulate a committed request whose response never reached the client.
    restarted = SQLiteRevisionJournal(store.ledger.database)
    replay = audit(restarted)
    assert replay.replayed
    assert replay.version == 1
    assert restarted.load(revision_id="revision-1").state == replay.state
    assert restarted.ledger.verify().events_checked == 3


def test_same_operation_key_different_input_is_rejected(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)
    audit(store)
    with pytest.raises(RevisionConflictError, match="different input"):
        audit(store, observation_ref="different-review")
    assert store.ledger.verify().events_checked == 3


def test_stale_writer_and_wrong_run_leave_no_orphan_events(tmp_path: Path) -> None:
    store = journal(tmp_path)
    doc, slot, _ = begin(store)
    audit(store)
    with pytest.raises(RevisionConflictError, match="stale"):
        audit(store, operation_id="op-other", version=0)
    with pytest.raises(RevisionConflictError, match="different run"):
        store.record_audit(
            revision_id="revision-1",
            operation_id="new-op",
            run_id="wrong-run",
            document=doc,
            expected_version=1,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=2,
            observation_ref="synthetic-other-run",
        )
    assert store.ledger.verify().events_checked == 3


def test_database_failure_after_audit_append_rolls_back_everything(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)
    with sqlite3.connect(store.ledger.database) as conn:
        conn.execute(
            """CREATE TRIGGER reject_revision_write BEFORE INSERT ON revision_snapshots
               WHEN NEW.version=1 BEGIN SELECT RAISE(ABORT, 'forced revision failure'); END"""
        )
    with pytest.raises(sqlite3.DatabaseError, match="forced revision failure"):
        audit(store)
    assert store.ledger.verify().events_checked == 1
    assert store.ledger.verify().evidence_objects_checked == 1
    assert store.load(revision_id="revision-1").version == 0


def test_process_crash_between_evidence_append_and_commit_recovers(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)
    script = """
import os
from pathlib import Path
from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_revision import SQLiteRevisionJournal
from awf.domain.revision_audit import AuditStatus
db = Path(__import__('sys').argv[1])
store = SQLiteRevisionJournal(db)
doc = MarkdownAdapter().parse(b'Citation and a controlled claim.', source_name='synthetic.md')
def crash(*args, **kwargs):
    os._exit(47)
store._commit = crash
store.record_audit(revision_id='revision-1', operation_id='crashed', run_id='run-1',
    document=doc, expected_version=0, slot_key=f'{doc.blocks[0].block_id}:attribution',
    status=AuditStatus.CLEAN, checks_executed=2, observation_ref='synthetic:crash')
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    process = subprocess.run(
        [sys.executable, "-c", script, str(store.ledger.database)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert process.returncode == 47, process.stderr
    reopened = SQLiteRevisionJournal(store.ledger.database)
    assert reopened.ledger.verify().events_checked == 1
    assert reopened.load(revision_id="revision-1").version == 0
    assert audit(reopened).version == 1


def test_concurrent_writers_only_one_version_wins(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)

    def write(n: int) -> str:
        try:
            audit(SQLiteRevisionJournal(store.ledger.database), operation_id=f"audit-{n}")
        except RevisionConflictError:
            return "stale"
        return "committed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write, (1, 2))) == ["committed", "stale"]
    assert store.ledger.verify().events_checked == 3


def test_legacy_evidence_database_is_extended_without_deleting_events(tmp_path: Path) -> None:
    path = tmp_path / "legacy.sqlite"
    original = SQLiteEvidenceLedger(path)
    original.initialize()
    event = original.append(
        kind=EvidenceKind.SOURCE_CHUNK,
        run_id="old-run",
        subject_id="ref-1",
        content=b"unrelated synthetic evidence",
    )
    revision = SQLiteRevisionJournal(path)
    revision.initialize()
    revision.initialize()
    begin(revision)
    assert revision.ledger.verify().events_checked == 2
    assert (
        revision.ledger.resolve_event(event_digest=event.digest)[1]
        == b"unrelated synthetic evidence"
    )


def test_missing_snapshot_cannot_be_replayed_as_success(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)
    audit(store)
    with sqlite3.connect(store.ledger.database) as conn:
        conn.execute("DROP TRIGGER revision_snapshot_immutable_delete")
        conn.execute("DELETE FROM revision_snapshots WHERE version=1")
        conn.execute(
            """CREATE TRIGGER revision_snapshot_immutable_delete
               BEFORE DELETE ON revision_snapshots
               BEGIN SELECT RAISE(ABORT, 'revision snapshots immutable'); END"""
        )
    with pytest.raises(EvidenceIntegrityError, match="lacks a matching"):
        store.load(revision_id="revision-1")
    with pytest.raises(EvidenceIntegrityError):
        audit(store)


def test_tampered_snapshot_and_missing_trigger_fail_closed(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)
    with sqlite3.connect(store.ledger.database) as conn:
        conn.execute("DROP TRIGGER revision_snapshot_immutable_update")
        conn.execute("UPDATE revision_snapshots SET state_bytes=? WHERE version=0", (b"{}",))
        conn.execute(
            """CREATE TRIGGER revision_snapshot_immutable_update
               BEFORE UPDATE ON revision_snapshots
               BEGIN SELECT RAISE(ABORT, 'revision snapshots immutable'); END"""
        )
    with pytest.raises(EvidenceIntegrityError, match="hash"):
        store.load(revision_id="revision-1")
    with sqlite3.connect(store.ledger.database) as conn:
        conn.execute("DROP TRIGGER revision_snapshot_immutable_update")
    with pytest.raises(EvidenceIntegrityError, match="trigger"):
        store.initialize()


def test_same_name_noop_revision_trigger_never_counts_as_immutable(tmp_path: Path) -> None:
    store = journal(tmp_path)
    begin(store)
    with sqlite3.connect(store.ledger.database) as conn:
        conn.execute("DROP TRIGGER revision_snapshot_immutable_update")
        conn.execute(
            "CREATE TRIGGER revision_snapshot_immutable_update "
            "BEFORE UPDATE ON revision_snapshots BEGIN SELECT 1; END"
        )
    with pytest.raises(EvidenceIntegrityError, match="revision schema definition changed"):
        store.load(revision_id="revision-1")
    with pytest.raises(EvidenceIntegrityError, match="revision schema definition changed"):
        audit(store)
    with pytest.raises(EvidenceIntegrityError, match="revision schema definition changed"):
        store.initialize()


def test_recovery_rejects_unrelated_state_delta_despite_valid_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = journal(tmp_path)
    begin(store)
    original_audit = revision_adapter.apply_audit

    def unsafe_audit(*args, **kwargs):
        # Simulate a regression that increments critic iterations on a basic
        # audit: the event and snapshot remain correctly hashed and committed.
        return replace(original_audit(*args, **kwargs), external_iterations=1)

    with monkeypatch.context() as patch:
        patch.setattr(revision_adapter, "apply_audit", unsafe_audit)
        audit(store)
    assert store.ledger.verify().events_checked == 3
    with pytest.raises(EvidenceIntegrityError, match="replayed audit changed unrelated"):
        store.load(revision_id="revision-1")


def test_uncommitted_pure_state_cannot_be_loaded(tmp_path: Path) -> None:
    store = journal(tmp_path)
    doc, slot, initial = begin(store)
    forged = replace(initial.state, dirty_keys=frozenset())
    assert forged != store.load(revision_id="revision-1").state
    with pytest.raises(ValueError, match="unregistered"):
        store.record_audit(
            revision_id="revision-1",
            operation_id="bad-slot",
            run_id="run-1",
            document=doc,
            expected_version=0,
            slot_key="wrong:slot",
            status=AuditStatus.CLEAN,
            checks_executed=2,
            observation_ref="synthetic",
        )
    assert store.load(revision_id="revision-1").state.dirty_keys == {slot.key}
    assert store.ledger.verify().events_checked == 1
