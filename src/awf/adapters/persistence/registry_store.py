"""Private, atomic JSON metadata export; never write the historical source ZIP."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def save_registry(path: Path, report: dict[str, Any]) -> None:
    """Replace registry report atomically without dereferencing destination symlinks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("registry destination symlinks are not permitted")
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp_path: Path | None = None
    try:
        fd, name = tempfile.mkstemp(prefix=".registry-", suffix=".tmp", dir=path.parent)
        tmp_path = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            os.chmod(name, 0o600)
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
