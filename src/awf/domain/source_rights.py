"""Pure source-rights claims. Recorded metadata is not a legal authorization.

No licence name, copyright notice, DOI or self-assertion grants a permission.
Positive decisions require separate evidence and an external authority verifier.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from awf.domain.evidence import EvidenceIntegrityError

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class RightsUse(StrEnum):
    READ = "READ"
    EVALUATE = "EVALUATE"
    TRANSFORM = "TRANSFORM"
    REDISTRIBUTE = "REDISTRIBUTE"
    TRAIN = "TRAIN"


class RightsOutcome(StrEnum):
    UNKNOWN = "UNKNOWN"
    RESTRICTED = "RESTRICTED"
    LICENSED_FOR_EVAL = "LICENSED_FOR_EVAL"
    TRAIN_ALLOWED = "TRAIN_ALLOWED"
    RIGHTS_SUPPORTED = "RIGHTS_SUPPORTED"


class RightsClaimKind(StrEnum):
    GRANT_CLAIM = "GRANT_CLAIM"
    DENIAL = "DENIAL"


@dataclass(frozen=True, slots=True)
class SourceAsset:
    """One exact file in an exact private archive; ranges are half-open byte offsets."""

    source_id: str
    archive_sha256: str
    file_sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_id, str)
            or _ID.fullmatch(self.source_id) is None
            or not isinstance(self.archive_sha256, str)
            or _SHA.fullmatch(self.archive_sha256) is None
            or not isinstance(self.file_sha256, str)
            or _SHA.fullmatch(self.file_sha256) is None
            or type(self.size_bytes) is not int
            or not 1 <= self.size_bytes <= 128 * 1024 * 1024
        ):
            raise EvidenceIntegrityError("invalid rights source identity")


@dataclass(frozen=True, slots=True)
class RightsClaim:
    """A claimed right over one concrete byte interval; not a verified grant."""

    claim_id: str
    start_byte: int
    end_byte: int
    kind: RightsClaimKind
    uses: frozenset[RightsUse]
    owner_id: str
    authority_id: str
    license_expression: str
    jurisdiction: str
    evidence_uri: str
    evidence_sha256: str
    valid_from: int
    valid_until: int
    revoked: bool

    def validate(self, asset: SourceAsset) -> None:
        if (
            not isinstance(self.claim_id, str)
            or _ID.fullmatch(self.claim_id) is None
            or type(self.start_byte) is not int
            or type(self.end_byte) is not int
            or not 0 <= self.start_byte < self.end_byte <= asset.size_bytes
            or not isinstance(self.kind, RightsClaimKind)
            or not isinstance(self.uses, frozenset)
            or not self.uses
            or not all(isinstance(u, RightsUse) for u in self.uses)
            or not isinstance(self.owner_id, str)
            or _ID.fullmatch(self.owner_id) is None
            or not isinstance(self.authority_id, str)
            or _ID.fullmatch(self.authority_id) is None
            or not isinstance(self.license_expression, str)
            or not 1 <= len(self.license_expression) <= 256
            or not isinstance(self.jurisdiction, str)
            or not 2 <= len(self.jurisdiction) <= 128
            or not isinstance(self.evidence_uri, str)
            or not 1 <= len(self.evidence_uri) <= 2048
            or not self.evidence_uri.startswith("https://")
            or not isinstance(self.evidence_sha256, str)
            or _SHA.fullmatch(self.evidence_sha256) is None
            or type(self.valid_from) is not int
            or type(self.valid_until) is not int
            or not 0 <= self.valid_from < self.valid_until
            or type(self.revoked) is not bool
        ):
            raise EvidenceIntegrityError("invalid or unscoped source-rights claim")


@dataclass(frozen=True, slots=True)
class RightsInventory:
    asset: SourceAsset
    claims: tuple[RightsClaim, ...]
    snapshot_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.snapshot_sha256, str)
            or _SHA.fullmatch(self.snapshot_sha256) is None
            or not self.claims
            or len(self.claims) > 1024
        ):
            raise EvidenceIntegrityError("invalid rights inventory snapshot")
        seen: set[str] = set()
        for claim in self.claims:
            claim.validate(self.asset)
            if claim.claim_id in seen:
                raise EvidenceIntegrityError("duplicate source-rights claim ID")
            seen.add(claim.claim_id)


@dataclass(frozen=True, slots=True)
class RightsDecision:
    use: RightsUse
    outcome: RightsOutcome
    reason: str
    evidence_checked: int
    rights_scope_verified: bool
    training_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "use": self.use.value,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "evidence_checked": self.evidence_checked,
            "rights_scope_verified": self.rights_scope_verified,
            "training_authorized": False,
            "source_content_exported": False,
        }
