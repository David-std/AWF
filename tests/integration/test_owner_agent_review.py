"""Owner is a project decision-maker, not a fabricated independent scientist."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.security.ed25519_reviewer import Ed25519ReviewerVerifier
from awf.application.commands.authorize_review import append_signed_review_claim
from awf.application.commands.owner_agent_review import (
    agent_report_payload,
    owner_review_decision_payload,
    verify_owner_review,
)
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.owner_agent_review import AgentVerdict, OwnerAction
from awf.domain.reviewer_auth import (
    ReviewerClaim,
    ReviewerRole,
    SignedReviewerClaim,
    parse_trust_policy,
)
from awf.domain.signed_documents import canonical_json_bytes

RUN = "pilot-001"
RULE = "DSR-001"
SOURCE = "a" * 64
RULE_SHA = "b" * 64
TASK = "c" * 64
NOW = 1_800_000_000


def _pub(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()


def _attest(store, *, target, key, actor, key_id, role, policy):
    claim = ReviewerClaim(
        actor_id=actor,
        key_id=key_id,
        role=role,
        run_id=RUN,
        subject_id=RULE,
        target_event_ref=f"event:{target.digest}",
        issued_at=NOW - 10,
    )
    signed = SignedReviewerClaim(claim, key.sign(claim.signing_bytes).hex())
    event = append_signed_review_claim(
        store=store, signed=signed, policy=policy,
        verifier=Ed25519ReviewerVerifier(), now=NOW,
    )
    return f"event:{event.digest}"


def _fixture(tmp_path: Path, *, action=OwnerAction.APPROVE_PILOT_EVALUATION,
             same_agent=False, wrong_source=False, owner_is_proposer=True):
    store = SQLiteEvidenceLedger(tmp_path / "owner-review.sqlite")
    store.initialize()
    proposer_key = Ed25519PrivateKey.generate()
    owner_key = proposer_key if owner_is_proposer else Ed25519PrivateKey.generate()
    proposer_actor = "project-owner" if owner_is_proposer else "rule-proposer"
    grants = [
        {
            "actor_id": proposer_actor,
            "key_id": "proposer-key",
            "public_key_hex": _pub(proposer_key),
            "roles": ["KNOWLEDGE_REVIEWER", "PROJECT_OWNER"]
            if owner_is_proposer else ["KNOWLEDGE_REVIEWER"],
            "runs": [RUN],
            "subjects": [RULE],
            "valid_from": NOW - 100,
            "valid_until": NOW + 100,
            "revoked": False,
        }
    ]
    if not owner_is_proposer:
        grants.append(
            {
                "actor_id": "project-owner",
                "key_id": "owner-key",
                "public_key_hex": _pub(owner_key),
                "roles": ["PROJECT_OWNER"],
                "runs": [RUN],
                "subjects": [RULE],
                "valid_from": NOW - 100,
                "valid_until": NOW + 100,
                "revoked": False,
            }
        )
    raw_policy = canonical_json_bytes({"schema": 1, "grants": grants})
    policy = parse_trust_policy(
        raw_policy, expected_sha256=sha256_bytes(raw_policy)
    )
    support = store.append(
        kind=EvidenceKind.RULE_SUPPORT, run_id=RUN, subject_id=RULE,
        content=b"synthetic source-linked evaluation reference",
    )
    evidence_ref = f"event:{support.digest}"
    proposal = store.append(
        kind=EvidenceKind.KNOWLEDGE_REVIEW_PROPOSAL, run_id=RUN, subject_id=RULE,
        content=canonical_json_bytes(
            {
                "schema": 1, "type": "private_dossier_review_proposal",
                "source_id": "aws-3.19.1", "archive_sha256": SOURCE,
                "requirement_id": RULE, "requirement_sha256": RULE_SHA,
                "reviewer_actor_id": proposer_actor,
                "review_template_sha256": "e" * 64,
                "review_status": "PROPOSAL_DOCUMENTED",
            }
        ),
    )
    proposal_ref = f"event:{proposal.digest}"
    proposal_sig = _attest(
        store, target=proposal, key=proposer_key, actor=proposer_actor,
        key_id="proposer-key", role=ReviewerRole.KNOWLEDGE_REVIEWER, policy=policy,
    )
    reviews = []
    for i, verdict in enumerate((AgentVerdict.SUPPORT, AgentVerdict.CONTEST)):
        report = store.append(
            kind=EvidenceKind.AGENT_REVIEW_REPORT,
            run_id=RUN, subject_id=RULE,
            content=agent_report_payload(
                source_id="aws-3.19.1",
                archive_sha256="f" * 64 if wrong_source and i == 1 else SOURCE,
                requirement_id=RULE, requirement_sha256=RULE_SHA,
                proposal_ref=proposal_ref,
                agent_id="agent-0" if same_agent else f"agent-{i}",
                execution_id=f"execution-{i}",
                model_id="qwen-same-model",
                task_sha256=TASK, verdict=verdict,
                evidence_refs=(evidence_ref,),
                reasoned_assessment="Synthetic source notes were reviewed and compared to constraints.",
                limitations="This model output does not establish external scholarly truth.",
            ),
        )
        reviews.append(f"event:{report.digest}")
    decision = store.append(
        kind=EvidenceKind.OWNER_EVALUATION_DECISION, run_id=RUN, subject_id=RULE,
        content=owner_review_decision_payload(
            source_id="aws-3.19.1",
            archive_sha256=SOURCE,
            requirement_id=RULE, requirement_sha256=RULE_SHA,
            proposal_ref=proposal_ref, task_sha256=TASK,
            owner_actor_id="project-owner",
            agent_report_refs=(reviews[0], reviews[1]),
            action=action,
            reason="The project owner approves a reproducible comparison experiment only.",
        ),
    )
    owner_ref = f"event:{decision.digest}"
    owner_sig = _attest(
        store, target=decision, key=owner_key, actor="project-owner",
        key_id="proposer-key" if owner_is_proposer else "owner-key",
        role=ReviewerRole.PROJECT_OWNER, policy=policy,
    )
    return {
        "store": store, "policy": policy,
        "proposal_refs": (proposal_ref, proposal_sig),
        "agent_report_refs": (reviews[0], reviews[1]),
        "owner_decision_refs": (owner_ref, owner_sig),
        "expected_head": store.verify().head_digest,
    }


def _check(case, **overrides):
    args = {
        "store": case["store"], "run_id": RUN, "rule_id": RULE,
        "source_id": "aws-3.19.1",
        "archive_sha256": SOURCE, "requirement_sha256": RULE_SHA,
        "task_sha256": TASK,
        "proposal_refs": case["proposal_refs"],
        "agent_report_refs": case["agent_report_refs"],
        "owner_decision_refs": case["owner_decision_refs"],
        "expected_owner_actor_id": "project-owner",
        "expected_reviewer_policy_sha256": case["policy"].policy_sha256,
        "expected_head": case["expected_head"], "policy": case["policy"],
        "verifier": Ed25519ReviewerVerifier(), "now": NOW,
    }
    args.update(overrides)
    return verify_owner_review(**args)


def test_owner_can_approve_pilot_even_when_owner_is_proposer(tmp_path: Path):
    result = _check(_fixture(tmp_path))
    assert result.pilot_evaluation_approved
    assert result.verified_agent_reports == 2
    assert result.distinct_model_ids == 1
    assert result.verdicts == (AgentVerdict.SUPPORT, AgentVerdict.CONTEST)
    assert result.to_dict()["scientific_adjudications"] == 0
    assert result.to_dict()["training_authorized"] is False
    assert result.to_dict()["historical_rule_disposition_changed"] is False


def test_owner_can_request_revision_without_pilot_authorization(tmp_path: Path):
    result = _check(_fixture(tmp_path, action=OwnerAction.REQUEST_REVISION))
    assert not result.pilot_evaluation_approved


def test_owner_can_be_different_from_proposer(tmp_path: Path):
    result = _check(_fixture(tmp_path, owner_is_proposer=False))
    assert result.owner_actor_id == "project-owner"
    assert result.pilot_evaluation_approved


def test_claimed_agent_execution_must_be_distinct(tmp_path: Path):
    case = _fixture(tmp_path, same_agent=True)
    with pytest.raises(EvidenceIntegrityError, match="same agent/run"):
        _check(case)


def test_wrong_agent_source_fails_even_when_owner_signed(tmp_path: Path):
    case = _fixture(tmp_path, wrong_source=True)
    with pytest.raises(EvidenceIntegrityError, match="source/task binding"):
        _check(case)


def test_stale_ledger_head_blocks_owner_action(tmp_path: Path):
    case = _fixture(tmp_path)
    old = case["expected_head"]
    case["store"].append(
        kind=EvidenceKind.RULE_SUPPORT,
        run_id=RUN, subject_id=RULE, content=b"subsequent evidence",
    )
    with pytest.raises(EvidenceIntegrityError, match="head"):
        _check(case, expected_head=old)


def test_swapping_reports_invalidates_signed_owner_decision(tmp_path: Path):
    case = _fixture(tmp_path)
    r0, r1 = case["agent_report_refs"]
    with pytest.raises(EvidenceIntegrityError, match="wrong reports/task/source"):
        _check(case, agent_report_refs=(r1, r0))


def test_fake_owner_actor_id_cannot_use_valid_original_signature(tmp_path: Path):
    case = _fixture(tmp_path)
    with pytest.raises(EvidenceIntegrityError, match="wrong reports/task/source"):
        _check(case, expected_owner_actor_id="imposter")


def test_corrupt_policy_anchor_is_rejected(tmp_path: Path):
    case = _fixture(tmp_path)
    with pytest.raises(EvidenceIntegrityError, match="externally pinned"):
        _check(case, expected_reviewer_policy_sha256="f" * 64)


def test_unbound_evidence_references_are_rejected():
    with pytest.raises(EvidenceIntegrityError, match="exact ledger"):
        agent_report_payload(
            source_id="aws-3.19.1", archive_sha256=SOURCE,
            requirement_id=RULE, requirement_sha256=RULE_SHA,
            proposal_ref="event:" + "e" * 64,
            agent_id="agent-a", execution_id="execution-b",
            model_id="qwen", task_sha256=TASK, verdict=AgentVerdict.SUPPORT,
            evidence_refs=("sha256:" + "e" * 64,),
            reasoned_assessment="Synthetic observations that are source-related but cannot prove truth.",
            limitations="No independent validation of the scientific correctness.",
        )
