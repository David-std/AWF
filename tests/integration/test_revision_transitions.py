"""Synthetic adverse cases for durable edit and finding operations."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

import awf.adapters.persistence.sqlite_revision as revision_adapter
from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_revision import RevisionConflictError, SQLiteRevisionJournal
from awf.application.commands.bind_evidence import audit_claim_payload
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.domain.revision_audit import (
    AuditScope,
    AuditSlot,
    AuditStatus,
    RevisionPolicy,
    RevisionVerdict,
    decision,
    record_audit,
    start_revision,
)


def doc(*, claim: str = "Claim with citation.", tail: str = "Independent limitation."):
    raw = f"# Research\n\n{claim}\n\n{tail}"
    return MarkdownAdapter().parse(raw.encode(), source_name="synthetic.md")


def setup(tmp_path: Path, *, local: bool = False, audited: bool = True):
    store = SQLiteRevisionJournal(tmp_path / "ledger.sqlite")
    store.initialize()
    original = doc()
    slot = AuditSlot(
        original.blocks[0 if local else 1].block_id,
        "sources",
        2,
        AuditScope.LOCAL_NEIGHBORS if local else AuditScope.DOCUMENT,
    )
    store.create(
        revision_id="revision-1",
        operation_id="start",
        run_id="run-1",
        document=original,
        slots=(slot,),
    )
    if audited:
        store.record_audit(
            revision_id="revision-1",
            operation_id="audit",
            run_id="run-1",
            document=original,
            expected_version=0,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=2,
            observation_ref="synthetic:review",
        )
    return store, original, slot


def edit(
    store, original, *, version: int = 1, op: str = "edit", observation: str = "synthetic:edit"
):
    revised = doc(tail="Changed limitation.")
    result = store.accept_edit(
        revision_id="revision-1",
        operation_id=op,
        run_id="run-1",
        old_document=original,
        new_document=revised,
        expected_version=version,
        policy=RevisionPolicy(),
        observation_ref=observation,
    )
    return revised, result


def open_issue(store, *, version: int = 1, op: str = "open", material: bool = True):
    return store.open_finding(
        revision_id="revision-1",
        operation_id=op,
        run_id="run-1",
        expected_version=version,
        finding_id="issue-1",
        material=material,
        observation_ref="synthetic:observation",
    )


def close_issue(store, *, version: int = 2, op: str = "close"):
    return store.resolve_finding(
        revision_id="revision-1",
        operation_id=op,
        run_id="run-1",
        expected_version=version,
        finding_id="issue-1",
        observation_ref="synthetic:resolution",
    )


def test_edit_invalidates_document_audit_and_recovers(tmp_path: Path) -> None:
    store, original, slot = setup(tmp_path)
    revised, result = edit(store, original)
    assert result.version == 2 and result.state.artifact_sha256 == revised.sha256
    assert result.state.receipts == () and result.state.dirty_keys == {slot.key}
    assert decision(result.state, revised) == RevisionVerdict.AUDIT_REQUIRED
    assert (
        SQLiteRevisionJournal(store.ledger.database)
        .load(revision_id="revision-1", expected_head=store.ledger.verify().head_digest)
        .state
        == result.state
    )
    assert store.ledger.verify().events_checked == 5


def test_local_scope_carries_only_unchanged_dependencies(tmp_path: Path) -> None:
    store, original, _ = setup(tmp_path, local=True)
    revised, result = edit(store, original)
    assert result.state.receipts[0].carried_from == original.sha256
    assert result.state.dirty_keys == frozenset()
    assert decision(result.state, revised) == RevisionVerdict.FRESH_CRITIC_REQUIRED
    assert store.load(revision_id="revision-1").state == result.state


def test_changed_neighbor_invalidates_local_receipt(tmp_path: Path) -> None:
    store, original, slot = setup(tmp_path, local=True)
    changed = doc(claim="Changed claim with citation.")
    result = store.accept_edit(
        revision_id="revision-1",
        operation_id="neighbor",
        run_id="run-1",
        old_document=original,
        new_document=changed,
        expected_version=1,
        policy=RevisionPolicy(),
        observation_ref="synthetic:neighbor",
    )
    assert result.state.receipts == () and result.state.dirty_keys == {slot.key}


def test_findings_survive_edit_and_require_explicit_resolution(tmp_path: Path) -> None:
    store, original, _ = setup(tmp_path)
    opened = open_issue(store)
    assert opened.state.findings[0].status == "OPEN"
    assert decision(opened.state, original) == RevisionVerdict.EDIT_REVIEW_REQUIRED
    revised, changed = edit(store, original, version=2)
    assert changed.state.findings == opened.state.findings
    assert decision(changed.state, revised) == RevisionVerdict.AUDIT_REQUIRED
    resolved = close_issue(store, version=3)
    assert resolved.state.findings[0].status == "RESOLVED"
    assert resolved.state.findings[0].evidence_ref == opened.state.findings[0].evidence_ref
    assert resolved.state.findings[0].resolution_evidence_ref.startswith("event:")
    assert store.load(revision_id="revision-1").state == resolved.state
    assert store.ledger.verify().events_checked == 9


def test_recovered_audit_after_edit_checks_current_artifact(tmp_path: Path) -> None:
    store, original, slot = setup(tmp_path)
    revised, _ = edit(store, original)
    result = store.record_audit(
        revision_id="revision-1",
        operation_id="audit-revised",
        run_id="run-1",
        document=revised,
        expected_version=2,
        slot_key=slot.key,
        status=AuditStatus.CLEAN,
        checks_executed=2,
        observation_ref="synthetic:updated",
    )
    assert result.state.dirty_keys == frozenset()
    assert store.load(revision_id="revision-1").state == result.state
    with pytest.raises(ValueError, match="bound"):
        store.record_audit(
            revision_id="revision-1",
            operation_id="audit-stale",
            run_id="run-1",
            document=original,
            expected_version=3,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=2,
            observation_ref="synthetic:stale",
        )
    assert store.ledger.verify().events_checked == 7


def test_intent_is_event_bound_to_run_and_operation(tmp_path: Path) -> None:
    store, _, _ = setup(tmp_path, audited=False)
    opened = open_issue(store, version=0)
    digest = opened.state.findings[0].evidence_ref.removeprefix("event:")
    event, raw = store.ledger.resolve_event(event_digest=digest)
    assert event.kind == EvidenceKind.REVISION_TRANSITION
    assert (event.run_id, event.subject_id) == ("run-1", "revision-1")
    assert json.loads(raw)["operation_kind"] == "FINDING_OPEN"


def test_recovery_rejects_audit_event_from_before_revision_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = SQLiteRevisionJournal(tmp_path / "ledger.sqlite")
    store.initialize()
    manuscript = doc()
    slot = AuditSlot(manuscript.blocks[1].block_id, "sources", 2)
    provisional = record_audit(
        start_revision(manuscript, (slot,)),
        manuscript,
        slot_key=slot.key,
        status=AuditStatus.CLEAN,
        checks_executed=2,
        evidence_ref="uncommitted-observation",
    )
    old_receipt_event = store.ledger.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-1",
        subject_id=slot.key,
        content=audit_claim_payload(provisional.receipts[0], observation_ref="synthetic:pre-start"),
    )
    store.create(
        revision_id="revision-1",
        operation_id="start",
        run_id="run-1",
        document=manuscript,
        slots=(slot,),
    )
    original_append = store.ledger._append_in_transaction

    def incorrectly_reuse_prior_event(conn, report, *, kind, run_id, subject_id, content):
        if kind == EvidenceKind.AUDIT_RECEIPT:
            return old_receipt_event
        return original_append(
            conn,
            report,
            kind=kind,
            run_id=run_id,
            subject_id=subject_id,
            content=content,
        )

    with monkeypatch.context() as patch:
        patch.setattr(store.ledger, "_append_in_transaction", incorrectly_reuse_prior_event)
        # A buggy orchestration path might also preserve the current head
        # instead of counting a new audit event that was never written.
        patch.setattr(revision_adapter, "_after_event", lambda report, _digest: report)
        store.record_audit(
            revision_id="revision-1",
            operation_id="audit",
            run_id="run-1",
            document=manuscript,
            expected_version=0,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=2,
            observation_ref="synthetic:pre-start",
        )
    # All bytes, event identities, state hashes and schema objects are sound;
    # only the temporal relationship between receipt and revision is false.
    assert store.ledger.verify().events_checked == 3
    with pytest.raises(EvidenceIntegrityError, match="audit event order"):
        store.load(revision_id="revision-1")


def test_retry_old_snapshot_and_changed_request_conflicts(tmp_path: Path) -> None:
    store, _, _ = setup(tmp_path, audited=False)
    first = open_issue(store, version=0)
    close_issue(store, version=1)
    replay = open_issue(SQLiteRevisionJournal(store.ledger.database), version=0)
    assert replay.replayed and replay.state == first.state and replay.version == 1
    assert store.load(revision_id="revision-1").version == 2
    with pytest.raises(RevisionConflictError, match="different input"):
        open_issue(store, version=0, material=False)
    assert store.ledger.verify().events_checked == 5


def test_edit_retry_and_stale_writer(tmp_path: Path) -> None:
    store, original, _ = setup(tmp_path, audited=False)
    edit(store, original, version=0)
    assert edit(store, original, version=0)[1].replayed
    with pytest.raises(RevisionConflictError, match="different input"):
        edit(store, original, version=0, observation="synthetic:other")
    with pytest.raises(RevisionConflictError, match="stale"):
        edit(store, original, version=0, op="second")
    assert store.ledger.verify().events_checked == 3


def test_invalid_resolution_and_unchanged_edit_rollback(tmp_path: Path) -> None:
    store, original, _ = setup(tmp_path, audited=False)
    with pytest.raises(ValueError, match="only recorded OPEN"):
        close_issue(store, version=0)
    with pytest.raises(ValueError, match="changed bytes"):
        store.accept_edit(
            revision_id="revision-1",
            operation_id="unchanged",
            run_id="run-1",
            old_document=original,
            new_document=original,
            expected_version=0,
            policy=RevisionPolicy(),
            observation_ref="synthetic:same",
        )
    assert store.ledger.verify().events_checked == 1


def test_policy_budget_and_wrong_previous_document(tmp_path: Path) -> None:
    store, original, _ = setup(tmp_path, audited=False)
    revised, _ = edit(store, original, version=0)
    with pytest.raises(ValueError, match="exhausted"):
        store.accept_edit(
            revision_id="revision-1",
            operation_id="budget",
            run_id="run-1",
            old_document=revised,
            new_document=original,
            expected_version=1,
            policy=RevisionPolicy(max_revision_cycles=1),
            observation_ref="synthetic:budget",
        )
    with pytest.raises(ValueError, match="bound"):
        edit(store, original, version=1, op="wrong-original")
    assert store.ledger.verify().events_checked == 3


def test_revision_policy_rejects_nonintegers() -> None:
    with pytest.raises(ValueError, match="integers"):
        RevisionPolicy(max_revision_cycles=True)
    with pytest.raises(ValueError, match="integers"):
        RevisionPolicy(clean_sweeps_required=1.5)


def test_snapshot_error_rolls_back_intent_event(tmp_path: Path) -> None:
    store, _, _ = setup(tmp_path, audited=False)
    with sqlite3.connect(store.ledger.database) as conn:
        conn.execute(
            """CREATE TRIGGER reject_findings BEFORE INSERT ON revision_snapshots
               WHEN NEW.version=1 BEGIN SELECT RAISE(ABORT, 'forced failure'); END"""
        )
    with pytest.raises(sqlite3.DatabaseError, match="forced failure"):
        open_issue(store, version=0)
    assert store.ledger.verify().events_checked == 1
    assert store.load(revision_id="revision-1").version == 0


def test_process_exit_after_intent_does_not_commit(tmp_path: Path) -> None:
    store, _, _ = setup(tmp_path, audited=False)
    script = """
