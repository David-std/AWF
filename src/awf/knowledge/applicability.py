"""Conservative applicability evaluation for reviewed knowledge items."""

from __future__ import annotations

from awf.domain.knowledge import Applicability, Disposition, KnowledgeItem, ReviewStatus


def applicability_for(item: KnowledgeItem, *, context_verified: bool) -> Applicability:
    """Only a verified context can enable a reviewed, executable policy.

    This intentionally does NOT infer applicability from title/keyword similarity.
    """
    if item.disposition in {Disposition.EVAL_ONLY, Disposition.REMOVE_FROM_ACTIVE}:
        return Applicability.NOT_APPLICABLE
    if item.review_status != ReviewStatus.REVIEW_ATTESTED or not context_verified:
        return Applicability.UNKNOWN
    if item.disposition == Disposition.KEEP_AS_CODE:
        return Applicability.APPLICABLE
    return Applicability.UNKNOWN
