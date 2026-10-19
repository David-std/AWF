"""Signed, external chain-head claims: no SQLite, key custody or wall-clock dependencies."""

from __future__ import annotations

import re
from dataclasses import dataclass

from awf.domain.evidence import EvidenceIntegrityError, sha256_bytes
from awf.domain.signed_documents import canonical_json_bytes as _canonical
from awf.domain.signed_documents import strict_json

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_SIG = re.compile(r"[a-f0-9]{128}\Z")
_PREFIX = b"AWF/ledger-checkpoint/v1\x00"


def _valid_id(value: str) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class CheckpointGrant:
    key_id: str
    public_key_hex: str
    ledger_ids: frozenset[str]
    valid_from: int
    valid_until: int
    revoked: bool = False

    def __post_init__(self) -> None:
        if (
            not _valid_id(self.key_id)
            or not isinstance(self.public_key_hex, str)
            or _SHA.fullmatch(self.public_key_hex) is None
            or type(self.ledger_ids) is not frozenset
            or not self.ledger_ids
            or any(not _valid_id(value) for value in self.ledger_ids)
            or type(self.valid_from) is not int
            or type(self.valid_until) is not int
            or not 0 <= self.valid_from < self.valid_until
            or type(self.revoked) is not bool
        ):
            raise EvidenceIntegrityError("invalid checkpoint signer grant")


@dataclass(frozen=True, slots=True)
class CheckpointTrustPolicy:
    grants: tuple[CheckpointGrant, ...]
    policy_sha256: str

    def __post_init__(self) -> None:
        if (
            type(self.grants) is not tuple
            or not self.grants
            or len(self.grants) > 32
            or any(not isinstance(g, CheckpointGrant) for g in self.grants)
            or len({g.key_id for g in self.grants}) != len(self.grants)
            or len({g.public_key_hex for g in self.grants}) != len(self.grants)
            or not isinstance(self.policy_sha256, str)
            or _SHA.fullmatch(self.policy_sha256) is None
        ):
            raise EvidenceIntegrityError("invalid or ambiguous checkpoint trust policy")

    def authorize(self, claim: CheckpointClaim, *, now: int) -> CheckpointGrant:
        if type(now) is not int or now < 0:
            raise EvidenceIntegrityError("trusted verification time is required")
        grant = next((g for g in self.grants if g.key_id == claim.key_id), None)
        if (
            grant is None
            or grant.revoked
            or claim.ledger_id not in grant.ledger_ids
            or not grant.valid_from <= claim.issued_at <= now < grant.valid_until
        ):
            raise EvidenceIntegrityError("checkpoint signer is not currently authorized")
        return grant


@dataclass(frozen=True, slots=True)
class CheckpointClaim:
    ledger_id: str
    key_id: str
    head_digest: str
    event_count: int
    issued_at: int
    previous_checkpoint_sha256: str | None = None

    def __post_init__(self) -> None:
        if (
            not _valid_id(self.ledger_id)
            or not _valid_id(self.key_id)
            or not isinstance(self.head_digest, str)
            or _SHA.fullmatch(self.head_digest) is None
            or type(self.event_count) is not int
            or self.event_count < 1
            or type(self.issued_at) is not int
            or self.issued_at < 0
            or (
                self.previous_checkpoint_sha256 is not None
                and (
                    not isinstance(self.previous_checkpoint_sha256, str)
                    or _SHA.fullmatch(self.previous_checkpoint_sha256) is None
                )
            )
        ):
            raise EvidenceIntegrityError("invalid checkpoint claim")

    def payload(self) -> dict[str, object]:
        return {
            "schema": 1,
            "ledger_id": self.ledger_id,
            "key_id": self.key_id,
            "head_digest": self.head_digest,
            "event_count": self.event_count,
            "issued_at": self.issued_at,
            "previous_checkpoint_sha256": self.previous_checkpoint_sha256,
        }

    @property
    def signing_bytes(self) -> bytes:
        return _PREFIX + _canonical(self.payload())


@dataclass(frozen=True, slots=True)
class SignedLedgerCheckpoint:
    claim: CheckpointClaim
    signature_hex: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.claim, CheckpointClaim)
            or not isinstance(self.signature_hex, str)
            or _SIG.fullmatch(self.signature_hex) is None
        ):
            raise EvidenceIntegrityError("invalid checkpoint signature encoding")

    def to_bytes(self) -> bytes:
        return _canonical({"claim": self.claim.payload(), "signature_hex": self.signature_hex})

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.to_bytes())

    @classmethod
    def from_bytes(cls, data: bytes) -> SignedLedgerCheckpoint:
        body = strict_json(data)
        if (
            set(body) != {"claim", "signature_hex"}
            or not isinstance(body["claim"], dict)
            or not isinstance(body["signature_hex"], str)
        ):
            raise EvidenceIntegrityError("invalid signed checkpoint fields")
        record = body["claim"]
        fields = {
            "schema",
            "ledger_id",
            "key_id",
            "head_digest",
            "event_count",
            "issued_at",
            "previous_checkpoint_sha256",
        }
        if set(record) != fields or type(record["schema"]) is not int or record["schema"] != 1:
            raise EvidenceIntegrityError("unknown checkpoint claim schema")
        return cls(
            claim=CheckpointClaim(
                ledger_id=record["ledger_id"],
                key_id=record["key_id"],
                head_digest=record["head_digest"],
                event_count=record["event_count"],
                issued_at=record["issued_at"],
                previous_checkpoint_sha256=record["previous_checkpoint_sha256"],
            ),
            signature_hex=body["signature_hex"],
        )


def parse_checkpoint_policy(data: bytes, *, expected_sha256: str) -> CheckpointTrustPolicy:
    if not isinstance(expected_sha256, str) or _SHA.fullmatch(expected_sha256) is None:
        raise EvidenceIntegrityError("checkpoint policy digest must be externally pinned")
    if sha256_bytes(data) != expected_sha256:
        raise EvidenceIntegrityError("checkpoint trust policy digest mismatch")
    body = strict_json(data)
    if set(body) != {"schema", "grants"} or type(body["schema"]) is not int or body["schema"] != 1:
        raise EvidenceIntegrityError("unsupported checkpoint trust policy")
    rows = body["grants"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
        raise EvidenceIntegrityError("checkpoint trust policy has invalid grant count")
    grants: list[CheckpointGrant] = []
    for row in rows:
        fields = {
            "key_id",
            "public_key_hex",
            "ledger_ids",
            "valid_from",
            "valid_until",
            "revoked",
        }
        if not isinstance(row, dict) or set(row) != fields:
            raise EvidenceIntegrityError("invalid checkpoint grant shape")
        ledger_ids = row["ledger_ids"]
        if (
            not isinstance(ledger_ids, list)
            or not all(isinstance(v, str) for v in ledger_ids)
            or len(ledger_ids) != len(set(ledger_ids))
        ):
            raise EvidenceIntegrityError("invalid or duplicate permitted ledger ids")
        grants.append(
            CheckpointGrant(
                key_id=row["key_id"],
                public_key_hex=row["public_key_hex"],
                ledger_ids=frozenset(ledger_ids),
                valid_from=row["valid_from"],
                valid_until=row["valid_until"],
                revoked=row["revoked"],
            )
        )
    return CheckpointTrustPolicy(tuple(grants), expected_sha256)
