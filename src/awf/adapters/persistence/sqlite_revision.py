"""Atomic local revision snapshots coordinated with the existing evidence ledger.

START, AUDIT, EDIT, FINDING_OPEN and FINDING_RESOLVE are durable. Critic sweeps
and external iterations remain in memory; no journal result certifies a critic.
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
    RevisionPolicy,
    RevisionState,
    _accept_edit_scopes,
    accept_edit,
    open_finding,
    resolve_finding,
    scope_fingerprint,
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
_DURABLE_KINDS = frozenset({"EDIT", "FINDING_OPEN", "FINDING_RESOLVE"})


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


def _after_event(report: LedgerAudit, digest: str) -> LedgerAudit:
    return LedgerAudit(
        events_checked=report.events_checked + 1,
        evidence_objects_checked=report.evidence_objects_checked,
        head_digest=digest,
    )


def _revision_request(
    kind: str, revision_id: str, run_id: str, expected_version: int, details: dict[str, object]
) -> str:
    # EDIT scope digests derive from the frozen inventory inside the write lock.
    request_details = (
        {key: value for key, value in details.items() if key not in {"old_scopes", "new_scopes"}}
        if kind == "EDIT"
        else details
    )
    return _request_hash(
        {
            "operation": kind,
            "revision_id": revision_id,
            "run_id": run_id,
            "expected_version": expected_version,
            "details": request_details,
        }
    )


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
        intent_event_digests: set[str] = set()
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
                elif isinstance(body, dict) and body.get("type") == "revision_intent":
                    intent_event_digests.add(str(digest))
        if revision_event_digests != {str(row[7]) for row in rows}:
            raise EvidenceIntegrityError("committed transition lacks a matching revision snapshot")
        snapshots: list[PersistedRevision] = []
        previous_digest = GENESIS_DIGEST
        previous_run: str | None = None
        previous_state: RevisionState | None = None
        claimed_intents: set[str] = set()
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
            shared = {
                "type": "revision_commit",
                "revision_id": revision_id,
                "run_id": run_id,
                "version": version,
                "operation_id": op_id,
                "request_sha256": req_sha,
                "previous_state_sha256": prev_sha,
                "state_sha256": state_sha,
            }
            if body.get("schema") == 1:
                expected = {
                    "schema": 1,
                    **shared,
                    "audit_event_ref": body.get("audit_event_ref"),
                    "audit_slot_key": body.get("audit_slot_key"),
                }
            elif body.get("schema") == 2:
                expected = {
                    "schema": 2,
                    **shared,
                    "operation_kind": body.get("operation_kind"),
                    "intent_event_ref": body.get("intent_event_ref"),
                }
            else:
                raise EvidenceIntegrityError("unknown revision transition schema")
            if _canonical(expected) != content:
                raise EvidenceIntegrityError("revision transition differs from snapshot metadata")
            if index == 0:
                if (
                    body.get("schema") != 1
                    or expected["audit_event_ref"] is not None
                    or expected["audit_slot_key"] is not None
                    or state.receipts
                    or state.findings
                    or state.clean_sweeps
                    or state.dirty_keys != frozenset(slot.key for slot in state.slots)
                    or state.event_log != (f"START:{state.artifact_sha256}",)
                ):
                    raise EvidenceIntegrityError("invalid initial revision snapshot")
            elif body.get("schema") == 1:
                self._check_audit_link(
                    conn,
                    state,
                    str(run_id),
                    expected["audit_slot_key"],
                    expected["audit_event_ref"],
                )
            else:
                intent_ref = expected["intent_event_ref"]
                if not isinstance(intent_ref, str) or not intent_ref.startswith("event:"):
                    raise EvidenceIntegrityError("revision transition lacks its intent event")
                claimed_intents.add(intent_ref[6:])
                if previous_state is None:
                    raise EvidenceIntegrityError("revision intent cannot be initial commit")
                self._check_intent_link(
                    conn,
                    previous_state,
                    state,
                    revision_id=revision_id,
                    run_id=str(run_id),
                    operation_id=str(op_id),
                    request_sha256=str(req_sha),
                    expected_version=index - 1,
                    kind=expected["operation_kind"],
                    intent_ref=intent_ref,
                )
            snapshots.append(
                PersistedRevision(revision_id, str(run_id), version, state, str(op_id), head)
            )
            previous_digest = str(state_sha)
            previous_run = str(run_id)
            previous_state = state
        if intent_event_digests != claimed_intents:
            raise EvidenceIntegrityError("revision intent lacks a matching committed snapshot")
        return snapshots

    @staticmethod
    def _check_intent_link(
        conn: sqlite3.Connection,
        previous: RevisionState,
        state: RevisionState,
        *,
        revision_id: str,
        run_id: str,
        operation_id: str,
        request_sha256: str,
        expected_version: int,
        kind: object,
        intent_ref: str,
    ) -> None:
        if not isinstance(kind, str) or kind not in _DURABLE_KINDS:
            raise EvidenceIntegrityError("unsupported durable revision operation")
        event_kind, event_run, subject, raw = _event_payload(conn, intent_ref[6:])
        if (event_kind, event_run, subject) != (
            EvidenceKind.REVISION_TRANSITION.value,
            run_id,
            revision_id,
        ):
            raise EvidenceIntegrityError("revision intent event identity mismatch")
        try:
            body = json.loads(raw)
            if not isinstance(body, dict) or not isinstance(body.get("details"), dict):
                raise ValueError("missing revision intent details")
            details = body["details"]
            expected = {
                "schema": 1,
                "type": "revision_intent",
                "revision_id": revision_id,
                "run_id": run_id,
                "operation_id": operation_id,
                "request_sha256": request_sha256,
                "operation_kind": kind,
                "details": details,
            }
            if (
                _canonical(expected) != raw
                or _revision_request(kind, revision_id, run_id, expected_version, details)
                != request_sha256
            ):
                raise ValueError("revision intent metadata differs from recorded request")
            if kind == "EDIT":
                if set(details) != {
                    "old_sha256",
                    "new_sha256",
                    "old_ir_sha256",
                    "new_ir_sha256",
                    "policy",
                    "observation_ref",
                    "old_scopes",
                    "new_scopes",
                }:
                    raise ValueError("unknown or missing edit metadata")
                if not all(
                    isinstance(details[name], str)
                    and len(details[name]) == 64
                    and all(char in "0123456789abcdef" for char in details[name])
                    for name in ("old_sha256", "new_sha256", "old_ir_sha256", "new_ir_sha256")
                ):
                    raise ValueError("invalid edit document fingerprint")
                policy_raw = details["policy"]
                if (
                    not isinstance(policy_raw, dict)
                    or any(type(value) is not int for value in policy_raw.values())
                    or set(policy_raw)
                    != {"max_revision_cycles", "max_external_iterations", "clean_sweeps_required"}
                ):
                    raise ValueError("invalid persisted edit policy")
                old_scopes = details["old_scopes"]
                new_scopes = details["new_scopes"]
                if not isinstance(old_scopes, dict) or not isinstance(new_scopes, dict):
                    raise ValueError("invalid persisted edit scopes")
                if not all(
                    isinstance(value, str)
                    and len(value) == 64
                    and all(char in "0123456789abcdef" for char in value)
                    for value in (*old_scopes.values(), *new_scopes.values())
                ):
                    raise ValueError("invalid scope fingerprint")
                expected_state = _accept_edit_scopes(
                    previous,
                    old_sha256=details["old_sha256"],
                    new_sha256=details["new_sha256"],
                    old_scopes=old_scopes,
                    new_scopes=new_scopes,
                    policy=RevisionPolicy(**policy_raw),
                    operation_ref=intent_ref,
                )
                if (
                    not isinstance(details["observation_ref"], str)
                    or not details["observation_ref"].strip()
                ):
                    raise ValueError("missing edit observation")
            elif kind == "FINDING_OPEN":
                if set(details) != {"finding_id", "material", "observation_ref"}:
                    raise ValueError("unknown or missing finding metadata")
                if type(details["material"]) is not bool:
                    raise ValueError("material flag must be boolean")
                expected_state = open_finding(
                    previous,
                    finding_id=details["finding_id"],
                    material=details["material"],
                    evidence_ref=intent_ref,
                )
                if (
                    not isinstance(details["observation_ref"], str)
                    or not details["observation_ref"].strip()
                ):
                    raise ValueError("missing finding observation")
            else:
                if set(details) != {"finding_id", "observation_ref"}:
                    raise ValueError("unknown or missing resolution metadata")
                expected_state = resolve_finding(
                    previous,
                    finding_id=details["finding_id"],
                    resolution_evidence_ref=intent_ref,
                )
                if (
                    not isinstance(details["observation_ref"], str)
                    or not details["observation_ref"].strip()
                ):
                    raise ValueError("missing resolution observation")
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise EvidenceIntegrityError("invalid committed revision intent") from exc
        if expected_state != state:
            raise EvidenceIntegrityError(
                "recovered revision differs from committed domain transition"
            )

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
        operation_kind: str | None = None,
        intent_ref: str | None = None,
    ) -> PersistedRevision:
        raw = encode_revision_state(state)
        state_sha = sha256_bytes(raw)
        payload: dict[str, object] = {
            "type": "revision_commit",
            "revision_id": revision_id,
            "run_id": run_id,
            "version": version,
            "operation_id": operation_id,
            "request_sha256": request_sha256,
            "previous_state_sha256": previous_sha256,
            "state_sha256": state_sha,
        }
        if operation_kind is None:
            payload.update(schema=1, audit_event_ref=audit_ref, audit_slot_key=audit_slot)
        else:
            payload.update(schema=2, operation_kind=operation_kind, intent_event_ref=intent_ref)
        content = _canonical(payload)
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
            [sqlite3.Connection, LedgerAudit, RevisionState | None, str | None],
            tuple[RevisionState, LedgerAudit, str | None, str | None],
        ],
        *,
        operation_kind: str | None = None,
        details: (
            dict[str, object] | Callable[[RevisionState | None], dict[str, object]] | None
        ) = None,
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
                intent_ref: str | None = None
                if operation_kind is not None:
                    if operation_kind not in _DURABLE_KINDS or details is None:
                        raise ValueError("unsupported durable revision intent")
                    intent_details = (
                        details(last.state if last is not None else None)
                        if callable(details)
                        else details
                    )
                    if (
                        _revision_request(
                            operation_kind, revision_id, run_id, expected_version, intent_details
                        )
                        != request_sha256
                    ):
                        raise EvidenceIntegrityError(
                            "durable intent differs from request fingerprint"
                        )
                    intent = self.ledger._append_in_transaction(
                        conn,
                        report,
                        kind=EvidenceKind.REVISION_TRANSITION,
                        run_id=run_id,
                        subject_id=revision_id,
                        content=_canonical(
                            {
                                "schema": 1,
                                "type": "revision_intent",
                                "revision_id": revision_id,
                                "run_id": run_id,
                                "operation_id": operation_id,
                                "request_sha256": request_sha256,
                                "operation_kind": operation_kind,
                                "details": intent_details,
                            }
                        ),
                    )
                    intent_ref = event_reference(intent)
                    report = _after_event(report, intent.digest)
                state, updated_report, audit_ref, audit_slot = build(
                    conn, report, last.state if last is not None else None, intent_ref
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
                    operation_kind=operation_kind,
                    intent_ref=intent_ref,
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
            _conn: sqlite3.Connection,
            report: LedgerAudit,
            previous: RevisionState | None,
            _intent_ref: str | None,
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
            conn: sqlite3.Connection,
            report: LedgerAudit,
            previous: RevisionState | None,
            _intent_ref: str | None,
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
            next_report = _after_event(report, event.digest)
            return next_state, next_report, ref, slot_key

        return self._write(revision_id, operation_id, run_id, request_sha, expected_version, build)

    def accept_edit(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        old_document: DocumentIR,
        new_document: DocumentIR,
        expected_version: int,
        policy: RevisionPolicy,
        observation_ref: str,
    ) -> PersistedRevision:
        """Atomically invalidate checks for an edited artifact; no academic approval."""
        if not observation_ref.strip():
            raise ValueError("edit requires a nonempty observation reference")
        policy_data: dict[str, object] = {
            "max_revision_cycles": policy.max_revision_cycles,
            "max_external_iterations": policy.max_external_iterations,
            "clean_sweeps_required": policy.clean_sweeps_required,
        }
        input_data: dict[str, object] = {
            "old_sha256": old_document.sha256,
            "new_sha256": new_document.sha256,
            "old_ir_sha256": sha256_bytes(_canonical(old_document.to_dict())),
            "new_ir_sha256": sha256_bytes(_canonical(new_document.to_dict())),
            "policy": policy_data,
            "observation_ref": observation_ref,
        }
        request_sha = _revision_request("EDIT", revision_id, run_id, expected_version, input_data)

        def details(previous: RevisionState | None) -> dict[str, object]:
            if previous is None:
                raise RevisionConflictError("revision must exist before editing")
            return {
                **input_data,
                "old_scopes": {
                    slot.key: scope_fingerprint(old_document, slot) for slot in previous.slots
                },
                "new_scopes": {
                    slot.key: scope_fingerprint(new_document, slot) for slot in previous.slots
                },
            }

        def build(
            _conn: sqlite3.Connection,
            report: LedgerAudit,
            previous: RevisionState | None,
            intent_ref: str | None,
        ) -> tuple[RevisionState, LedgerAudit, str | None, str | None]:
            if previous is None or intent_ref is None:
                raise RevisionConflictError("revision must exist before editing")
            return (
                accept_edit(
                    previous,
                    old_document,
                    new_document,
                    policy=policy,
                    operation_ref=intent_ref,
                ),
                report,
                None,
                None,
            )

        return self._write(
            revision_id,
            operation_id,
            run_id,
            request_sha,
            expected_version,
            build,
            operation_kind="EDIT",
            details=details,
        )

    def open_finding(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        expected_version: int,
        finding_id: str,
        material: bool,
        observation_ref: str,
    ) -> PersistedRevision:
        """Persist a finding and event-bound local observation in one transaction."""
        if type(material) is not bool or not observation_ref.strip():
            raise ValueError("finding requires a boolean material flag and an observation")
        details: dict[str, object] = {
            "finding_id": finding_id,
            "material": material,
            "observation_ref": observation_ref,
        }
        request_sha = _revision_request(
            "FINDING_OPEN", revision_id, run_id, expected_version, details
        )

        def build(
            _conn: sqlite3.Connection,
            report: LedgerAudit,
            previous: RevisionState | None,
            intent_ref: str | None,
        ) -> tuple[RevisionState, LedgerAudit, str | None, str | None]:
            if previous is None or intent_ref is None:
                raise RevisionConflictError("revision must exist before recording a finding")
            return (
                open_finding(
                    previous,
                    finding_id=finding_id,
                    material=material,
                    evidence_ref=intent_ref,
                ),
                report,
                None,
                None,
            )

        return self._write(
            revision_id,
            operation_id,
            run_id,
            request_sha,
            expected_version,
            build,
            operation_kind="FINDING_OPEN",
            details=details,
        )

    def resolve_finding(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        expected_version: int,
        finding_id: str,
        observation_ref: str,
    ) -> PersistedRevision:
        """Resolve an existing OPEN finding, retaining its original event reference."""
        if not observation_ref.strip():
            raise ValueError("finding resolution requires an observation")
        details: dict[str, object] = {"finding_id": finding_id, "observation_ref": observation_ref}
        request_sha = _revision_request(
            "FINDING_RESOLVE", revision_id, run_id, expected_version, details
        )

        def build(
            _conn: sqlite3.Connection,
            report: LedgerAudit,
            previous: RevisionState | None,
            intent_ref: str | None,
        ) -> tuple[RevisionState, LedgerAudit, str | None, str | None]:
            if previous is None or intent_ref is None:
                raise RevisionConflictError("revision must exist before resolving a finding")
            return (
                resolve_finding(
                    previous,
                    finding_id=finding_id,
                    resolution_evidence_ref=intent_ref,
                ),
                report,
                None,
                None,
            )

        return self._write(
            revision_id,
            operation_id,
            run_id,
            request_sha,
            expected_version,
            build,
            operation_kind="FINDING_RESOLVE",
            details=details,
        )
