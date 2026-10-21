"""Owner-controlled *evaluation* approvals, never scientific or legal authorizations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgentVerdict(StrEnum):
    SUPPORT = "SUPPORT"
    CONTEST = "CONTEST"
    INCONCLUSIVE = "INCONCLUSIVE"


class OwnerAction(StrEnum):
    APPROVE_PILOT_EVALUATION = "APPROVE_PILOT_EVALUATION"
    REQUEST_REVISION = "REQUEST_REVISION"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class OwnerReviewResult:
    rule_id: str
    owner_actor_id: str
    verified_agent_reports: int
    verdicts: tuple[AgentVerdict, ...]
    distinct_model_ids: int
    owner_action: OwnerAction
    pilot_evaluation_approved: bool
    independent_scientific_adjudication: bool = False
    training_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "rule_id": self.rule_id,
            "owner_actor_id": self.owner_actor_id,
            "verified_agent_reports": self.verified_agent_reports,
            "verdicts": [value.value for value in self.verdicts],
            "distinct_model_ids": self.distinct_model_ids,
            "owner_action": self.owner_action.value,
            "pilot_evaluation_approved": self.pilot_evaluation_approved,
            "independent_scientific_adjudication": False,
            "scientific_adjudications": 0,
            "training_authorized": False,
            "source_rights_verified": False,
            "review_attestation_authorized": False,
            "historical_rule_disposition_changed": False,
            "contains_private_source_text": False,
        }
