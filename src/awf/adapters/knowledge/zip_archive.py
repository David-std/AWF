"""Strict local ZIP adapter for a pinned historic AWS requirement ledger.

The ZIP is never extracted and its contents are never uploaded or printed.
This is not a generic arbitrary-ZIP importer: both checksum and ledger path
must be listed in the local trusted source manifest.
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from pathlib import Path
from typing import Any

LEDGER_PATH = "academic_writing_suite/runtime/deep_spec_requirement_ledger.json"
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_LEDGER_BYTES = 3 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 3000


class KnowledgeSourceError(ValueError):
    """The private archive or its provenance cannot be trusted."""


def checksum_file(path: Path) -> str:
    """Stream SHA-256 of the original ZIP bytes, not decompressed content."""
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_source_manifest(path: Path, *, source_id: str) -> dict[str, Any]:
    """Select one verified archive entry from the metadata-only public manifest."""
    document = json.loads(path.read_text(encoding="utf-8"))
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise KnowledgeSourceError("manifest requires an artifacts list")
    found = [
        entry for entry in artifacts if isinstance(entry, dict) and entry.get("id") == source_id
    ]
    if len(found) != 1:
        raise KnowledgeSourceError("source ID must resolve to exactly one manifest artifact")
    entry = found[0]
    digest = entry.get("sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
    ):
        raise KnowledgeSourceError("manifest has no valid pinned archive SHA-256")
    if entry.get("repo_committed") is not False:
        raise KnowledgeSourceError("only external, uncommitted local sources are accepted")
    return entry


def read_requirement_ledger(
    path: Path,
    *,
    expected_sha256: str,
    expected_version: str,
    expected_count: int,
) -> list[dict[str, object]]:
    """Verify exact ZIP identity, boundaries, ledger shape and expected coverage."""
    if not path.is_file():
        raise KnowledgeSourceError("source ZIP does not exist locally")
    try:
        with path.open("rb") as source:
            size = os.fstat(source.fileno()).st_size
            if size == 0 or size > MAX_ARCHIVE_BYTES:
                raise KnowledgeSourceError("ZIP size is outside the permitted range")
            hasher = hashlib.sha256()
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(chunk)
            if hasher.hexdigest() != expected_sha256:
                raise KnowledgeSourceError("source ZIP SHA-256 differs from pinned manifest")
            source.seek(0)
            # Use the same opened file descriptor that was hashed. Reopening the
            # pathname after verification would permit archive replacement.
            with zipfile.ZipFile(source) as archive:
                if len(archive.infolist()) > MAX_ARCHIVE_ENTRIES:
                    raise KnowledgeSourceError("archive exceeds entry-count limit")
                matches = [item for item in archive.infolist() if item.filename == LEDGER_PATH]
                if len(matches) != 1:
                    raise KnowledgeSourceError("required ledger path must occur exactly once")
                info = matches[0]
                if info.file_size > MAX_LEDGER_BYTES:
                    raise KnowledgeSourceError("ledger exceeds decompressed-size limit")
                with archive.open(info, "r") as stream:
                    raw = stream.read(MAX_LEDGER_BYTES + 1)
                if len(raw) > MAX_LEDGER_BYTES:
                    raise KnowledgeSourceError("ledger exceeds read limit")
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise KnowledgeSourceError("invalid ZIP archive") from exc
    try:
        ledger = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise KnowledgeSourceError("invalid UTF-8 JSON ledger") from exc
    if not isinstance(ledger, dict) or ledger.get("suite_version") != expected_version:
        raise KnowledgeSourceError("source ledger has an unexpected suite version")
    rows = ledger.get("requirements")
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise KnowledgeSourceError("source ledger count does not match expected coverage")
    if not all(isinstance(row, dict) for row in rows):
        raise KnowledgeSourceError("source ledger must contain only requirement objects")
    return rows
