"""Private transactional evidence ledger: SQLite WAL + content-addressed bytes.

The ledger detects corruption, missing objects and modified history. A party
with complete local database write access could replace the entire chain;
independent attestation/remote anchors are intentionally OUT OF SCOPE.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from awf.domain.evidence import (
    GENESIS_DIGEST,
    EvidenceIntegrityError,
    EvidenceKind,
    EvidenceRecord,
    LedgerAudit,
    event_digest,
    sha256_bytes,
    validate_metadata,
)

_SCHEMA_VERSION = 1
_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_objects (
    sha256 TEXT PRIMARY KEY NOT NULL,
    byte_length INTEGER NOT NULL CHECK (byte_length > 0),
    payload BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY NOT NULL,
    kind TEXT NOT NULL,
    run_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL REFERENCES evidence_objects(sha256),
    evidence_bytes INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    previous_digest TEXT NOT NULL,
    digest TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS evidence_immutable_update
BEFORE UPDATE ON evidence_objects BEGIN SELECT RAISE(ABORT, 'evidence immutable'); END;
CREATE TRIGGER IF NOT EXISTS evidence_immutable_delete
BEFORE DELETE ON evidence_objects BEGIN SELECT RAISE(ABORT, 'evidence immutable'); END;
CREATE TRIGGER IF NOT EXISTS event_immutable_update
BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events immutable'); END;
CREATE TRIGGER IF NOT EXISTS event_immutable_delete
BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events immutable'); END;
"""
_TRIGGERS = frozenset(
    {
        "evidence_immutable_update",
        "evidence_immutable_delete",
        "event_immutable_update",
        "event_immutable_delete",
    }
)
_COLUMNS = (
    "sequence, kind, run_id, subject_id, evidence_sha256, evidence_bytes, "
    "recorded_at, previous_digest, digest"
)


