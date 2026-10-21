"""Compare two source-bound independent signed scientific opinions.

Reuses PR #34's signature and source gates rather than creating new signing
roles. A disputed rule requires a separately hash-pinned *unsigned* private
case plan. This protocol is not a formal adjudication or training permission.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, cast

from awf.application.commands.authorize_review import verify_signed_review_event
from awf.application.commands.scientific_assessments import (
    verify_independent_scientific_assessments,
)
from awf.application.ports import EvidenceStorePort, ReviewerSignatureVerifierPort
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import ReviewerRole, ReviewerTrustPolicy
from awf.domain.scientific_disagreements import (
    ComparisonStatus,
    DisagreementProtocolResult,
    ProposedNextAction,
)
from awf.domain.signed_documents import canonical_json_bytes, strict_json
from awf.knowledge.adjudication_dossiers import audit_private_dossiers

_EVENT = re.compile(r"event:([a-f0-9]{64})\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_ID = re.compile(r"DSR-[0-9]{3}\Z")
_CASE_KEYS = frozenset(
    {
        "schema", "type", "source_id", "archive_sha256", "requirement_id",
        "requirement_sha256", "proposal_ref", "left_assessment_ref",
        "right_assessment_ref", "claim_in_dispute", "evidence_gaps",
        "methodological_divergence", "proposed_next_action",
    }
)


def _digest(ref: str) -> str:
    if not isinstance(ref, str) or (match := _EVENT.fullmatch(ref)) is None:
        raise EvidenceIntegrityError("an exact ledger event reference is required")
    return match.group(1)


def disagreement_case_payload(
    *,
    source_id: str,
    archive_sha256: str,
    requirement_id: str,
    requirement_sha256: str,
    proposal_ref: str,
    left_assessment_ref: str,
    right_assessment_ref: str,
    claim_in_dispute: str,
    evidence_gaps: str,
    methodological_divergence: str,
    proposed_next_action: ProposedNextAction,
) -> bytes:
    """Create canonical private plan; its content is not a verified adjudication."""
    if (
        not isinstance(source_id, str)
        or not 1 <= len(source_id) <= 128
        or not isinstance(requirement_id, str)
        or _ID.fullmatch(requirement_id) is None
        or any(
            not isinstance(value, str) or _SHA.fullmatch(value) is None
            for value in (archive_sha256, requirement_sha256)
        )
        or _digest(proposal_ref) in {_digest(left_assessment_ref), _digest(right_assessment_ref)}
        or left_assessment_ref == right_assessment_ref
        or not isinstance(proposed_next_action, ProposedNextAction)
        or not all(
            isinstance(text, str) and 30 <= len(text.strip()) <= 4096
            for text in (claim_in_dispute, evidence_gaps, methodological_divergence)
        )
    ):
        raise EvidenceIntegrityError("invalid or incomplete scientific disagreement case")
    return canonical_json_bytes(
        {
            "schema": 1,
            "type": "scientific_disagreement_case",
            "source_id": source_id,
            "archive_sha256": archive_sha256,
            "requirement_id": requirement_id,
            "requirement_sha256": requirement_sha256,
            "proposal_ref": proposal_ref,
            "left_assessment_ref": left_assessment_ref,
            "right_assessment_ref": right_assessment_ref,
            "claim_in_dispute": claim_in_dispute,
            "evidence_gaps": evidence_gaps,
            "methodological_divergence": methodological_divergence,
            "proposed_next_action": proposed_next_action.value,
        }
    )


def _compare_verdicts(left: str, right: str) -> ComparisonStatus:
    if left == "INCONCLUSIVE" or right == "INCONCLUSIVE":
        return ComparisonStatus.INCONCLUSIVE
    if left != right:
        return ComparisonStatus.DIVERGENT
    if left == "SUPPORT":
        return ComparisonStatus.CONCORDANT_SUPPORT
    if left == "CONTEST" and right == "CONTEST":
        return ComparisonStatus.CONCORDANT_CONTEST
    raise EvidenceIntegrityError("unexpected scientific verdict")


def verify_disagreement_protocol(
    *,
    canonical_manifest: Mapping[str, Any],
    canonical_packets: Mapping[str, Mapping[str, Any]],
    observed_manifest: Mapping[str, Any],
    observed_packets: Mapping[str, Mapping[str, Any]],
    proposal_refs: Mapping[str, tuple[str, str]],
    left_assessments: Mapping[str, tuple[str, str]],
    right_assessments: Mapping[str, tuple[str, str]],
    case_bytes: Mapping[str, bytes],
    expected_case_sha256: Mapping[str, str],
    store: EvidenceStorePort,
    run_id: str,
    expected_head: str,
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
) -> DisagreementProtocolResult:
    """Verify two independently signed opinions and the dispute case snapshot.

    Each PR #34 gate independently authenticates the full *documented* dossier
    inventory with the SAME externally pinned head and reviewer policy.
    A failed prerequisite is a hard stop, never a weakly validated comparison.
    """
    if not isinstance(expected_head, str) or _SHA.fullmatch(expected_head) is None:
        raise EvidenceIntegrityError("externally retained ledger head is mandatory")
    for inventory in (left_assessments, right_assessments):
        result = verify_independent_scientific_assessments(
            canonical_manifest=canonical_manifest,
            canonical_packets=canonical_packets,
            observed_manifest=observed_manifest,
            observed_packets=observed_packets,
            proposal_refs=proposal_refs,
            assessment_refs=inventory,
            store=store,
            run_id=run_id,
            expected_head=expected_head,
            policy=policy,
            verifier=verifier,
            now=now,
        )
        if not result.all_credentials_verified or result.checked == 0:
            raise EvidenceIntegrityError("signed scientific assessment prerequisite failed")

    dossier = audit_private_dossiers(
        canonical_manifest=canonical_manifest,
        canonical_packets=canonical_packets,
        observed_manifest=observed_manifest,
        observed_packets=observed_packets,
    )
    rows = dossier["rules"]
    if not isinstance(rows, list):
        raise EvidenceIntegrityError("invalid source-bound review inventory")
    documented = {
        str(row["id"]) for row in rows if row["status"] == "PROPOSAL_DOCUMENTED"
    }
    if (
        not documented
        or set(left_assessments) != documented
        or set(right_assessments) != documented
        or set(proposal_refs) != documented
        or set(case_bytes) != set(expected_case_sha256)
    ):
        raise EvidenceIntegrityError("incomplete or mismatched scientific inventory")
    canonical = {
        str(row["id"]): row
        for packet in canonical_packets.values()
        for row in packet["rules"]
    }

    comparisons: list[tuple[str, ComparisonStatus]] = []
    required_cases: set[str] = set()
    with store.verified_read(expected_head=expected_head) as reader:
        for rule_id in sorted(documented):
            proposal_ref, _ = proposal_refs[rule_id]
            left_ref, left_sig = left_assessments[rule_id]
            right_ref, right_sig = right_assessments[rule_id]
            if left_ref == right_ref or left_sig == right_sig:
                raise EvidenceIntegrityError("two distinct scientific assessments required")
            actors: list[str] = []
            verdicts: list[str] = []
            for assessment_ref, signed_ref in ((left_ref, left_sig), (right_ref, right_sig)):
                record, data = reader.resolve_event(
                    event_digest=_digest(assessment_ref), expected_head=expected_head
                )
                if (
                    record.kind != EvidenceKind.SCIENTIFIC_RULE_ASSESSMENT
                    or record.run_id != run_id
                    or record.subject_id != rule_id
                ):
                    raise EvidenceIntegrityError("scientific comparison points to wrong event")
                body = strict_json(data)
                actor = verify_signed_review_event(
                    store=reader,
                    attestation_ref=signed_ref,
                    target_ref=assessment_ref,
                    expected_role=ReviewerRole.SCIENTIFIC_REVIEWER,
                    run_id=run_id,
                    subject_id=rule_id,
                    policy=policy,
                    verifier=verifier,
                    now=now,
                    expected_head=expected_head,
                )
                if (
                    body.get("assessment_actor_id") != actor
                    or body.get("proposal_ref") != proposal_ref
                ):
                    raise EvidenceIntegrityError("cross-proposal or cross-actor assessment")
                actors.append(actor)
                verdicts.append(cast(str, body["verdict"]))
            if actors[0] == actors[1]:
                raise EvidenceIntegrityError("self-comparison is not independent peer review")
            status = _compare_verdicts(*verdicts)
            comparisons.append((rule_id, status))
            if status in {ComparisonStatus.DIVERGENT, ComparisonStatus.INCONCLUSIVE}:
                required_cases.add(rule_id)
                if rule_id not in case_bytes:
                    continue
                data = case_bytes[rule_id]
                pinned = expected_case_sha256[rule_id]
                if (
                    not isinstance(data, bytes)
                    or not isinstance(pinned, str)
                    or _SHA.fullmatch(pinned) is None
                    or sha256_bytes(data) != pinned
                ):
                    raise EvidenceIntegrityError("disagreement case lacks external SHA pin")
                case = strict_json(data)
                if set(case) != _CASE_KEYS or type(case["schema"]) is not int or case["schema"] != 1:
                    raise EvidenceIntegrityError("invalid disagreement case schema")
                try:
                    rebuilt = disagreement_case_payload(
                        source_id=cast(str, case["source_id"]),
                        archive_sha256=cast(str, case["archive_sha256"]),
                        requirement_id=cast(str, case["requirement_id"]),
                        requirement_sha256=cast(str, case["requirement_sha256"]),
                        proposal_ref=cast(str, case["proposal_ref"]),
                        left_assessment_ref=cast(str, case["left_assessment_ref"]),
                        right_assessment_ref=cast(str, case["right_assessment_ref"]),
                        claim_in_dispute=cast(str, case["claim_in_dispute"]),
                        evidence_gaps=cast(str, case["evidence_gaps"]),
                        methodological_divergence=cast(str, case["methodological_divergence"]),
                        proposed_next_action=ProposedNextAction(
                            cast(str, case["proposed_next_action"])
                        ),
                    )
                except (KeyError, ValueError, TypeError) as exc:
                    raise EvidenceIntegrityError("malformed disagreement case") from exc
                if (
                    rebuilt != data
                    or case["type"] != "scientific_disagreement_case"
                    or case["source_id"] != canonical_manifest["source_id"]
                    or case["archive_sha256"] != canonical_manifest["archive_sha256"]
                    or case["requirement_id"] != rule_id
                    or case["requirement_sha256"] != canonical[rule_id]["requirement_sha256"]
                    or case["proposal_ref"] != proposal_ref
                    or case["left_assessment_ref"] != left_ref
                    or case["right_assessment_ref"] != right_ref
                ):
                    raise EvidenceIntegrityError("scientific dispute case binds wrong source/events")
    if not set(case_bytes) <= required_cases:
        raise EvidenceIntegrityError("extra or silently substituted disagreement cases")
    missing = tuple(sorted(required_cases - set(case_bytes)))
    return DisagreementProtocolResult(
        checked=len(documented),
        comparisons=tuple(comparisons),
        case_rule_ids=tuple(sorted(case_bytes)),
        missing_case_rule_ids=missing,
        evidence_links_verified=not missing,
    )
