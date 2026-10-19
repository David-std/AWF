"""Private, atomic JSON metadata export; never write the historical source ZIP."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _serialized_report(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def save_registry(path: Path, report: dict[str, Any]) -> None:
    """Replace registry report atomically without dereferencing destination symlinks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("registry destination symlinks are not permitted")
    serialized = _serialized_report(report)
    tmp_path: Path | None = None
    try:
        fd, name = tempfile.mkstemp(prefix=".registry-", suffix=".tmp", dir=path.parent)
        tmp_path = Path(name)
        with os.fdopen(fd, "wb") as stream:
            os.chmod(name, 0o600)
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def save_review_workbench(
    output_dir: Path,
    *,
    overview: dict[str, Any],
    packets: dict[str, dict[str, Any]],
) -> None:
    """Resume generated packets, refusing to overwrite any manual review changes.

    Preflight the complete batch before creating new files. The manifest is
    published last, so a crash before that point is retryable without erasure.
    """
    if "manifest.json" in packets:
        raise ValueError("review packet must not replace the manifest")
    reports = sorted(packets.items()) + [("manifest.json", overview)]
    for name, report in reports:
        if Path(name).name != name or not name.endswith(".json"):
            raise ValueError("invalid private review packet filename")
        destination = output_dir / name
        if destination.is_symlink():
            raise ValueError(f"private review packet is a symbolic link: {name}")
        if destination.exists() and destination.read_bytes() != _serialized_report(report):
            raise ValueError(f"private review packet has local changes: {name}")
    for name, report in reports:
        destination = output_dir / name
        if not destination.exists():
            save_registry(destination, report)
