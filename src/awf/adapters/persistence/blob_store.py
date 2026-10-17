"""Local content-addressed blob storage with exclusive creation and verification."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


class BlobIntegrityError(OSError):
    """Existing content at a digest path differs from the requested source."""


class FileBlobStore:
    """Write private original bytes under <root>/<first-two-digest-characters>/<digest>."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, digest: str) -> Path:
        """Return a deterministic, sandbox-root-relative object location."""
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid SHA-256 digest")
        return self.root / digest[:2] / digest

    def put(self, raw: bytes) -> str:
        digest = hashlib.sha256(raw).hexdigest()
        path = self.path_for(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            handle = path.open("xb")
        except FileExistsError as exc:
            if path.read_bytes() != raw:
                raise BlobIntegrityError("existing blob has wrong content for its SHA-256") from exc
            return digest

        try:
            with handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            path.unlink(missing_ok=True)
            raise
        return digest
