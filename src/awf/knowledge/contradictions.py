"""Syntactic duplicate detection, not speculative semantic contradiction claims."""

from __future__ import annotations

from collections import defaultdict

from awf.domain.knowledge import KnowledgeItem


def exact_description_duplicates(
    records: tuple[KnowledgeItem, ...],
) -> tuple[tuple[str, ...], ...]:
    """Flag identical normalized source descriptions across different IDs.

    A duplicate group is an inspection signal, NOT permission to delete items.
    Opposing claims cannot be inferred from the absence of duplicate strings.
    """
    by_hash: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_hash[record.source_text_sha256].append(record.item_id)
    return tuple(
        sorted(
            (tuple(sorted(ids)) for ids in by_hash.values() if len(ids) > 1),
            key=lambda group: group[0],
        )
    )
