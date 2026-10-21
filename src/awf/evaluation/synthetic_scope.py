"""Evaluate bounded synthetic edits against the *actual* exact-invariant checker.

This is a development diagnostic, never an independent semantic benchmark.
Dataset labels are explicitly synthetic; status PASS is not document approval.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from awf.verification.exact_checks import parse_contract, verify_exact_invariants

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_ALLOWED_FAMILIES = frozenset(
    {"quantity", "citation", "negation", "causality", "modality", "scope", "context"}
)
_MAX_DATASET_BYTES = 2 * 1024 * 1024
_MAX_CASE_BYTES = 16 * 1024


def _string(value: object, *, key: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid benchmark field: {key}")
    return value


def _ratio(top: int, bottom: int) -> float | None:
    return top / bottom if bottom else None


def _read_pinned_dataset(source: Path, expected_sha256: str) -> dict[str, Any]:
    if not isinstance(expected_sha256, str) or _HASH.fullmatch(expected_sha256) is None:
        raise ValueError("synthetic benchmark requires a valid externally pinned SHA")
    if source.is_symlink() or not source.is_file():
        raise ValueError("benchmark dataset must be a regular non-symlinked file")
    with source.open("rb") as f:
        if not 0 < f.seek(0, 2) <= _MAX_DATASET_BYTES:
            raise ValueError("synthetic benchmark dataset exceeds size limits")
        f.seek(0)
        raw = f.read(_MAX_DATASET_BYTES + 1)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("synthetic benchmark dataset hash mismatch")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("synthetic benchmark dataset is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, dict) or set(parsed) != {
        "schema_version", "dataset_role", "cases"
    }:
        raise ValueError("unexpected synthetic benchmark dataset schema")
    if parsed["schema_version"] != "1.0.0" or parsed["dataset_role"] != "SYNTHETIC_DEVELOPMENT":
        raise ValueError("only explicitly synthetic developer tests are accepted")
    if not isinstance(parsed["cases"], list) or not 2 <= len(parsed["cases"]) <= 128:
        raise ValueError("synthetic benchmark needs 2..128 cases")
    return parsed


def run_synthetic_scope_benchmark(source: Path, *, expected_sha256: str) -> dict[str, Any]:
    """Run exact probe on actual case bytes; suppress original/candidate text in report."""
    dataset = _read_pinned_dataset(source, expected_sha256)
    observed: list[dict[str, str]] = []
    case_ids: set[str] = set()
    document_languages: dict[str, str] = {}
    for case in dataset["cases"]:
        if not isinstance(case, dict) or set(case) != {
            "case_id", "document_id", "language", "risk_family",
            "gold_label", "gold_provenance", "baseline", "candidate", "contract"
        }:
            raise ValueError("unexpected synthetic case fields")
        case_id = _string(case["case_id"], key="case_id")
        document_id = _string(case["document_id"], key="document_id")
        if (
            _ID.fullmatch(case_id) is None or case_id in case_ids
            or _ID.fullmatch(document_id) is None
        ):
            raise ValueError("invalid or duplicate benchmark identifiers")
        case_ids.add(case_id)
        language = _string(case["language"], key="language")
        if language not in {"es", "en"}:
            raise ValueError("unsupported benchmark language")
        if document_id in document_languages and document_languages[document_id] != language:
            raise ValueError("document identifier crosses benchmark languages")
        document_languages[document_id] = language
        family = _string(case["risk_family"], key="risk_family")
        if family not in _ALLOWED_FAMILIES:
            raise ValueError("unrecognized benchmark risk family")
        label = _string(case["gold_label"], key="gold_label")
        if label not in {"DRIFT", "PRESERVED"}:
            raise ValueError("unsupported synthetic label")
        if case["gold_provenance"] != "DEVELOPER_SYNTHETIC":
            raise ValueError("benchmark gold annotation must be marked synthetic")
        original = _string(case["baseline"], key="baseline").encode("utf-8")
        candidate = _string(case["candidate"], key="candidate").encode("utf-8")
        if max(len(original), len(candidate)) > _MAX_CASE_BYTES:
            raise ValueError("benchmark case text exceeds size limit")
        if original == candidate and label == "DRIFT":
            raise ValueError("unchanged text cannot be labelled changed")
        contract = parse_contract(case["contract"])
        result = verify_exact_invariants(original, candidate, contract)
        status = result["scope_status"]
        if status not in ("FAIL", "PASS", "NEEDS_REVIEW"):
            raise ValueError("unexpected exact checker status")
        observed.append({
            "case_id": case_id,
            "document_id": document_id,
            "language": language,
            "risk_family": family,
            "gold_label": label,
            "syntactic_scope_status": str(status),
            "baseline_sha256": hashlib.sha256(original).hexdigest(),
            "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        })

    def tally(rows: list[dict[str, str]]) -> dict[str, Any]:
        counts = Counter(
            (row["gold_label"], row["syntactic_scope_status"]) for row in rows
        )
        tp = counts["DRIFT", "FAIL"]
        fn = counts["DRIFT", "PASS"]
        pending_drift = counts["DRIFT", "NEEDS_REVIEW"]
        fp = counts["PRESERVED", "FAIL"]
        tn = counts["PRESERVED", "PASS"]
        pending_preserved = counts["PRESERVED", "NEEDS_REVIEW"]
        drift = tp + fn + pending_drift
        preserved = fp + tn + pending_preserved
        return {
            "cases": len(rows),
            "drift_cases": drift,
            "preserved_cases": preserved,
            "fail_on_drift": tp,
            "false_clear_on_drift": fn,
            "review_on_drift": pending_drift,
            "fail_on_preserved": fp,
            "pass_on_preserved": tn,
            "review_on_preserved": pending_preserved,
            "strict_drift_detection_rate": _ratio(tp, drift),
            "false_clear_rate_on_drift": _ratio(fn, drift),
            "review_escalation_rate": _ratio(pending_drift + pending_preserved, len(rows)),
            "failure_precision_excluding_abstentions": _ratio(tp, tp + fp),
        }

    return {
        "schema_version": "1.0.0",
        "benchmark_id": "synthetic_exact_scope_v1",
        "dataset_sha256": expected_sha256,
        "dataset_role": "SYNTHETIC_DEVELOPMENT",
        "checker_id": "exact_invariants:v1",
        "evaluation": tally(observed),
        "by_language": {
            language: tally([row for row in observed if row["language"] == language])
            for language in sorted(set(row["language"] for row in observed))
        },
        "results": observed,
        "independent_gold_verified": False,
        "semantic_equivalence_verified": False,
        "citation_grounding_verified": False,
        "training_authorized": False,
        "document_acceptance": "NEEDS_REVIEW",
        "source_text_exported": False,
        "conclusion": "SYNTHETIC_SCOPE_DIAGNOSTIC_ONLY",
    }
