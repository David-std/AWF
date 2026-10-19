"""Verify externally pinned, signed SQLite ledger checkpoints and prefix ancestry.

This does not publish the checkpoint or manage the custodian's private key.
"""

from __future__ import annotations

from dataclasses import dataclass

from awf.application.ports import EvidenceStorePort, SignatureVerifierPort
from awf.domain.checkpoints import (
    CheckpointClaim,
    CheckpointTrustPolicy,
    SignedLedgerCheckpoint,
)
from awf.domain.evidence import EvidenceIntegrityError


@dataclass(frozen=True, slots=True)
class CheckpointValidation:
    checkpoint_event_count: int
    current_event_count: int
    checkpoint_is_current_head: bool
    external_custody_proven: bool = False


def _verify_signature(
    signed: SignedLedgerCheckpoint,
    *,
    policy: CheckpointTrustPolicy,
    verifier: SignatureVerifierPort,
    now: int,
) -> None:
    grant = policy.authorize(signed.claim, now=now)
    verifier.verify(
        public_key_hex=grant.public_key_hex,
        signature_hex=signed.signature_hex,
        message=signed.claim.signing_bytes,
    )


def propose_checkpoint(
    *,
    store: EvidenceStorePort,
    ledger_id: str,
    key_id: str,
    issued_at: int,
    previous: SignedLedgerCheckpoint | None = None,
) -> CheckpointClaim:
    """Build an unsigned claim; the external custodian must sign it separately."""
    report = (
        store.verify_anchors(anchors=((previous.claim.event_count, previous.claim.head_digest),))
        if previous is not None
        else store.verify()
    )
    if report.events_checked < 1:
        raise EvidenceIntegrityError("an empty ledger cannot yield a protective checkpoint")
    if previous is not None:
        if previous.claim.ledger_id != ledger_id:
            raise EvidenceIntegrityError("checkpoint lineage crosses ledger identities")
        if previous.claim.event_count >= report.events_checked:
            raise EvidenceIntegrityError("checkpoint lineage has not advanced")
        if issued_at < previous.claim.issued_at:
            raise EvidenceIntegrityError("checkpoint issue time regressed")
    return CheckpointClaim(
        ledger_id=ledger_id,
        key_id=key_id,
        head_digest=report.head_digest,
        event_count=report.events_checked,
        issued_at=issued_at,
        previous_checkpoint_sha256=previous.sha256 if previous is not None else None,
    )


def verify_signed_checkpoint(
    *,
    store: EvidenceStorePort,
    signed: SignedLedgerCheckpoint,
    expected_signed_sha256: str,
    policy: CheckpointTrustPolicy,
    verifier: SignatureVerifierPort,
    now: int,
    previous: SignedLedgerCheckpoint | None = None,
    history: tuple[SignedLedgerCheckpoint, ...] = (),
    require_current_head: bool = False,
) -> CheckpointValidation:
    """Verify signature, trust policy, retained digest, and actual ledger ancestry.

    The expected digest must be obtained from an independently controlled
    witness; using a hash computed from the same untrusted file is not a root
    of trust. A signed prefix can be followed by later valid events.
    """
    if signed.sha256 != expected_signed_sha256:
        raise EvidenceIntegrityError("external signed checkpoint digest mismatch")
    if previous is not None and history:
        raise EvidenceIntegrityError("supply either previous or complete history, not both")
    lineage = history if history else ((previous,) if previous is not None else ())
    if len(lineage) > 1023:
        raise EvidenceIntegrityError("checkpoint verification lineage exceeds bound")
    chain = (*lineage, signed)
    anchors: tuple[tuple[int, str], ...] = ()
    for i, checkpoint in enumerate(chain):
        claim = checkpoint.claim
        if i == 0:
            if claim.previous_checkpoint_sha256 is not None:
                raise EvidenceIntegrityError("complete checkpoint history from genesis is required")
        else:
            predecessor = chain[i - 1]
            if (
                claim.previous_checkpoint_sha256 != predecessor.sha256
                or claim.ledger_id != predecessor.claim.ledger_id
                or claim.event_count <= predecessor.claim.event_count
                or claim.issued_at < predecessor.claim.issued_at
            ):
                raise EvidenceIntegrityError("checkpoint chain is not monotonic or is substituted")
        _verify_signature(checkpoint, policy=policy, verifier=verifier, now=now)
        anchors += ((claim.event_count, claim.head_digest),)
    report = store.verify_anchors(anchors=anchors)
    claim = signed.claim
    is_current = (
        claim.event_count == report.events_checked and claim.head_digest == report.head_digest
    )
    if require_current_head and not is_current:
        raise EvidenceIntegrityError("signed checkpoint is not the current ledger head")
    return CheckpointValidation(
        checkpoint_event_count=claim.event_count,
        current_event_count=report.events_checked,
        checkpoint_is_current_head=is_current,
    )
