"""Require a pinned signed current head before publishing any backup or restore."""

from __future__ import annotations

from pathlib import Path

from awf.application.commands.checkpoints import verify_signed_checkpoint
from awf.application.dto import SnapshotReceipt
from awf.application.ports import EvidenceStorePort, SignatureVerifierPort, SnapshotWriterPort
from awf.domain.checkpoints import CheckpointTrustPolicy, SignedLedgerCheckpoint
from awf.domain.evidence import EvidenceIntegrityError


def create_verified_snapshot(
    *,
    store: EvidenceStorePort,
    writer: SnapshotWriterPort,
    destination: Path,
    signed: SignedLedgerCheckpoint,
    expected_signed_sha256: str,
    policy: CheckpointTrustPolicy,
    verifier: SignatureVerifierPort,
    now: int,
    history: tuple[SignedLedgerCheckpoint, ...] = (),
) -> SnapshotReceipt:
    """Create a *new* snapshot with an exact signed head, never replace state.

    A source append between authorization and SQLite's online backup is safe:
    the resulting backup must still equal the originally authorized head.
    This operation does not transfer external custody to the snapshot.
    """
    outcome = verify_signed_checkpoint(
        store=store,
        signed=signed,
        expected_signed_sha256=expected_signed_sha256,
        policy=policy,
        verifier=verifier,
        now=now,
        history=history,
        require_current_head=True,
    )
    if not outcome.checkpoint_is_current_head:
        raise EvidenceIntegrityError("snapshot requires a signed current ledger head")
    return writer.create_new(
        destination=destination,
        expected_head=signed.claim.head_digest,
        expected_events=signed.claim.event_count,
    )