import os
from pathlib import Path
from awf.adapters.persistence.sqlite_revision import SQLiteRevisionJournal
store = SQLiteRevisionJournal(Path(__import__('sys').argv[1]))
def crash(*args, **kwargs):
    os._exit(49)
store._commit = crash
store.open_finding(revision_id='revision-1', operation_id='crashed', run_id='run-1',
    expected_version=0, finding_id='issue-1', material=True,
    observation_ref='synthetic:crash')
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    result = subprocess.run(
        [sys.executable, "-c", script, str(store.ledger.database)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 49, result.stderr
    assert store.ledger.verify().events_checked == 1
    assert store.load(revision_id="revision-1").version == 0
    assert open_issue(store, version=0, op="crashed").version == 1


def test_concurrent_findings_only_one_version_wins(tmp_path: Path) -> None:
    store, _, _ = setup(tmp_path, audited=False)

    def write(n: int) -> str:
        try:
            open_issue(SQLiteRevisionJournal(store.ledger.database), version=0, op=f"find-{n}")
        except RevisionConflictError:
            return "conflict"
        return "committed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write, (1, 2))) == ["committed", "conflict"]
    assert store.ledger.verify().events_checked == 3


def test_duplicate_finding_wrong_run_and_orphan_intent_fail(tmp_path: Path) -> None:
    store, _, _ = setup(tmp_path, audited=False)
    open_issue(store, version=0)
    with pytest.raises(ValueError, match="immutable"):
        open_issue(store, version=1, op="duplicate")
    with pytest.raises(RevisionConflictError, match="different run"):
        store.resolve_finding(
            revision_id="revision-1",
            operation_id="wrong-run",
            run_id="different-run",
            expected_version=1,
            finding_id="issue-1",
            observation_ref="synthetic",
        )
    assert store.ledger.verify().events_checked == 3
    store.ledger.append(
        kind=EvidenceKind.REVISION_TRANSITION,
        run_id="run-1",
        subject_id="revision-1",
        content=b'{"type":"revision_intent","schema":1}',
    )
    with pytest.raises(EvidenceIntegrityError, match="intent lacks"):
        store.load(revision_id="revision-1")
