"""Bounded atomic evidence batches, including failures, races and manifest binding."""

from __future__ import annotations

import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.application.commands.bind_evidence import (
    ObservedChunk,
    record_evidenced_chunks,
    verify_chunk_coverage,
)
from awf.domain.evidence import (
    GENESIS_DIGEST,
    MAX_BATCH_BYTES,
    MAX_BATCH_EVENTS,
    EvidenceAppend,
    EvidenceIntegrityError,
    EvidenceKind,
    sha256_bytes,
)
from awf.domain.knowledge_integrity import AxisReceipt, SourceInput, build_manifest


def _store(tmp_path: Path) -> SQLiteEvidenceLedger:
    store = SQLiteEvidenceLedger(tmp_path / "evidence.sqlite")
    store.initialize()
    return store


def _entry(index: int, content: bytes | None = None) -> EvidenceAppend:
    return EvidenceAppend(
        EvidenceKind.SOURCE_CHUNK,
        "batch-run",
        f"source:C{index:04d}",
        content if content is not None else f"synthetic-{index}".encode(),
    )


def test_atomic_batch_has_contiguous_order_reuses_content_and_one_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    original = SQLiteEvidenceLedger._audit_transaction.__func__
    calls: list[int] = []

    def counted(cls, conn):
        calls.append(1)
        return original(cls, conn)

    monkeypatch.setattr(SQLiteEvidenceLedger, "_audit_transaction", classmethod(counted))
    records = store.append_batch(
        entries=(_entry(1, b"equal"), _entry(2, b"equal"), _entry(3, b"different")),
        expected_head=GENESIS_DIGEST,
    )
    assert len(calls) == 1
    assert [record.sequence for record in records] == [1, 2, 3]
    assert [record.previous_digest for record in records] == [
        GENESIS_DIGEST,
        records[0].digest,
        records[1].digest,
    ]
    assert records[0].evidence_sha256 == records[1].evidence_sha256
    report = store.verify(expected_head=records[-1].digest)
    assert (report.events_checked, report.evidence_objects_checked) == (3, 2)


def test_empty_oversized_and_bad_middle_metadata_leave_no_events(tmp_path: Path) -> None:
    store = _store(tmp_path)
    invalid_batches = (
        (),
        tuple(_entry(n) for n in range(MAX_BATCH_EVENTS + 1)),
        (_entry(1), EvidenceAppend(EvidenceKind.SOURCE_CHUNK, "bad run", "chunk", b"ok")),
        (_entry(1), _entry(2, b"")),
        (_entry(1), EvidenceAppend(EvidenceKind.SOURCE_CHUNK, "run", "chunk", b"x" * 524289)),
        (_entry(1), _entry(2, b"x" * (MAX_BATCH_BYTES + 1))),
    )
    for entries in invalid_batches:
        with pytest.raises(ValueError):
            store.append_batch(entries=entries)
    assert store.verify(expected_head=GENESIS_DIGEST).events_checked == 0


