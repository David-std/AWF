"""Conservative classification; no skill rules are automatically made executable."""

from __future__ import annotations

from awf.domain.knowledge import Disposition


def initial_disposition(priority: str) -> Disposition:
    """Lab-only material stays evaluation-only; every MUST needs human review."""
    if priority == "DEFERRED_LAB":
        return Disposition.EVAL_ONLY
    if priority == "MUST":
        return Disposition.UNRESOLVED
    raise ValueError(f"unknown requirement priority: {priority!r}")


def validate_human_decision(
    target: Disposition, *, reviewer: str | None, reason: str | None
) -> None:
    """Reject untraceable promotion; a training decision still needs data rights review."""
    if target == Disposition.UNRESOLVED:
        raise ValueError("a review decision must select a non-UNRESOLVED disposition")
    if reviewer is None or len(reviewer.strip()) < 2:
        raise ValueError("reviewer identity is required")
    if reason is None or len(reason.strip()) < 20:
        raise ValueError("a substantive review reason (at least 20 characters) is required")
