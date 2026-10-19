"""Pure compilation of historic requirement metadata into an auditable registry."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence

from awf.domain.knowledge import Disposition, KnowledgeItem, KnowledgeRegistry, ReviewStatus
from awf.knowledge.classify import initial_disposition, validate_human_decision
from awf.knowledge.contradictions import exact_description_duplicates


def _normalized_digest(description: str) -> str:
    normalized = " ".join(description.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compile_knowledge(
    rows: Sequence[Mapping[str, object]],
    *,
    source_id: str,
    archive_sha256: str,
    suite_version: str,
    review_decisions: Mapping[str, Mapping[str, object]] | None = None,
) -> KnowledgeRegistry:
    """Compile without publishing requirement descriptions.

    Review overlays may be supplied only with explicit reviewer and reason.
    No semantic contradiction is claimed without a separate adjudication.
    """
    ids: set[str] = set()
    output: list[KnowledgeItem] = []
    reviews = review_decisions or {}
    for row in rows:
        item_id = row.get("id")
        description = row.get("requirement")
        priority = row.get("priority")
        domain = row.get("domain")
        sources = row.get("source_ids")
        if not (
            isinstance(item_id, str)
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,80}", item_id)
            and isinstance(description, str)
            and description.strip()
            and isinstance(domain, str)
            and domain.strip()
            and isinstance(priority, str)
            and isinstance(sources, list)
            and bool(sources)
            and all(isinstance(s, str) and s.strip() for s in sources)
        ):
            raise ValueError("invalid or incomplete historic requirement")
        if item_id in ids:
            raise ValueError(f"duplicate historic requirement ID: {item_id}")
        ids.add(item_id)
        target = initial_disposition(priority)
        reviewer = reason = None
        review_status = ReviewStatus.UNREVIEWED
        if item_id in reviews:
            overlay = reviews[item_id]
            if not isinstance(overlay, Mapping):
                raise ValueError(f"malformed review: {item_id}")
            try:
                target = Disposition(str(overlay.get("disposition")))
            except ValueError as exc:
                raise ValueError(f"invalid disposition for {item_id}") from exc
            rv, rs = overlay.get("reviewer"), overlay.get("reason")
            reviewer = rv if isinstance(rv, str) else None
            reason = rs if isinstance(rs, str) else None
            validate_human_decision(target, reviewer=reviewer, reason=reason)
            if priority == "DEFERRED_LAB" and target != Disposition.EVAL_ONLY:
                raise ValueError("lab-only evidence cannot be promoted to execution or training")
            # A name and a rationale alone are a proposal, not proof of an
            # authorized adjudicator, scientific adequacy or training rights.
            review_status = ReviewStatus.REVIEW_PROPOSED
        output.append(
            KnowledgeItem(
                item_id=item_id,
                domain=domain,
                priority=priority,
                source_ids=tuple(sorted(set(sources))),
                source_text_sha256=_normalized_digest(description),
                disposition=target,
                review_status=review_status,
                reviewer=reviewer,
                decision_reason=reason,
            )
        )
    unknown_reviews = set(reviews) - ids
    if unknown_reviews:
        raise ValueError(f"review refers to missing IDs: {sorted(unknown_reviews)}")
    records = tuple(sorted(output, key=lambda row: row.item_id))
    return KnowledgeRegistry(
        source_id=source_id,
        archive_sha256=archive_sha256,
        suite_version=suite_version,
        records=records,
        possible_duplicate_groups=exact_description_duplicates(records),
    )
