"""Minimal provider-facing protocols; no parser, storage or ML dependency leaks inward."""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol

from awf.application.dto import LoadedKnowledgeSource, PersistedRevision, SnapshotReceipt
from awf.domain.agent_execution import AgentTask, ProviderObservation
from awf.domain.document import DocumentIR
from awf.domain.evidence import EvidenceAppend, EvidenceKind, EvidenceRecord, LedgerAudit
from awf.domain.revision_audit import AuditSlot, AuditStatus, RevisionPolicy


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


class VerifiedEvidenceReaderPort(Protocol):
    """Read event bytes from one fully audited, immutable transaction snapshot."""

    def resolve_event(
        self, *, event_digest: str, expected_head: str | None = None
    ) -> tuple[EvidenceRecord, bytes]:
        """Resolve a single event within the previously audited snapshot."""
        ...


class EvidenceStorePort(VerifiedEvidenceReaderPort, Protocol):
    """Port for a durable, locally verifiable evidence repository."""

    def initialize(self) -> None:
        """Create a new local evidence store."""
        ...

    def append(
        self, *, kind: EvidenceKind, run_id: str, subject_id: str, content: bytes
    ) -> EvidenceRecord:
        """Persist bytes and event in one transaction, returning a source-bound receipt."""
        ...

    def append_batch(
        self,
        *,
        entries: tuple[EvidenceAppend, ...],
        expected_head: str | None = None,
    ) -> tuple[EvidenceRecord, ...]:
        """Append an ordered, bounded batch atomically after one complete integrity audit."""
        ...

    def verify(self, *, expected_head: str | None = None) -> LedgerAudit:
        """Verify chain, metadata and payloads; optionally check a trusted prior head."""
        ...

    def verify_anchors(self, *, anchors: tuple[tuple[int, str], ...]) -> LedgerAudit:
        """Audit the full chain and all signed (sequence, digest) prefixes atomically."""
        ...

    def verified_read(
        self, *, expected_head: str | None = None
    ) -> AbstractContextManager[VerifiedEvidenceReaderPort]:
        """Audit once, then resolve multiple events in that same read transaction."""
        ...


class SignatureVerifierPort(Protocol):
    """Verify a detached signature against an independently trusted public key."""

    def verify(self, *, public_key_hex: str, signature_hex: str, message: bytes) -> None:
        """Raise EvidenceIntegrityError for an invalid signature or unsupported backend."""
        ...


# Compatibility: reviewer authorization published the narrower name in PR #22.
ReviewerSignatureVerifierPort = SignatureVerifierPort


class SnapshotWriterPort(Protocol):
    """Produce a validated new snapshot without overwriting existing state."""

    def create_new(
        self, *, destination: Path, expected_head: str, expected_events: int
    ) -> SnapshotReceipt:
        """Commit a coherent copy only when its contents match this trusted head."""
        ...


class RevisionJournalPort(Protocol):
    """Atomic revision/evidence commits; never authorizes final scholarly acceptance."""

    def initialize(self) -> None: ...

    def create(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        document: DocumentIR,
        slots: tuple[AuditSlot, ...],
    ) -> PersistedRevision: ...

    def record_audit(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        document: DocumentIR,
        expected_version: int,
        slot_key: str,
        status: AuditStatus,
        checks_executed: int,
        observation_ref: str,
    ) -> PersistedRevision: ...

    def accept_edit(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        old_document: DocumentIR,
        new_document: DocumentIR,
        expected_version: int,
        policy: RevisionPolicy,
        observation_ref: str,
    ) -> PersistedRevision: ...

    def open_finding(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        expected_version: int,
        finding_id: str,
        material: bool,
        observation_ref: str,
    ) -> PersistedRevision: ...

    def resolve_finding(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        expected_version: int,
        finding_id: str,
        observation_ref: str,
    ) -> PersistedRevision: ...

    def record_clean_sweep(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        document: DocumentIR,
        expected_version: int,
        policy: RevisionPolicy,
        critic_id: str,
        isolated_context_ref: str,
        observation_ref: str,
        inherited_diagnosis: bool = False,
    ) -> PersistedRevision: ...

    def record_external_iteration(
        self,
        *,
        revision_id: str,
        operation_id: str,
        run_id: str,
        expected_version: int,
        policy: RevisionPolicy,
        observation_ref: str,
    ) -> PersistedRevision: ...

    def load(self, *, revision_id: str, expected_head: str | None = None) -> PersistedRevision: ...


class AgentExecutionPort(Protocol):
    """Attempt a bounded inference; caller independently times the invocation."""

    def generate(self, task: AgentTask) -> ProviderObservation:
        """Return observed model output without asserting correctness or independence."""
        ...
