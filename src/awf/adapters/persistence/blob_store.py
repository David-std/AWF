"""Local content-addressed blob storage with exclusive creation and verification."""

from __future__ import annotations

import hashlib
import os
import tempfile
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
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # A pre-existing symlinked digest directory must not redirect private
        # original bytes outside the caller-selected store.
        if path.parent.resolve() != self.root.resolve() / digest[:2]:
            raise BlobIntegrityError("blob directory escapes the selected store")

        # Publish only after the complete file is flushed. Creating the final
        # path before writing lets a concurrent ingest observe partial bytes.
        fd, temporary_name = tempfile.mkstemp(prefix=".awf-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # Hard-link creation is exclusive and atomic on supported local
                # filesystems. Never replace an existing content-addressed blob.
                os.link(temporary_name, path)
            except FileExistsError as exc:
                if path.is_symlink() or path.read_bytes() != raw:
                    raise BlobIntegrityError(
                        "existing blob has wrong content for its SHA-256"
                    ) from exc
        finally:
            Path(temporary_name).unlink(missing_ok=True)
        return digest
