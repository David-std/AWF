"""Verify reviewer identity and role for exact persisted evidence events.

An authenticated authorization does NOT certify a scholarly claim, reviewer
independence, the accuracy of an audit or completion of a historic rule.
"""

from __future__ import annotations

from dataclasses import dataclass

from awf.application.commands.bind_evidence import (
    verify_audit_receipts,
    verify_progress_claims,
)
from awf.application.ports import (
    EvidenceStorePort,
    ReviewerSignatureVerifierPort,
    VerifiedEvidenceReaderPort,
)
from awf.domain.document import DocumentIR
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, EvidenceRecord
from awf.domain.knowledge_integrity import (
    AxisReceipt,
    CanonicalManifest,
    ChunkReceipt,
    KnowledgeProgress,
    KnowledgeStage,
)
from awf.domain.reviewer_auth import (
    ReviewerRole,
    ReviewerTrustPolicy,
    SignedReviewerClaim,
)
from awf.domain.revision_audit import RevisionState


@dataclass(frozen=True, slots=True)
class AuthorizationGateResult:
    checked: int
    unverified: tuple[str, ...]
    authorization_verified: bool
    independent_adjudication_proven: bool = False


def _verify_claim(
    signed: SignedReviewerClaim,
    *,
    store: VerifiedEvidenceReaderPort,
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
    expected_head: str | None,
) -> EvidenceRecord:
    claim = signed.claim
    grant = policy.authorize(claim, now=now)
    record, _ = store.resolve_event(
        event_digest=claim.target_event_ref[6:], expected_head=expected_head
    )
    if (record.kind, record.run_id, record.subject_id) != (
        claim.target_kind,
        claim.run_id,
        claim.subject_id,
    ):
        raise EvidenceIntegrityError("signed reviewer claim references a different event identity")
    verifier.verify(
        public_key_hex=grant.public_key_hex,
        signature_hex=signed.signature_hex,
        message=claim.signing_bytes,
    )
    return record


def append_signed_review_claim(
    *,
    store: EvidenceStorePort,
    signed: SignedReviewerClaim,
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
    expected_head: str | None = None,
) -> EvidenceRecord:
    """Append only a verified reviewer statement; never sign on behalf of a reviewer."""
    _verify_claim(
        signed,
        store=store,
        policy=policy,
        verifier=verifier,
        now=now,
        expected_head=expected_head,
    )
    return store.append(
        kind=EvidenceKind.REVIEW_ATTESTATION,
        run_id=signed.claim.run_id,
        subject_id=signed.claim.subject_id,
        content=signed.to_bytes(),
    )


def verify_signed_review_event(
    *,
    store: VerifiedEvidenceReaderPort,
    attestation_ref: str,
    target_ref: str,
    expected_role: ReviewerRole,
    run_id: str,
    subject_id: str,
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
    expected_head: str | None = None,
) -> str:
    """Return authorized actor ID only after full ledger and signature checks."""
    if not attestation_ref.startswith("event:"):
        raise EvidenceIntegrityError("authorization must reference a ledger event")
    record, data = store.resolve_event(
        event_digest=attestation_ref[6:], expected_head=expected_head
    )
    if (record.kind, record.run_id, record.subject_id) != (
        EvidenceKind.REVIEW_ATTESTATION,
        run_id,
        subject_id,
    ):
        raise EvidenceIntegrityError("review attestation event identity mismatch")
    signed = SignedReviewerClaim.from_bytes(data)
    claim = signed.claim
    if (
        claim.target_event_ref != target_ref
        or claim.role != expected_role
        or claim.run_id != run_id
        or claim.subject_id != subject_id
    ):
        raise EvidenceIntegrityError("reviewer authorization is not for this exact operation")
    target = _verify_claim(
        signed,
        store=store,
        policy=policy,
        verifier=verifier,
        now=now,
        expected_head=expected_head,
    )
    if record.sequence <= target.sequence:
        raise EvidenceIntegrityError("reviewer attestation predates its target event")
    return claim.actor_id


def verify_authorized_audit_receipts(
    state: RevisionState,
    document: DocumentIR,
    *,
    store: EvidenceStorePort,
    run_id: str,
    attestation_refs: dict[str, str],
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
    expected_head: str | None = None,
) -> AuthorizationGateResult:
    """Require a separately signed reviewer statement for every clean audit."""
    baseline = verify_audit_receipts(
        state, document, store=store, run_id=run_id, expected_head=expected_head
    )
    invalid = list(baseline.unverified)
    targets = {receipt.evidence_ref for receipt in state.receipts}
    if set(attestation_refs) != targets:
        invalid.append("attestation_inventory_mismatch")
    for receipt in state.receipts:
        attestation_ref = attestation_refs.get(receipt.evidence_ref)
        try:
            if attestation_ref is None:
                raise EvidenceIntegrityError("audit receipt lacks reviewer attestation")
            verify_signed_review_event(
                store=store,
                attestation_ref=attestation_ref,
                target_ref=receipt.evidence_ref,
                expected_role=ReviewerRole.AUDITOR,
                run_id=run_id,
                subject_id=receipt.slot_key,
                policy=policy,
                verifier=verifier,
                now=now,
                expected_head=expected_head,
            )
        except (EvidenceIntegrityError, ValueError):
            invalid.append(receipt.slot_key)
    return AuthorizationGateResult(
        checked=len(state.receipts),
        unverified=tuple(sorted(set(invalid))),
        authorization_verified=baseline.local_integrity_passed and not invalid,
    )


def verify_authorized_knowledge_progress(
    progress: KnowledgeProgress,
    *,
    store: EvidenceStorePort,
    manifest: CanonicalManifest | None,
    chunks: tuple[ChunkReceipt, ...],
    axes: tuple[AxisReceipt, ...],
    attestation_refs: dict[str, str],
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
    expected_head: str | None = None,
) -> AuthorizationGateResult:
    """Gate the adjudicated stages without mistaking them for real understanding."""
    base = verify_progress_claims(
        progress,
        store=store,
        manifest=manifest,
        chunks=chunks,
        axes=axes,
        expected_head=expected_head,
    )
    invalid = list(base.unverified)
    targets = {
        claim.evidence_ref
        for claim in progress.claims
        if claim.stage in {KnowledgeStage.UNDERSTOOD, KnowledgeStage.APPLICABLE}
    }
    if set(attestation_refs) != targets:
        invalid.append("attestation_inventory_mismatch")
    for claim in progress.claims:
        if claim.stage not in (KnowledgeStage.UNDERSTOOD, KnowledgeStage.APPLICABLE):
            continue
        role = (
            ReviewerRole.CALIBRATOR
            if claim.stage == KnowledgeStage.UNDERSTOOD
            else ReviewerRole.APPLICABILITY_REVIEWER
        )
        try:
            attestation_ref = attestation_refs.get(claim.evidence_ref)
            if attestation_ref is None:
                raise EvidenceIntegrityError("knowledge stage lacks reviewer attestation")
            verify_signed_review_event(
                store=store,
                attestation_ref=attestation_ref,
                target_ref=claim.evidence_ref,
                expected_role=role,
                run_id=claim.context_ref,
                subject_id=f"{claim.reference_id}:{claim.stage.value}",
                policy=policy,
                verifier=verifier,
                now=now,
                expected_head=expected_head,
            )
        except (EvidenceIntegrityError, ValueError):
            invalid.append(claim.stage.value)
    return AuthorizationGateResult(
        checked=len(targets),
        unverified=tuple(sorted(set(invalid))),
        authorization_verified=base.local_integrity_passed and not invalid and bool(targets),
    )
