"""One-audit read snapshots under many receipts and concurrent ledger appends."""

from __future__ import annotations

from pathlib import Path

import pytest

import awf.application.commands.bind_evidence as bindings
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
    KnowledgeProgress,
    KnowledgeStage,
    SourceInput,
    build_manifest,
)
from awf.domain.revision_audit import AuditSlot, AuditStatus, start_revision


def _ledger(tmp_path: Path) -> SQLiteEvidenceLedger:
    store = SQLiteEvidenceLedger(tmp_path / "evidence.sqlite")
    store.initialize()
    return store


def _inventory(store: SQLiteEvidenceLedger, *, count: int = 48):
    raw = b"".join(i.to_bytes(4, "big") for i in range(count))
    manifest = build_manifest(
        (SourceInput("source", raw, "private:synthetic"),),
        version="v1",
        expected_axes=("fidelity",),
        chunk_bytes=4,
    )
    chunks = tuple(
        record_evidenced_chunk(
            store=store,
            run_id="run-a",
            reader_ref="synthetic-reader",
            reference_id="source",
            chunk_id=chunk.chunk_id,
            chunk_bytes=raw[chunk.offset_start : chunk.offset_end],
        )
        for chunk in manifest.sources[0].chunks
    )
    axis = store.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-a",
        subject_id="axis:fidelity",
        content=b"synthetic axis observation",
    )
    return manifest, chunks, (AxisReceipt("fidelity", event_reference(axis)),)


def _count_audits(monkeypatch) -> list[int]:
    calls: list[int] = []
    original = SQLiteEvidenceLedger._audit_transaction.__func__

    def spy(cls, conn):
        calls.append(1)
        return original(cls, conn)

    monkeypatch.setattr(SQLiteEvidenceLedger, "_audit_transaction", classmethod(spy))
    return calls


def test_many_chunks_validate_with_one_full_ledger_audit(tmp_path: Path, monkeypatch):
    store = _ledger(tmp_path)
    manifest, chunks, axes = _inventory(store)
    expected_head = store.verify().head_digest
    calls = _count_audits(monkeypatch)
    assessment = verify_chunk_coverage(
        manifest, chunks, axes, store=store, run_id="run-a", expected_head=expected_head
    )
    assert assessment.complete and assessment.required_chunks == 48
    assert len(calls) == 1


def test_knowledge_read_reuses_same_audit_for_stages_and_chunks(tmp_path: Path, monkeypatch):
    store = _ledger(tmp_path)
    manifest, chunks, axes = _inventory(store, count=16)
    available = record_stage_claim(
        KnowledgeProgress("source"),
        store=store,
        stage=KnowledgeStage.AVAILABLE,
        context_ref="run-a",
    )
    read = record_stage_claim(
        available,
        store=store,
        stage=KnowledgeStage.READ,
        context_ref="run-a",
        manifest=manifest,
        chunks=chunks,
        axes=axes,
    )
    calls = _count_audits(monkeypatch)
    result = verify_progress_claims(read, store=store, manifest=manifest, chunks=chunks, axes=axes)
    assert result.local_integrity_passed and result.checked == 2
    assert len(calls) == 1


def test_multiple_audit_receipts_share_one_full_chain_check(tmp_path: Path, monkeypatch):
    store = _ledger(tmp_path)
    document = MarkdownAdapter().parse(b"Synthetic academic sentence.\n", source_name="paper.md")
    slots = tuple(AuditSlot(document.blocks[0].block_id, f"axis_{i}", 1) for i in range(8))
    state = start_revision(document, slots)
    for slot in slots:
        state = record_evidenced_audit(
            state,
            document,
            store=store,
            run_id="run-a",
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=1,
            observation_ref="synthetic",
        )
    calls = _count_audits(monkeypatch)
    result = verify_audit_receipts(state, document, store=store, run_id="run-a")
    assert result.local_integrity_passed and result.checked == 8
    assert len(calls) == 1


