"""Evidence-bound knowledge integrity primitives, independent of model/providers.

The contracts prevent *structural* false passes. A checksum or attestable
receipt does not prove that a human/LLM read, understood, or correctly applied
knowledge. Evidence authenticity must be checked at another trust boundary.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from enum import StrEnum

from awf.knowledge.dependency_graph import dependency_closure


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _identifier(value: str) -> bool:
    return re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,99}", value) is not None


@dataclass(frozen=True, slots=True)
class SourceChunk:
    chunk_id: str
    offset_start: int
    offset_end: int
    sha256: str


@dataclass(frozen=True, slots=True)
class CanonicalReference:
    """Source identity, not an embedded copy of licensed or private text."""

    reference_id: str
    sha256: str
    byte_length: int
    chunks: tuple[SourceChunk, ...]
    dependencies: tuple[str, ...] = ()
    critical: bool = False
    negative_knowledge: bool = False
    evidence_pointer: str = ""


@dataclass(frozen=True, slots=True)
class CanonicalManifest:
    version: str
    sources: tuple[CanonicalReference, ...]
    expected_axes: tuple[str, ...]

    def __post_init__(self) -> None:
        ids = [ref.reference_id for ref in self.sources]
        if not self.version or not ids or len(ids) != len(set(ids)):
            raise ValueError("manifest requires unique nonempty source inventory")
        if not self.expected_axes or len(set(self.expected_axes)) != len(self.expected_axes):
            raise ValueError("manifest requires unique nonempty expected axes")
        declared = set(ids)
        for ref in self.sources:
            if not _identifier(ref.reference_id) or not ref.evidence_pointer:
                raise ValueError("source ID and evidence pointer are required")
            if not set(ref.dependencies).issubset(declared):
                raise ValueError("unknown referenced source dependency")
            if ref.byte_length < 0 or not ref.chunks:
                raise ValueError("each reference requires one or more verified chunks")
            offset = 0
            for chunk in ref.chunks:
                if chunk.offset_start != offset or chunk.offset_end < offset:
                    raise ValueError("source chunks must cover contiguous byte offsets")
                offset = chunk.offset_end
            if offset != ref.byte_length:
                raise ValueError("source chunk inventory must cover source to EOF")
        graph = {ref.reference_id: set(ref.dependencies) for ref in self.sources}
        dependency_closure(declared, graph)


@dataclass(frozen=True, slots=True)
class SourceInput:
    reference_id: str
    original_bytes: bytes
    evidence_pointer: str
    dependencies: tuple[str, ...] = ()
    critical: bool = False
    negative_knowledge: bool = False


def build_manifest(
    sources: tuple[SourceInput, ...],
    *,
    version: str,
    expected_axes: tuple[str, ...],
    chunk_bytes: int = 4096,
) -> CanonicalManifest:
    """Compute SHA and byte-contiguous chunks without exporting original text."""
    if chunk_bytes < 1 or chunk_bytes > 1024 * 1024:
        raise ValueError("chunk_bytes outside supported limits")
    refs: list[CanonicalReference] = []
    for source in sources:
        raw = source.original_bytes
        chunks = []
        for offset in range(0, max(1, len(raw)), chunk_bytes):
            part = raw[offset : offset + chunk_bytes]
            chunks.append(
                SourceChunk(
                    chunk_id=f"C{len(chunks) + 1:04d}",
                    offset_start=offset,
                    offset_end=offset + len(part),
                    sha256=_sha(part),
                )
            )
        refs.append(
            CanonicalReference(
                reference_id=source.reference_id,
                sha256=_sha(raw),
                byte_length=len(raw),
                chunks=tuple(chunks),
                dependencies=source.dependencies,
                critical=source.critical,
                negative_knowledge=source.negative_knowledge,
                evidence_pointer=source.evidence_pointer,
            )
        )
    return CanonicalManifest(version, tuple(refs), expected_axes)


@dataclass(frozen=True, slots=True)
class ChunkReceipt:
    reference_id: str
    chunk_id: str
    sha256: str
    reader_ref: str
    observation_ref: str


@dataclass(frozen=True, slots=True)
class AxisReceipt:
    axis_id: str
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class CoverageAssessment:
    required_chunks: int
    accepted_chunks: int
    missing_chunks: tuple[str, ...]
    missing_axes: tuple[str, ...]
    invalid_receipts: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return (
            self.required_chunks > 0
            and self.accepted_chunks == self.required_chunks
            and not self.missing_chunks
            and not self.missing_axes
            and not self.invalid_receipts
        )


def assess_coverage(
    manifest: CanonicalManifest,
    chunk_receipts: tuple[ChunkReceipt, ...],
    axis_receipts: tuple[AxisReceipt, ...],
) -> CoverageAssessment:
    """Compare receipts to expected chunks, not merely to observed receipts.

    A forged but internally consistent digest remains possible; this is an
    inventory validator, not evidence that any agent actually read the text.
    """
    expected = {
        (ref.reference_id, chunk.chunk_id): chunk.sha256
        for ref in manifest.sources
        for chunk in ref.chunks
    }
    seen: set[tuple[str, str]] = set()
    accepted: set[tuple[str, str]] = set()
    invalid: list[str] = []
    for receipt in chunk_receipts:
        key = (receipt.reference_id, receipt.chunk_id)
        label = ":".join(key)
        if key in seen:
            invalid.append(f"duplicate:{label}")
        seen.add(key)
        if (
            key not in expected
            or receipt.sha256 != expected.get(key)
            or not receipt.reader_ref.strip()
            or not receipt.observation_ref.strip()
        ):
            invalid.append(f"invalid:{label}")
        else:
            accepted.add(key)
    expected_axes = set(manifest.expected_axes)
    observed_axes: set[str] = set()
    for receipt in axis_receipts:
        if (
            receipt.axis_id not in expected_axes
            or receipt.axis_id in observed_axes
            or not receipt.evidence_ref.strip()
        ):
            invalid.append(f"invalid_axis:{receipt.axis_id}")
        observed_axes.add(receipt.axis_id)
    missing = tuple(sorted(f"{ref}:{chunk}" for ref, chunk in expected.keys() - accepted))
    return CoverageAssessment(
        required_chunks=len(expected),
        accepted_chunks=len(accepted),
        missing_chunks=missing,
        missing_axes=tuple(sorted(expected_axes - observed_axes)),
        invalid_receipts=tuple(sorted(invalid)),
    )


class KnowledgeStage(StrEnum):
    AVAILABLE = "AVAILABLE"
    READ = "READ"
    UNDERSTOOD = "UNDERSTOOD"
    APPLICABLE = "APPLICABLE"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True, slots=True)
class StageClaim:
    reference_id: str
    stage: KnowledgeStage
    evidence_ref: str
    context_ref: str


@dataclass(frozen=True, slots=True)
class KnowledgeProgress:
    """Append-only stage evidence. Claims are attested, not automatically trusted."""

    reference_id: str
    claims: tuple[StageClaim, ...] = ()


def advance_stage(
    progress: KnowledgeProgress,
    *,
    stage: KnowledgeStage,
    evidence_ref: str,
    context_ref: str,
    complete_chunk_coverage: bool = False,
    challenge_adjudicated: bool = False,
    applicability_adjudicated: bool = False,
) -> KnowledgeProgress:
    """Require explicit, non-skippable evidence for every escalation."""
    if not isinstance(stage, KnowledgeStage):
        raise ValueError("unrecognized stage")
    if not evidence_ref.strip() or not context_ref.strip():
        raise ValueError("stage claims need evidence and execution context")
    old_stages = [c.stage for c in progress.claims]
    ordered = list(KnowledgeStage)
    expected = ordered[len(old_stages)] if len(old_stages) < len(ordered) else None
    if stage != expected:
        raise ValueError("knowledge stages cannot be skipped or duplicated")
    if stage == KnowledgeStage.READ and not complete_chunk_coverage:
        raise ValueError("READ requires complete source chunk coverage")
    if stage == KnowledgeStage.UNDERSTOOD and not challenge_adjudicated:
        raise ValueError("UNDERSTOOD requires external comprehension adjudication")
    if stage == KnowledgeStage.APPLICABLE and not applicability_adjudicated:
        raise ValueError("APPLICABLE requires reviewed scope applicability")
    return replace(
        progress,
        claims=progress.claims + (StageClaim(progress.reference_id, stage, evidence_ref, context_ref),),
    )


def preservation_debt(
    old: CanonicalManifest, new: CanonicalManifest
) -> tuple[str, ...]:
    """Fail closed on disappearing or changed sources, including negative knowledge."""
    previous = {ref.reference_id: ref for ref in old.sources}
    current = {ref.reference_id: ref for ref in new.sources}
    debt = []
    for key, prior in previous.items():
        latest = current.get(key)
        if latest is None:
            debt.append(f"removed:{key}")
        elif prior.sha256 != latest.sha256 or prior.negative_knowledge != latest.negative_knowledge:
            debt.append(f"changed:{key}")
    return tuple(sorted(debt))


def retrieval_closure(
    manifest: CanonicalManifest, selected: set[str]
) -> tuple[str, ...]:
    """Preserve transitive dependencies and critical exceptions.

    The caller must establish applicability separately. All critical sources
    are conservatively included until a reviewed applicability filter exists.
    """
    graph = {ref.reference_id: set(ref.dependencies) for ref in manifest.sources}
    critical = {ref.reference_id for ref in manifest.sources if ref.critical}
    return dependency_closure(selected | critical, graph)
