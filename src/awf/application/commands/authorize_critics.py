"""Authenticate declared critic sweeps against signed, scoped ledger observations.

This verifies key authorization and causal evidence, not evaluator independence,
scientific correctness, or the integrity of an externally held trust root.
"""

from __future__ import annotations

from awf.application.commands.authorize_review import (
    AuthorizationGateResult,
    verify_signed_review_event,
)
from awf.application.ports import (
    EvidenceStorePort,
    ReviewerSignatureVerifierPort,
    RevisionJournalPort,
    VerifiedEvidenceReaderPort,
)
from awf.domain.document import DocumentIR
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.domain.reviewer_auth import ReviewerRole, ReviewerTrustPolicy
from awf.domain.revision_audit import (
    CleanSweep,
    RevisionPolicy,
    RevisionVerdict,
    decision,
)
from awf.domain.signed_documents import strict_json


def _bound_critic_observation(
    reader: VerifiedEvidenceReaderPort,
    sweep: CleanSweep,
    *,
    revision_id: str,
    run_id: str,
    artifact_sha256: str,
) -> str:
    """Recover the observation the durable sweep actually cited at commit."""
    if not sweep.evidence_ref.startswith("event:"):
        raise EvidenceIntegrityError("clean sweep lacks a committed event identity")
    event, data = reader.resolve_event(event_digest=sweep.evidence_ref[6:])
    if (event.kind, event.run_id, event.subject_id) != (
        EvidenceKind.REVISION_TRANSITION,
        run_id,
        revision_id,
    ):
        raise EvidenceIntegrityError("clean sweep intent has wrong event identity")
    body = strict_json(data)
    details = body.get("details")
    if (
        body.get("type") != "revision_intent"
        or body.get("operation_kind") != "CLEAN_SWEEP"
        or body.get("revision_id") != revision_id
        or body.get("run_id") != run_id
        or not isinstance(details, dict)
        or details.get("critic_id") != sweep.critic_id
        or details.get("isolated_context_ref") != sweep.isolated_context_ref
        or details.get("artifact_sha256") != artifact_sha256
    ):
        raise EvidenceIntegrityError("clean sweep state is not bound to its intent")
    observation_ref = details.get("observation_ref")
    if not isinstance(observation_ref, str) or not observation_ref.startswith("event:"):
        raise EvidenceIntegrityError("clean sweep lacks its original critic observation")
    return observation_ref


def verify_authorized_critic_sweeps(
    *,
    journal: RevisionJournalPort,
    store: EvidenceStorePort,
    revision_id: str,
    run_id: str,
    document: DocumentIR,
    revision_policy: RevisionPolicy,
    attestation_refs: dict[str, str],
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
    expected_head: str,
) -> AuthorizationGateResult:
    """Verify each sweep using a pinned head, signed event and trusted policy.

    The attestation map is keyed by CLEAN_SWEEP intent references. Each signed
    REVIEW_ATTESTATION must target the original observation in that intent,
    carry role CRITIC, and identify the same actor as the sweep.
    """
    if not isinstance(expected_head, str) or len(expected_head) != 64:
        raise EvidenceIntegrityError("externally held ledger head is required")
    recovered = journal.load(revision_id=revision_id, expected_head=expected_head)
    if recovered.run_id != run_id:
        raise EvidenceIntegrityError("revision belongs to another run")

    sweeps = recovered.state.clean_sweeps
    try:
        verdict = decision(recovered.state, document, revision_policy)
    except ValueError:
        verdict = None
    if verdict != RevisionVerdict.CONVERGED:
        return AuthorizationGateResult(
            checked=len(sweeps),
            unverified=("revision_not_locally_converged",),
            authorization_verified=False,
        )

    targets = [sweep.evidence_ref for sweep in sweeps]
    if (
        not sweeps
        or len(set(targets)) != len(targets)
        or set(attestation_refs) != set(targets)
        or len(attestation_refs) != len(sweeps)
    ):
        return AuthorizationGateResult(
            checked=len(sweeps),
            unverified=("critic_attestation_inventory_mismatch",),
            authorization_verified=False,
        )

    invalid: list[str] = []
    # One verified read snapshot, not one full-ledger audit per critic.
    # A concurrent append after journal.load fails the exact-head comparison.
    with store.verified_read(expected_head=recovered.ledger_head) as reader:
        for sweep in sweeps:
            try:
                attestation_ref = attestation_refs[sweep.evidence_ref]
                if not isinstance(attestation_ref, str):
                    raise EvidenceIntegrityError("critic attestation must reference an event")
                observation_ref = _bound_critic_observation(
                    reader,
                    sweep,
                    revision_id=revision_id,
                    run_id=run_id,
                    artifact_sha256=document.sha256,
                )
                actor_id = verify_signed_review_event(
                    store=reader,
                    attestation_ref=attestation_ref,
                    target_ref=observation_ref,
                    expected_role=ReviewerRole.CRITIC,
                    run_id=run_id,
                    subject_id=revision_id,
                    policy=policy,
                    verifier=verifier,
                    now=now,
                )
                if actor_id != sweep.critic_id:
                    raise EvidenceIntegrityError("signed critic actor differs from sweep critic")
            except (EvidenceIntegrityError, ValueError):
                invalid.append(sweep.evidence_ref)
    return AuthorizationGateResult(
        checked=len(sweeps),
        unverified=tuple(sorted(set(invalid))),
        authorization_verified=not invalid,
    )