def test_absent_audit_receipts_remain_unverified_without_unnecessary_reader(
    tmp_path: Path, monkeypatch
):
    store = _ledger(tmp_path)
    document = MarkdownAdapter().parse(b"Text.\n", source_name="paper.md")
    slot = AuditSlot(document.blocks[0].block_id, "fidelity", 1)
    state = start_revision(document, (slot,))
    calls = _count_audits(monkeypatch)
    gate = verify_audit_receipts(state, document, store=store, run_id="run-a")
    assert not gate.local_integrity_passed and gate.unverified == (slot.key,)
    assert not calls


def test_verified_reader_keeps_snapshot_consistent_through_concurrent_append(tmp_path: Path):
    store = _ledger(tmp_path)
    first = store.append(
        kind=EvidenceKind.SOURCE_CHUNK,
        run_id="run-a",
        subject_id="source:C0001",
        content=b"first",
    )
    pinned_head = store.verify().head_digest
    with store.verified_read(expected_head=pinned_head) as reader:
        assert reader.resolve_event(event_digest=first.digest)[1] == b"first"
        later = store.append(
            kind=EvidenceKind.SOURCE_CHUNK,
            run_id="run-a",
            subject_id="source:C0002",
            content=b"second",
        )
        assert reader.resolve_event(event_digest=first.digest)[1] == b"first"
        with pytest.raises(EvidenceIntegrityError, match="unknown evidence"):
            reader.resolve_event(event_digest=later.digest)
        with pytest.raises(EvidenceIntegrityError, match="trusted head"):
            reader.resolve_event(event_digest=first.digest, expected_head="f" * 64)
    assert store.verify().events_checked == 2
    with pytest.raises(EvidenceIntegrityError, match="trusted head"):
        with store.verified_read(expected_head=pinned_head):
            pytest.fail("outdated checkpoint must never authorize a new snapshot")


def test_progress_gate_does_not_mix_heads_when_writer_appends_mid_check(
    tmp_path: Path, monkeypatch
):
    store = _ledger(tmp_path)
    manifest, chunks, axes = _inventory(store, count=8)
    available = record_stage_claim(
        KnowledgeProgress("source"),
        store=store,
        stage=KnowledgeStage.AVAILABLE,
        context_ref="run-a",
    )
    read = record_stage_claim(
        available,
        store=store,
        stage=KnowledgeStage.READ,
        context_ref="run-a",
        manifest=manifest,
        chunks=chunks,
        axes=axes,
    )
    pinned_head = store.verify().head_digest
    original = bindings._get_event
    injected = False

    def interleaved(*args, **kwargs):
        nonlocal injected
        raw = original(*args, **kwargs)
        if not injected:
            injected = True
            store.append(
                kind=EvidenceKind.SOURCE_CHUNK,
                run_id="run-a",
                subject_id="later",
                content=b"later event during a verified read",
            )
        return raw

    monkeypatch.setattr(bindings, "_get_event", interleaved)
    gate = verify_progress_claims(
        read,
        store=store,
        manifest=manifest,
        chunks=chunks,
        axes=axes,
        expected_head=pinned_head,
    )
    assert injected and gate.local_integrity_passed
    assert store.verify().events_checked == 12
    assert not verify_progress_claims(
        read,
        store=store,
        manifest=manifest,
        chunks=chunks,
        axes=axes,
        expected_head=pinned_head,
    ).local_integrity_passed


def test_corrupted_schema_never_grants_verified_read(tmp_path: Path):
    import sqlite3

    store = _ledger(tmp_path)
    first = store.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-a",
        subject_id="subject",
        content=b"synthetic",
    )
    with sqlite3.connect(store.database) as conn:
        conn.execute("DROP TRIGGER event_immutable_delete")
    with pytest.raises(EvidenceIntegrityError, match="trigger"):
        with store.verified_read() as reader:
            reader.resolve_event(event_digest=first.digest)
