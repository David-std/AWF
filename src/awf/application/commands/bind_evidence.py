"""Application-level evidence bindings for source chunks, audit receipts and stages.

A ledger event proves only what bytes were committed under what declared
metadata, not whether a critic is independent or a scholarly claim is correct.
No domain module imports persistence or provider-specific packages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from awf.application.ports import EvidenceStorePort, VerifiedEvidenceReaderPort
from awf.domain.document import DocumentIR
from awf.domain.evidence import (
    EvidenceAppend,
    EvidenceIntegrityError,
    EvidenceKind,
    EvidenceRecord,
    sha256_bytes,
)
from awf.domain.knowledge_integrity import (
    AxisReceipt,
    CanonicalManifest,
    ChunkReceipt,
    CoverageAssessment,
    KnowledgeProgress,
    KnowledgeStage,
    assess_coverage,
)
from awf.domain.revision_audit import (
    AuditReceipt,
    AuditSlot,
    AuditStatus,
    RevisionState,
    record_audit,
    scope_fingerprint,
)

_EVENT_PREFIX = "event:"


def _canonical(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def event_reference(record: EvidenceRecord) -> str:
    return _EVENT_PREFIX + record.digest


def _get_event(
    store: VerifiedEvidenceReaderPort,
    evidence_ref: str,
    *,
    kind: EvidenceKind,
    run_id: str,
    subject_id: str,
    expected_head: str | None,
) -> bytes:
    if not evidence_ref.startswith(_EVENT_PREFIX):
        raise EvidenceIntegrityError("evidence must refer to a ledger event, not a bare hash")
    record, payload = store.resolve_event(
        event_digest=evidence_ref[len(_EVENT_PREFIX) :],
        expected_head=expected_head,
    )
    if (record.kind, record.run_id, record.subject_id) != (kind, run_id, subject_id):
        raise EvidenceIntegrityError("evidence event kind, run or subject mismatch")
    return payload


def audit_claim_payload(receipt: AuditReceipt, *, observation_ref: str) -> bytes:
    """One canonical event payload shared by volatile and durable audit paths."""
    if not observation_ref.strip():
        raise ValueError("an audit needs an observation reference")
    return _canonical(
        {
            "schema": 1,
            "type": "audit_receipt",
            "slot_key": receipt.slot_key,
            "artifact_sha256": receipt.artifact_sha256,
            "scope_sha256": receipt.scope_sha256,
            "status": receipt.status.value,
            "checks_executed": receipt.checks_executed,
            "observation_ref": observation_ref,
        }
    )


def record_evidenced_audit(
    state: RevisionState,
    document: DocumentIR,
    *,
    store: EvidenceStorePort,
    run_id: str,
    slot_key: str,
    status: AuditStatus,
    checks_executed: int,
    observation_ref: str,
) -> RevisionState:
    """Validate a pure transition before writing the source-bound claim.

    An observation_ref identifies the external observation, but is not itself
    authenticated. Storage failure does not mutate the caller's immutable state.
    """
    if not observation_ref.strip():
        raise ValueError("an audit needs an observation reference")
    provisional = record_audit(
        state,
        document,
        slot_key=slot_key,
        status=status,
        checks_executed=checks_executed,
        evidence_ref="uncommitted-observation",
    )
    receipt = next(r for r in provisional.receipts if r.slot_key == slot_key)
    content = audit_claim_payload(receipt, observation_ref=observation_ref)
    event = store.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id=run_id,
        subject_id=slot_key,
        content=content,
    )
    final_receipt = replace(receipt, evidence_ref=event_reference(event))
    return replace(
        provisional,
        receipts=tuple(
            final_receipt if r.slot_key == slot_key else r for r in provisional.receipts
        ),
    )


@dataclass(frozen=True, slots=True)
class EvidenceGateResult:
    checked: int
    unverified: tuple[str, ...]
    local_integrity_passed: bool
    independent_adjudication_proven: bool = False


@dataclass(frozen=True, slots=True)
class ObservedChunk:
    """Private bytes for one chunk declared in a canonical source manifest."""

    reference_id: str
    chunk_id: str
    content: bytes


def verify_audit_receipts(
    state: RevisionState,
    document: DocumentIR,
    *,
    store: EvidenceStorePort,
    run_id: str,
    expected_head: str | None = None,
) -> EvidenceGateResult:
    """Verify receipts for the current artifact; a pure CONVERGED alone is insufficient.

    Carried-forward local receipts may be attached to a newer artifact; their
    evidence payload intentionally records original artifact and scope, while
    the current scope is validated separately by the domain decision function.
    This function doesn't attest clean sweeps or open-finding resolutions.
    """
    if state.artifact_sha256 != document.sha256:
        raise EvidenceIntegrityError("audit state bound to different artifact")
    missing: list[str] = []
    slots = {slot.key: slot for slot in state.slots}
    receipt_keys = [receipt.slot_key for receipt in state.receipts]
    receipts = set(receipt_keys)
    missing.extend(sorted(slots.keys() - receipts))
    if len(slots) != len(state.slots):
        missing.append("duplicate_audit_slots")
    if len(receipts) != len(receipt_keys):
        missing.append("duplicate_audit_receipts")
    missing.extend(f"unknown_dirty:{key}" for key in sorted(state.dirty_keys - slots.keys()))
    if not state.receipts:
        return EvidenceGateResult(0, tuple(sorted(missing)), False)
    try:
        with store.verified_read(expected_head=expected_head) as reader:
            _verify_audit_receipts_in_snapshot(
                state,
                document,
                reader=reader,
                run_id=run_id,
                expected_head=expected_head,
                slots=slots,
                missing=missing,
            )
    except EvidenceIntegrityError:
        missing.extend(receipt.slot_key for receipt in state.receipts)
    return EvidenceGateResult(
        checked=len(state.receipts),
        unverified=tuple(sorted(missing)),
        local_integrity_passed=bool(slots) and not missing,
    )


def _verify_audit_receipts_in_snapshot(
    state: RevisionState,
    document: DocumentIR,
    *,
    reader: VerifiedEvidenceReaderPort,
    run_id: str,
    expected_head: str | None,
    slots: dict[str, AuditSlot],
    missing: list[str],
) -> None:
    """Check receipts against one fully verified read view."""
    for receipt in state.receipts:
        original = receipt.carried_from or receipt.artifact_sha256
        try:
            slot = slots.get(receipt.slot_key)
            if (
                slot is None
                or receipt.artifact_sha256 != document.sha256
                or receipt.slot_key in state.dirty_keys
                or receipt.status != AuditStatus.CLEAN
                or receipt.checks_executed != slot.required_checks
                or receipt.scope_sha256 != scope_fingerprint(document, slot)
            ):
                raise EvidenceIntegrityError("stale, unclean or unknown audit receipt")
            payload = _get_event(
                reader,
                receipt.evidence_ref,
                kind=EvidenceKind.AUDIT_RECEIPT,
                run_id=run_id,
                subject_id=receipt.slot_key,
                expected_head=expected_head,
            )
            claim = json.loads(payload)
            if (
                not isinstance(claim, dict)
                or claim.get("schema") != 1
                or claim.get("type") != "audit_receipt"
                or claim.get("slot_key") != receipt.slot_key
                or claim.get("artifact_sha256") != original
                or claim.get("scope_sha256") != receipt.scope_sha256
                or claim.get("status") != receipt.status.value
                or claim.get("checks_executed") != receipt.checks_executed
                or not isinstance(claim.get("observation_ref"), str)
                or not claim["observation_ref"].strip()
            ):
                raise EvidenceIntegrityError("audit event payload disagrees with receipt")
        except (EvidenceIntegrityError, ValueError, TypeError, json.JSONDecodeError):
            missing.append(receipt.slot_key)


def record_evidenced_chunk(
    *,
    store: EvidenceStorePort,
    run_id: str,
    reader_ref: str,
    reference_id: str,
    chunk_id: str,
    chunk_bytes: bytes,
) -> ChunkReceipt:
    """Store exact chunk bytes; identity is checked against the canonical manifest later."""
    if not reader_ref.strip():
        raise ValueError("reader reference is required")
    record = store.append(
        kind=EvidenceKind.SOURCE_CHUNK,
        run_id=run_id,
        subject_id=f"{reference_id}:{chunk_id}",
        content=chunk_bytes,
    )
    return ChunkReceipt(
        reference_id=reference_id,
        chunk_id=chunk_id,
        sha256=sha256_bytes(chunk_bytes),
        reader_ref=reader_ref,
        observation_ref=event_reference(record),
    )


def record_evidenced_chunks(
    *,
    store: EvidenceStorePort,
    manifest: CanonicalManifest,
    observations: tuple[ObservedChunk, ...],
    run_id: str,
    reader_ref: str,
    expected_head: str | None = None,
) -> tuple[ChunkReceipt, ...]:
    """Commit an ordered subset of observed manifest chunks as one ledger transaction.

    Every item is checked against canonical identity, offsets and content hash
    *before* writing. Partial batches are allowed; full source coverage remains
    the responsibility of ``verify_chunk_coverage`` after all batches complete.
    """
    if not isinstance(reader_ref, str) or not reader_ref.strip():
        raise ValueError("reader reference is required")
    expected = {
        (source.reference_id, chunk.chunk_id): (chunk.sha256, chunk.offset_end - chunk.offset_start)
        for source in manifest.sources
        for chunk in source.chunks
    }
    seen: set[tuple[str, str]] = set()
    entries: list[EvidenceAppend] = []
    for observation in observations:
        if not isinstance(observation, ObservedChunk):
            raise ValueError("invalid observed chunk")
        key = (observation.reference_id, observation.chunk_id)
        if key in seen:
            raise ValueError("duplicate observed chunk")
        seen.add(key)
        matched = expected.get(key)
        if (
            matched is None
            or not isinstance(observation.content, bytes)
            or len(observation.content) != matched[1]
            or sha256_bytes(observation.content) != matched[0]
        ):
            raise EvidenceIntegrityError("observed chunk differs from canonical manifest")
        entries.append(
            EvidenceAppend(
                EvidenceKind.SOURCE_CHUNK,
                run_id,
                f"{observation.reference_id}:{observation.chunk_id}",
                observation.content,
            )
        )
    records = store.append_batch(entries=tuple(entries), expected_head=expected_head)
    return tuple(
        ChunkReceipt(
            reference_id=observation.reference_id,
            chunk_id=observation.chunk_id,
            sha256=sha256_bytes(observation.content),
            reader_ref=reader_ref,
            observation_ref=event_reference(record),
        )
        for observation, record in zip(observations, records, strict=True)
    )


def verify_chunk_coverage(
    manifest: CanonicalManifest,
    chunks: tuple[ChunkReceipt, ...],
    axes: tuple[AxisReceipt, ...],
    *,
    store: EvidenceStorePort,
    run_id: str,
    expected_head: str | None = None,
) -> CoverageAssessment:
    """Reconcile declared inventory with persisted source bytes in verified events.

    Axis events attest only to a recorded observation. They do not prove the
    quality of a reviewer, independent verification or model comprehension.
    """
    baseline = assess_coverage(manifest, chunks, axes)
    try:
        with store.verified_read(expected_head=expected_head) as reader:
            return _verify_chunk_coverage_in_snapshot(
                baseline, chunks, axes, reader=reader, run_id=run_id, expected_head=expected_head
            )
    except EvidenceIntegrityError:
        # Invalid ledger, schema or trusted head: every local observation is
        # unverified. Fail closed without misrepresenting any as authenticated.
        unverified = [
            *(f"unverified_chunk:{item.reference_id}:{item.chunk_id}" for item in chunks),
            *(f"unverified_axis:{axis.axis_id}" for axis in axes),
        ]
        return replace(
            baseline,
            invalid_receipts=tuple(sorted(set((*baseline.invalid_receipts, *unverified)))),
        )


def _verify_chunk_coverage_in_snapshot(
    baseline: CoverageAssessment,
    chunks: tuple[ChunkReceipt, ...],
    axes: tuple[AxisReceipt, ...],
    *,
    reader: VerifiedEvidenceReaderPort,
    run_id: str,
    expected_head: str | None,
) -> CoverageAssessment:
    """Check each binding with precise errors, amortizing the ledger audit."""
    unexpected: list[str] = list(baseline.invalid_receipts)
    for item in chunks:
        try:
            payload = _get_event(
                reader,
                item.observation_ref,
                kind=EvidenceKind.SOURCE_CHUNK,
                run_id=run_id,
                subject_id=f"{item.reference_id}:{item.chunk_id}",
                expected_head=expected_head,
            )
            if sha256_bytes(payload) != item.sha256:
                raise EvidenceIntegrityError("source chunk bytes differ from claim")
        except (EvidenceIntegrityError, ValueError):
            unexpected.append(f"unverified_chunk:{item.reference_id}:{item.chunk_id}")
    for axis in axes:
        try:
            payload = _get_event(
                reader,
                axis.evidence_ref,
                kind=EvidenceKind.AUDIT_RECEIPT,
                run_id=run_id,
                subject_id=f"axis:{axis.axis_id}",
                expected_head=expected_head,
            )
            if not payload:
                raise EvidenceIntegrityError("empty axis evidence")
        except (EvidenceIntegrityError, ValueError):
            unexpected.append(f"unverified_axis:{axis.axis_id}")
    return replace(baseline, invalid_receipts=tuple(sorted(set(unexpected))))


def _stage_kind(stage: KnowledgeStage) -> EvidenceKind:
    if stage == KnowledgeStage.UNDERSTOOD:
        return EvidenceKind.CALIBRATION_JUDGMENT
    if stage == KnowledgeStage.APPLICABLE:
        return EvidenceKind.REVIEW_DECISION
    return EvidenceKind.REVISION_TRANSITION


def _coverage_refs(
    chunks: tuple[ChunkReceipt, ...], axes: tuple[AxisReceipt, ...]
) -> dict[str, object]:
    return {
        "chunk_refs": sorted((r.reference_id, r.chunk_id, r.observation_ref) for r in chunks),
        "axis_refs": sorted((r.axis_id, r.evidence_ref) for r in axes),
    }


def verify_progress_claims(
    progress: KnowledgeProgress,
    *,
    store: EvidenceStorePort,
    manifest: CanonicalManifest | None = None,
    chunks: tuple[ChunkReceipt, ...] = (),
    axes: tuple[AxisReceipt, ...] = (),
    expected_head: str | None = None,
) -> EvidenceGateResult:
    """Check stage receipts and recheck any READ claim against the live manifest."""
    if not progress.claims:
        return EvidenceGateResult(0, ("no_claims",), False)
    try:
        with store.verified_read(expected_head=expected_head) as reader:
            return _verify_progress_claims_in_snapshot(
                progress,
                reader=reader,
                manifest=manifest,
                chunks=chunks,
                axes=axes,
                expected_head=expected_head,
            )
    except EvidenceIntegrityError:
        return EvidenceGateResult(
            len(progress.claims),
            tuple(sorted(claim.stage.value for claim in progress.claims)),
            False,
        )


def _verify_progress_claims_in_snapshot(
    progress: KnowledgeProgress,
    *,
    reader: VerifiedEvidenceReaderPort,
    manifest: CanonicalManifest | None,
    chunks: tuple[ChunkReceipt, ...],
    axes: tuple[AxisReceipt, ...],
    expected_head: str | None,
) -> EvidenceGateResult:
    """Verify stage claims, coverage and adjudication from the same read snapshot."""
    missing: list[str] = []
    order = list(KnowledgeStage)
    execution = progress.claims[0].context_ref
    for index, claim in enumerate(progress.claims):
        try:
            if (
                claim.reference_id != progress.reference_id
                or claim.context_ref != execution
                or index >= len(order)
                or order[index] != claim.stage
            ):
                raise EvidenceIntegrityError("missing, reordered or mixed-context knowledge stage")
            payload = _get_event(
                reader,
                claim.evidence_ref,
                kind=_stage_kind(claim.stage),
                run_id=claim.context_ref,
                subject_id=f"{claim.reference_id}:{claim.stage.value}",
                expected_head=expected_head,
            )
            decoded = json.loads(payload)
            if not isinstance(decoded, dict):
                raise EvidenceIntegrityError("stage payload must be JSON object")
            extras: dict[str, object] = {}
            if claim.stage == KnowledgeStage.READ:
                if manifest is None:
                    raise EvidenceIntegrityError("READ needs original manifest to reverify")
                if progress.reference_id not in {ref.reference_id for ref in manifest.sources}:
                    raise EvidenceIntegrityError("stage reference missing from canonical manifest")
                coverage = _verify_chunk_coverage_in_snapshot(
                    assess_coverage(manifest, chunks, axes),
                    chunks,
                    axes,
                    reader=reader,
                    run_id=claim.context_ref,
                    expected_head=expected_head,
                )
                if not coverage.complete:
                    raise EvidenceIntegrityError("stored chunk coverage is incomplete")
                extras = {"manifest_version": manifest.version, **_coverage_refs(chunks, axes)}
            if claim.stage in (KnowledgeStage.UNDERSTOOD, KnowledgeStage.APPLICABLE):
                proof_ref = decoded.get("adjudication_ref")
                if not isinstance(proof_ref, str):
                    raise EvidenceIntegrityError("stage lacks adjudication source event")
                kind = _stage_kind(claim.stage)
                subject = (
                    f"{claim.reference_id}:calibration"
                    if claim.stage == KnowledgeStage.UNDERSTOOD
                    else f"{claim.reference_id}:applicability"
                )
                external_payload = _get_event(
                    reader,
                    proof_ref,
                    kind=kind,
                    run_id=claim.context_ref,
                    subject_id=subject,
                    expected_head=expected_head,
                )
                if not external_payload:
                    raise EvidenceIntegrityError("empty adjudication evidence")
                extras = {"adjudication_ref": proof_ref}
            expected = _canonical(
                {
                    "schema": 1,
                    "type": "knowledge_stage",
                    "reference_id": claim.reference_id,
                    "stage": claim.stage.value,
                    "context_ref": claim.context_ref,
                    **extras,
                }
            )
            if payload != expected:
                raise EvidenceIntegrityError("stage payload does not match its provenance")
        except (EvidenceIntegrityError, ValueError, TypeError):
            missing.append(claim.stage.value)
    return EvidenceGateResult(
        checked=len(progress.claims),
        unverified=tuple(sorted(missing)),
        local_integrity_passed=not missing,
    )


def record_stage_claim(
    progress: KnowledgeProgress,
    *,
    store: EvidenceStorePort,
    stage: KnowledgeStage,
    context_ref: str,
    manifest: CanonicalManifest | None = None,
    chunks: tuple[ChunkReceipt, ...] = (),
    axes: tuple[AxisReceipt, ...] = (),
    adjudication_ref: str | None = None,
    expected_head: str | None = None,
) -> KnowledgeProgress:
    """No caller-supplied boolean can convert declarations into stage evidence.

    READ rechecks stored source bytes; understanding/applicability require a
    separate ledger-bound adjudication record. These are local integrity
    conditions, not independently proven scientific or cognitive results.
    """
    from awf.domain.knowledge_integrity import advance_stage

    checked_coverage: CoverageAssessment | None = None
    if stage == KnowledgeStage.READ:
        if manifest is None:
            raise EvidenceIntegrityError("READ needs pinned canonical manifest")
        if progress.reference_id not in {ref.reference_id for ref in manifest.sources}:
            raise EvidenceIntegrityError("stage reference missing from canonical manifest")
        checked_coverage = verify_chunk_coverage(
            manifest,
            chunks,
            axes,
            store=store,
            run_id=context_ref,
            expected_head=expected_head,
        )
    adjudicated = False
    if stage in (KnowledgeStage.UNDERSTOOD, KnowledgeStage.APPLICABLE):
        if adjudication_ref is None:
            raise EvidenceIntegrityError("stage requires separately stored adjudication")
        kind = _stage_kind(stage)
        subject = (
            f"{progress.reference_id}:calibration"
            if stage == KnowledgeStage.UNDERSTOOD
            else f"{progress.reference_id}:applicability"
        )
        adjudicated = bool(
            _get_event(
                store,
                adjudication_ref,
                kind=kind,
                run_id=context_ref,
                subject_id=subject,
                expected_head=expected_head,
            )
        )
    provisional = advance_stage(
        progress,
        stage=stage,
        evidence_ref="uncommitted-observation",
        context_ref=context_ref,
        coverage=checked_coverage,
        challenge_adjudicated=adjudicated,
        applicability_adjudicated=adjudicated,
    )
    extras: dict[str, object] = {}
    if stage == KnowledgeStage.READ:
        assert manifest is not None
        extras = {"manifest_version": manifest.version, **_coverage_refs(chunks, axes)}
    elif stage in (KnowledgeStage.UNDERSTOOD, KnowledgeStage.APPLICABLE):
        extras = {"adjudication_ref": adjudication_ref}
    payload = _canonical(
        {
            "schema": 1,
            "type": "knowledge_stage",
            "reference_id": progress.reference_id,
            "stage": stage.value,
            "context_ref": context_ref,
            **extras,
        }
    )
    event = store.append(
        kind=_stage_kind(stage),
        run_id=context_ref,
        subject_id=f"{progress.reference_id}:{stage.value}",
        content=payload,
    )
    recorded_claim = replace(provisional.claims[-1], evidence_ref=event_reference(event))
    return replace(provisional, claims=provisional.claims[:-1] + (recorded_claim,))
