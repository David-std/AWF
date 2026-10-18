"""Minimal provider-facing protocols; no parser, storage or ML dependency leaks inward."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from awf.application.dto import LoadedKnowledgeSource
from awf.domain.document import DocumentIR
from awf.domain.evidence import EvidenceKind, EvidenceRecord, LedgerAudit


class DocumentParserPort(Protocol):
    def parse(self, raw: bytes, *, source_name: str) -> DocumentIR:
        """Return a parsed, hash-bound view or raise a typed parse exception."""
        ...


class BlobStorePort(Protocol):
    def put(self, raw: bytes) -> str:
        """Store immutable bytes by content hash and return their SHA-256."""
        ...


class KnowledgeSourcePort(Protocol):
    def load(
        self, *, archive_path: Path, manifest_path: Path, source_id: str
    ) -> LoadedKnowledgeSource:
        """Read source metadata only after all origin-integrity checks."""
        ...


class KnowledgeReviewPort(Protocol):
    def load(self, path: Path, *, expected_source_sha256: str) -> dict[str, dict[str, object]]:
        """Read explicit, hash-bound review attestations."""
        ...


class EvidenceStorePort(Protocol):
    """Port for a durable, locally verifiable evidence repository."""

    def initialize(self) -> None:
        """Create a new local evidence store."""
        ...

    def append(
        self, *, kind: EvidenceKind, run_id: str, subject_id: str, content: bytes
    ) -> EvidenceRecord:
        """Persist bytes and event in one transaction, returning a source-bound receipt."""
        ...

    def verify(self, *, expected_head: str | None = None) -> LedgerAudit:
        """Verify chain, metadata and payloads; optionally check a trusted prior head."""
        ...

    def resolve_event(
        self, *, event_digest: str, expected_head: str | None = None
    ) -> tuple[EvidenceRecord, bytes]:
        """Verify the entire chain and resolve exactly one event and its bytes."""
        ...
