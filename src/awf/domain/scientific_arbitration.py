"""Immutable procedural arbitration status; never an assertion of scientific truth."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ArbitrationPosition(StrEnum):
    SUPPORT = "SUPPORT"
    CONTEST = "CONTEST"
    DEFER = "DEFER"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class ArbitrationResult:
    rule_id: str
    authenticated_decisions: int
    latest_position: ArbitrationPosition
    appeal_count: int
    independently_qualified: bool
    procedure_verified: bool
    scientific_adjudications: int = 0
    training_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "authenticated_decisions": self.authenticated_decisions,
            "latest_position": self.latest_position.value,
            "appeal_count": self.appeal_count,
            "independently_qualified": self.independently_qualified,
            "procedure_verified": self.procedure_verified,
            "scientific_adjudications": 0,
            "review_attestation_authorized": False,
            "training_authorized": False,
            "source_rights_verified": False,
            "historical_rule_disposition_changed": False,
            "contains_private_source_text": False,
        }
