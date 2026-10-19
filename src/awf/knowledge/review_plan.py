"""Deterministic, local-only review packets for legacy rules.

This is a *review preparation* tool. It does not make semantic decisions,
grant dataset rights, or mark any knowledge as reviewed/executable.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from awf.domain.knowledge import KnowledgeRegistry

_REVIEW_QUESTIONS = (
    "Is the original rule applicable to AWF's goals and current architecture?",
    "What evidence supports it, and which sources or snapshots may be obsolete?",
    "Is it redundant with or in tension with another identified rule?",
    "Can a deterministic test verify behavior, or is a model/human judgment needed?",
    "Which negative tests would falsify a false PASS?",
    "Is the rule a production constraint, contextual reference, training candidate, or lab-only?",
    "What source/data rights permit the chosen use?",
)


def _digest(description: str) -> str:
    normalized = " ".join(description.split()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _as_list(value: object) -> list[str]:
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return value
    return []


def make_review_packets(
    rows: Sequence[Mapping[str, object]],
    *,
    registry: KnowledgeRegistry,
    batch_size: int = 12,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Build a private review workbench without implicitly accepting any rules.

    The manifest is metadata-only; individual batch JSONs contain full source
    rule text, and MUST remain inside the user's Git-ignored local .awf folder.
    """
    if not 1 <= batch_size <= 50:
        raise ValueError("batch_size must be between 1 and 50")
    by_id = {record.item_id: record for record in registry.records}
    seen: set[str] = set()
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    boundary_counts: Counter[str] = Counter()

    for row in rows:
        identifier, requirement = row.get("id"), row.get("requirement")
        if not isinstance(identifier, str) or not isinstance(requirement, str):
            raise ValueError("review plan requires a rule ID and text")
        if identifier in seen or identifier not in by_id:
            raise ValueError(f"duplicate or unknown review rule: {identifier}")
        seen.add(identifier)
        record = by_id[identifier]
        if _digest(requirement) != record.source_text_sha256:
            raise ValueError(f"source text hash changed for {identifier}")
        if row.get("priority") != record.priority or row.get("domain") != record.domain:
            raise ValueError(f"rule metadata differs from compiled registry: {identifier}")
        boundary = row.get("second_pass_class")
        if boundary not in {
            "ROBUST_MECHANICAL_CONTRACT",
            "STRUCTURAL_ENFORCED_BOUNDED",
            "DEFERRED_EMPIRICAL",
        }:
            raise ValueError(f"unknown verification boundary for {identifier}")
        boundary_counts[str(boundary)] += 1

        lane = (
            "DEFERRED_RESEARCH"
            if record.priority == "DEFERRED_LAB"
            else "STRUCTURAL_BOUNDARY"
            if boundary == "STRUCTURAL_ENFORCED_BOUNDED"
            else "MECHANICAL_CLAIM_REVIEW"
        )
        groups[record.domain].append(
            {
                "id": identifier,
                "domain": record.domain,
                "priority": record.priority,
                "requirement": requirement,
                "requirement_sha256": record.source_text_sha256,
                "source_ids": list(record.source_ids),
                "legacy_implementation_paths": _as_list(row.get("implementation_paths")),
                "legacy_verification_ids": _as_list(row.get("verification")),
                "legacy_status_claim": row.get("status"),
                "legacy_verification_strength": row.get("verification_strength"),
                "legacy_second_pass_class": boundary,
                "legacy_acceptance_metric": row.get("acceptance_metric"),
                "legacy_residual_uncertainty": row.get("residual_uncertainty"),
                "negative_test_expected": row.get("negative_test_expected"),
                "review_lane": lane,
                "awf_disposition": record.disposition.value,
                "review_status": "OPEN",
                "review_questions": list(_REVIEW_QUESTIONS),
                "review_template": {
                    "reviewer": None,
                    "reason": None,
                    "evidence_ids": [],
                    "conflicting_rule_ids": [],
                    "desired_disposition": None,
                    "proposed_tests": [],
                    "source_rights_status": "NOT_EVALUATED",
                    "current_model_or_version_evidence": None,
                },
            }
        )

    missing = set(by_id) - seen
    if missing:
        raise ValueError(f"missing {len(missing)} original rules from review plan")

    manifest_batches: list[dict[str, object]] = []
    packets: dict[str, dict[str, Any]] = {}
    batch_index = 0
    for domain in sorted(groups):
        ordered = sorted(groups[domain], key=lambda item: str(item["id"]))
        for offset in range(0, len(ordered), batch_size):
            batch_index += 1
            subset = ordered[offset : offset + batch_size]
            filename = f"batch-{batch_index:03d}.json"
            packets[filename] = {
                "schema_version": "1.0.0",
                "source_id": registry.source_id,
                "archive_sha256": registry.archive_sha256,
                "suite_version": registry.suite_version,
                "domain": domain,
                "batch_id": f"AWF-REVIEW-{batch_index:03d}",
                "contains_private_source_text": True,
                "rules": subset,
            }
            manifest_batches.append(
                {
                    "file": filename,
                    "batch_id": f"AWF-REVIEW-{batch_index:03d}",
                    "domain": domain,
                    "count": len(subset),
                    "ids": [item["id"] for item in subset],
                    "status": "OPEN",
                }
            )

    manifest: dict[str, Any] = {
        "schema_version": "1.0.0",
        "source_id": registry.source_id,
        "archive_sha256": registry.archive_sha256,
        "suite_version": registry.suite_version,
        "source_text_in_manifest": False,
        "private_review_packets": True,
        "no_training_or_execution_authorized": True,
        "requirements_count": len(registry.records),
        "priority_counts": dict(sorted(Counter(r.priority for r in registry.records).items())),
        "legacy_verification_class_counts": dict(sorted(boundary_counts.items())),
        "domains": {domain: len(groups[domain]) for domain in sorted(groups)},
        "batches": manifest_batches,
        "reviewed_count": 0,
        "open_count": len(registry.records),
    }
    return manifest, packets
