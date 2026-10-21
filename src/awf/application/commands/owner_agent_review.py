"""Owner-governed agent review: separate experiments from formal adjudication.

The owner may also be the rule proposer. Two agent execution receipts are
compared as *claimed* runs, not verified distinct humans or independent truth.
An existing Ed25519 reviewer attestation authenticates only owner intent.
"""

from __future__ import annotations

import re
from typing import cast

from awf.application.commands.authorize_review import verify_signed_review_event
from awf.application.ports import EvidenceStorePort, ReviewerSignatureVerifierPort
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.domain.owner_agent_review import AgentVerdict, OwnerAction, OwnerReviewResult
from awf.domain.reviewer_auth import ReviewerRole, ReviewerTrustPolicy
from awf.domain.signed_documents import canonical_json_bytes, strict_json

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_EVENT = re.compile(r"event:([a-f0-9]{64})\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_REPORT_FIELDS = frozenset(
    {
        "schema",
        "type",
        "source_id",
        "archive_sha256",
        "requirement_id",
        "requirement_sha256",
        "proposal_ref",
        "agent_id",
        "execution_id",
        "model_id",
        "task_sha256",
        "verdict",
        "evidence_refs",
        "reasoned_assessment",
        "limitations",
    }
)
_DECISION_FIELDS = frozenset(
    {
        "schema",
        "type",
        "source_id",
        "archive_sha256",
        "requirement_id",
        "requirement_sha256",
        "proposal_ref",
        "task_sha256",
        "owner_actor_id",
        "agent_report_refs",
        "action",
        "reason",
    }
)


def _ref(value: str) -> str:
    if not isinstance(value, str) or (m := _EVENT.fullmatch(value)) is None:
        raise EvidenceIntegrityError("owner agent workflow requires exact ledger references")
    return m.group(1)


def _identity(value: str) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _sha(value: str) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def agent_report_payload(
    *,
    source_id: str,
    archive_sha256: str,
    requirement_id: str,
    requirement_sha256: str,
    proposal_ref: str,
    agent_id: str,
    execution_id: str,
    model_id: str,
    task_sha256: str,
    verdict: AgentVerdict,
    evidence_refs: tuple[str, ...],
    reasoned_assessment: str,
    limitations: str,
) -> bytes:
    if (
        not all(_identity(v) for v in (source_id, requirement_id, agent_id, execution_id, model_id))
        or not all(_sha(v) for v in (archive_sha256, requirement_sha256, task_sha256))
        or not isinstance(verdict, AgentVerdict)
        or not isinstance(evidence_refs, tuple)
        or not 1 <= len(evidence_refs) <= 32
        or len(set(evidence_refs)) != len(evidence_refs)
        or not isinstance(reasoned_assessment, str)
        or not 30 <= len(reasoned_assessment.strip()) <= 4096
        or not isinstance(limitations, str)
        or not 20 <= len(limitations.strip()) <= 4096
    ):
        raise EvidenceIntegrityError("invalid agent review report")
    _ref(proposal_ref)
    for ref in evidence_refs:
        _ref(ref)
    return canonical_json_bytes(
        {
            "schema": 1,
            "type": "owner_workflow_agent_report",
            "source_id": source_id,
            "archive_sha256": archive_sha256,
            "requirement_id": requirement_id,
            "requirement_sha256": requirement_sha256,
            "proposal_ref": proposal_ref,
            "agent_id": agent_id,
            "execution_id": execution_id,
            "model_id": model_id,
            "task_sha256": task_sha256,
            "verdict": verdict.value,
            "evidence_refs": list(evidence_refs),
            "reasoned_assessment": reasoned_assessment,
            "limitations": limitations,
        }
    )


def owner_review_decision_payload(
    *,
    source_id: str,
    archive_sha256: str,
    requirement_id: str,
    requirement_sha256: str,
    proposal_ref: str,
    task_sha256: str,
    owner_actor_id: str,
    agent_report_refs: tuple[str, str],
    action: OwnerAction,
    reason: str,
) -> bytes:
    if (
        not all(_identity(v) for v in (source_id, requirement_id, owner_actor_id))
        or not all(_sha(v) for v in (archive_sha256, requirement_sha256, task_sha256))
        or not isinstance(agent_report_refs, tuple)
        or len(agent_report_refs) != 2
        or len(set(agent_report_refs)) != 2
        or not isinstance(action, OwnerAction)
        or not isinstance(reason, str)
        or not 30 <= len(reason.strip()) <= 4096
    ):
        raise EvidenceIntegrityError("invalid owner review decision")
    _ref(proposal_ref)
    for ref in agent_report_refs:
        _ref(ref)
    return canonical_json_bytes(
        {
            "schema": 1,
            "type": "owner_workflow_decision",
            "source_id": source_id,
            "archive_sha256": archive_sha256,
            "requirement_id": requirement_id,
            "requirement_sha256": requirement_sha256,
            "proposal_ref": proposal_ref,
            "task_sha256": task_sha256,
            "owner_actor_id": owner_actor_id,
            "agent_report_refs": list(agent_report_refs),
            "action": action.value,
            "reason": reason,
        }
    )


