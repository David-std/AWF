"""Conservative applicability evaluation for reviewed knowledge items."""

from __future__ import annotations

from awf.domain.knowledge import Applicability, KnowledgeItem


def applicability_for(item: KnowledgeItem, *, context_verified: bool) -> Applicability:
    """Only a verified context can enable a reviewed, executable policy.

    This intentionally does NOT infer applicability from title/keyword similarity.
    """
    if item.disposition in {item.disposition.EVAL_ONLY, item.disposition.REMOVE_FROM_ACTIVE}:
        return Applicability.NOT_APPLICABLE
    if item.review_status != "HUMAN_REVIEWED" or not context_verified:
        return Applicability.UNKNOWN
    if item.disposition == item.disposition.KEEP_AS_CODE:
        return Applicability.APPLICABLE
    return Applicability.UNKNOWN
