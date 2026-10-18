"""Application-level evidence bindings for source chunks, audit receipts and stages.

A ledger event proves only what bytes were committed under what declared
metadata, not whether a critic is independent or a scholarly claim is correct.
No domain module imports persistence or provider-specific packages.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from awf.application.ports import EvidenceStorePort
from awf.domain.document import DocumentIR
from awf.domain.evidence import (
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
    AuditStatus,
    RevisionState,
    record_audit,
)

_EVENT_PREFIX = "event:"


def _canonical(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def event_reference(record: EvidenceRecord) -> str:
    return _EVENT_PREFIX + record.digest


def _get_event(
    store: EvidenceStorePort,
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
    content = _canonical(
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
    for receipt in state.receipts:
        original = receipt.carried_from or receipt.artifact_sha256
        try:
            payload = _get_event(
                store,
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
    return EvidenceGateResult(
        checked=len(state.receipts),
        unverified=tuple(sorted(missing)),
        local_integrity_passed=bool(state.receipts) and not missing,
    )


def record_evidenced_chunk(
    *, store: EvidenceStorePort, run_id: str, reader_ref: str,
    reference_id: str, chunk_id: str, chunk_bytes: bytes,
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
    unexpected: list[str] = list(baseline.invalid_receipts)
    for item in chunks:
        try:
            payload = _get_event(
                store, item.observation_ref,
                kind=EvidenceKind.SOURCE_CHUNK, run_id=run_id,
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
                store, axis.evidence_ref,
                kind=EvidenceKind.AUDIT_RECEIPT, run_id=run_id,
                subject_id=f"axis:{axis.axis_id}",
                expected_head=expected_head,
            )
            if not payload:
                raise EvidenceIntegrityError("empty axis evidence")
        except (EvidenceIntegrityError, ValueError):
            unexpected.append(f"unverified_axis:{axis.axis_id}")
    return replace(baseline, invalid_receipts=tuple(sorted(set(unexpected))))


def verify_progress_claims(
    progress: KnowledgeProgress,
    *,
    store: EvidenceStorePort,
    expected_head: str | None = None,
) -> EvidenceGateResult:
    """Verify typed ledger link of each epistemic-stage receipt, not its truth."""
    if not progress.claims:
        return EvidenceGateResult(0, ("no_claims",), False)
    missing: list[str] = []
    for claim in progress.claims:
        kind = (
            EvidenceKind.CALIBRATION_JUDGMENT
            if claim.stage == KnowledgeStage.UNDERSTOOD
            else EvidenceKind.REVIEW_DECISION
            if claim.stage == KnowledgeStage.APPLICABLE
            else EvidenceKind.REVISION_TRANSITION
        )
        try:
            payload = _get_event(
                store, claim.evidence_ref,
                kind=kind, run_id=claim.context_ref,
                subject_id=f"{claim.reference_id}:{claim.stage.value}",
                expected_head=expected_head,
            )
            expected = _canonical(
                {"schema": 1, "type": "knowledge_stage", "reference_id": claim.reference_id,
                 "stage": claim.stage.value, "context_ref": claim.context_ref}
            )
            if payload != expected:
                raise EvidenceIntegrityError("stage evidence payload differs from claim")
        except (EvidenceIntegrityError, ValueError):
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
    coverage: CoverageAssessment | None = None,
    challenge_adjudicated: bool = False,
    applicability_adjudicated: bool = False,
) -> KnowledgeProgress:
    """Persist claim and then use the same pure transition contract as before."""
    from awf.domain.knowledge_integrity import advance_stage

    provisional = advance_stage(
        progress,
        stage=stage,
        evidence_ref="uncommitted-observation",
        context_ref=context_ref,
        coverage=coverage,
        challenge_adjudicated=challenge_adjudicated,
        applicability_adjudicated=applicability_adjudicated,
    )
    kind = (
        EvidenceKind.CALIBRATION_JUDGMENT if stage == KnowledgeStage.UNDERSTOOD
        else EvidenceKind.REVIEW_DECISION if stage == KnowledgeStage.APPLICABLE
        else EvidenceKind.REVISION_TRANSITION
    )
    payload = _canonical(
        {"schema": 1, "type": "knowledge_stage", "reference_id": progress.reference_id,
         "stage": stage.value, "context_ref": context_ref}
    )
    event = store.append(
        kind=kind,
        run_id=context_ref,
        subject_id=f"{progress.reference_id}:{stage.value}",
        content=payload,
    )
    recorded_claim = replace(provisional.claims[-1], evidence_ref=event_reference(event))
    return replace(provisional, claims=provisional.claims[:-1] + (recorded_claim,))
