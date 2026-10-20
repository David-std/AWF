"""Inspect private historical-rule annotations against the SHA-pinned workbench.

Only structural proposal completeness is tested. Links, claimed reviewers,
permissions, source accuracy and independent adjudications are NOT authenticated.
Never publish annotated packets, legacy requirements, or arbitrary review prose.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from awf.domain.knowledge import Disposition

_FIELDS = frozenset(
    {
        "reviewer",
        "reason",
        "evidence_ids",
        "conflicting_rule_ids",
        "desired_disposition",
        "proposed_tests",
        "source_rights_status",
        "current_model_or_version_evidence",
    }
)
_RIGHTS = frozenset({"NOT_EVALUATED", "NOT_APPLICABLE", "RESTRICTED", "PERMISSION_VERIFIED"})


def _text(value: object, *, minimum: int = 1) -> bool:
    return isinstance(value, str) and minimum <= len(value.strip()) <= 4096


def _strings(value: object) -> bool:
    if not isinstance(value, list) or len(value) > 64:
        return False
    if not all(isinstance(entry, str) for entry in value):
        return False
    return len(value) == len(set(value)) and all(_text(entry) for entry in value)


def _inspect_rule(
    canonical: Mapping[str, Any],
    actual: Mapping[str, Any],
    *,
    known_ids: frozenset[str],
) -> dict[str, object]:
    identifier = str(canonical["id"])
    if set(actual) != set(canonical):
        raise ValueError(f"immutable review rule shape changed for {identifier}")
    for key in canonical:
        if key != "review_template" and actual[key] != canonical[key]:
            raise ValueError(f"immutable source-bound rule field changed: {identifier}:{key}")
    template = actual["review_template"]
    if not isinstance(template, dict) or set(template) != _FIELDS:
        raise ValueError(f"unknown or missing private review fields: {identifier}")
    if any(
        type(template[k]) is not type(canonical["review_template"][k])
        for k in (
            "evidence_ids",
            "conflicting_rule_ids",
            "proposed_tests",
        )
    ):
        raise ValueError(f"review list field shape changed: {identifier}")
    for k in ("evidence_ids", "conflicting_rule_ids", "proposed_tests"):
        if not _strings(template[k]):
            raise ValueError(f"invalid duplicate or overlong review list: {identifier}:{k}")
    if not set(template["conflicting_rule_ids"]) <= known_ids - {identifier}:
        raise ValueError(f"unknown or self-referential conflict ID: {identifier}")
    rights = template["source_rights_status"]
    if not isinstance(rights, str) or rights not in _RIGHTS:
        raise ValueError(f"invalid rights declaration: {identifier}")
    disposition = template["desired_disposition"]
    if disposition is None:
        if template != canonical["review_template"]:
            return {
                "id": identifier,
                "status": "PARTIAL",
                "missing": ["desired_disposition"],
            }
        return {"id": identifier, "status": "OPEN", "missing": []}
    try:
        selected = Disposition(disposition)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid requested disposition: {identifier}") from exc
    if selected == Disposition.UNRESOLVED:
        raise ValueError(f"unresolved cannot be claimed as an adjudicated choice: {identifier}")
    if canonical["priority"] == "DEFERRED_LAB" and selected != Disposition.EVAL_ONLY:
        raise ValueError(f"deferred laboratory material cannot be promoted: {identifier}")
    missing = []
    if not _text(template["reviewer"], minimum=2):
        missing.append("reviewer")
    if not _text(template["reason"], minimum=30):
        missing.append("reason")
    if not template["evidence_ids"]:
        missing.append("evidence_ids")
    if not template["proposed_tests"]:
        missing.append("proposed_tests")
    if not _text(template["current_model_or_version_evidence"]):
        missing.append("current_model_or_version_evidence")
    if rights == "NOT_EVALUATED":
        missing.append("source_rights_status")
    # Even complete metadata is not authorization to use a dataset or model.
    if selected == Disposition.TRAIN:
        missing.append("training_license_independently_verified")
    if template["conflicting_rule_ids"]:
        missing.append("conflict_resolution")
    return {
        "id": identifier,
        "status": "PROPOSAL_INCOMPLETE" if missing else "PROPOSAL_DOCUMENTED",
        "missing": sorted(missing),
    }


def audit_private_dossiers(
    *,
    canonical_manifest: Mapping[str, Any],
    canonical_packets: Mapping[str, Mapping[str, Any]],
    observed_manifest: Mapping[str, Any],
    observed_packets: Mapping[str, Mapping[str, Any]],
) -> dict[str, object]:
    """Fail closed on source/manifest edits; never approve a historical rule.

    This checks ALL expected rules. It does not accept a shorter reviewed subset,
    and it does not trust a workbench manifest to be a source of authority.
    """
    if observed_manifest != canonical_manifest:
        raise ValueError("private workbench manifest differs from pinned source")
    if set(observed_packets) != set(canonical_packets):
        raise ValueError("private review batch inventory changed")
    expected_ids = {
        str(row["id"]) for packet in canonical_packets.values() for row in packet["rules"]
    }
    if len(expected_ids) != sum(len(p["rules"]) for p in canonical_packets.values()):
        raise ValueError("canonical source contains duplicate IDs")
    outcomes: list[dict[str, object]] = []
    for filename in sorted(canonical_packets):
        expected = canonical_packets[filename]
        actual = observed_packets[filename]
        if set(actual) != set(expected) or any(
            actual[field] != value for field, value in expected.items() if field != "rules"
        ):
            raise ValueError(f"private batch metadata changed: {filename}")
        originals = expected["rules"]
        candidates = actual["rules"]
        if not isinstance(candidates, list) or len(originals) != len(candidates):
            raise ValueError(f"private batch length changed: {filename}")
        for original, proposed in zip(originals, candidates, strict=True):
            if not isinstance(proposed, dict):
                raise ValueError(f"private batch rule is not a mapping: {filename}")
            outcomes.append(_inspect_rule(original, proposed, known_ids=frozenset(expected_ids)))
    counts = Counter(str(entry["status"]) for entry in outcomes)
    return {
        "schema_version": "1.0.0",
        "source_sha256": canonical_manifest["archive_sha256"],
        "requirements_count": len(expected_ids),
        "status_counts": dict(sorted(counts.items())),
        "rules": outcomes,
        "all_rules_adjudicated": False,
        "independent_evidence_verified": False,
        "review_attestation_authorized": False,
        "training_authorized": False,
        "contains_private_source_text": False,
    }
