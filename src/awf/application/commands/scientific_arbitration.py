"""Source-bound third-party arbitration and append-only reconsideration records.

A valid Ed25519 signature verifies a credential, not professional competence,
human independence, source truth, legal rights or actual scientific consensus.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Protocol, cast

from awf.application.commands.authorize_review import verify_signed_review_event
from awf.application.commands.scientific_disagreements import verify_disagreement_protocol
from awf.application.ports import EvidenceStorePort, ReviewerSignatureVerifierPort
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import ReviewerRole, ReviewerTrustPolicy
from awf.domain.scientific_arbitration import ArbitrationPosition, ArbitrationResult
from awf.domain.scientific_disagreements import ComparisonStatus
from awf.domain.signed_documents import canonical_json_bytes, strict_json

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_EVENT = re.compile(r"event:([a-f0-9]{64})\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_FIELDS = frozenset(
    {
        "schema", "type", "source_id", "archive_sha256", "requirement_id",
        "requirement_sha256", "proposal_ref", "left_assessment_ref",
        "right_assessment_ref", "case_sha256", "arbitrator_actor_id",
        "position", "reasoned_findings", "limitations", "evidence_refs",
        "supersedes_ref", "reconsideration_basis",
    }
)


class ExternalQualificationPort(Protocol):
    """Trusted outside authority attests qualification, distinct persons and COI.

    A self-written credential JSON or a different key is not sufficient.
    """

    def verify(
        self,
        *,
        actor_id: str,
        excluded_actor_ids: tuple[str, ...],
        requirement_id: str,
        case_sha256: str,
        qualification_evidence: bytes,
        policy_sha256: str,
        at_time: int,
    ) -> None:
        """Raise EvidenceIntegrityError if qualification/independence is unverified."""
        ...


def _ref_digest(ref: str) -> str:
    if not isinstance(ref, str) or (match := _EVENT.fullmatch(ref)) is None:
        raise EvidenceIntegrityError("scientific arbitration requires an exact event reference")
    return match.group(1)


def arbitration_payload(
    *,
    source_id: str,
    archive_sha256: str,
    requirement_id: str,
    requirement_sha256: str,
    proposal_ref: str,
    left_assessment_ref: str,
    right_assessment_ref: str,
    case_sha256: str,
    arbitrator_actor_id: str,
    position: ArbitrationPosition,
    reasoned_findings: str,
    limitations: str,
    evidence_refs: tuple[str, ...],
    supersedes_ref: str | None = None,
    reconsideration_basis: str | None = None,
) -> bytes:
    """Canonical private decision or appeal, with complete context and evidence."""
    if (
        not isinstance(source_id, str)
        or _ID.fullmatch(source_id) is None
        or not isinstance(requirement_id, str)
        or _ID.fullmatch(requirement_id) is None
        or not isinstance(arbitrator_actor_id, str)
        or _ID.fullmatch(arbitrator_actor_id) is None
        or any(
            not isinstance(value, str) or _SHA.fullmatch(value) is None
            for value in (archive_sha256, requirement_sha256, case_sha256)
        )
        or len({_ref_digest(ref) for ref in (
            proposal_ref, left_assessment_ref, right_assessment_ref,
        )}) != 3
        or not isinstance(position, ArbitrationPosition)
        or not isinstance(reasoned_findings, str)
        or not 40 <= len(reasoned_findings.strip()) <= 4096
        or not isinstance(limitations, str)
        or not 30 <= len(limitations.strip()) <= 4096
        or not isinstance(evidence_refs, tuple)
        or not 1 <= len(evidence_refs) <= 32
        or len(set(evidence_refs)) != len(evidence_refs)
    ):
        raise EvidenceIntegrityError("incomplete or invalid scientific arbitration payload")
    for ref in evidence_refs:
        _ref_digest(ref)
    if supersedes_ref is None:
        if reconsideration_basis is not None:
            raise EvidenceIntegrityError("initial decision cannot claim reconsideration")
    elif (
        _ref_digest(supersedes_ref) in {_ref_digest(ref) for ref in evidence_refs}
        or not isinstance(reconsideration_basis, str)
        or not 40 <= len(reconsideration_basis.strip()) <= 4096
    ):
        raise EvidenceIntegrityError("reconsideration requires predecessor and substantive basis")
    return canonical_json_bytes(
        {
            "schema": 1,
            "type": "scientific_arbitration",
            "source_id": source_id,
            "archive_sha256": archive_sha256,
            "requirement_id": requirement_id,
            "requirement_sha256": requirement_sha256,
            "proposal_ref": proposal_ref,
            "left_assessment_ref": left_assessment_ref,
            "right_assessment_ref": right_assessment_ref,
            "case_sha256": case_sha256,
            "arbitrator_actor_id": arbitrator_actor_id,
            "position": position.value,
            "reasoned_findings": reasoned_findings,
            "limitations": limitations,
            "evidence_refs": list(evidence_refs),
            "supersedes_ref": supersedes_ref,
            "reconsideration_basis": reconsideration_basis,
        }
    )


def _reconstruct(raw: dict[str, object]) -> bytes:
    if set(raw) != _FIELDS or type(raw["schema"]) is not int or raw["schema"] != 1:
        raise EvidenceIntegrityError("unsupported scientific arbitration schema")
    if raw["type"] != "scientific_arbitration":
        raise EvidenceIntegrityError("invalid scientific arbitration document type")
    try:
        refs = raw["evidence_refs"]
        if not isinstance(refs, list):
            raise EvidenceIntegrityError("arbitration evidence refs must be a list")
        if not all(isinstance(ref, str) for ref in refs):
            raise EvidenceIntegrityError("arbitration evidence refs must be strings")
        return arbitration_payload(
            source_id=cast(str, raw["source_id"]),
            archive_sha256=cast(str, raw["archive_sha256"]),
            requirement_id=cast(str, raw["requirement_id"]),
            requirement_sha256=cast(str, raw["requirement_sha256"]),
            proposal_ref=cast(str, raw["proposal_ref"]),
            left_assessment_ref=cast(str, raw["left_assessment_ref"]),
            right_assessment_ref=cast(str, raw["right_assessment_ref"]),
            case_sha256=cast(str, raw["case_sha256"]),
            arbitrator_actor_id=cast(str, raw["arbitrator_actor_id"]),
            position=ArbitrationPosition(cast(str, raw["position"])),
            reasoned_findings=cast(str, raw["reasoned_findings"]),
            limitations=cast(str, raw["limitations"]),
            evidence_refs=tuple(cast(list[str], refs)),
            supersedes_ref=cast(str | None, raw["supersedes_ref"]),
            reconsideration_basis=cast(str | None, raw["reconsideration_basis"]),
        )
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise EvidenceIntegrityError("invalid scientific arbitration fields") from exc


def verify_scientific_arbitration(
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
    rule_id: str,
    arbitration_refs: tuple[tuple[str, str], ...],
    qualification_bytes: Mapping[str, bytes],
    expected_qualification_sha256: Mapping[str, str],
    qualification_policy_sha256: str | None,
    qualification_verifier: ExternalQualificationPort | None,
    store: EvidenceStorePort,
    run_id: str,
    expected_head: str,
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
) -> ArbitrationResult:
    """Check complete prior dispute chain and an append-only signed decision chain.

    Only independent third-party qualification verification can establish the
    procedural prerequisite. Never mutates the 184-rule registry or training.
    """
    baseline = verify_disagreement_protocol(
        canonical_manifest=canonical_manifest,
        canonical_packets=canonical_packets,
        observed_manifest=observed_manifest,
        observed_packets=observed_packets,
        proposal_refs=proposal_refs,
        left_assessments=left_assessments,
        right_assessments=right_assessments,
        case_bytes=case_bytes,
        expected_case_sha256=expected_case_sha256,
        store=store,
        run_id=run_id,
        expected_head=expected_head,
        policy=policy,
        verifier=verifier,
        now=now,
    )
    comparison = dict(baseline.comparisons)
    if (
        rule_id not in comparison
        or comparison[rule_id]
        not in {ComparisonStatus.DIVERGENT, ComparisonStatus.INCONCLUSIVE}
        or rule_id in baseline.missing_case_rule_ids
        or rule_id not in case_bytes
        or rule_id not in expected_case_sha256
    ):
        raise EvidenceIntegrityError("scientific arbitration requires a verified open case")
    if not isinstance(arbitration_refs, tuple) or not 1 <= len(arbitration_refs) <= 5:
        raise EvidenceIntegrityError("initial scientific decision or bounded appeal chain required")
    if set(qualification_bytes) != set(expected_qualification_sha256):
        raise EvidenceIntegrityError("qualification evidence/pins inventory mismatch")
    if qualification_verifier is not None and (
        not isinstance(qualification_policy_sha256, str)
        or _SHA.fullmatch(qualification_policy_sha256) is None
    ):
        raise EvidenceIntegrityError("external qualification policy SHA is required")

    case_hash = expected_case_sha256[rule_id]
    canonical = {
        str(row["id"]): row
        for packet in canonical_packets.values()
        for row in packet["rules"]
    }
    expected_rule = canonical[rule_id]
    proposal_ref, signed_proposal_ref = proposal_refs[rule_id]
    left_ref, left_sig_ref = left_assessments[rule_id]
    right_ref, right_sig_ref = right_assessments[rule_id]
    positions: list[ArbitrationPosition] = []
    seen_actors: set[str] = set()
    seen_evidence: set[str] = set()
    prior_ref: str | None = None
    prior_sequence = 0
    with store.verified_read(expected_head=expected_head) as reader:
        excluded: set[str] = {
            verify_signed_review_event(
                store=reader,
                attestation_ref=signed_ref,
                target_ref=target_ref,
                expected_role=role,
                run_id=run_id,
                subject_id=rule_id,
                policy=policy,
                verifier=verifier,
                now=now,
                expected_head=expected_head,
            )
            for target_ref, signed_ref, role in (
                (proposal_ref, signed_proposal_ref, ReviewerRole.KNOWLEDGE_REVIEWER),
                (left_ref, left_sig_ref, ReviewerRole.SCIENTIFIC_REVIEWER),
                (right_ref, right_sig_ref, ReviewerRole.SCIENTIFIC_REVIEWER),
            )
        }
        prerequisite_sequences = []
        for signed_ref in (signed_proposal_ref, left_sig_ref, right_sig_ref):
            rec, _ = reader.resolve_event(
                event_digest=_ref_digest(signed_ref), expected_head=expected_head
            )
            prerequisite_sequences.append(rec.sequence)
        prior_sequence = max(prerequisite_sequences)
        for decision_ref, attestation_ref in arbitration_refs:
            decision_record, data = reader.resolve_event(
                event_digest=_ref_digest(decision_ref), expected_head=expected_head
            )
            attestation_record, _ = reader.resolve_event(
                event_digest=_ref_digest(attestation_ref), expected_head=expected_head
            )
            if (
                decision_record.kind != EvidenceKind.SCIENTIFIC_ARBITRATION
                or decision_record.run_id != run_id
                or decision_record.subject_id != rule_id
                or decision_record.sequence <= prior_sequence
                or attestation_record.sequence <= decision_record.sequence
            ):
                raise EvidenceIntegrityError("scientific arbitration event order/scope mismatch")
            value = strict_json(data)
            if _reconstruct(value) != data:
                raise EvidenceIntegrityError("noncanonical scientific arbitration evidence")
            signed_actor = verify_signed_review_event(
                store=reader,
                attestation_ref=attestation_ref,
                target_ref=decision_ref,
                expected_role=ReviewerRole.SCIENTIFIC_ARBITER,
                run_id=run_id,
                subject_id=rule_id,
                policy=policy,
                verifier=verifier,
                now=now,
                expected_head=expected_head,
            )
            if (
                signed_actor in excluded
                or signed_actor in seen_actors
                or value["arbitrator_actor_id"] != signed_actor
                or value["source_id"] != canonical_manifest["source_id"]
                or value["archive_sha256"] != canonical_manifest["archive_sha256"]
                or value["requirement_id"] != rule_id
                or value["requirement_sha256"] != expected_rule["requirement_sha256"]
                or value["proposal_ref"] != proposal_ref
                or value["left_assessment_ref"] != left_ref
                or value["right_assessment_ref"] != right_ref
                or value["case_sha256"] != case_hash
                or value["supersedes_ref"] != prior_ref
            ):
                raise EvidenceIntegrityError("arbitrator independence or source binding failed")
            evidence = cast(list[str], value["evidence_refs"])
            new_evidence_recorded_after_predecessor = False
            for evidence_ref in evidence:
                support, _ = reader.resolve_event(
                    event_digest=_ref_digest(evidence_ref), expected_head=expected_head
                )
                if prior_ref is not None and support.sequence > prior_sequence:
                    new_evidence_recorded_after_predecessor = True
                if (
                    support.kind != EvidenceKind.RULE_SUPPORT
                    or support.run_id != run_id
                    or support.subject_id != rule_id
                    or support.sequence >= decision_record.sequence
                ):
                    raise EvidenceIntegrityError("arbitration cites inadmissible support event")
            if prior_ref is not None and (
                not set(evidence) - seen_evidence
                or not new_evidence_recorded_after_predecessor
            ):
                raise EvidenceIntegrityError("appeal must cite newly recorded support evidence")
            seen_evidence.update(evidence)
            positions.append(ArbitrationPosition(cast(str, value["position"])))
            seen_actors.add(signed_actor)
            excluded.add(signed_actor)
            prior_ref = decision_ref
            prior_sequence = attestation_record.sequence

    independently_qualified = False
    if qualification_verifier is not None:
        for actor in sorted(seen_actors):
            evidence = qualification_bytes.get(actor)
            digest = expected_qualification_sha256.get(actor)
            if (
                not isinstance(evidence, bytes)
                or not isinstance(digest, str)
                or _SHA.fullmatch(digest) is None
                or sha256_bytes(evidence) != digest
            ):
                raise EvidenceIntegrityError("external arbitrator qualifications unverified")
            qualification_verifier.verify(
                actor_id=actor,
                excluded_actor_ids=tuple(sorted(excluded - {actor})),
                requirement_id=rule_id,
                case_sha256=case_hash,
                qualification_evidence=evidence,
                policy_sha256=cast(str, qualification_policy_sha256),
                at_time=now,
            )
        independently_qualified = True
    return ArbitrationResult(
        rule_id=rule_id,
        authenticated_decisions=len(positions),
        latest_position=positions[-1],
        appeal_count=len(positions) - 1,
        independently_qualified=independently_qualified,
        procedure_verified=independently_qualified,
    )