class SQLiteEvidenceLedger:
    """Local-first ledger; append and verify operations are synchronous and bounded."""

    def __init__(self, database: Path):
        self.database = database
        if database.is_symlink() or database.parent.is_symlink():
            raise ValueError("symlinked evidence database paths are not accepted")
        if database.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}:
            raise ValueError("use a dedicated SQLite database file")
        parent_existed = self.database.parent.exists()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt" and not parent_existed:
            os.chmod(self.database.parent, 0o700)

    @contextmanager
    def _open(self) -> Iterator[sqlite3.Connection]:
        if self.database.is_symlink():
            raise ValueError("symlinked evidence database paths are not accepted")
        connection = sqlite3.connect(self.database, isolation_level=None, timeout=5)
        try:
            connection.execute("PRAGMA busy_timeout=5000")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            if os.name != "nt":
                os.chmod(self.database, 0o600)
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the schema once; reject unexpected versions and missing triggers."""
        with self._open() as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version not in (0, _SCHEMA_VERSION):
                raise EvidenceIntegrityError("unsupported evidence database schema")
            if version == 0:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    # executescript commits pending transactions: split safe constant DDL.
                    for statement in _SCHEMA.strip().split(";\n"):
                        statement = statement.strip().rstrip(";")
                        if statement:
                            connection.execute(statement)
                    connection.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
                    connection.execute("COMMIT")
                except (sqlite3.Error, ValueError):
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
                    raise
            self._check_schema(connection)

    @staticmethod
    def _check_schema(connection: sqlite3.Connection) -> None:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version != _SCHEMA_VERSION:
            raise EvidenceIntegrityError("database has unsupported schema version")
        triggers = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
        if not _TRIGGERS.issubset(triggers):
            raise EvidenceIntegrityError("immutable trigger contract missing")
        status = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        if status != "ok":
            raise EvidenceIntegrityError("SQLite quick_check failed")

    @staticmethod
    def _row_to_record(row: tuple[object, ...]) -> EvidenceRecord:
        if len(row) != 9:
            raise EvidenceIntegrityError("invalid evidence event field count")
        (
            sequence,
            raw_kind,
            run_id,
            subject_id,
            evidence_sha256,
            evidence_bytes,
            recorded_at,
            previous_digest,
            digest,
        ) = row
        if (
            not isinstance(sequence, int)
            or not isinstance(evidence_bytes, int)
            or not all(
                isinstance(value, str)
                for value in (
                    raw_kind,
                    run_id,
                    subject_id,
                    evidence_sha256,
                    recorded_at,
                    previous_digest,
                    digest,
                )
            )
        ):
            raise EvidenceIntegrityError("invalid evidence event field types")
        try:
            return EvidenceRecord(
                sequence=sequence,
                kind=EvidenceKind(str(raw_kind)),
                run_id=str(run_id),
                subject_id=str(subject_id),
                evidence_sha256=str(evidence_sha256),
                evidence_bytes=evidence_bytes,
                recorded_at=str(recorded_at),
                previous_digest=str(previous_digest),
                digest=str(digest),
            )
        except ValueError as exc:
            raise EvidenceIntegrityError("invalid evidence event record") from exc

    @classmethod
    def _audit_transaction(cls, connection: sqlite3.Connection) -> LedgerAudit:
        status = connection.execute("PRAGMA foreign_key_check").fetchall()
        if status:
            raise EvidenceIntegrityError("orphan evidence reference detected")
        previous = GENESIS_DIGEST
        seq = 0
        expected_objects: set[str] = set()
        for row in connection.execute(f"SELECT {_COLUMNS} FROM events ORDER BY sequence ASC"):
            record = cls._row_to_record(row)
            seq += 1
            if record.sequence != seq or record.previous_digest != previous:
                raise EvidenceIntegrityError("evidence sequence gap or broken previous digest")
            try:
                expected_digest = event_digest(
                    sequence=record.sequence,
                    kind=record.kind,
                    run_id=record.run_id,
                    subject_id=record.subject_id,
                    evidence_sha256=record.evidence_sha256,
                    evidence_bytes=record.evidence_bytes,
                    recorded_at=record.recorded_at,
                    previous_digest=record.previous_digest,
                )
            except ValueError as exc:
                raise EvidenceIntegrityError("invalid evidence event fields") from exc
            if expected_digest != record.digest:
                raise EvidenceIntegrityError("event digest mismatch")
            expected_objects.add(record.evidence_sha256)
            previous = record.digest
        objects_checked = 0
        found_objects: set[str] = set()
        for digest, byte_length, raw in connection.execute(
            "SELECT sha256, byte_length, payload FROM evidence_objects"
        ):
            objects_checked += 1
            if not isinstance(raw, bytes):
                raise EvidenceIntegrityError("malformed evidence object payload")
            if sha256_bytes(raw) != digest or len(raw) != byte_length:
                raise EvidenceIntegrityError("evidence bytes/hash mismatch")
            found_objects.add(str(digest))
        if expected_objects != found_objects:
            raise EvidenceIntegrityError("missing or unreferenced evidence payload")
        return LedgerAudit(
            events_checked=seq,
            evidence_objects_checked=objects_checked,
            head_digest=previous,
        )

    def verify(self, *, expected_head: str | None = None) -> LedgerAudit:
        """Audit entire store; a trusted external checkpoint detects truncation."""
        if not self.database.is_file():
            raise FileNotFoundError("evidence ledger does not exist")
        with self._open() as conn:
            self._check_schema(conn)
            conn.execute("BEGIN")
            try:
                report = self._audit_transaction(conn)
                if expected_head is not None and expected_head != report.head_digest:
                    raise EvidenceIntegrityError("trusted head digest does not match ledger")
                conn.execute("COMMIT")
                return report
            except (sqlite3.Error, EvidenceIntegrityError):
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def append(
        self, *, kind: EvidenceKind, run_id: str, subject_id: str, content: bytes
    ) -> EvidenceRecord:
        """Atomically store content bytes and one chain event; reject corrupt histories."""
        validate_metadata(kind, run_id, subject_id, len(content))
        digest = sha256_bytes(content)
        with self._open() as conn:
            self._check_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                report = self._audit_transaction(conn)
                old = conn.execute(
                    "SELECT byte_length, payload FROM evidence_objects WHERE sha256=?", (digest,)
                ).fetchone()
                if old is None:
                    conn.execute(
                        "INSERT INTO evidence_objects(sha256, byte_length, payload) VALUES(?,?,?)",
                        (digest, len(content), sqlite3.Binary(content)),
                    )
                elif int(old[0]) != len(content) or old[1] != content:
                    raise EvidenceIntegrityError("content-addressed object collision or corruption")
                sequence = report.events_checked + 1
                time_stamp = datetime.now(UTC).isoformat()
                row_digest = event_digest(
                    sequence=sequence,
                    kind=kind,
                    run_id=run_id,
                    subject_id=subject_id,
                    evidence_sha256=digest,
                    evidence_bytes=len(content),
                    recorded_at=time_stamp,
                    previous_digest=report.head_digest,
                )
                conn.execute(
                    f"INSERT INTO events({_COLUMNS}) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        sequence,
                        kind.value,
                        run_id,
                        subject_id,
                        digest,
                        len(content),
                        time_stamp,
                        report.head_digest,
                        row_digest,
                    ),
                )
                conn.execute("COMMIT")
                return EvidenceRecord(
                    sequence,
                    kind,
                    run_id,
                    subject_id,
                    digest,
                    len(content),
                    time_stamp,
                    report.head_digest,
                    row_digest,
                )
            except (sqlite3.Error, ValueError):
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise

    def retrieve(self, evidence_sha256: str) -> bytes:
        """Retrieve only verified content. Requires a valid complete chain first."""
        if not self.database.is_file():
            raise FileNotFoundError("evidence ledger does not exist")
        with self._open() as conn:
            self._check_schema(conn)
            conn.execute("BEGIN")
            try:
                self._audit_transaction(conn)
                row = conn.execute(
                    "SELECT payload FROM evidence_objects WHERE sha256=?", (evidence_sha256,)
                ).fetchone()
                if row is None:
                    raise EvidenceIntegrityError("unknown evidence hash")
                raw = row[0]
                if not isinstance(raw, bytes) or sha256_bytes(raw) != evidence_sha256:
                    raise EvidenceIntegrityError("requested evidence does not match hash")
                conn.execute("COMMIT")
                return raw
            except (sqlite3.Error, EvidenceIntegrityError):
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
