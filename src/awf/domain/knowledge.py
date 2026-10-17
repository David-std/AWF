"""Pure, immutable metadata types for the research knowledge registry.

The registry intentionally contains *no* source text or model prompts.
Classification is a reviewed research decision, not a string heuristic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Disposition(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    EVAL_ONLY = "EVAL_ONLY"
    KEEP_AS_CODE = "KEEP_AS_CODE"
    KEEP_AS_CONTEXT = "KEEP_AS_CONTEXT"
    TRAIN = "TRAIN"
    REMOVE_FROM_ACTIVE = "REMOVE_FROM_ACTIVE"


class Applicability(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class KnowledgeItem:
    """Identifier and evidence pointers for one historic requirement.

    `source_text_sha256` identifies the precise requirement description,
    without copying its text into a public or exported registry.
    """

    item_id: str
    domain: str
    priority: str
    source_ids: tuple[str, ...]
    source_text_sha256: str
    disposition: Disposition
    review_status: str
    reviewer: str | None = None
    decision_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.item_id,
            "domain": self.domain,
            "priority": self.priority,
            "source_ids": list(self.source_ids),
            "source_text_sha256": self.source_text_sha256,
            "disposition": self.disposition.value,
            "review_status": self.review_status,
            "reviewer": self.reviewer,
            "decision_reason": self.decision_reason,
        }


@dataclass(frozen=True, slots=True)
class KnowledgeRegistry:
    """A metadata-only, immutable report bound to original ZIP bytes."""

    source_id: str
    archive_sha256: str
    suite_version: str
    records: tuple[KnowledgeItem, ...]
    possible_duplicate_groups: tuple[tuple[str, ...], ...]

    def counts(self) -> dict[str, int]:
        counts = {decision.value: 0 for decision in Disposition}
        for item in self.records:
            counts[item.disposition.value] += 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "source_id": self.source_id,
            "archive_sha256": self.archive_sha256,
            "suite_version": self.suite_version,
            "rights_status": "local_private_source_not_redistributed",
            "requirements_count": len(self.records),
            "disposition_counts": self.counts(),
            "unreviewed_count": sum(
                item.review_status != "REVIEW_ATTESTED" for item in self.records
            ),
            "possible_duplicate_groups": [
                list(group) for group in self.possible_duplicate_groups
            ],
            "records": [item.to_dict() for item in self.records],
            "guarantees": {
                "source_text_not_exported": True,
                "semantic_contradictions_verified": False,
                "model_training_authorized": False,
                "operational_behavior_validated": False,
            },
        }
