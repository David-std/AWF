"""Immutable evidence ledger contracts; no storage or model dependencies.

An internally consistent SHA-256 chain is *tamper evident relative to a trusted
checkpoint*, not a signature or proof that an evaluator's claim is true.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum

GENESIS_DIGEST = "0" * 64
MAX_EVIDENCE_BYTES = 512 * 1024
MAX_BATCH_EVENTS = 512
MAX_BATCH_BYTES = 8 * 1024 * 1024
_SHA_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class EvidenceKind(StrEnum):
    SOURCE_CHUNK = "SOURCE_CHUNK"
    AUDIT_RECEIPT = "AUDIT_RECEIPT"
    CALIBRATION_JUDGMENT = "CALIBRATION_JUDGMENT"
    REVIEW_DECISION = "REVIEW_DECISION"
    RULE_SUPPORT = "RULE_SUPPORT"
    KNOWLEDGE_REVIEW_PROPOSAL = "KNOWLEDGE_REVIEW_PROPOSAL"
    SCIENTIFIC_RULE_ASSESSMENT = "SCIENTIFIC_RULE_ASSESSMENT"
    SCIENTIFIC_ARBITRATION = "SCIENTIFIC_ARBITRATION"
    REVISION_TRANSITION = "REVISION_TRANSITION"
    REVIEW_ATTESTATION = "REVIEW_ATTESTATION"
    CRITIC_OBSERVATION = "CRITIC_OBSERVATION"
    CRITIC_CONTEXT = "CRITIC_CONTEXT"
    EXTERNAL_ITERATION_OBSERVATION = "EXTERNAL_ITERATION_OBSERVATION"


class EvidenceIntegrityError(ValueError):
    """A ledger cannot be safely read, continued, or accepted."""


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    sequence: int
    kind: EvidenceKind
    run_id: str
    subject_id: str
    evidence_sha256: str
    evidence_bytes: int
    recorded_at: str
    previous_digest: str
    digest: str

    @property
    def evidence_ref(self) -> str:
        return f"sha256:{self.evidence_sha256}"


@dataclass(frozen=True, slots=True)
class EvidenceAppend:
    """One proposed ledger event, still uncommitted and unverified."""

    kind: EvidenceKind
    run_id: str
    subject_id: str
    content: bytes


@dataclass(frozen=True, slots=True)
class LedgerAudit:
    events_checked: int
    evidence_objects_checked: int
    head_digest: str
    valid: bool = True


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_metadata(kind: EvidenceKind, run_id: str, subject_id: str, size: int) -> None:
    if not isinstance(kind, EvidenceKind):
        raise ValueError("unknown evidence kind")
    if not isinstance(run_id, str) or _ID_PATTERN.fullmatch(run_id) is None:
        raise ValueError("invalid run identifier")
    if not isinstance(subject_id, str) or _ID_PATTERN.fullmatch(subject_id) is None:
        raise ValueError("invalid subject identifier")
    if not 1 <= size <= MAX_EVIDENCE_BYTES:
        raise ValueError("evidence payload must be nonempty and within size limit")


def event_digest(
    *,
    sequence: int,
    kind: EvidenceKind,
    run_id: str,
    subject_id: str,
    evidence_sha256: str,
    evidence_bytes: int,
    recorded_at: str,
    previous_digest: str,
) -> str:
    """Canonical hash binds ordering, source bytes, identity and timestamp."""
    if sequence < 1 or _SHA_PATTERN.fullmatch(evidence_sha256) is None:
        raise ValueError("invalid event identity or evidence hash")
    if _SHA_PATTERN.fullmatch(previous_digest) is None:
        raise ValueError("invalid previous digest")
    validate_metadata(kind, run_id, subject_id, evidence_bytes)
    if not recorded_at:
        raise ValueError("missing event timestamp")
    payload = {
        "schema": 1,
        "sequence": sequence,
        "kind": kind.value,
        "run_id": run_id,
        "subject_id": subject_id,
        "evidence_sha256": evidence_sha256,
        "evidence_bytes": evidence_bytes,
        "recorded_at": recorded_at,
        "previous_digest": previous_digest,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256_bytes(raw.encode("utf-8"))
