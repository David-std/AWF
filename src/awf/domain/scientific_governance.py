"""Governance is a separate reversible procedural register, never scientific truth."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from awf.domain.evidence import EvidenceIntegrityError, sha256_bytes
from awf.domain.signed_documents import strict_json

_SHA = re.compile(r"[a-f0-9]{64}\Z")


class GovernanceState(StrEnum):
    OPEN = "OPEN"
    RATIFIED_PROCEDURAL = "RATIFIED_PROCEDURAL"
    SUSPENDED = "SUSPENDED"


class GovernanceAction(StrEnum):
    RATIFY = "RATIFY"
    SUSPEND = "SUSPEND"
    REOPEN = "REOPEN"


_TRANSITIONS = {
    (GovernanceState.OPEN, GovernanceAction.RATIFY): GovernanceState.RATIFIED_PROCEDURAL,
    (GovernanceState.RATIFIED_PROCEDURAL, GovernanceAction.SUSPEND): GovernanceState.SUSPENDED,
    (GovernanceState.SUSPENDED, GovernanceAction.REOPEN): GovernanceState.OPEN,
}


def next_governance_state(before: GovernanceState, action: GovernanceAction) -> GovernanceState:
    """A reversible procedural decision, never a historic knowledge transition."""
    try:
        return _TRANSITIONS[(before, action)]
    except (KeyError, TypeError) as exc:
        raise EvidenceIntegrityError("invalid scientific governance state transition") from exc


@dataclass(frozen=True, slots=True)
class GovernancePolicy:
    """Externally SHA-pinned local governance policy (not proof of authority)."""

    sha256: str
    quorum: int
    max_transitions: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sha256, str)
            or _SHA.fullmatch(self.sha256) is None
            or type(self.quorum) is not int
            or not 2 <= self.quorum <= 5
            or type(self.max_transitions) is not int
            or not 1 <= self.max_transitions <= 16
        ):
            raise EvidenceIntegrityError("invalid externally pinned governance policy")


def parse_governance_policy(data: bytes, *, expected_sha256: str) -> GovernancePolicy:
    """Hash must be independently retained, not read from the same editable file."""
    if not isinstance(data, bytes) or sha256_bytes(data) != expected_sha256:
        raise EvidenceIntegrityError("governance policy differs from external trusted hash")
    raw = strict_json(data)
    if set(raw) != {"schema", "quorum", "max_transitions"} or raw["schema"] != 1:
        raise EvidenceIntegrityError("unsupported scientific governance policy")
    if type(raw["schema"]) is not int:
        raise EvidenceIntegrityError("invalid governance policy schema")
    return GovernancePolicy(
        sha256=expected_sha256,
        quorum=cast(int, raw["quorum"]),
        max_transitions=cast(int, raw["max_transitions"]),
    )


@dataclass(frozen=True, slots=True)
class GovernanceResult:
    rule_id: str
    signed_actions: int
    applied_actions: int
    state: GovernanceState
    external_authority_verified: bool
    arbitration_qualified: bool
    scientific_adjudications: int = 0
    training_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "signed_actions": self.signed_actions,
            "applied_actions": self.applied_actions,
            "state": self.state.value,
            "external_authority_verified": self.external_authority_verified,
            "arbitration_qualified": self.arbitration_qualified,
            "scientific_adjudications": 0,
            "training_authorized": False,
            "source_rights_verified": False,
            "review_attestation_authorized": False,
            "historical_rule_disposition_changed": False,
            "contains_private_source_text": False,
        }
