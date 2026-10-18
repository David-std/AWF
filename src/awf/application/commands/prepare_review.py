"""Prepare a local review workbench through the source and storage ports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from awf.application.ports import KnowledgeSourcePort
from awf.knowledge.compiler import compile_knowledge
from awf.knowledge.review_plan import make_review_packets


def prepare_review(
    *,
    archive_path: Path,
    manifest_path: Path,
    reader: KnowledgeSourcePort,
    source_id: str = "aws-3.19.1",
    batch_size: int = 12,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Build review data, never a decision or model-training dataset."""
    source = reader.load(
        archive_path=archive_path, manifest_path=manifest_path, source_id=source_id
    )
    registry = compile_knowledge(
        source.rows,
        source_id=source.source_id,
        archive_sha256=source.archive_sha256,
        suite_version=source.suite_version,
    )
    return make_review_packets(source.rows, registry=registry, batch_size=batch_size)
