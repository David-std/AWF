"""Governance decision chain atop independently verified scientific arbitration.

The register is a *procedural* projection. Only a separately appointed real
external authority can validate quorum members, competence and conflicts.
It never mutates historical rule dispositions or grants model training rights.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from awf.application.commands.authorize_review import verify_signed_review_event
from awf.application.commands.scientific_arbitration import (
    ExternalQualificationPort,
    verify_scientific_arbitration,
)
from awf.application.ports import EvidenceStorePort, ReviewerSignatureVerifierPort
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import ReviewerRole, ReviewerTrustPolicy
from awf.domain.scientific_arbitration import ArbitrationPosition
from awf.domain.scientific_governance import (
    GovernanceAction,
    GovernancePolicy,
    GovernanceResult,
    GovernanceState,
    next_governance_state,
)
from awf.domain.signed_documents import canonical_json_bytes, strict_json

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_EVENT = re.compile(r"event:([a-f0-9]{64})\Z")
_FIELDS = frozenset(
    {
        "schema",
        "type",
        "source_id",
        "archive_sha256",
        "requirement_id",
        "requirement_sha256",
        "case_sha256",
        "final_arbitration_ref",
        "previous_decision_ref",
        "from_state",
        "action",
        "reason",
        "support_refs",
        "governance_policy_sha256",
    }
)


class ExternalGovernanceAuthorityPort(Protocol):
    """Independent appointed organization validates each governor's person and COI.

    A local key, signature, claimed qualification, invented name or JSON record
    cannot verify their own appointing institution.
    """

    def verify(
        self,
        *,
        actor_id: str,
        excluded_actor_ids: tuple[str, ...],
        rule_id: str,
        case_sha256: str,
        decision_ref: str,
        evidence: bytes,
        governance_policy_sha256: str,
        at_time: int,
    ) -> None:
        """Raise on invalid mandate, identity, competence, independence or conflict."""
        ...


@dataclass(frozen=True, slots=True)
class ArbitrationContext:
    canonical_manifest: Mapping[str, Any]
    canonical_packets: Mapping[str, Mapping[str, Any]]
    observed_manifest: Mapping[str, Any]
    observed_packets: Mapping[str, Mapping[str, Any]]
    proposal_refs: Mapping[str, tuple[str, str]]
    left_assessments: Mapping[str, tuple[str, str]]
    right_assessments: Mapping[str, tuple[str, str]]
    case_bytes: Mapping[str, bytes]
    expected_case_sha256: Mapping[str, str]
    rule_id: str
    arbitration_refs: tuple[tuple[str, str], ...]
    qualification_bytes: Mapping[str, bytes]
    expected_qualification_sha256: Mapping[str, str]
    qualification_policy_sha256: str | None
    qualification_verifier: ExternalQualificationPort | None
    store: EvidenceStorePort
    run_id: str
    expected_head: str
    reviewer_policy: ReviewerTrustPolicy
    verifier: ReviewerSignatureVerifierPort
    now: int


def _digest(ref: str) -> str:
    if not isinstance(ref, str) or (m := _EVENT.fullmatch(ref)) is None:
        raise EvidenceIntegrityError("governance requires exact ledger event references")
    return m.group(1)


def governance_transition_payload(
    *,
    source_id: str,
    archive_sha256: str,
    requirement_id: str,
    requirement_sha256: str,
    case_sha256: str,
    final_arbitration_ref: str,
    previous_decision_ref: str | None,
    from_state: GovernanceState,
    action: GovernanceAction,
    reason: str,
    support_refs: tuple[str, ...],
    governance_policy_sha256: str,
) -> bytes:
    """Canonical decision intent. An intent by itself cannot change any state."""
    if (
        not isinstance(source_id, str)
        or _ID.fullmatch(source_id) is None
        or not isinstance(requirement_id, str)
        or _ID.fullmatch(requirement_id) is None
        or any(
            not isinstance(v, str) or _SHA.fullmatch(v) is None
            for v in (
                archive_sha256,
                requirement_sha256,
                case_sha256,
                governance_policy_sha256,
            )
        )
        or not isinstance(from_state, GovernanceState)
        or not isinstance(action, GovernanceAction)
        or not isinstance(reason, str)
        or not 40 <= len(reason.strip()) <= 4096
        or not isinstance(support_refs, tuple)
        or not 1 <= len(support_refs) <= 32
        or len(set(support_refs)) != len(support_refs)
    ):
        raise EvidenceIntegrityError("invalid governance transition intent")
    _digest(final_arbitration_ref)
    if previous_decision_ref is not None:
        _digest(previous_decision_ref)
        if previous_decision_ref == final_arbitration_ref:
            raise EvidenceIntegrityError("governance predecessor is an arbitration event")
    for ref in support_refs:
        _digest(ref)
    next_governance_state(from_state, action)
    return canonical_json_bytes(
        {
            "schema": 1,
            "type": "scientific_governance_transition",
            "source_id": source_id,
            "archive_sha256": archive_sha256,
            "requirement_id": requirement_id,
            "requirement_sha256": requirement_sha256,
            "case_sha256": case_sha256,
            "final_arbitration_ref": final_arbitration_ref,
            "previous_decision_ref": previous_decision_ref,
            "from_state": from_state.value,
            "action": action.value,
            "reason": reason,
            "support_refs": list(support_refs),
            "governance_policy_sha256": governance_policy_sha256,
        }
    )


def _rebuild(value: dict[str, object]) -> bytes:
    if (
        set(value) != _FIELDS
        or type(value["schema"]) is not int
        or value["schema"] != 1
        or value["type"] != "scientific_governance_transition"
    ):
        raise EvidenceIntegrityError("invalid governance transition schema")
    try:
        refs = value["support_refs"]
        if not isinstance(refs, list) or not all(isinstance(v, str) for v in refs):
            raise EvidenceIntegrityError("invalid governance support references")
        return governance_transition_payload(
            source_id=cast(str, value["source_id"]),
            archive_sha256=cast(str, value["archive_sha256"]),
            requirement_id=cast(str, value["requirement_id"]),
            requirement_sha256=cast(str, value["requirement_sha256"]),
            case_sha256=cast(str, value["case_sha256"]),
            final_arbitration_ref=cast(str, value["final_arbitration_ref"]),
            previous_decision_ref=cast(str | None, value["previous_decision_ref"]),
            from_state=GovernanceState(cast(str, value["from_state"])),
            action=GovernanceAction(cast(str, value["action"])),
            reason=cast(str, value["reason"]),
            support_refs=tuple(cast(list[str], refs)),
            governance_policy_sha256=cast(str, value["governance_policy_sha256"]),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise EvidenceIntegrityError("malformed governance transition") from exc


def verify_governance_register(
    context: ArbitrationContext,
    *,
    policy: GovernancePolicy,
    transitions: tuple[tuple[str, tuple[str, ...]], ...],
    authority_evidence: Mapping[str, bytes],
    expected_authority_evidence_sha256: Mapping[str, str],
    authority: ExternalGovernanceAuthorityPort | None = None,
) -> GovernanceResult:
    """Project a reversible register only after full external governance checks.

    A mere signed act may be inspected but never applied without the real
    independent arbitrator qualification AND separate governing authority.
    No production authority adapter is shipped.
    """
    result = verify_scientific_arbitration(
        canonical_manifest=context.canonical_manifest,
        canonical_packets=context.canonical_packets,
        observed_manifest=context.observed_manifest,
        observed_packets=context.observed_packets,
        proposal_refs=context.proposal_refs,
        left_assessments=context.left_assessments,
        right_assessments=context.right_assessments,
        case_bytes=context.case_bytes,
        expected_case_sha256=context.expected_case_sha256,
        rule_id=context.rule_id,
        arbitration_refs=context.arbitration_refs,
        qualification_bytes=context.qualification_bytes,
        expected_qualification_sha256=context.expected_qualification_sha256,
        qualification_policy_sha256=context.qualification_policy_sha256,
        qualification_verifier=context.qualification_verifier,
        store=context.store,
        run_id=context.run_id,
        expected_head=context.expected_head,
        policy=context.reviewer_policy,
        verifier=context.verifier,
        now=context.now,
    )
    if not isinstance(transitions, tuple) or len(transitions) > policy.max_transitions:
        raise EvidenceIntegrityError("governance transitions exceed approved policy")
    if set(authority_evidence) != set(expected_authority_evidence_sha256):
        raise EvidenceIntegrityError("governance evidence pins inventory mismatch")

    initial = GovernanceState.OPEN
    intended_state = initial
    previous_ref: str | None = None
    preceding_signature_sequence = 0
    checked_actors: dict[str, tuple[str, str, tuple[str, ...]]] = {}
    latest_arb_ref = context.arbitration_refs[-1][0]
    expected_case = context.expected_case_sha256[context.rule_id]
    canonical = {
        str(row["id"]): row
        for packet in context.canonical_packets.values()
        for row in packet["rules"]
    }
    rule_sha = canonical[context.rule_id]["requirement_sha256"]
    excluded_actors: set[str] = set()

    with context.store.verified_read(expected_head=context.expected_head) as reader:
        prerequisites = [
            (context.proposal_refs[context.rule_id], ReviewerRole.KNOWLEDGE_REVIEWER),
            (context.left_assessments[context.rule_id], ReviewerRole.SCIENTIFIC_REVIEWER),
            (context.right_assessments[context.rule_id], ReviewerRole.SCIENTIFIC_REVIEWER),
            *((signed, ReviewerRole.SCIENTIFIC_ARBITER) for signed in context.arbitration_refs),
        ]
        for (event_ref, signed_ref), role in prerequisites:
            excluded_actors.add(
                verify_signed_review_event(
                    store=reader,
                    attestation_ref=signed_ref,
                    target_ref=event_ref,
                    expected_role=role,
                    run_id=context.run_id,
                    subject_id=context.rule_id,
                    policy=context.reviewer_policy,
                    verifier=context.verifier,
                    now=context.now,
                    expected_head=context.expected_head,
                )
            )
            rec, _ = reader.resolve_event(
                event_digest=_digest(signed_ref), expected_head=context.expected_head
            )
            preceding_signature_sequence = max(preceding_signature_sequence, rec.sequence)
        for event_ref, signatures in transitions:
            if (
                not isinstance(signatures, tuple)
                or len(signatures) < policy.quorum
                or len(signatures) > 8
                or len(set(signatures)) != len(signatures)
            ):
                raise EvidenceIntegrityError("missing unique governance approval quorum")
            record, data = reader.resolve_event(
                event_digest=_digest(event_ref), expected_head=context.expected_head
            )
            if (
                record.kind != EvidenceKind.SCIENTIFIC_GOVERNANCE
                or record.run_id != context.run_id
                or record.subject_id != context.rule_id
                or record.sequence <= preceding_signature_sequence
            ):
                raise EvidenceIntegrityError("governance event identity/chronology mismatch")
            value = strict_json(data)
            if _rebuild(value) != data:
                raise EvidenceIntegrityError("governance transition content not canonical")
            if (
                value["source_id"] != context.canonical_manifest["source_id"]
                or value["archive_sha256"] != context.canonical_manifest["archive_sha256"]
                or value["requirement_id"] != context.rule_id
                or value["requirement_sha256"] != rule_sha
                or value["case_sha256"] != expected_case
                or value["final_arbitration_ref"] != latest_arb_ref
                or value["previous_decision_ref"] != previous_ref
                or value["governance_policy_sha256"] != policy.sha256
                or value["from_state"] != intended_state.value
            ):
                raise EvidenceIntegrityError("governance state/source/predecessor drift")
            action = GovernanceAction(cast(str, value["action"]))
            if action == GovernanceAction.RATIFY and result.latest_position not in {
                ArbitrationPosition.SUPPORT,
                ArbitrationPosition.CONTEST,
            }:
                raise EvidenceIntegrityError("unresolved arbitration cannot be ratified")
            evidence = cast(list[str], value["support_refs"])
            freshly_recorded = False
            for evidence_ref in evidence:
                support, _ = reader.resolve_event(
                    event_digest=_digest(evidence_ref), expected_head=context.expected_head
                )
                if (
                    support.kind != EvidenceKind.RULE_SUPPORT
                    or support.run_id != context.run_id
                    or support.subject_id != context.rule_id
                    or support.sequence >= record.sequence
                ):
                    raise EvidenceIntegrityError("governance cites inadmissible evidence")
                if support.sequence > preceding_signature_sequence:
                    freshly_recorded = True
            if previous_ref is not None and not freshly_recorded:
                raise EvidenceIntegrityError("governance reconsideration requires fresh evidence")
            signed_actors: set[str] = set()
            max_sig = record.sequence
            for sig_ref in signatures:
                actor = verify_signed_review_event(
                    store=reader,
                    attestation_ref=sig_ref,
                    target_ref=event_ref,
                    expected_role=ReviewerRole.GOVERNANCE_APPROVER,
                    run_id=context.run_id,
                    subject_id=context.rule_id,
                    policy=context.reviewer_policy,
                    verifier=context.verifier,
                    now=context.now,
                    expected_head=context.expected_head,
                )
                signed_rec, _ = reader.resolve_event(
                    event_digest=_digest(sig_ref), expected_head=context.expected_head
                )
                if actor in signed_actors or actor in excluded_actors or actor in checked_actors:
                    raise EvidenceIntegrityError("governance signer duplicated or conflicted")
                signed_actors.add(actor)
                max_sig = max(max_sig, signed_rec.sequence)
                checked_actors[actor] = (
                    event_ref,
                    cast(str, value["case_sha256"]),
                    tuple(sorted(excluded_actors)),
                )
            intended_state = next_governance_state(intended_state, action)
            previous_ref = event_ref
            preceding_signature_sequence = max_sig

    all_actors = set(checked_actors)
    if authority is None or not result.procedure_verified or not transitions:
        return GovernanceResult(
            context.rule_id,
            len(transitions),
            0,
            GovernanceState.OPEN,
            False,
            result.independently_qualified,
        )
    if set(authority_evidence) != all_actors:
        raise EvidenceIntegrityError("externally verified governance actors inventory mismatch")
    for actor, (event_ref, case_sha256, earlier_exclusions) in checked_actors.items():
        raw = authority_evidence[actor]
        digest = expected_authority_evidence_sha256[actor]
        if (
            not isinstance(raw, bytes)
            or not isinstance(digest, str)
            or _SHA.fullmatch(digest) is None
            or sha256_bytes(raw) != digest
        ):
            raise EvidenceIntegrityError("externally pinned governing evidence invalid")
        authority.verify(
            actor_id=actor,
            excluded_actor_ids=tuple(sorted(set(earlier_exclusions) | (all_actors - {actor}))),
            rule_id=context.rule_id,
            case_sha256=case_sha256,
            decision_ref=event_ref,
            evidence=raw,
            governance_policy_sha256=policy.sha256,
            at_time=context.now,
        )
    return GovernanceResult(
        context.rule_id,
        len(transitions),
        len(transitions),
        intended_state,
        True,
        result.independently_qualified,
    )
