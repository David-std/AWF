"""Application data transfer objects independent of source/ML/storage frameworks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LoadedKnowledgeSource:
    """Verified source description and parsed rows, private to the import boundary."""

    source_id: str
    archive_sha256: str
    suite_version: str
    rows: tuple[dict[str, object], ...]
