"""Private historical-source pilot: measure exact-invariant probe boundaries.

Works only on rows from the separately verified ZIP adapter. Neither source
statements nor adversarial candidate texts are exported into the report.
This measures engineering behavior, not academic quality or model performance.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from awf.verification.exact_checks import parse_contract, verify_exact_invariants

PILOT_IDS: tuple[str, ...] = ("DSR-001", "DSR-055", "DSR-059", "DSR-063", "DSR-065", "DSR-066")
_TOKEN = re.compile(r"[A-Za-z]{5,}")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _select_anchor(text: str) -> tuple[str, str, str]:
    """Prefer a unique lexical anchor near the sentence midpoint."""
    center = len(text) // 2
    tokens = sorted(
        _TOKEN.finditer(text),
        key=lambda m: (abs((m.start() + m.end()) // 2 - center), m.start()),
    )
    for match in tokens:
        left = text[max(0, match.start() - 12) : match.start()]
        value = match.group()
        right = text[match.end() : match.end() + 12]
        if left and right and text.count(value) == 1 and text.count(left + value + right) == 1:
            return left, value, right
    raise ValueError("historical statement lacks a unique protected local anchor")


def run_historical_pilot(
    rows: Sequence[Mapping[str, object]],
    *,
    source_sha256: str,
    suite_version: str,
    rule_ids: Sequence[str] = PILOT_IDS,
) -> dict[str, Any]:
    """Five deterministic cases per authentic pinned-ledger requirement.

    PASS for an unlisted distant contradiction is recorded as a *scope gap*;
    never transform PASS into semantic/document acceptance.
    """
    if suite_version != "3.19.1" or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None:
        raise ValueError("pilot requires the pinned AWS 3.19.1 source")
    if not rule_ids or len(set(rule_ids)) != len(rule_ids):
        raise ValueError("rule IDs must be nonempty and distinct")
    by_id: dict[str, Mapping[str, object]] = {}
    for row in rows:
        item_id = row.get("id")
        if not isinstance(item_id, str) or item_id in by_id:
            raise ValueError("missing or duplicate historical ID")
        by_id[item_id] = row
    cases: list[dict[str, object]] = []
    selected: list[dict[str, object]] = []
    for item_id in rule_ids:
        if item_id not in by_id:
            raise ValueError("selected rule not present in pinned ledger")
        row = by_id[item_id]
        statement = row.get("requirement")
        if (
            row.get("priority") != "MUST"
            or not isinstance(statement, str)
            or not statement.strip()
            or not isinstance(row.get("source_ids"), list)
            or not isinstance(row.get("implementation_paths"), list)
        ):
            raise ValueError("incomplete real historical pilot requirement")
        left, value, right = _select_anchor(statement)
        original = statement.encode("utf-8")
        contract = parse_contract(
            {
                "schema_version": "1.0.0",
                "baseline_sha256": _digest(original),
                "checks": [
                    {
                        "id": item_id,
                        "kind": "QUOTE",
                        "value": value,
                        "left_context": left,
                        "right_context": right,
                    }
                ],
            }
        )
        span = left + value + right
        mutations = {
            "unchanged_control": statement,
            "protected_literal_mutation": statement.replace(span, left + "[ALTERED]" + right, 1),
            "local_context_mutation": statement.replace(span, left + "X" + value + right, 1),
            "unlisted_numeric_addition": statement + " 987654.",
            "distant_semantic_override": statement + " This requirement is optional.",
        }
        for kind, modified in mutations.items():
            result = verify_exact_invariants(original, modified.encode("utf-8"), contract)
            cases.append(
                {
                    "rule_id": item_id,
                    "case_id": kind,
                    "baseline_sha256": _digest(original),
                    "candidate_sha256": _digest(modified.encode("utf-8")),
                    "scope_status": result["scope_status"],
                    "document_acceptance": result["document_acceptance"],
                    "review_signals": result["review_signals"],
                    "semantic_equivalence_verified": result["semantic_equivalence_verified"],
                }
            )
        original_source_ids = row["source_ids"]
        historical_paths = row["implementation_paths"]
        if not isinstance(original_source_ids, list) or not all(
            isinstance(v, str) for v in original_source_ids
        ) or not isinstance(historical_paths, list):
            raise ValueError("malformed historical reference inventory")
        selected.append(
            {
                "id": item_id,
                "rule_sha256": _digest(original),
                "source_ids": sorted(set(original_source_ids)),
                "historical_surface_count": len(historical_paths),
                "legacy_status_claim": row.get("status"),
                "awf_review_status": "UNREVIEWED",
            }
        )
    counts = Counter(str(case["scope_status"]) for case in cases)
    distant_gaps = sum(
        case["case_id"] == "distant_semantic_override" and case["scope_status"] == "PASS"
        for case in cases
    )
    return {
        "schema_version": "1.0.0",
        "pilot_id": "aws3191-actual-ledger-syntax-v1",
        "source_sha256": source_sha256,
        "suite_version": suite_version,
        "real_source_rule_count": len(selected),
        "case_count": len(cases),
        "counts_by_scope_status": dict(sorted(counts.items())),
        "synthetic_semantic_override_syntactic_pass_count": distant_gaps,
        "synthetic_semantic_override_total": len(selected),
        "gold_semantic_labels_independently_reviewed": False,
        "legacy_code_executed": False,
        "original_text_exported": False,
        "rule_adjudications_issued": 0,
        "training_authorized": False,
        "source_truth_verified": False,
        "status": "EXPERIMENTAL_SCOPE_MEASUREMENT_ONLY",
        "selected": selected,
        "cases": cases,
    }
