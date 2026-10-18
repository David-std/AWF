"""Atomic local revision snapshots coordinated with the existing evidence ledger.

This is an intentionally narrow S2 implementation: START and AUDIT are the
only durable transitions. Findings, edits and critic sweeps have no durable
command yet and therefore cannot be recovered or certified by this adapter.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from awf.adapters.persistence.revision_codec import decode_revision_state, encode_revision_state
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.application.commands.bind_evidence import audit_claim_payload, event_reference
from awf.application.dto import PersistedRevision
from awf.domain.document import DocumentIR
from awf.domain.evidence import (
    GENESIS_DIGEST,
    EvidenceIntegrityError,
    EvidenceKind,
    LedgerAudit,
    sha256_bytes,
    validate_metadata,
)
from awf.domain.revision_audit import (
    AuditSlot,
    AuditStatus,
    RevisionState,
    start_revision,
)
from awf.domain.revision_audit import (
    record_audit as apply_audit,
)

_CREATE_TABLE = """
CREATE TABLE revision_snapshots (
    revision_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version >= 0),
    operation_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    request_sha256 TEXT NOT NULL,
    previous_state_sha256 TEXT NOT NULL,
    state_sha256 TEXT NOT NULL,
    state_bytes BLOB NOT NULL,
    transition_digest TEXT NOT NULL UNIQUE REFERENCES events(digest),
    PRIMARY KEY(revision_id, version),
    UNIQUE(revision_id, operation_id)
)
"""
_CREATE_TRIGGERS = (
    """CREATE TRIGGER revision_snapshot_immutable_update BEFORE UPDATE ON revision_snapshots
    BEGIN SELECT RAISE(ABORT, 'revision snapshots immutable'); END""",
    """CREATE TRIGGER revision_snapshot_immutable_delete BEFORE DELETE ON revision_snapshots
    BEGIN SELECT RAISE(ABORT, 'revision snapshots immutable'); END""",
)
_REVISION_TRIGGERS = {"revision_snapshot_immutable_update", "revision_snapshot_immutable_delete"}
_SELECT = (
    "version, operation_id, run_id, request_sha256, previous_state_sha256, "
    "state_sha256, state_bytes, transition_digest"
)


class RevisionConflictError(ValueError):
    """Stale optimistic version, reused operation identity or changed run."""


def _canonical(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _request_hash(payload: dict[str, object]) -> str:
    return sha256_bytes(_canonical(payload))


def _event_payload(conn: sqlite3.Connection, digest: str) -> tuple[str, str, str, bytes]:
    row = conn.execute(
        """SELECT e.kind, e.run_id, e.subject_id, o.payload
           FROM events e JOIN evidence_objects o ON e.evidence_sha256=o.sha256
           WHERE e.digest=?""",
        (digest,),
    ).fetchone()
    if row is None or not isinstance(row[3], bytes):
        raise EvidenceIntegrityError("revision references a missing evidence event")
    return str(row[0]), str(row[1]), str(row[2]), row[3]


class SQLiteRevisionJournal:
    """Read and append immutable snapshots with exactly-once operation keys.

    The ledger and snapshots MUST use the same SQLite database, not ATTACHed
    files or separate stores. An idempotency key is scoped to one revision and
    cannot be reused with different input. The return is never an academic PASS.
    """

    def __init__(self, database: Path):
        self.ledger = SQLiteEvidenceLedger(database)

    def initialize(self) -> None:
        """Extend schema v1 additively; refuse to repair a damaged revision table."""
        self.ledger.initialize()
        with self.ledger._open() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                existed = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='revision_snapshots'"
                ).fetchone()
                if existed is None:
                    conn.execute(_CREATE_TABLE)
                    for statement in _CREATE_TRIGGERS:
                        conn.execute(statement)
                self._check_schema(conn)
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    @staticmethod
    def _check_schema(conn: sqlite3.Connection) -> None:
        existing = {
            str(row[0])
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(revision_snapshots)")}
        required = {
            "revision_id",
            "version",
            "operation_id",
            "run_id",
            "request_sha256",
            "previous_state_sha256",
            "state_sha256",
            "state_bytes",
            "transition_digest",
        }
        if not _REVISION_TRIGGERS.issubset(existing) or columns != required:
            raise EvidenceIntegrityError("revision snapshot schema or immutability trigger missing")

    def _recover(
        self, conn: sqlite3.Connection, revision_id: str, head: str
    ) -> list[PersistedRevision]:
        rows = conn.execute(
            f"SELECT {_SELECT} FROM revision_snapshots WHERE revision_id=? ORDER BY version",
            (revision_id,),
        ).fetchall()
        revision_event_digests: set[str] = set()
        for digest, raw in conn.execute(
            """SELECT e.digest, o.payload FROM events e
               JOIN evidence_objects o ON e.evidence_sha256=o.sha256
               WHERE e.kind=? AND e.subject_id=?""",
            (EvidenceKind.REVISION_TRANSITION.value, revision_id),
        ):
            if isinstance(raw, bytes):
                try:
                    body = json.loads(raw)
                except (ValueError, TypeError) as exc:
                    raise EvidenceIntegrityError("malformed revision transition") from exc
                if isinstance(body, dict) and body.get("type") == "revision_commit":
                    revision_event_digests.add(str(digest))
        if revision_event_digests != {str(row[7]) for row in rows}:
            raise EvidenceIntegrityError("committed transition lacks a matching revision snapshot")
        snapshots: list[PersistedRevision] = []
        previous_digest = GENESIS_DIGEST
        previous_run: str | None = None
        for index, row in enumerate(rows):
            version, op_id, run_id, req_sha, prev_sha, state_sha, raw, transition = row
            if (
                type(version) is not int
                or version != index
                or not isinstance(raw, bytes)
                or sha256_bytes(raw) != state_sha
                or prev_sha != previous_digest
                or (previous_run is not None and run_id != previous_run)
            ):
                raise EvidenceIntegrityError("revision snapshot sequence, hash or run mismatch")
            state = decode_revision_state(raw)
            kind, event_run, event_subject, content = _event_payload(conn, str(transition))
            if (kind, event_run, event_subject) != (
                EvidenceKind.REVISION_TRANSITION.value,
                run_id,
                revision_id,
            ):
                raise EvidenceIntegrityError("revision transition event identity mismatch")
            try:
                body = json.loads(content)
            except (ValueError, TypeError) as exc:
                raise EvidenceIntegrityError("malformed revision transition") from exc
            if not isinstance(body, dict):
                raise EvidenceIntegrityError("revision transition must be an object")
            expected = {
                "schema": 1,
                "type": "revision_commit",
                "revision_id": revision_id,
                "run_id": run_id,
                "version": version,
                "operation_id": op_id,
                "request_sha256": req_sha,
                "previous_state_sha256": prev_sha,
                "state_sha256": state_sha,
                "audit_event_ref": body.get("audit_event_ref"),
                "audit_slot_key": body.get("audit_slot_key"),
            }
            if _canonical(expected) != content:
                raise EvidenceIntegrityError("revision transition differs from snapshot metadata")
            if index == 0:
                if (
                    expected["audit_event_ref"] is not None
                    or expected["audit_slot_key"] is not None
                    or state.receipts
                    or state.findings
                    or state.clean_sweeps
                    or state.dirty_keys != frozenset(slot.key for slot in state.slots)
                    or state.event_log != (f"START:{state.artifact_sha256}",)
                ):
                    raise EvidenceIntegrityError("invalid initial revision snapshot")
            else:
                self._check_audit_link(
                    conn,
                    state,
                    str(run_id),
                    expected["audit_slot_key"],
                    expected["audit_event_ref"],
                )
            snapshots.append(
                PersistedRevision(revision_id, str(run_id), version, state, str(op_id), head)
            )
            previous_digest = str(state_sha)
            previous_run = str(run_id)
        return snapshots

    @staticmethod
    def _check_audit_link(
        conn: sqlite3.Connection,
        state: RevisionState,
        run_id: str,
        slot_key: object,
        evidence_ref: object,
    ) -> None:
        if (
            not isinstance(slot_key, str)
            or not isinstance(evidence_ref, str)
            or not evidence_ref.startswith("event:")
        ):
            raise EvidenceIntegrityError("audit transition lacks its original receipt event")
        receipt = next((r for r in state.receipts if r.slot_key == slot_key), None)
        if receipt is None or receipt.evidence_ref != evidence_ref:
            raise EvidenceIntegrityError("revision state does not contain the bound audit receipt")
        kind, event_run, subject, payload = _event_payload(conn, evidence_ref[6:])
        if (kind, event_run, subject) != (EvidenceKind.AUDIT_RECEIPT.value, run_id, slot_key):
            raise EvidenceIntegrityError("audit receipt event has wrong kind, run or slot")
        try:
            claim = json.loads(payload)
        except (ValueError, TypeError) as exc:
            raise EvidenceIntegrityError("malformed stored audit receipt") from exc
        if (
            not isinstance(claim, dict)
            or not isinstance(claim.get("observation_ref"), str)
            or not claim["observation_ref"].strip()
            or audit_claim_payload(receipt, observation_ref=claim["observation_ref"]) != payload
        ):
            raise EvidenceIntegrityError("audit event payload differs from recovered receipt")

    def load(self, *, revision_id: str, expected_head: str | None = None) -> PersistedRevision:
        """Replay and verify the whole per-revision snapshot chain after a restart."""
        validate_metadata(EvidenceKind.REVISION_TRANSITION, "recovery", revision_id, 1)
        if not self.ledger.database.is_file():
            raise FileNotFoundError("revision journal does not exist")
        with self.ledger._open() as conn:
            self.ledger._check_schema(conn)
            self._check_schema(conn)
            conn.execute("BEGIN")
            try:
                report = self.ledger._audit_transaction(conn)
                if expected_head is not None and report.head_digest != expected_head:
                    raise EvidenceIntegrityError("trusted head digest does not match ledger")
                history = self._recover(conn, revision_id, report.head_digest)
                if not history:
                    raise KeyError("unknown revision identifier")
                conn.execute("COMMIT")
                return history[-1]
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def _commit(
        self,
        conn: sqlite3.Connection,
        report: LedgerAudit,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        request_sha256: str,
        previous_sha256: str,
        version: int,
        state: RevisionState,
        audit_ref: str | None = None,
        audit_slot: str | None = None,
    ) -> PersistedRevision:
        raw = encode_revision_state(state)
        state_sha = sha256_bytes(raw)
        content = _canonical(
            {
                "schema": 1,
                "type": "revision_commit",
                "revision_id": revision_id,
                "run_id": run_id,
                "version": version,
                "operation_id": operation_id,
                "request_sha256": request_sha256,
                "previous_state_sha256": previous_sha256,
                "state_sha256": state_sha,
                "audit_event_ref": audit_ref,
                "audit_slot_key": audit_slot,
            }
        )
        event = self.ledger._append_in_transaction(
            conn,
            report,
            kind=EvidenceKind.REVISION_TRANSITION,
            run_id=run_id,
            subject_id=revision_id,
            content=content,
        )
        conn.execute(
            """INSERT INTO revision_snapshots
               (revision_id, version, operation_id, run_id, request_sha256,
                previous_state_sha256, state_sha256, state_bytes, transition_digest)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                revision_id,
                version,
                operation_id,
                run_id,
                request_sha256,
                previous_sha256,
                state_sha,
                sqlite3.Binary(raw),
                event.digest,
            ),
        )
        return PersistedRevision(revision_id, run_id, version, state, operation_id, event.digest)

    def _write(
        self,
        revision_id: str,
        operation_id: str,
        run_id: str,
        request_sha256: str,
        expected_version: int,
        build: Callable[
            [sqlite3.Connection, LedgerAudit, RevisionState | None],
            tuple[RevisionState, LedgerAudit, str | None, str | None],
        ],
    ) -> PersistedRevision:
        validate_metadata(EvidenceKind.REVISION_TRANSITION, run_id, revision_id, 1)
        validate_metadata(EvidenceKind.REVISION_TRANSITION, run_id, operation_id, 1)
        with self.ledger._open() as conn:
            self.ledger._check_schema(conn)
            self._check_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                report = self.ledger._audit_transaction(conn)
                history = self._recover(conn, revision_id, report.head_digest)
                for snapshot in history:
                    if snapshot.operation_id == operation_id:
                        recorded_hash = conn.execute(
                            """SELECT request_sha256 FROM revision_snapshots
                               WHERE revision_id=? AND version=?""",
                            (revision_id, snapshot.version),
                        ).fetchone()
                        if recorded_hash is None or recorded_hash[0] != request_sha256:
                            raise RevisionConflictError("operation ID reused with different input")
                        conn.execute("COMMIT")
                        return replace(snapshot, replayed=True)
                last = history[-1] if history else None
                if (last.version if last is not None else -1) != expected_version:
                    raise RevisionConflictError("stale revision version; reload before writing")
                if last is not None and last.run_id != run_id:
                    raise RevisionConflictError("revision belongs to a different run")
                state, updated_report, audit_ref, audit_slot = build(
                    conn, report, last.state if last is not None else None
                )
                previous_sha = (
                    sha256_bytes(encode_revision_state(last.state))
                    if last is not None
                    else GENESIS_DIGEST
                )
                result = self._commit(
                    conn,
                    updated_report,
                    revision_id=revision_id,
                    operation_id=operation_id,
                    run_id=run_id,
                    request_sha256=request_sha256,
                    previous_sha256=previous_sha,
                    version=expected_version + 1,
                    state=state,
                    audit_ref=audit_ref,
                    audit_slot=audit_slot,
                )
                conn.execute("COMMIT")
                return result
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def create(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        document: DocumentIR,
        slots: tuple[AuditSlot, ...],
    ) -> PersistedRevision:
        """Create version zero; retrying the same request never appends twice."""
        initial = start_revision(document, slots)
        request_sha = _request_hash(
            {
                "operation": "START",
                "run_id": run_id,
                "revision_id": revision_id,
                "initial_state_sha256": sha256_bytes(encode_revision_state(initial)),
            }
        )

        def build(
            _conn: sqlite3.Connection, report: LedgerAudit, previous: RevisionState | None
        ) -> tuple[RevisionState, LedgerAudit, str | None, str | None]:
            if previous is not None:
                raise RevisionConflictError("revision already exists")
            return initial, report, None, None

        return self._write(revision_id, operation_id, run_id, request_sha, -1, build)

    def record_audit(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        document: DocumentIR,
        expected_version: int,
        slot_key: str,
        status: AuditStatus,
        checks_executed: int,
        observation_ref: str,
    ) -> PersistedRevision:
        """Commit audit evidence and new RevisionState in one SQLite transaction."""
        if not isinstance(status, AuditStatus):
            raise ValueError("unsupported audit disposition")
        if not observation_ref.strip():
            raise ValueError("an audit needs an observation reference")
        request_sha = _request_hash(
            {
                "operation": "AUDIT",
                "revision_id": revision_id,
                "run_id": run_id,
                "document_sha256": document.sha256,
                "expected_version": expected_version,
                "slot_key": slot_key,
                "status": status.value,
                "checks_executed": checks_executed,
                "observation_ref": observation_ref,
            }
        )

        def build(
            conn: sqlite3.Connection, report: LedgerAudit, previous: RevisionState | None
        ) -> tuple[RevisionState, LedgerAudit, str | None, str | None]:
            if previous is None:
                raise RevisionConflictError("revision must be created before auditing")
            provisional = apply_audit(
                previous,
                document,
                slot_key=slot_key,
                status=status,
                checks_executed=checks_executed,
                evidence_ref="uncommitted-observation",
            )
            receipt = next(r for r in provisional.receipts if r.slot_key == slot_key)
            event = self.ledger._append_in_transaction(
                conn,
                report,
                kind=EvidenceKind.AUDIT_RECEIPT,
                run_id=run_id,
                subject_id=slot_key,
                content=audit_claim_payload(receipt, observation_ref=observation_ref),
            )
            ref = event_reference(event)
            recorded = replace(receipt, evidence_ref=ref)
            next_state = replace(
                provisional,
                receipts=tuple(
                    recorded if r.slot_key == slot_key else r for r in provisional.receipts
                ),
            )
            next_report = LedgerAudit(
                events_checked=event.sequence,
                evidence_objects_checked=report.evidence_objects_checked,
                head_digest=event.digest,
            )
            return next_state, next_report, ref, slot_key

        return self._write(revision_id, operation_id, run_id, request_sha, expected_version, build)
