"""Metadata-only, fail-closed candidate-gold intake and blinded annotation audit.

This module cannot prove source rights, human independence or semantic truth.
It never loads source text, candidate text, sealed holdouts or model outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}\Z")
_FAMILIES = frozenset(
    {
        "negation",
        "quantity",
        "citation",
        "causality",
        "population",
        "modality",
        "temporal_scope",
        "source_support",
    }
)
_LABELS = frozenset({"PRESERVED", "DRIFT", "UNKNOWN"})
_REASON_CODES = frozenset(
    {
        "SUPPORTED",
        "UNSUPPORTED",
        "NEGATION_CHANGED",
        "QUANTITY_CHANGED",
        "CITATION_CHANGED",
        "CAUSALITY_CHANGED",
        "SCOPE_CHANGED",
        "INSUFFICIENT_EVIDENCE",
        "OTHER",
    }
)
_CASE_KEYS = frozenset(
    {
        "case_id",
        "document_group",
        "author_group",
        "source_group",
        "language",
        "genre",
        "split",
        "risk_families",
        "blind_conditions",
        "original_sha256",
        "source_evidence_sha256",
        "rights_evidence_sha256",
        "rights_basis",
    }
)
_ANNOTATION_KEYS = frozenset(
    {
        "case_id",
        "blind_condition",
        "risk_family",
        "reviewer_id",
        "label",
        "rationale_code",
        "evidence_sha256",
    }
)


def _read_pinned(path: Path, sha256: str, *, max_size: int) -> dict[str, Any]:
    if not isinstance(sha256, str) or _SHA.fullmatch(sha256) is None:
        raise ValueError("an external SHA-256 pin is mandatory")
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be a regular non-symlink file")
    if not 0 < path.stat().st_size <= max_size:
        raise ValueError("input exceeds configured size bounds")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("externally pinned SHA-256 mismatch")

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("input is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("input must contain a JSON object")
    return value


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _digest(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _safe_case(case: Any, *, role: str) -> None:
    if not isinstance(case, dict) or set(case) != _CASE_KEYS:
        raise ValueError("invalid candidate-gold case schema")
    if not all(
        _identifier(case[key])
        for key in ("case_id", "document_group", "author_group", "source_group", "genre")
    ):
        raise ValueError("invalid case identity")
    if case["language"] not in {"es", "en"}:
        raise ValueError("unsupported case language")
    if case["split"] not in {"train", "validation", "test_sealed"}:
        raise ValueError("invalid split")
    if not all(
        _digest(case[key])
        for key in ("original_sha256", "source_evidence_sha256", "rights_evidence_sha256")
    ):
        raise ValueError("invalid source or rights SHA")
    if case["blind_conditions"] != ["A", "B"]:
        raise ValueError("blind comparison requires two opaque A/B conditions")
    families = case["risk_families"]
    if (
        not isinstance(families, list)
        or not families
        or len(families) > len(_FAMILIES)
        or any(not isinstance(x, str) or x not in _FAMILIES for x in families)
        or len(families) != len(set(families))
    ):
        raise ValueError("invalid or duplicate risk families")
    if role == "SYNTHETIC_DEVELOPMENT":
        if case["rights_basis"] != "SYNTHETIC_FIXTURE":
            raise ValueError("synthetic rights basis is required")
    elif case["rights_basis"] not in {"OWNER_ATTESTED", "THIRD_PARTY_PERMISSION_CLAIM"}:
        raise ValueError("real-world rights basis must be declared")


def _validate_manifest(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    if set(manifest) != {"schema_version", "dataset_role", "cases"}:
        raise ValueError("unrecognized candidate-gold manifest schema")
    if manifest["schema_version"] != "1.0.0":
        raise ValueError("unsupported candidate-gold manifest version")
    role = manifest["dataset_role"]
    if role not in {"SYNTHETIC_DEVELOPMENT", "CANDIDATE_REVIEW"}:
        raise ValueError("unsupported role: reviewed gold cannot be self-declared")
    cases = manifest["cases"]
    if not isinstance(cases, list) or not 2 <= len(cases) <= 512:
        raise ValueError("candidate manifest needs 2..512 cases")
    ids: set[str] = set()
    across_splits: dict[tuple[str, str], str] = {}
    cases_by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        _safe_case(case, role=role)
        identity = case["case_id"]
        if identity in ids:
            raise ValueError("duplicate candidate-gold case identity")
        ids.add(identity)
        cases_by_id[identity] = case
        for dimension in (
            "document_group",
            "author_group",
            "source_group",
            "original_sha256",
            "source_evidence_sha256",
        ):
            key = (dimension, case[dimension])
            previous = across_splits.setdefault(key, case["split"])
            if previous != case["split"]:
                raise ValueError("train/validation/holdout group leakage")
    return list(cases_by_id.values()), role


def _validate_reviews(
    reviews: dict[str, Any], cases: list[dict[str, Any]]
) -> tuple[dict[tuple[str, str, str], str], dict[str, Any]]:
    if set(reviews) != {"schema_version", "review_role", "annotations"}:
        raise ValueError("unrecognized blind annotation schema")
    if (
        reviews["schema_version"] != "1.0.0"
        or reviews["review_role"] != "BLIND_CANDIDATE_ANNOTATIONS"
    ):
        raise ValueError("cannot claim independent gold with a review string")
    data = reviews["annotations"]
    if not isinstance(data, list) or not 1 <= len(data) <= 4096:
        raise ValueError("invalid annotation count")
    indexed = {case["case_id"]: case for case in cases}
    votes: dict[tuple[str, str, str], dict[str, str]] = {}
    all_reviewers: set[str] = set()
    for annotation in data:
        if not isinstance(annotation, dict) or set(annotation) != _ANNOTATION_KEYS:
            raise ValueError("unexpected annotation fields")
        case_id = annotation["case_id"]
        if not isinstance(case_id, str) or case_id not in indexed:
            raise ValueError("annotation references unknown case")
        case = indexed[case_id]
        if case["split"] == "test_sealed":
            raise ValueError("sealed holdout cannot enter development review")
        condition = annotation["blind_condition"]
        family = annotation["risk_family"]
        reviewer = annotation["reviewer_id"]
        if (
            condition not in {"A", "B"}
            or family not in case["risk_families"]
            or not _identifier(reviewer)
            or annotation["label"] not in _LABELS
            or annotation["rationale_code"] not in _REASON_CODES
            or not _digest(annotation["evidence_sha256"])
        ):
            raise ValueError("invalid blind annotation values")
        key = (case_id, condition, family)
        row = votes.setdefault(key, {})
        if reviewer in row or len(row) >= 2:
            raise ValueError("duplicate or excessive reviewer vote")
        row[reviewer] = annotation["label"]
        all_reviewers.add(reviewer)
    assessed: dict[tuple[str, str, str], str] = {}
    disagreements = 0
    missing = 0
    unresolved = 0
    for case in cases:
        if case["split"] == "test_sealed":
            continue
        for condition in ("A", "B"):
            for family in case["risk_families"]:
                key = (case["case_id"], condition, family)
                entries = tuple(votes.get(key, {}).values())
                if len(entries) != 2:
                    assessed[key] = "UNKNOWN"
                    missing += 1
                elif entries[0] != entries[1]:
                    assessed[key] = "UNKNOWN"
                    disagreements += 1
                elif entries[0] == "UNKNOWN":
                    assessed[key] = "UNKNOWN"
                    unresolved += 1
                else:
                    assessed[key] = entries[0]
    return assessed, {
        "distinct_declared_reviewer_ids": len(all_reviewers),
        "missing_double_reviews": missing,
        "discordant_double_reviews": disagreements,
        "concordant_unknowns": unresolved,
        "reviewer_identity_independently_verified": False,
        "reviewer_competence_verified": False,
        "human_gold_adjudicated": False,
    }


def _case_status(
    case: dict[str, Any], condition: str, assessed: dict[tuple[str, str, str], str]
) -> str:
    states = [
        assessed.get((case["case_id"], condition, family), "UNKNOWN")
        for family in case["risk_families"]
    ]
    if "DRIFT" in states:
        return "DRIFT"
    if "UNKNOWN" in states:
        return "UNKNOWN"
    return "PRESERVED"


def audit_candidate_gold(
    manifest: dict[str, Any], *, review: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Return privacy-preserving readiness counts; never promote review strings to gold."""
    cases, role = _validate_manifest(manifest)
    if review is None:
        assessed: dict[tuple[str, str, str], str] = {}
        review_summary = {
            "distinct_declared_reviewer_ids": 0,
            "missing_double_reviews": sum(
                2 * len(case["risk_families"]) for case in cases if case["split"] != "test_sealed"
            ),
            "discordant_double_reviews": 0,
            "concordant_unknowns": 0,
            "reviewer_identity_independently_verified": False,
            "reviewer_competence_verified": False,
            "human_gold_adjudicated": False,
        }
    else:
        assessed, review_summary = _validate_reviews(review, cases)

    counts = Counter(case["split"] for case in cases)
    languages = Counter(case["language"] for case in cases if case["split"] != "test_sealed")
    outcomes: Counter[str] = Counter()
    by_condition: dict[str, Counter[str]] = {"A": Counter(), "B": Counter()}
    for case in cases:
        if case["split"] == "test_sealed":
            continue
        a = _case_status(case, "A", assessed)
        b = _case_status(case, "B", assessed)
        by_condition["A"][a] += 1
        by_condition["B"][b] += 1
        if "UNKNOWN" in (a, b):
            outcomes["unknown_pair"] += 1
        elif a == "DRIFT" and b == "DRIFT":
            outcomes["both_drift"] += 1
        elif a == "PRESERVED" and b == "PRESERVED":
            outcomes["both_preserved"] += 1
        elif a == "DRIFT":
            outcomes["condition_a_only_drift"] += 1
        else:
            outcomes["condition_b_only_drift"] += 1
    return {
        "schema_version": "1.0.0",
        "status": "CANDIDATE_REVIEW_DIAGNOSTIC_ONLY",
        "dataset_role": role,
        "split_counts": dict(sorted(counts.items())),
        "development_language_counts": dict(sorted(languages.items())),
        "blind_condition_counts": {
            key: dict(sorted(count.items())) for key, count in by_condition.items()
        },
        "paired_discordance": dict(sorted(outcomes.items())),
        "review_coverage": review_summary,
        "split_group_overlap_observed": False,
        "source_rights_independently_verified": False,
        "source_evidence_bytes_verified": False,
        "blind_condition_mapping_unsealed": False,
        "test_holdout_opened": False,
        "independent_gold_verified": False,
        "semantic_equivalence_verified": False,
        "model_quality_certified": False,
        "document_acceptance": "NEEDS_REVIEW",
        "source_text_exported": False,
        "next_gate": "EXTERNAL_RIGHTS_AND_REVIEWER_VERIFICATION_REQUIRED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="awf-gold-intake")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--reviews-sha256")
    args = parser.parse_args(argv)
    if (args.reviews is None) != (args.reviews_sha256 is None):
        parser.error("review file and independently pinned hash must be supplied together")
    try:
        manifest = _read_pinned(args.manifest, args.manifest_sha256, max_size=2 * 1024 * 1024)
        review = (
            _read_pinned(args.reviews, args.reviews_sha256, max_size=2 * 1024 * 1024)
            if args.reviews is not None
            else None
        )
        result = audit_candidate_gold(manifest, review=review)
        result["manifest_sha256"] = args.manifest_sha256
        result["reviews_sha256"] = args.reviews_sha256
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"AWF_ERROR [GOLD_INTAKE_FAILED] {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
