"""Application use case: compile a verified local knowledge source via ports.

The command has no dependency on ZIP, JSON files, network or persistence adapters.
"""

from __future__ import annotations

from pathlib import Path

from awf.application.ports import KnowledgeReviewPort, KnowledgeSourcePort
from awf.domain.knowledge import KnowledgeRegistry
from awf.knowledge.compiler import compile_knowledge


def import_knowledge(
    *,
    archive_path: Path,
    manifest_path: Path,
    archive_reader: KnowledgeSourcePort,
    source_id: str = "aws-3.19.1",
    review_path: Path | None = None,
    review_reader: KnowledgeReviewPort | None = None,
) -> KnowledgeRegistry:
    """Import a verified source and optionally apply explicit, attestable decisions."""
    source = archive_reader.load(
        archive_path=archive_path, manifest_path=manifest_path, source_id=source_id
    )
    if review_path is not None and review_reader is None:
        raise ValueError("review path requires a configured review reader")
    reviews = (
        review_reader.load(review_path, expected_source_sha256=source.archive_sha256)
        if review_path is not None and review_reader is not None
        else None
    )
    return compile_knowledge(
        source.rows,
        source_id=source.source_id,
        archive_sha256=source.archive_sha256,
        suite_version=source.suite_version,
        review_decisions=reviews,
    )
