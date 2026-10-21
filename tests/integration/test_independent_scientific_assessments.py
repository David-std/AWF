"""Synthetic independent scientific reviewer receipts are never adjudications."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.security.ed25519_reviewer import Ed25519ReviewerVerifier
from awf.application.commands.authorize_dossiers import private_dossier_proposal_payload
from awf.application.commands.authorize_review import append_signed_review_claim
from awf.application.commands.scientific_assessments import (
    parse_scientific_assessment_inventory,
    scientific_assessment_payload,
    verify_independent_scientific_assessments,
)
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import (
    ReviewerClaim,
    ReviewerRole,
    SignedReviewerClaim,
    parse_trust_policy,
)
from awf.domain.signed_documents import canonical_json_bytes

RUN = "science-run-001"
RULE = "DSR-001"
NOW = 1_800_000_000
SOURCE = "a" * 64
RULE_SHA = "b" * 64


def _public(key: Ed25519PrivateKey) -> str:
    return (
        key.public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        .hex()
    )


def _make_policy(
    proposer_key, scientist_key, *, scientist_role="SCIENTIFIC_REVIEWER", revoked=False
):
    raw = canonical_json_bytes(
        {
            "schema": 1,
            "grants": [
                {
                    "actor_id": actor,
                    "key_id": key_id,
                    "public_key_hex": _public(key),
                    "roles": [role],
                    "runs": [RUN],
                    "subjects": [RULE],
                    "valid_from": NOW - 100,
                    "valid_until": NOW + 100,
                    "revoked": revoked if actor == "scientist-b" else False,
                }
                for actor, key_id, key, role in [
                    ("proposer-a", "proposer-key", proposer_key, "KNOWLEDGE_REVIEWER"),
                    ("scientist-b", "scientist-key", scientist_key, scientist_role),
                ]
            ],
        }
    )
    return parse_trust_policy(raw, expected_sha256=sha256_bytes(raw))


def _attest(store, *, key, actor, key_id, role, target, policy):
    claim = ReviewerClaim(
        actor_id=actor,
        key_id=key_id,
        role=role,
        run_id=RUN,
        subject_id=RULE,
        target_event_ref=f"event:{target.digest}",
        issued_at=NOW - 10,
    )
    return append_signed_review_claim(
        store=store,
        signed=SignedReviewerClaim(claim, key.sign(claim.signing_bytes).hex()),
        policy=policy,
        verifier=Ed25519ReviewerVerifier(),
        now=NOW,
    )


def scenario(tmp_path: Path):
    store = SQLiteEvidenceLedger(tmp_path / "ledger.sqlite")
    store.initialize()
    proposer_key = Ed25519PrivateKey.generate()
    scientist_key = Ed25519PrivateKey.generate()
    policy = _make_policy(proposer_key, scientist_key)
    manifest = {"archive_sha256": SOURCE, "source_id": "aws-3.19.1"}
    empty = {
        "reviewer": None,
        "reason": None,
        "evidence_ids": [],
        "conflicting_rule_ids": [],
        "desired_disposition": None,
        "proposed_tests": [],
        "source_rights_status": "NOT_EVALUATED",
        "current_model_or_version_evidence": None,
    }
    canonical = {
        "id": RULE,
        "priority": "MUST",
        "requirement_sha256": RULE_SHA,
        "review_template": empty,
    }
    original = {"batch-001.json": {"batch_id": "B-001", "rules": [canonical]}}
    support = store.append(
        kind=EvidenceKind.RULE_SUPPORT,
        run_id=RUN,
        subject_id=RULE,
        content=canonical_json_bytes(
            {
                "schema_version": "1.0.0",
                "purpose": "knowledge_review_support",
                "archive_sha256": SOURCE,
                "source_id": "aws-3.19.1",
                "requirement_id": RULE,
                "requirement_sha256": RULE_SHA,
            }
        ),
    )
    annotated = {
        **canonical,
        "review_template": {
            **empty,
            "reviewer": "proposer-a",
            "reason": "Specific synthetic motivation; reviewer not yet independent.",
            "evidence_ids": [f"event:{support.digest}"],
            "desired_disposition": "KEEP_AS_CONTEXT",
            "proposed_tests": ["test code-based and contextual variants"],
            "source_rights_status": "NOT_APPLICABLE",
            "current_model_or_version_evidence": "Synthetic version snapshot",
        },
    }
    observed = {"batch-001.json": {"batch_id": "B-001", "rules": [annotated]}}
    proposal = store.append(
        kind=EvidenceKind.KNOWLEDGE_REVIEW_PROPOSAL,
        run_id=RUN,
        subject_id=RULE,
        content=private_dossier_proposal_payload(
            canonical_manifest=manifest,
            canonical_rule=canonical,
            observed_rule=annotated,
        ),
    )
    proposal_sig = _attest(
        store,
        key=proposer_key,
        actor="proposer-a",
        key_id="proposer-key",
        role=ReviewerRole.KNOWLEDGE_REVIEWER,
        target=proposal,
        policy=policy,
    )
    assessment = store.append(
        kind=EvidenceKind.SCIENTIFIC_RULE_ASSESSMENT,
        run_id=RUN,
        subject_id=RULE,
        content=scientific_assessment_payload(
            source_id="aws-3.19.1",
            archive_sha256=SOURCE,
            requirement_id=RULE,
            requirement_sha256=RULE_SHA,
            proposal_ref=f"event:{proposal.digest}",
            actor_id="scientist-b",
            verdict="INCONCLUSIVE",
            method_notes="Review limitations of a synthetic benchmark and the rule scope.",
            evidence_analysis="Inspect primary source links and potential contradicting cases.",
            limitations="No human scientific review was actually carried out.",
        ),
    )
    assessment_sig = _attest(
        store,
        key=scientist_key,
        actor="scientist-b",
        key_id="scientist-key",
        role=ReviewerRole.SCIENTIFIC_REVIEWER,
        target=assessment,
        policy=policy,
    )
    return {
        "store": store,
        "manifest": manifest,
        "original": original,
        "observed": observed,
        "policy": policy,
        "proposal_refs": {RULE: (f"event:{proposal.digest}", f"event:{proposal_sig.digest}")},
        "assessment_refs": {RULE: (f"event:{assessment.digest}", f"event:{assessment_sig.digest}")},
        "proposal": proposal,
        "proposer_key": proposer_key,
        "scientist_key": scientist_key,
        "assessment": assessment,
        "assessment_sig": assessment_sig,
    }


def check(s, *, head=None, policy=None, proposal_refs=None, assessment_refs=None, store=None):
    return verify_independent_scientific_assessments(
        canonical_manifest=s["manifest"],
        canonical_packets=s["original"],
        observed_manifest=s["manifest"],
        observed_packets=s["observed"],
        proposal_refs=s["proposal_refs"] if proposal_refs is None else proposal_refs,
        assessment_refs=s["assessment_refs"] if assessment_refs is None else assessment_refs,
        store=s["store"] if store is None else store,
        run_id=RUN,
        expected_head=s["assessment_sig"].digest if head is None else head,
        policy=s["policy"] if policy is None else policy,
        verifier=Ed25519ReviewerVerifier(),
        now=NOW,
    )


def test_two_distinct_signed_reviews_are_not_scientific_adjudication(tmp_path: Path):
    s = scenario(tmp_path)
    reloaded = SQLiteEvidenceLedger(s["store"].database)
    result = check(s, store=reloaded)
    assert result.checked == result.verified == 1
    assert result.all_credentials_verified
    assert result.independent_adjudication_proven is False
    assert result.training_authorized is False
    assert result.review_attestation_authorized is False
    assert result.to_dict()["contains_private_source_text"] is False


@pytest.mark.parametrize(
    "problem",
    ["missing", "extra", "bad_kind", "swapped", "unsupported_ref"],
)
def test_wrong_assessment_inventory_fails_closed(tmp_path: Path, problem: str):
    s = scenario(tmp_path)
    pair = s["assessment_refs"][RULE]
    changes = {
        "missing": {},
        "extra": {**s["assessment_refs"], "DSR-002": pair},
        "bad_kind": {RULE: (s["proposal_refs"][RULE][0], pair[1])},
        "swapped": {RULE: (pair[1], pair[0])},
        "unsupported_ref": {RULE: ("event:" + "f" * 64, pair[1])},
    }
    result = check(s, assessment_refs=changes[problem])
    assert not result.all_credentials_verified


def test_reviewer_role_revocation_and_mismatch_fail_closed(tmp_path: Path):
    s = scenario(tmp_path)
    wrong_role = _make_policy(s["proposer_key"], s["scientist_key"], scientist_role="CRITIC")
    revoked = _make_policy(s["proposer_key"], s["scientist_key"], revoked=True)
    assert not check(s, policy=wrong_role).all_credentials_verified
    assert not check(s, policy=revoked).all_credentials_verified


def test_compromised_proposer_credential_blocks_scientific_gate(tmp_path: Path):
    s = scenario(tmp_path)
    bad = {RULE: (s["proposal_refs"][RULE][1], s["proposal_refs"][RULE][0])}
    result = check(s, proposal_refs=bad)
    assert not result.all_credentials_verified
    assert result.verified == 0


def test_old_head_rejected_even_if_events_still_exist(tmp_path: Path):
    s = scenario(tmp_path)
    s["store"].append(
        kind=EvidenceKind.RULE_SUPPORT,
        run_id=RUN,
        subject_id=RULE,
        content=b"subsequent unrelated append",
    )
    with pytest.raises(EvidenceIntegrityError, match="head"):
        check(s)


def test_canonical_inventory_rejects_duplicate_keys_and_wrong_refs():
    valid = canonical_json_bytes(
        {
            "schema": 1,
            "assessments": {
                RULE: {
                    "assessment_ref": "event:" + "a" * 64,
                    "attestation_ref": "event:" + "b" * 64,
                }
            },
        }
    )
    assert parse_scientific_assessment_inventory(valid)[RULE] == (
        "event:" + "a" * 64,
        "event:" + "b" * 64,
    )
    for invalid in (
        b'{"schema":1,"schema":1,"assessments":{}}\n',
        valid.replace(b'"schema":1', b'"schema":2'),
        valid.replace(b"event:" + b"a" * 64, b"sha256:" + b"a" * 64),
    ):
        with pytest.raises(EvidenceIntegrityError):
            parse_scientific_assessment_inventory(invalid)


def test_assessment_payload_requires_substantive_fields():
    fields = {
        "source_id": "aws-3.19.1",
        "archive_sha256": SOURCE,
        "requirement_id": RULE,
        "requirement_sha256": RULE_SHA,
        "proposal_ref": "event:" + "d" * 64,
        "actor_id": "science-b",
        "verdict": "SUPPORT",
        "method_notes": "Methods, independent research and provenance were reviewed.",
        "evidence_analysis": "Research question and negative evidence inspected in tests.",
        "limitations": "This does not prove truth or independence.",
    }
    assert json.loads(scientific_assessment_payload(**fields))["verdict"] == "SUPPORT"
    for bad in (
        {"verdict": "ACCEPTED"},
        {"method_notes": "short"},
        {"proposal_ref": "sha256:" + "d" * 64},
        {"archive_sha256": "unknown"},
    ):
        with pytest.raises(EvidenceIntegrityError):
            scientific_assessment_payload(**(fields | bad))
