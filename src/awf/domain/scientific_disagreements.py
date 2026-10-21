"""Provisional epistemic comparisons; none adjudicate source claims or rights."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ComparisonStatus(StrEnum):
    CONCORDANT_SUPPORT = "CONCORDANT_SUPPORT"
    CONCORDANT_CONTEST = "CONCORDANT_CONTEST"
    DIVERGENT = "DIVERGENT"
    INCONCLUSIVE = "INCONCLUSIVE"


class ProposedNextAction(StrEnum):
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE"
    REPLICATE_EXPERIMENT = "REPLICATE_EXPERIMENT"
    ESCALATE_PANEL = "ESCALATE_PANEL"
    RETAIN_DISAGREEMENT = "RETAIN_DISAGREEMENT"


@dataclass(frozen=True, slots=True)
class DisagreementProtocolResult:
    checked: int
    comparisons: tuple[tuple[str, ComparisonStatus], ...]
    case_rule_ids: tuple[str, ...]
    missing_case_rule_ids: tuple[str, ...]
    evidence_links_verified: bool
    scientific_adjudications: int = 0
    review_attestation_authorized: bool = False
    training_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "checked": self.checked,
            "comparisons": [
                {"rule_id": rule, "status": status.value} for rule, status in self.comparisons
            ],
            "case_rule_ids": list(self.case_rule_ids),
            "missing_case_rule_ids": list(self.missing_case_rule_ids),
            "evidence_links_verified": self.evidence_links_verified,
            "scientific_adjudications": 0,
            "review_attestation_authorized": False,
            "training_authorized": False,
            "source_rights_verified": False,
            "contains_private_source_text": False,
        }
