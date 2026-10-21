"""Independent credential-bound scientific assessments of historical-rule proposals.

This verifies source bindings and two distinct authorized signatures, not truth,
reviewer competence, legal permission, or a formal rule adjudication.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from awf.application.commands.authorize_dossiers import (
    verify_authorized_dossier_proposals,
)
from awf.application.commands.authorize_review import verify_signed_review_event
from awf.application.ports import EvidenceStorePort, ReviewerSignatureVerifierPort
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.domain.reviewer_auth import ReviewerRole, ReviewerTrustPolicy
from awf.domain.signed_documents import canonical_json_bytes, strict_json
from awf.knowledge.adjudication_dossiers import audit_private_dossiers

_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_EVENT = re.compile(r"event:([a-f0-9]{64})\Z")
_VERDICTS = frozenset({"SUPPORT", "CONTEST", "INCONCLUSIVE"})
_FIELDS = frozenset(
    {
        "schema",
        "type",
        "source_id",
        "archive_sha256",
        "requirement_id",
        "requirement_sha256",
        "proposal_ref",
        "assessment_actor_id",
        "verdict",
        "method_notes",
        "evidence_analysis",
        "limitations",
    }
)


def _event(ref: str) -> str:
    if not isinstance(ref, str) or (matched := _EVENT.fullmatch(ref)) is None:
        raise EvidenceIntegrityError("scientific assessment requires an exact ledger event")
    return matched.group(1)


def parse_scientific_assessment_inventory(data: bytes) -> dict[str, tuple[str, str]]:
    """Require canonical, bounded and unambiguous private per-rule references."""
    body = strict_json(data)
    if (
        set(body) != {"schema", "assessments"}
        or type(body["schema"]) is not int
        or body["schema"] != 1
    ):
        raise EvidenceIntegrityError("invalid scientific assessment inventory schema")
    rows = body["assessments"]
    if not isinstance(rows, dict) or not 1 <= len(rows) <= 184:
        raise EvidenceIntegrityError("invalid scientific assessment inventory size")
    result: dict[str, tuple[str, str]] = {}
    for rule_id, refs in rows.items():
        if (
            not isinstance(rule_id, str)
            or not rule_id.startswith("DSR-")
            or not isinstance(refs, dict)
            or set(refs) != {"assessment_ref", "attestation_ref"}
        ):
            raise EvidenceIntegrityError("invalid scientific assessment inventory row")
        result[rule_id] = (
            "event:" + _event(refs["assessment_ref"]),
            "event:" + _event(refs["attestation_ref"]),
        )
    return result


def scientific_assessment_payload(
    *,
    source_id: str,
    archive_sha256: str,
    requirement_id: str,
    requirement_sha256: str,
    proposal_ref: str,
    actor_id: str,
    verdict: str,
    method_notes: str,
    evidence_analysis: str,
    limitations: str,
) -> bytes:
    """Create a canonical local-only assessment; stores full private notes in ledger."""
    if not all(isinstance(v, str) and v for v in (source_id, requirement_id, actor_id)):
        raise EvidenceIntegrityError("missing assessment source/actor identity")
    if any(_DIGEST.fullmatch(v) is None for v in (archive_sha256, requirement_sha256)):
        raise EvidenceIntegrityError("invalid scientific assessment source digest")
    _event(proposal_ref)
    if (
        verdict not in _VERDICTS
        or not isinstance(method_notes, str)
        or not isinstance(evidence_analysis, str)
        or not isinstance(limitations, str)
        or not 30 <= len(method_notes.strip()) <= 4096
        or not 30 <= len(evidence_analysis.strip()) <= 4096
        or not 20 <= len(limitations.strip()) <= 4096
    ):
        raise EvidenceIntegrityError("scientific assessment is incomplete")
    payload: dict[str, object] = {
        "schema": 1,
        "type": "independent_scientific_assessment",
        "source_id": source_id,
        "archive_sha256": archive_sha256,
        "requirement_id": requirement_id,
        "requirement_sha256": requirement_sha256,
        "proposal_ref": proposal_ref,
        "assessment_actor_id": actor_id,
        "verdict": verdict,
        "method_notes": method_notes,
        "evidence_analysis": evidence_analysis,
        "limitations": limitations,
    }
    return canonical_json_bytes(payload)


@dataclass(frozen=True, slots=True)
class ScientificAssessmentResult:
    checked: int
    verified: int
    unverified_rule_ids: tuple[str, ...]
    all_credentials_verified: bool
    independent_adjudication_proven: bool = False
    review_attestation_authorized: bool = False
    training_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "checked": self.checked,
            "verified": self.verified,
            "unverified_rule_ids": list(self.unverified_rule_ids),
            "all_credentials_verified": self.all_credentials_verified,
            "independent_adjudication_proven": False,
            "review_attestation_authorized": False,
            "training_authorized": False,
            "contains_private_source_text": False,
        }


def verify_independent_scientific_assessments(
    *,
    canonical_manifest: Mapping[str, Any],
    canonical_packets: Mapping[str, Mapping[str, Any]],
    observed_manifest: Mapping[str, Any],
    observed_packets: Mapping[str, Mapping[str, Any]],
    proposal_refs: Mapping[str, tuple[str, str]],
    assessment_refs: Mapping[str, tuple[str, str]],
    store: EvidenceStorePort,
    run_id: str,
    expected_head: str,
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
) -> ScientificAssessmentResult:
    """Authenticate two distinct role-scoped actors against the SAME pinned head.

    The PR #33 proposal gate is called first; two audits are performed, with
    the same external head digest and no interim write. This does NOT approve
    any scientific assertion or rights claim.
    """
    original = verify_authorized_dossier_proposals(
        canonical_manifest=canonical_manifest,
        canonical_packets=canonical_packets,
        observed_manifest=observed_manifest,
        observed_packets=observed_packets,
        attestation_refs=proposal_refs,
        store=store,
        run_id=run_id,
        expected_head=expected_head,
        policy=policy,
        verifier=verifier,
        now=now,
    )
    if not original.authorization_verified:
        return ScientificAssessmentResult(
            checked=original.checked,
            verified=0,
            unverified_rule_ids=original.unverified or ("prior_proposal_authorization_failed",),
            all_credentials_verified=False,
        )
    audit = audit_private_dossiers(
        canonical_manifest=canonical_manifest,
        canonical_packets=canonical_packets,
        observed_manifest=observed_manifest,
        observed_packets=observed_packets,
    )
    outcomes = audit.get("rules")
    if not isinstance(outcomes, list) or any(not isinstance(row, dict) for row in outcomes):
        raise EvidenceIntegrityError("invalid audited scientific dossier records")
    documented = {
        str(item["id"]) for item in outcomes if item.get("status") == "PROPOSAL_DOCUMENTED"
    }
    if not documented or set(assessment_refs) != documented:
        return ScientificAssessmentResult(
            checked=len(documented),
            verified=0,
            unverified_rule_ids=("scientific_assessment_inventory_mismatch",),
            all_credentials_verified=False,
        )
    invalid: set[str] = set()
    with store.verified_read(expected_head=expected_head) as reader:
        for filename in sorted(canonical_packets):
            originals = canonical_packets[filename]["rules"]
            annotations = observed_packets[filename]["rules"]
            for canonical, observed in zip(originals, annotations, strict=True):
                rule_id = canonical["id"]
                if rule_id not in documented:
                    continue
                try:
                    proposal_ref, signed_proposal_ref = proposal_refs[rule_id]
                    assessment_ref, signed_assessment_ref = assessment_refs[rule_id]
                    # The previous gate authenticates this record; parsing again
                    # provides the original ledger order in this read snapshot.
                    proposal_signature, _ = reader.resolve_event(
                        event_digest=_event(signed_proposal_ref), expected_head=expected_head
                    )
                    assessment_record, assessment_bytes = reader.resolve_event(
                        event_digest=_event(assessment_ref), expected_head=expected_head
                    )
                    if (
                        assessment_record.kind != EvidenceKind.SCIENTIFIC_RULE_ASSESSMENT
                        or assessment_record.run_id != run_id
                        or assessment_record.subject_id != rule_id
                        or assessment_record.sequence <= proposal_signature.sequence
                    ):
                        raise EvidenceIntegrityError("scientific assessment event is out of scope")
                    value = strict_json(assessment_bytes)
                    if (
                        set(value) != _FIELDS
                        or type(value["schema"]) is not int
                        or value["schema"] != 1
                    ):
                        raise EvidenceIntegrityError("scientific assessment fields mismatch")
                    if any(not isinstance(value[key], str) for key in _FIELDS - {"schema"}):
                        raise EvidenceIntegrityError("invalid scientific assessment field types")
                    if (
                        value["type"] != "independent_scientific_assessment"
                        or value["source_id"] != canonical_manifest["source_id"]
                        or value["archive_sha256"] != canonical_manifest["archive_sha256"]
                        or value["requirement_id"] != rule_id
                        or value["requirement_sha256"] != canonical["requirement_sha256"]
                        or value["proposal_ref"] != proposal_ref
                    ):
                        raise EvidenceIntegrityError("scientific assessment source binding failed")
                    rebuilt = scientific_assessment_payload(
                        source_id=cast(str, value["source_id"]),
                        archive_sha256=cast(str, value["archive_sha256"]),
                        requirement_id=cast(str, value["requirement_id"]),
                        requirement_sha256=cast(str, value["requirement_sha256"]),
                        proposal_ref=cast(str, value["proposal_ref"]),
                        actor_id=cast(str, value["assessment_actor_id"]),
                        verdict=cast(str, value["verdict"]),
                        method_notes=cast(str, value["method_notes"]),
                        evidence_analysis=cast(str, value["evidence_analysis"]),
                        limitations=cast(str, value["limitations"]),
                    )
                    if rebuilt != assessment_bytes:
                        raise EvidenceIntegrityError("noncanonical scientific assessment")
                    proposer = verify_signed_review_event(
                        store=reader,
                        attestation_ref=signed_proposal_ref,
                        target_ref=proposal_ref,
                        expected_role=ReviewerRole.KNOWLEDGE_REVIEWER,
                        run_id=run_id,
                        subject_id=rule_id,
                        policy=policy,
                        verifier=verifier,
                        now=now,
                        expected_head=expected_head,
                    )
                    scientist = verify_signed_review_event(
                        store=reader,
                        attestation_ref=signed_assessment_ref,
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
                        proposer == scientist
                        or scientist != value["assessment_actor_id"]
                        or scientist == observed["review_template"]["reviewer"]
                    ):
                        raise EvidenceIntegrityError("self-review or actor mismatch")
                except (EvidenceIntegrityError, ValueError, TypeError, KeyError):
                    invalid.add(rule_id)
    return ScientificAssessmentResult(
        checked=len(documented),
        verified=len(documented) - len(invalid),
        unverified_rule_ids=tuple(sorted(invalid)),
        all_credentials_verified=not invalid,
    )