def test_stale_or_malformed_head_rejects_entire_batch(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.append_batch(entries=(_entry(1),), expected_head=GENESIS_DIGEST)[0]
    for head in (GENESIS_DIGEST, "x" * 64):
        with pytest.raises(EvidenceIntegrityError if head == GENESIS_DIGEST else ValueError):
            store.append_batch(entries=(_entry(2), _entry(3)), expected_head=head)
    assert store.verify(expected_head=first.digest).events_checked == 1


def test_middle_insert_failure_and_exception_roll_back_every_object(
    tmp_path: Path, monkeypatch
) -> None:
    store = _store(tmp_path)
    existing = store.append_batch(entries=(_entry(1),))[0]
    with sqlite3.connect(store.database) as conn:
        conn.execute(
            """CREATE TRIGGER abort_third BEFORE INSERT ON events
            WHEN NEW.sequence=3 BEGIN SELECT RAISE(ABORT, 'injected insert failure'); END"""
        )
    with pytest.raises(sqlite3.DatabaseError, match="injected insert failure"):
        store.append_batch(entries=(_entry(2), _entry(3)))
    assert store.verify(expected_head=existing.digest).evidence_objects_checked == 1
    with sqlite3.connect(store.database) as conn:
        conn.execute("DROP TRIGGER abort_third")

    original = SQLiteEvidenceLedger._append_in_transaction
    calls = 0

    def interrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt("simulated process interruption")
        return original(*args, **kwargs)

    monkeypatch.setattr(SQLiteEvidenceLedger, "_append_in_transaction", staticmethod(interrupted))
    with pytest.raises(KeyboardInterrupt, match="interruption"):
        store.append_batch(entries=(_entry(4), _entry(5)))
    assert store.verify(expected_head=existing.digest).events_checked == 1


def test_schema_is_checked_inside_locked_write_transaction(tmp_path: Path, monkeypatch) -> None:
    store = _store(tmp_path)
    original = SQLiteEvidenceLedger._check_schema
    checks: list[bool] = []

    def inspected(conn):
        checks.append(conn.in_transaction)
        return original(conn)

    monkeypatch.setattr(SQLiteEvidenceLedger, "_check_schema", staticmethod(inspected))
    store.append_batch(entries=(_entry(1), _entry(2)))
    assert checks == [True]


def test_tampered_schema_and_prior_bytes_reject_batch(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = store.append_batch(entries=(_entry(1),))[0]
    with sqlite3.connect(store.database) as conn:
        conn.execute("DROP TRIGGER event_immutable_update")
        conn.execute(
            "CREATE TRIGGER event_immutable_update BEFORE UPDATE ON events BEGIN SELECT 1; END"
        )
    with pytest.raises(EvidenceIntegrityError, match="schema definition"):
        store.append_batch(entries=(_entry(2),))
    with sqlite3.connect(store.database) as conn:
        conn.execute("DROP TRIGGER event_immutable_update")
        conn.execute(
            """CREATE TRIGGER event_immutable_update BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT, 'events immutable'); END"""
        )
        conn.execute("DROP TRIGGER evidence_immutable_update")
        conn.execute(
            "UPDATE evidence_objects SET payload=? WHERE sha256=?",
            (b"corrupt", first.evidence_sha256),
        )
        conn.execute(
            """CREATE TRIGGER evidence_immutable_update BEFORE UPDATE ON evidence_objects
            BEGIN SELECT RAISE(ABORT, 'evidence immutable'); END"""
        )
    with pytest.raises(EvidenceIntegrityError, match="bytes/hash"):
        store.append_batch(entries=(_entry(3),))


def test_concurrent_batches_remain_indivisible(tmp_path: Path) -> None:
    store = _store(tmp_path)

    def write(index: int):
        return SQLiteEvidenceLedger(store.database).append_batch(
            entries=(_entry(index * 10), _entry(index * 10 + 1))
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        batches = list(pool.map(write, range(6)))
    assert sorted(record.sequence for pair in batches for record in pair) == list(range(1, 13))
    assert all(second.sequence == first.sequence + 1 for first, second in batches)
    assert store.verify().events_checked == 12


def test_two_writers_with_same_trusted_head_only_one_commits(tmp_path: Path) -> None:
    store = _store(tmp_path)

    def write(index: int):
        try:
            return SQLiteEvidenceLedger(store.database).append_batch(
                entries=(_entry(index), _entry(index + 10)),
                expected_head=GENESIS_DIGEST,
            )
        except EvidenceIntegrityError:
            return ()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, (1, 2)))
    assert sorted(map(len, results)) == [0, 2]
    assert store.verify().events_checked == 2


@settings(max_examples=18, deadline=None)
@given(st.lists(st.binary(min_size=1, max_size=48), min_size=1, max_size=25))
def test_property_batch_preserves_exact_event_payloads(payloads: list[bytes]):
    with tempfile.TemporaryDirectory(prefix="awf-batch-property-") as directory:
        store = _store(Path(directory))
        entries = tuple(_entry(index + 1, raw) for index, raw in enumerate(payloads))
        records = store.append_batch(entries=entries, expected_head=GENESIS_DIGEST)
        assert len(records) == len(payloads)
        assert store.verify(expected_head=records[-1].digest).evidence_objects_checked == len(
            set(payloads)
        )
        with store.verified_read(expected_head=records[-1].digest) as reader:
            for record, entry in zip(records, entries, strict=True):
                retrieved, raw = reader.resolve_event(event_digest=record.digest)
                assert retrieved.subject_id == entry.subject_id
                assert raw == entry.content


def test_manifest_bound_batch_verifies_partial_and_full_coverage(tmp_path: Path) -> None:
    store = _store(tmp_path)
    source = b"abcdefgh"
    manifest = build_manifest(
        (SourceInput("ref-1", source, "private:source"),),
        version="v1",
        expected_axes=("fidelity",),
        chunk_bytes=4,
    )
    original_head = store.verify().head_digest
    first = record_evidenced_chunks(
        store=store,
        manifest=manifest,
        observations=(ObservedChunk("ref-1", "C0001", b"abcd"),),
        run_id="run-a",
        reader_ref="reader-a",
        expected_head=original_head,
    )
    rest = record_evidenced_chunks(
        store=store,
        manifest=manifest,
        observations=(ObservedChunk("ref-1", "C0002", b"efgh"),),
        run_id="run-a",
        reader_ref="reader-a",
        expected_head=store.verify().head_digest,
    )
    axis = store.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-a",
        subject_id="axis:fidelity",
        content=b"synthetic-axis",
    )
    assert not verify_chunk_coverage(
        manifest,
        first,
        (AxisReceipt("fidelity", f"event:{axis.digest}"),),
        store=store,
        run_id="run-a",
    ).complete
    assert verify_chunk_coverage(
        manifest,
        first + rest,
        (AxisReceipt("fidelity", f"event:{axis.digest}"),),
        store=store,
        run_id="run-a",
    ).complete
    assert first[0].sha256 == sha256_bytes(b"abcd")


@pytest.mark.parametrize(
    "observations",
    [
        (ObservedChunk("ref-1", "C0001", b"abce"),),
        (ObservedChunk("ref-1", "C0003", b"abcd"),),
        (ObservedChunk("wrong", "C0001", b"abcd"),),
        (ObservedChunk("ref-1", "C0001", b"abcd"),) * 2,
        (ObservedChunk("ref-1", "C0002", b"efgh"), ObservedChunk("ref-1", "C0001", b"bad!")),
    ],
)
def test_manifest_mismatch_cannot_commit_any_chunk(tmp_path: Path, observations) -> None:
    store = _store(tmp_path)
    manifest = build_manifest(
        (SourceInput("ref-1", b"abcdefgh", "private:source"),),
        version="v1",
        expected_axes=("fidelity",),
        chunk_bytes=4,
    )
    with pytest.raises((EvidenceIntegrityError, ValueError)):
        record_evidenced_chunks(
            store=store,
            manifest=manifest,
            observations=observations,
            run_id="run-a",
            reader_ref="reader-a",
        )
    assert store.verify(expected_head=GENESIS_DIGEST).events_checked == 0
