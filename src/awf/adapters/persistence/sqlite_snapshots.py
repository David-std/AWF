"""Crash-safe, create-only SQLite online backups and fresh-path restorations."""

from __future__ import annotations

import hashlib
import math
import os
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path

from awf.adapters.persistence.sqlite_revision import SQLiteRevisionJournal
from awf.application.dto import SnapshotReceipt
from awf.domain.evidence import EvidenceIntegrityError


class SQLiteSnapshotWriter:
    """Uses sqlite3.backup: never copy a live WAL database with file-copy APIs."""

    def __init__(self, source: Path, *, timeout_seconds: float = 120.0):
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or not 1 <= timeout_seconds <= 3600
        ):
            raise ValueError("SQLite snapshot transfer timeout must be between 1 and 3600 s")
        self.source = source
        self.timeout_seconds = timeout_seconds

    def create_new(
        self, *, destination: Path, expected_head: str, expected_events: int
    ) -> SnapshotReceipt:
        if (
            destination.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}
            or self.source.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}
            or destination.is_symlink()
            or destination.parent.is_symlink()
            or self.source.is_symlink()
            or self.source.parent.is_symlink()
            or not self.source.is_file()
            or destination.resolve() == self.source.resolve()
        ):
            raise ValueError("snapshot paths must be distinct SQLite files without symlinks")
        if destination.exists():
            raise FileExistsError(
                "snapshot destination already exists; existing ledgers are immutable"
            )
        if type(expected_events) is not int or expected_events < 1:
            raise EvidenceIntegrityError("snapshot event count must be positive")
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, staging_name = tempfile.mkstemp(
            prefix=f".{destination.stem}.awf-snapshot-",
            suffix=".sqlite",
            dir=destination.parent,
        )
        os.close(descriptor)
        staged = Path(staging_name)
        try:
            deadline = time.monotonic() + self.timeout_seconds

            def progress(_status: int, _remaining: int, _total: int) -> None:
                if time.monotonic() > deadline:
                    raise TimeoutError("SQLite online backup transfer exceeded deadline")

            with closing(sqlite3.connect(self.source, timeout=5)) as origin:
                # The SQLite backup API reads a coherent source snapshot under
                # concurrent writers and includes committed WAL frames.
                with closing(sqlite3.connect(staged, timeout=5)) as target:
                    origin.backup(target, pages=128, progress=progress, sleep=0.01)
            report, _revision_count = SQLiteRevisionJournal(staged).verify_all_revisions(
                expected_head=expected_head
            )
            if report.events_checked != expected_events:
                raise EvidenceIntegrityError("snapshot event count differs from signed checkpoint")
            # Close/reformat the staging DB as a single-file, non-WAL snapshot.
            with closing(sqlite3.connect(staged)) as connection:
                mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()
                if mode is None or str(mode[0]).lower() != "delete":
                    raise EvidenceIntegrityError("snapshot cannot finalize single-file journal")
            # A source or malicious backup cannot overwrite an existing target:
            # same-directory hardlink is atomic and O_EXCL-style create-only.
            with staged.open("rb+") as stream:
                file_hash = hashlib.sha256()
                bytes_checked = 0
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    file_hash.update(block)
                    bytes_checked += len(block)
                if not bytes_checked:
                    raise EvidenceIntegrityError("empty SQLite snapshot")
                os.fsync(stream.fileno())
            os.link(staged, destination)
            if os.name != "nt":
                directory_handle = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_handle)
                finally:
                    os.close(directory_handle)
            return SnapshotReceipt(
                destination=destination,
                event_count=report.events_checked,
                head_digest=report.head_digest,
                file_sha256=file_hash.hexdigest(),
            )
        finally:
            staged.unlink(missing_ok=True)
            # Only remove sidecars bearing the unguessable *staging* basename.
            for suffix in ("-wal", "-shm", "-journal"):
                Path(f"{staging_name}{suffix}").unlink(missing_ok=True)