def _rebuild_report(value: dict[str, object]) -> bytes:
    if set(value) != _REPORT_FIELDS or type(value["schema"]) is not int or value["schema"] != 1:
        raise EvidenceIntegrityError("unsupported agent report schema")
    refs = value["evidence_refs"]
    if not isinstance(refs, list) or not all(isinstance(v, str) for v in refs):
        raise EvidenceIntegrityError("agent evidence references must be strings")
    try:
        return agent_report_payload(
            source_id=cast(str, value["source_id"]),
            archive_sha256=cast(str, value["archive_sha256"]),
            requirement_id=cast(str, value["requirement_id"]),
            requirement_sha256=cast(str, value["requirement_sha256"]),
            proposal_ref=cast(str, value["proposal_ref"]),
            agent_id=cast(str, value["agent_id"]),
            execution_id=cast(str, value["execution_id"]),
            model_id=cast(str, value["model_id"]),
            task_sha256=cast(str, value["task_sha256"]),
            verdict=AgentVerdict(cast(str, value["verdict"])),
            evidence_refs=tuple(cast(list[str], refs)),
            reasoned_assessment=cast(str, value["reasoned_assessment"]),
            limitations=cast(str, value["limitations"]),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise EvidenceIntegrityError("malformed agent report") from exc


def _rebuild_decision(value: dict[str, object]) -> bytes:
    if set(value) != _DECISION_FIELDS or type(value["schema"]) is not int or value["schema"] != 1:
        raise EvidenceIntegrityError("unsupported owner decision schema")
    refs = value["agent_report_refs"]
    if not isinstance(refs, list) or len(refs) != 2 or not all(isinstance(v, str) for v in refs):
        raise EvidenceIntegrityError("owner decision requires two agent event refs")
    try:
        return owner_review_decision_payload(
            source_id=cast(str, value["source_id"]),
            archive_sha256=cast(str, value["archive_sha256"]),
            requirement_id=cast(str, value["requirement_id"]),
            requirement_sha256=cast(str, value["requirement_sha256"]),
            proposal_ref=cast(str, value["proposal_ref"]),
            task_sha256=cast(str, value["task_sha256"]),
            owner_actor_id=cast(str, value["owner_actor_id"]),
            agent_report_refs=(cast(str, refs[0]), cast(str, refs[1])),
            action=OwnerAction(cast(str, value["action"])),
            reason=cast(str, value["reason"]),
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise EvidenceIntegrityError("malformed owner decision") from exc


def verify_owner_review(
    *,
    store: EvidenceStorePort,
    run_id: str,
    rule_id: str,
    source_id: str,
    archive_sha256: str,
    requirement_sha256: str,
    task_sha256: str,
    proposal_refs: tuple[str, str],
    agent_report_refs: tuple[str, str],
    owner_decision_refs: tuple[str, str],
    expected_owner_actor_id: str,
    expected_reviewer_policy_sha256: str,
    expected_head: str,
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
) -> OwnerReviewResult:
    """Verify exact owner authorization of a reproducible EVAL_ONLY pilot.

    Caller MUST externally retain canonical source/task/reviewer-policy hashes
    and exact ledger head. No result licenses data, trains models or adjudicates
    historical science.
    """
    if (
        not all(
            _sha(v)
            for v in (
                archive_sha256,
                requirement_sha256,
                task_sha256,
                expected_reviewer_policy_sha256,
                expected_head,
            )
        )
        or policy.policy_sha256 != expected_reviewer_policy_sha256
        or not _identity(expected_owner_actor_id)
        or not _identity(source_id)
        or not _identity(rule_id)
        or not isinstance(agent_report_refs, tuple)
        or len(agent_report_refs) != 2
        or len(set(agent_report_refs)) != 2
        or not isinstance(proposal_refs, tuple)
        or len(proposal_refs) != 2
        or not isinstance(owner_decision_refs, tuple)
        or len(owner_decision_refs) != 2
    ):
        raise EvidenceIntegrityError("externally pinned owner review inventory required")
    identities = (source_id, archive_sha256, rule_id, requirement_sha256)
    proposal_ref, proposal_sig = proposal_refs
    decision_ref, decision_sig = owner_decision_refs
    verdicts: list[AgentVerdict] = []
    agent_ids: set[str] = set()
    executions: set[str] = set()
    models: set[str] = set()
    with store.verified_read(expected_head=expected_head) as reader:
        signed_proposer = verify_signed_review_event(
            store=reader,
            attestation_ref=proposal_sig,
            target_ref=proposal_ref,
            expected_role=ReviewerRole.KNOWLEDGE_REVIEWER,
            run_id=run_id,
            subject_id=rule_id,
            policy=policy,
            verifier=verifier,
            now=now,
            expected_head=expected_head,
        )
        proposal_record, proposal_data = reader.resolve_event(
            event_digest=_ref(proposal_ref), expected_head=expected_head
        )
        proposal = strict_json(proposal_data)
        if (
            proposal_record.kind != EvidenceKind.KNOWLEDGE_REVIEW_PROPOSAL
            or proposal_record.run_id != run_id
            or proposal_record.subject_id != rule_id
            or proposal.get("type") != "private_dossier_review_proposal"
            or tuple(
                proposal.get(key)
                for key in ("source_id", "archive_sha256", "requirement_id", "requirement_sha256")
            )
            != identities
            or proposal.get("reviewer_actor_id") != signed_proposer
        ):
            raise EvidenceIntegrityError("owner workflow proposal identity/source mismatch")

        latest_report_sequence = proposal_record.sequence
        for ref in agent_report_refs:
            record, data = reader.resolve_event(event_digest=_ref(ref), expected_head=expected_head)
            if (
                record.kind != EvidenceKind.AGENT_REVIEW_REPORT
                or record.run_id != run_id
                or record.subject_id != rule_id
                or record.sequence <= proposal_record.sequence
            ):
                raise EvidenceIntegrityError("agent report run or chronology mismatch")
            row = strict_json(data)
            if (
                _rebuild_report(row) != data
                or (
                    row["source_id"],
                    row["archive_sha256"],
                    row["requirement_id"],
                    row["requirement_sha256"],
                )
                != identities
                or row["proposal_ref"] != proposal_ref
                or row["task_sha256"] != task_sha256
            ):
                raise EvidenceIntegrityError("agent report source/task binding mismatch")
            agent = cast(str, row["agent_id"])
            execution = cast(str, row["execution_id"])
            if agent in agent_ids or execution in executions:
                raise EvidenceIntegrityError("same agent/run cannot be counted as second review")
            agent_ids.add(agent)
            executions.add(execution)
            models.add(cast(str, row["model_id"]))
            verdicts.append(AgentVerdict(cast(str, row["verdict"])))
            latest_report_sequence = max(latest_report_sequence, record.sequence)
            for evidence_ref in cast(list[str], row["evidence_refs"]):
                support, _ = reader.resolve_event(
                    event_digest=_ref(evidence_ref), expected_head=expected_head
                )
                if (
                    support.kind != EvidenceKind.RULE_SUPPORT
                    or support.run_id != run_id
                    or support.subject_id != rule_id
                    or support.sequence >= record.sequence
                ):
                    raise EvidenceIntegrityError("agent cites wrong or unrecorded source support")

        decision_record, data = reader.resolve_event(
            event_digest=_ref(decision_ref), expected_head=expected_head
        )
        decision = strict_json(data)
        if (
            decision_record.kind != EvidenceKind.OWNER_EVALUATION_DECISION
            or decision_record.run_id != run_id
            or decision_record.subject_id != rule_id
            or decision_record.sequence <= latest_report_sequence
            or _rebuild_decision(decision) != data
            or tuple(
                decision[key]
                for key in ("source_id", "archive_sha256", "requirement_id", "requirement_sha256")
            )
            != identities
            or decision["proposal_ref"] != proposal_ref
            or decision["task_sha256"] != task_sha256
            or decision["agent_report_refs"] != list(agent_report_refs)
            or decision["owner_actor_id"] != expected_owner_actor_id
        ):
            raise EvidenceIntegrityError("owner decision binds wrong reports/task/source")
        signed_owner = verify_signed_review_event(
            store=reader,
            attestation_ref=decision_sig,
            target_ref=decision_ref,
            expected_role=ReviewerRole.PROJECT_OWNER,
            run_id=run_id,
            subject_id=rule_id,
            policy=policy,
            verifier=verifier,
            now=now,
            expected_head=expected_head,
        )
        if signed_owner != expected_owner_actor_id or signed_owner in agent_ids:
            raise EvidenceIntegrityError("owner signer identity mismatch")
        action = OwnerAction(cast(str, decision["action"]))

    return OwnerReviewResult(
        rule_id=rule_id,
        owner_actor_id=expected_owner_actor_id,
        verified_agent_reports=2,
        verdicts=tuple(verdicts),
        distinct_model_ids=len(models),
        owner_action=action,
        pilot_evaluation_approved=action is OwnerAction.APPROVE_PILOT_EVALUATION,
    )
