"""Pure reviewer authorization contracts, separate from scientific correctness.

The trust root and trustworthy time must be provided outside the SQLite ledger.
Neither an authenticated signer nor a permitted role proves reviewer independence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.signed_documents import canonical_json_bytes as _canonical
from awf.domain.signed_documents import strict_json

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_SIG = re.compile(r"[a-f0-9]{128}\Z")
_DOMAIN = b"AWF/reviewer-authorization/v1\x00"


class ReviewerRole(StrEnum):
    AUDITOR = "AUDITOR"
    CRITIC = "CRITIC"
    CALIBRATOR = "CALIBRATOR"
    APPLICABILITY_REVIEWER = "APPLICABILITY_REVIEWER"
    KNOWLEDGE_REVIEWER = "KNOWLEDGE_REVIEWER"


_ROLE_KINDS = {
    ReviewerRole.AUDITOR: EvidenceKind.AUDIT_RECEIPT,
    ReviewerRole.CRITIC: EvidenceKind.CRITIC_OBSERVATION,
    ReviewerRole.CALIBRATOR: EvidenceKind.CALIBRATION_JUDGMENT,
    ReviewerRole.APPLICABILITY_REVIEWER: EvidenceKind.REVIEW_DECISION,
    ReviewerRole.KNOWLEDGE_REVIEWER: EvidenceKind.KNOWLEDGE_REVIEW_PROPOSAL,
}


def _identifier(value: str) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class ReviewerGrant:
    actor_id: str
    key_id: str
    public_key_hex: str
    roles: frozenset[ReviewerRole]
    runs: frozenset[str]
    subjects: frozenset[str]
    valid_from: int
    valid_until: int
    revoked: bool = False

    def __post_init__(self) -> None:
        if (
            not _identifier(self.actor_id)
            or not _identifier(self.key_id)
            or not isinstance(self.public_key_hex, str)
            or _SHA.fullmatch(self.public_key_hex) is None
            or type(self.roles) is not frozenset
            or not self.roles
            or any(not isinstance(role, ReviewerRole) for role in self.roles)
            or type(self.runs) is not frozenset
            or not self.runs
            or any(not _identifier(value) for value in self.runs)
            or type(self.subjects) is not frozenset
            or not self.subjects
            or any(not _identifier(value) for value in self.subjects)
            or type(self.valid_from) is not int
            or type(self.valid_until) is not int
            or self.valid_from < 0
            or self.valid_until <= self.valid_from
            or type(self.revoked) is not bool
        ):
            raise EvidenceIntegrityError("invalid reviewer grant")


@dataclass(frozen=True, slots=True)
class ReviewerTrustPolicy:
    """Externally pinned allowlist; grants are not inferred from ledger claims."""

    grants: tuple[ReviewerGrant, ...]
    policy_sha256: str

    def __post_init__(self) -> None:
        identities = [(grant.actor_id, grant.key_id) for grant in self.grants]
        public_keys = [grant.key_id for grant in self.grants]
        key_material = [grant.public_key_hex for grant in self.grants]
        if (
            type(self.grants) is not tuple
            or not self.grants
            or len(set(identities)) != len(identities)
            or len(set(public_keys)) != len(public_keys)
            or len(set(key_material)) != len(key_material)
            or not isinstance(self.policy_sha256, str)
            or _SHA.fullmatch(self.policy_sha256) is None
        ):
            raise EvidenceIntegrityError("ambiguous or empty reviewer trust policy")

    def authorize(self, claim: ReviewerClaim, *, now: int) -> ReviewerGrant:
        if type(now) is not int or now < 0:
            raise EvidenceIntegrityError("trusted verification time is required")
        grant = next(
            (g for g in self.grants if (g.actor_id, g.key_id) == (claim.actor_id, claim.key_id)),
            None,
        )
        if (
            grant is None
            or grant.revoked
            or claim.role not in grant.roles
            or claim.run_id not in grant.runs
            or claim.subject_id not in grant.subjects
            or not grant.valid_from <= claim.issued_at <= now < grant.valid_until
        ):
            raise EvidenceIntegrityError("reviewer is not authorized in this context")
        return grant


@dataclass(frozen=True, slots=True)
class ReviewerClaim:
    """A signed assertion about one exact existing ledger event."""

    actor_id: str
    key_id: str
    role: ReviewerRole
    run_id: str
    subject_id: str
    target_event_ref: str
    issued_at: int

    def __post_init__(self) -> None:
        if (
            not all(
                _identifier(value)
                for value in (self.actor_id, self.key_id, self.run_id, self.subject_id)
            )
            or not isinstance(self.role, ReviewerRole)
            or not isinstance(self.target_event_ref, str)
            or not self.target_event_ref.startswith("event:")
            or _SHA.fullmatch(self.target_event_ref[6:]) is None
            or type(self.issued_at) is not int
            or self.issued_at < 0
        ):
            raise EvidenceIntegrityError("invalid reviewer claim")

    @property
    def target_kind(self) -> EvidenceKind:
        return _ROLE_KINDS[self.role]

    def payload(self) -> dict[str, object]:
        return {
            "schema": 1,
            "actor_id": self.actor_id,
            "key_id": self.key_id,
            "role": self.role.value,
            "run_id": self.run_id,
            "subject_id": self.subject_id,
            "target_event_ref": self.target_event_ref,
            "issued_at": self.issued_at,
        }

    @property
    def signing_bytes(self) -> bytes:
        return _DOMAIN + _canonical(self.payload())


@dataclass(frozen=True, slots=True)
class SignedReviewerClaim:
    claim: ReviewerClaim
    signature_hex: str

    def __post_init__(self) -> None:
        if not isinstance(self.signature_hex, str) or _SIG.fullmatch(self.signature_hex) is None:
            raise EvidenceIntegrityError("invalid Ed25519 signature encoding")

    def to_bytes(self) -> bytes:
        return _canonical({"claim": self.claim.payload(), "signature_hex": self.signature_hex})

    @classmethod
    def from_bytes(cls, data: bytes) -> SignedReviewerClaim:
        body = strict_json(data)
        if (
            set(body) != {"claim", "signature_hex"}
            or not isinstance(body["claim"], dict)
            or not isinstance(body["signature_hex"], str)
        ):
            raise EvidenceIntegrityError("unexpected signed claim fields")
        record = body["claim"]
        required = {
            "schema",
            "actor_id",
            "key_id",
            "role",
            "run_id",
            "subject_id",
            "target_event_ref",
            "issued_at",
        }
        if set(record) != required or record["schema"] != 1 or type(record["schema"]) is not int:
            raise EvidenceIntegrityError("unsupported reviewer claim schema")
        try:
            claim = ReviewerClaim(
                actor_id=record["actor_id"],
                key_id=record["key_id"],
                role=ReviewerRole(record["role"]),
                run_id=record["run_id"],
                subject_id=record["subject_id"],
                target_event_ref=record["target_event_ref"],
                issued_at=record["issued_at"],
            )
            return cls(claim=claim, signature_hex=body["signature_hex"])
        except (TypeError, ValueError) as exc:
            raise EvidenceIntegrityError("invalid signed reviewer claim") from exc


def parse_trust_policy(data: bytes, *, expected_sha256: str) -> ReviewerTrustPolicy:
    """Validate trust bytes against an independent, caller-pinned SHA-256."""
    if not isinstance(expected_sha256, str) or _SHA.fullmatch(expected_sha256) is None:
        raise EvidenceIntegrityError("trusted policy digest must be externally pinned")
    if sha256_bytes(data) != expected_sha256:
        raise EvidenceIntegrityError("reviewer trust policy changed or was substituted")
    body = strict_json(data)
    if set(body) != {"schema", "grants"} or body["schema"] != 1 or type(body["schema"]) is not int:
        raise EvidenceIntegrityError("unsupported reviewer policy schema")
    rows = body["grants"]
    if not isinstance(rows, list) or not rows or len(rows) > 128:
        raise EvidenceIntegrityError("reviewer policy must contain bounded grants")
    grants: list[ReviewerGrant] = []
    for row in rows:
        required = {
            "actor_id",
            "key_id",
            "public_key_hex",
            "roles",
            "runs",
            "subjects",
            "valid_from",
            "valid_until",
            "revoked",
        }
        if not isinstance(row, dict) or set(row) != required:
            raise EvidenceIntegrityError("invalid grant shape")
        roles, runs, subjects = row["roles"], row["runs"], row["subjects"]
        if not all(
            isinstance(values, list)
            and all(isinstance(member, str) for member in values)
            and len(values) == len(set(values))
            for values in (roles, runs, subjects)
        ):
            raise EvidenceIntegrityError("duplicate or invalid grant members")
        try:
            grants.append(
                ReviewerGrant(
                    actor_id=row["actor_id"],
                    key_id=row["key_id"],
                    public_key_hex=row["public_key_hex"],
                    roles=frozenset(ReviewerRole(value) for value in roles),
                    runs=frozenset(runs),
                    subjects=frozenset(subjects),
                    valid_from=row["valid_from"],
                    valid_until=row["valid_until"],
                    revoked=row["revoked"],
                )
            )
        except (TypeError, ValueError) as exc:
            raise EvidenceIntegrityError("invalid grant members") from exc
    return ReviewerTrustPolicy(tuple(grants), policy_sha256=expected_sha256)
