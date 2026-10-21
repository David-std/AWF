"""Read-only inspection of SHA-pinned historical evidence pointers.

Checks historical paths/sources without executing code, exporting text, or
authorizing training. Uses the same descriptor for hashing and ZIP inspection.
"""

from __future__ import annotations

import hashlib
import os
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

_SOURCE_FILES = {
    "deep_01": "docs/research_inputs/deep_01.md",
    "deep_02": "docs/research_inputs/deep_02.md",
    "deep_03": "docs/research_inputs/deep_03.md",
    "deep_06": "docs/research_inputs/deep_06_turnitin_operations.md",
    "forensic_main": "docs/research_inputs/forensic_3_13_iterative_chat.md",
    "pre_3_18": "docs/research_inputs/pre_3_18_knowledge_layer.md",
}


def _safe_path(raw: str) -> str:
    if (
        not raw
        or raw.startswith("/")
        or "\\" in raw
        or any(part in ("", ".", "..") for part in raw.split("/"))
    ):
        raise ValueError("invalid source-surface path")
    return "academic_writing_suite/" + raw


def inspect_historical_evidence(
    archive_path: Path, *, expected_sha256: str, rows: Sequence[Mapping[str, object]]
) -> dict[str, Any]:
    """Count existing *historical* file/dir and research document pointers.

    Neither a source ID nor a path is asserted as truthful solely by existing.
    """
    if archive_path.is_symlink() or not archive_path.is_file():
        raise ValueError("pilot ZIP must be a regular local file")
    if len(expected_sha256) != 64:
        raise ValueError("pilot lacks expected archive hash")
    files = directories = source_docs = 0
    try:
        with archive_path.open("rb") as raw:
            if not 0 < os.fstat(raw.fileno()).st_size <= 128 * 1024 * 1024:
                raise ValueError("oversized or empty pilot archive")
            digest = hashlib.sha256()
            for block in iter(lambda: raw.read(1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != expected_sha256:
                raise ValueError("pilot ZIP differs from separately pinned source")
            raw.seek(0)
            with zipfile.ZipFile(raw) as archive:
                names = archive.namelist()
                if len(names) > 3000 or len(names) != len(set(names)):
                    raise ValueError("unsafe pilot ZIP inventory")
                known = set(names)
                for row in rows:
                    paths = row.get("implementation_paths")
                    sources = row.get("source_ids")
                    if not isinstance(paths, list) or not paths:
                        raise ValueError("historical source lacks implementation paths")
                    if not isinstance(sources, list) or not sources:
                        raise ValueError("historical source lacks document pointers")
                    for path in paths:
                        if not isinstance(path, str):
                            raise ValueError("invalid historical path type")
                        full = _safe_path(path)
                        if full in known and not full.endswith("/"):
                            files += 1
                        elif any(item.startswith(full.rstrip("/") + "/") for item in names):
                            directories += 1
                        else:
                            raise ValueError("historical implementation surface missing")
                    for source_id in sources:
                        if not isinstance(source_id, str) or source_id not in _SOURCE_FILES:
                            raise ValueError("historical source ID has no explicit mapping")
                        if _safe_path(_SOURCE_FILES[source_id]) not in known:
                            raise ValueError("historical research source missing")
                        source_docs += 1
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError("invalid historical pilot ZIP") from exc
    return {
        "historical_implementation_file_refs_resolved": files,
        "historical_implementation_directory_refs_resolved": directories,
        "historical_research_source_refs_resolved": source_docs,
        "original_prose_exported": False,
        "historical_code_executed": False,
        "source_authorization_verified": False,
        "independent_scientific_review": False,
    }
