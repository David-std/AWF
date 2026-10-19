"""Application data transfer objects independent of source/ML/storage frameworks."""

from __future__ import annotations

from dataclasses import dataclass

from awf.domain.revision_audit import RevisionState


@dataclass(frozen=True, slots=True)
class LoadedKnowledgeSource:
    """Verified source description and parsed rows, private to the import boundary."""

    source_id: str
    archive_sha256: str
    suite_version: str
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class PersistedRevision:
    """Recovered immutable revision state, with local-commit identity only."""

    revision_id: str
    run_id: str
    version: int
    state: RevisionState
    operation_id: str
    ledger_head: str
    replayed: bool = False
