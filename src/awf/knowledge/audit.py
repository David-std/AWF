"""Self-consistency audit for metadata-only knowledge registry exports.

A registry export can be edited, so this audit proves structural consistency,
not identity of a third-party source unless the archive is rechecked.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping

from awf.domain.knowledge import Disposition


def audit_registry(report: Mapping[str, object]) -> dict[str, object]:
    errors: list[str] = []
    records = report.get("records")
    if not isinstance(records, list):
        return {"valid": False, "errors": ["missing records list"]}
    ids: set[str] = set()
    counts: Counter[str] = Counter()
    for i, raw in enumerate(records):
        if not isinstance(raw, dict):
            errors.append(f"invalid record at index {i}")
            continue
        identifier = raw.get("id")
        digest = raw.get("source_text_sha256")
        disposition = raw.get("disposition")
        priority = raw.get("priority")
        if not isinstance(identifier, str) or identifier in ids:
            errors.append(f"duplicate/invalid ID at index {i}")
        else:
            ids.add(identifier)
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            errors.append(f"invalid source text digest at index {i}")
        try:
            selected = Disposition(disposition)
            counts[selected.value] += 1
        except (ValueError, TypeError):
            errors.append(f"invalid disposition at index {i}")
            continue
        if priority not in {"MUST", "DEFERRED_LAB"}:
            errors.append(f"unknown priority at index {i}")
        if raw.get("review_status") != "REVIEW_ATTESTED":
            if (priority == "MUST" and selected != Disposition.UNRESOLVED) or (
                priority == "DEFERRED_LAB" and selected != Disposition.EVAL_ONLY
            ):
                errors.append(f"unreviewed promotion at index {i}")
        elif not raw.get("reviewer") or not raw.get("decision_reason"):
            errors.append(f"reviewed disposition missing reviewer/reason at index {i}")
    expected = report.get("disposition_counts")
    if not isinstance(expected, dict) or any(expected.get(k) != counts[k] for k in Disposition):
        errors.append("disposition counts do not match records")
    if report.get("requirements_count") != len(records):
        errors.append("requirements count does not match records")
    unreviewed = sum(
        isinstance(r, dict) and r.get("review_status") != "REVIEW_ATTESTED" for r in records
    )
    if report.get("unreviewed_count") != unreviewed:
        errors.append("unreviewed count does not match records")
    digest = report.get("archive_sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        errors.append("archive SHA-256 is invalid")
    if report.get("schema_version") != "1.0.0":
        errors.append("unsupported report schema version")
    return {
        "valid": not errors,
        "errors": errors,
        "requirements_count": len(records),
        "unreviewed_count": unreviewed,
        "disposition_counts": dict(counts),
    }
