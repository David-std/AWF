"""Knowledge source adapter implementing the application import port."""

from __future__ import annotations

from pathlib import Path

from awf.adapters.knowledge.zip_archive import read_requirement_ledger, read_source_manifest
from awf.application.dto import LoadedKnowledgeSource


class PinnedAwsArchive:
    """Verify and read a manifest-pinned AWS ZIP entirely on the local machine."""

    def load(
        self, *, archive_path: Path, manifest_path: Path, source_id: str
    ) -> LoadedKnowledgeSource:
        manifest = read_source_manifest(manifest_path, source_id=source_id)
        version = manifest.get("version", "3.19.1")
        count = manifest.get("requirements_count", 184)
        digest = manifest["sha256"]
        if not isinstance(version, str) or not isinstance(count, int):
            raise ValueError("source manifest lacks typed version/count")
        if not isinstance(digest, str):
            raise ValueError("source manifest lacks pinned SHA-256")
        rows = read_requirement_ledger(
            archive_path,
            expected_sha256=digest,
            expected_version=version,
            expected_count=count,
        )
        return LoadedKnowledgeSource(
            source_id=source_id,
            archive_sha256=digest,
            suite_version=version,
            rows=tuple(rows),
        )
