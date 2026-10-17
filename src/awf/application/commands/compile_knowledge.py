"""Application command: compile a verified local research archive.

The application depends on a source adapter for verified ZIP reads and a
pure knowledge compiler; only metadata is eligible for the output registry.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from awf.adapters.knowledge.zip_archive import (
    read_requirement_ledger,
    read_source_manifest,
)
from awf.domain.knowledge import KnowledgeRegistry
from awf.knowledge.compiler import compile_knowledge


def load_review_overlay(path: Path, *, expected_source_sha256: str) -> dict[str, dict[str, Any]]:
    """Only accept explicit, checksum-bound human decisions.

    This is an attestation format, not independent verification of the
    reviewer's identity or of semantic/evidential validity.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("source_sha256") != expected_source_sha256:
        raise ValueError("review overlay is not bound to the exact source archive hash")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("review overlay requires decisions list")
    result: dict[str, dict[str, Any]] = {}
    for item in decisions:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("malformed knowledge review decision")
        identifier = item["id"]
        if identifier in result:
            raise ValueError(f"duplicate review decision ID: {identifier}")
        result[identifier] = item
    return result


def import_knowledge(
    *,
    archive_path: Path,
    manifest_path: Path,
    source_id: str = "aws-3.19.1",
    review_path: Path | None = None,
) -> KnowledgeRegistry:
    """Verify the pinned local source and return a metadata-only, audited registry."""
    source = read_source_manifest(manifest_path, source_id=source_id)
    expected_hash = source["sha256"]
    version = source.get("version", "3.19.1")
    expected_count = source.get("requirements_count", 184)
    if not isinstance(version, str) or not isinstance(expected_count, int):
        raise ValueError("source manifest lacks typed version/count")
    rows = read_requirement_ledger(
        archive_path,
        expected_sha256=expected_hash,
        expected_version=version,
        expected_count=expected_count,
    )
    reviews = (
        load_review_overlay(review_path, expected_source_sha256=expected_hash)
        if review_path is not None
        else None
    )
    return compile_knowledge(
        rows,
        source_id=source_id,
        archive_sha256=expected_hash,
        suite_version=version,
        review_decisions=reviews,
    )
