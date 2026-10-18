"""End-to-end synthetic evidence bindings across revision and knowledge modules."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.application.commands.bind_evidence import (
    event_reference,
    record_evidenced_audit,
    record_evidenced_chunk,
    record_stage_claim,
    verify_audit_receipts,
    verify_chunk_coverage,
    verify_progress_claims,
)
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.domain.knowledge_integrity import (
    AxisReceipt,
    ChunkReceipt,
    KnowledgeProgress,
    KnowledgeStage,
    SourceInput,
    build_manifest,
)
from awf.domain.revision_audit import (
    AuditScope,
    AuditSlot,
    AuditStatus,
    RevisionPolicy,
    accept_edit,
    start_revision,
)


def ledger(tmp_path: Path) -> SQLiteEvidenceLedger:
    store = SQLiteEvidenceLedger(tmp_path / "private" / "evidence.sqlite")
    store.initialize()
    return store


def doc(raw: str):
    return MarkdownAdapter().parse(raw.encode("utf-8"), source_name="paper.md")


def slot_for(document, scope: AuditScope = AuditScope.DOCUMENT):
    return AuditSlot(document.blocks[0].block_id, "causal_force", 2, scope)


def test_evidenced_audit_survives_restart_with_external_head(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manuscript = doc("Causal claim with a source.")
    slot = slot_for(manuscript)
    state = start_revision(manuscript, (slot,))
    result = record_evidenced_audit(
        state, manuscript, store=store, run_id="run-1", slot_key=slot.key,
        status=AuditStatus.CLEAN, checks_executed=2,
        observation_ref="synthetic:external-judge-note",
    )
    assert state.dirty_keys == {slot.key}
    assert result.dirty_keys == frozenset()
    assert result.receipts[0].evidence_ref.startswith("event:")
    head = store.verify().head_digest
    reopened = SQLiteEvidenceLedger(store.database)
    gate = verify_audit_receipts(
        result, manuscript, store=reopened, run_id="run-1", expected_head=head,
    )
    assert gate.local_integrity_passed
    assert gate.checked == 1
    assert gate.unverified == ()
    assert gate.independent_adjudication_proven is False


def test_unbound_hash_and_wrong_run_cannot_verify_audit(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manuscript = doc("Paragraph.")
    slot = slot_for(manuscript)
    result = record_evidenced_audit(
        start_revision(manuscript, (slot,)), manuscript, store=store,
        run_id="run-a", slot_key=slot.key, status=AuditStatus.CLEAN,
        checks_executed=2, observation_ref="synthetic-observation",
    )
    original = result.receipts[0]
    tampered = replace(result, receipts=(replace(original, evidence_ref="sha256:" + "a" * 64),))
    assert not verify_audit_receipts(
        tampered, manuscript, store=store, run_id="run-a",
    ).local_integrity_passed
    assert not verify_audit_receipts(
        result, manuscript, store=store, run_id="run-b",
    ).local_integrity_passed


def test_audit_receipt_is_bound_to_slot_status_and_current_document(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manuscript = doc("Paragraph.")
    slot = slot_for(manuscript)
    state = record_evidenced_audit(
        start_revision(manuscript, (slot,)), manuscript, store=store,
        run_id="run", slot_key=slot.key, status=AuditStatus.CLEAN,
        checks_executed=2, observation_ref="synthetic-note",
    )
    altered = replace(
        state, receipts=(replace(state.receipts[0], scope_sha256="0" * 64),)
    )
    assert not verify_audit_receipts(
        altered, manuscript, store=store, run_id="run",
    ).local_integrity_passed
    extra = start_revision(manuscript, (slot, AuditSlot(slot.block_id, "sources", 1)))
    incomplete = replace(extra, receipts=state.receipts, dirty_keys=frozenset())
    report = verify_audit_receipts(incomplete, manuscript, store=store, run_id="run")
    assert not report.local_integrity_passed
    assert any("sources" in key for key in report.unverified)
    with pytest.raises(EvidenceIntegrityError, match="different artifact"):
        verify_audit_receipts(state, doc("Different."), store=store, run_id="run")


def test_local_carried_audit_validates_origin_event_and_live_scope(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    previous = doc("Paragraph one.\n\nParagraph two.\n\nParagraph three.")
    updated = doc("Paragraph one.\n\nParagraph two.\n\nParagraph three changed.")
    slot = slot_for(previous, AuditScope.LOCAL_NEIGHBORS)
    current = record_evidenced_audit(
        start_revision(previous, (slot,)), previous, store=store,
        run_id="one", slot_key=slot.key, status=AuditStatus.CLEAN,
        checks_executed=2, observation_ref="first-version-observation",
    )
    edited = accept_edit(
        current, previous, updated, policy=RevisionPolicy(),
        operation_ref="edit-third-paragraph",
    )
    assert edited.receipts[0].carried_from == previous.sha256
    assert verify_audit_receipts(
        edited, updated, store=store, run_id="one",
    ).local_integrity_passed
    assert not verify_audit_receipts(
        edited, updated, store=store, run_id="wrong",
    ).local_integrity_passed


def _source_manifest():
    return build_manifest(
        (SourceInput("ref-1", b"abcdefgh", "private:ref-1"),),
        version="v1", expected_axes=("fidelity",), chunk_bytes=4,
    )


def _source_receipts(store: SQLiteEvidenceLedger):
    chunks = (
        record_evidenced_chunk(
            store=store, run_id="session-1", reader_ref="synthetic-reader",
            reference_id="ref-1", chunk_id="C0001", chunk_bytes=b"abcd",
        ),
        record_evidenced_chunk(
            store=store, run_id="session-1", reader_ref="synthetic-reader",
            reference_id="ref-1", chunk_id="C0002", chunk_bytes=b"efgh",
        ),
    )
    axis_event = store.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="session-1", subject_id="axis:fidelity",
        content=b"synthetic axis observation",
    )
    return chunks, (AxisReceipt("fidelity", event_reference(axis_event)),)


def test_knowledge_coverage_requires_real_stored_chunks_and_axes(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manifest = _source_manifest()
    chunks, axes = _source_receipts(store)
    checkpoint = store.verify().head_digest
    result = verify_chunk_coverage(
        manifest, chunks, axes, store=store, run_id="session-1",
        expected_head=checkpoint,
    )
    assert result.complete
    assert result.accepted_chunks == 2
    assert not verify_chunk_coverage(
        manifest, chunks[:-1], axes, store=store, run_id="session-1",
    ).complete
    assert not verify_chunk_coverage(
        manifest, chunks, axes, store=store, run_id="other-session",
    ).complete


def test_swapped_event_and_forged_metadata_block_knowledge_coverage(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manifest = _source_manifest()
    chunks, axes = _source_receipts(store)
    forged = replace(chunks[0], observation_ref=chunks[1].observation_ref)
    assert not verify_chunk_coverage(
        manifest, (forged, chunks[1]), axes, store=store, run_id="session-1",
    ).complete
    bare_digest = replace(chunks[0], observation_ref=chunks[0].sha256)
    assert not verify_chunk_coverage(
        manifest, (bare_digest, chunks[1]), axes, store=store, run_id="session-1",
    ).complete
    fake_axis = (replace(axes[0], evidence_ref=chunks[0].observation_ref),)
    assert not verify_chunk_coverage(
        manifest, chunks, fake_axis, store=store, run_id="session-1",
    ).complete


def test_read_stage_requires_verified_chunks_not_invented_boolean(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manifest = _source_manifest()
    progress = record_stage_claim(
        KnowledgeProgress("ref-1"), store=store,
        stage=KnowledgeStage.AVAILABLE, context_ref="session-1",
    )
    with pytest.raises(EvidenceIntegrityError, match="canonical manifest"):
        record_stage_claim(
            progress, store=store, stage=KnowledgeStage.READ,
            context_ref="session-1",
        )
    with pytest.raises(ValueError, match="READ requires"):
        record_stage_claim(
            progress, store=store, stage=KnowledgeStage.READ,
            context_ref="session-1", manifest=manifest,
        )
    chunks, axes = _source_receipts(store)
    read = record_stage_claim(
        progress, store=store, stage=KnowledgeStage.READ,
        context_ref="session-1", manifest=manifest,
        chunks=chunks, axes=axes,
    )
    report = verify_progress_claims(
        read, store=SQLiteEvidenceLedger(store.database),
        manifest=manifest, chunks=chunks, axes=axes,
        expected_head=store.verify().head_digest,
    )
    assert report.local_integrity_passed
    assert not report.independent_adjudication_proven
    assert not verify_progress_claims(read, store=store).local_integrity_passed
    assert not verify_progress_claims(
        read, store=store, manifest=manifest, chunks=chunks[:-1], axes=axes,
    ).local_integrity_passed


def test_understanding_and_applicability_need_separate_bound_adjudications(
    tmp_path: Path,
) -> None:
    store = ledger(tmp_path)
    manifest = _source_manifest()
    chunks, axes = _source_receipts(store)
    available = record_stage_claim(
        KnowledgeProgress("ref-1"), store=store,
        stage=KnowledgeStage.AVAILABLE, context_ref="session-1",
    )
    read = record_stage_claim(
        available, store=store, stage=KnowledgeStage.READ,
        context_ref="session-1", manifest=manifest, chunks=chunks, axes=axes,
    )
    with pytest.raises(EvidenceIntegrityError, match="separately stored"):
        record_stage_claim(
            read, store=store, stage=KnowledgeStage.UNDERSTOOD,
            context_ref="session-1",
        )
    wrong = store.append(
        kind=EvidenceKind.CALIBRATION_JUDGMENT, run_id="session-1",
        subject_id="ref-other:calibration", content=b"synthetic wrong subject",
    )
    with pytest.raises(EvidenceIntegrityError, match="subject mismatch"):
        record_stage_claim(
            read, store=store, stage=KnowledgeStage.UNDERSTOOD,
            context_ref="session-1", adjudication_ref=event_reference(wrong),
        )
    calibration = store.append(
        kind=EvidenceKind.CALIBRATION_JUDGMENT, run_id="session-1",
        subject_id="ref-1:calibration", content=b"synthetic reviewed example",
    )
    understood = record_stage_claim(
        read, store=store, stage=KnowledgeStage.UNDERSTOOD,
        context_ref="session-1", adjudication_ref=event_reference(calibration),
    )
    scope = store.append(
        kind=EvidenceKind.REVIEW_DECISION, run_id="session-1",
        subject_id="ref-1:applicability", content=b"synthetic scope review",
    )
    applicable = record_stage_claim(
        understood, store=store, stage=KnowledgeStage.APPLICABLE,
        context_ref="session-1", adjudication_ref=event_reference(scope),
    )
    result = verify_progress_claims(
        applicable, store=store, manifest=manifest, chunks=chunks, axes=axes,
    )
    assert result.local_integrity_passed
    assert not result.independent_adjudication_proven
    forged = replace(
        applicable,
        claims=applicable.claims[:-1]
        + (replace(applicable.claims[-1], evidence_ref=event_reference(calibration)),),
    )
    assert not verify_progress_claims(
        forged, store=store, manifest=manifest, chunks=chunks, axes=axes,
    ).local_integrity_passed


def test_checkpoint_rejects_consistent_but_older_ledger_state(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manifest = _source_manifest()
    chunks, axes = _source_receipts(store)
    head = store.verify().head_digest
    assert verify_chunk_coverage(
        manifest, chunks, axes, store=store, run_id="session-1",
        expected_head=head,
    ).complete
    with pytest.raises(EvidenceIntegrityError, match="trusted head"):
        store.resolve_event(
            event_digest=chunks[0].observation_ref.removeprefix("event:"),
            expected_head="1" * 64,
        )
    assert not verify_chunk_coverage(
        manifest, chunks, axes, store=store, run_id="session-1",
        expected_head="1" * 64,
    ).complete


def test_corrupt_or_missing_event_fails_closed(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    with pytest.raises(EvidenceIntegrityError, match="unknown evidence"):
        store.resolve_event(event_digest="a" * 64)
    with pytest.raises(ValueError, match="lowercase"):
        store.resolve_event(event_digest="NOT-HASH")
    with pytest.raises(FileNotFoundError):
        SQLiteEvidenceLedger(tmp_path / "other.sqlite").resolve_event(
            event_digest="a" * 64,
        )


def test_failed_store_append_does_not_mutate_pure_state(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manuscript = doc("Paragraph.")
    slot = slot_for(manuscript)
    state = start_revision(manuscript, (slot,))
    import sqlite3
    with sqlite3.connect(store.database) as conn:
        conn.execute(
            "CREATE TRIGGER simulate_failure BEFORE INSERT ON events "
            "BEGIN SELECT RAISE(ABORT, 'write failed'); END"
        )
    with pytest.raises(sqlite3.DatabaseError, match="write failed"):
        record_evidenced_audit(
            state, manuscript, store=store, run_id="run",
            slot_key=slot.key, status=AuditStatus.CLEAN,
            checks_executed=2, observation_ref="synthetic",
        )
    assert len(state.receipts) == 0
    assert store.verify().events_checked == 0
