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
from awf.application.commands.scientific_arbitration import (
    arbitration_payload,
    verify_scientific_arbitration,
)
from awf.application.commands.scientific_assessments import (
    parse_scientific_assessment_inventory,
    scientific_assessment_payload,
    verify_independent_scientific_assessments,
)
from awf.application.commands.scientific_disagreements import (
    disagreement_case_payload,
    verify_disagreement_protocol,
)
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import (
    ReviewerClaim,
    ReviewerGrant,
    ReviewerRole,
    ReviewerTrustPolicy,
    SignedReviewerClaim,
    parse_trust_policy,
)
from awf.domain.scientific_arbitration import ArbitrationPosition
from awf.domain.scientific_disagreements import ComparisonStatus, ProposedNextAction
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


def scenario(tmp_path: Path, *, verdict: str = "INCONCLUSIVE"):
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
            verdict=verdict,
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


def _second_scientist(s, *, verdict: str = "CONTEST", same_actor: bool = False, revoked=False):
    """Synthetic independent signer and source-bound second assessment."""
    second_key = s["scientist_key"] if same_actor else Ed25519PrivateKey.generate()
    actor = "scientist-b" if same_actor else "scientist-c"
    key_id = "scientist-key" if same_actor else "scientist-c-key"
    grants = list(s["policy"].grants)
    if not same_actor:
        grant = ReviewerGrant(
            actor_id=actor,
            key_id=key_id,
            public_key_hex=_public(second_key),
            roles=frozenset({ReviewerRole.SCIENTIFIC_REVIEWER}),
            runs=frozenset({RUN}),
            subjects=frozenset({RULE}),
            valid_from=NOW - 100,
            valid_until=NOW + 100,
            revoked=revoked,
        )
        grants.append(grant)
    raw_policy = canonical_json_bytes(
        {
            "schema": 1,
            "grants": [
                {
                    "actor_id": g.actor_id,
                    "key_id": g.key_id,
                    "public_key_hex": g.public_key_hex,
                    "roles": sorted(role.value for role in g.roles),
                    "runs": sorted(g.runs),
                    "subjects": sorted(g.subjects),
                    "valid_from": g.valid_from,
                    "valid_until": g.valid_until,
                    "revoked": g.revoked,
                }
                for g in grants
            ],
        }
    )
    policy = parse_trust_policy(raw_policy, expected_sha256=sha256_bytes(raw_policy))
    proposal_ref, _ = s["proposal_refs"][RULE]
    event = s["store"].append(
        kind=EvidenceKind.SCIENTIFIC_RULE_ASSESSMENT,
        run_id=RUN,
        subject_id=RULE,
        content=scientific_assessment_payload(
            source_id="aws-3.19.1",
            archive_sha256=SOURCE,
            requirement_id=RULE,
            requirement_sha256=RULE_SHA,
            proposal_ref=proposal_ref,
            actor_id=actor,
            verdict=verdict,
            method_notes="An independent synthetic assessment compared repeatability.",
            evidence_analysis="A second evaluator inspected method and negative cases.",
            limitations="This is simulated and not independent real-world research.",
        ),
    )
    signature = _attest(
        s["store"],
        key=second_key,
        actor=actor,
        key_id=key_id,
        role=ReviewerRole.SCIENTIFIC_REVIEWER,
        target=event,
        policy=policy,
    )
    return (f"event:{event.digest}", f"event:{signature.digest}"), policy, signature.digest


def _dispute_case(s, second):
    return disagreement_case_payload(
        source_id="aws-3.19.1",
        archive_sha256=SOURCE,
        requirement_id=RULE,
        requirement_sha256=RULE_SHA,
        proposal_ref=s["proposal_refs"][RULE][0],
        left_assessment_ref=s["assessment_refs"][RULE][0],
        right_assessment_ref=second[0],
        claim_in_dispute="The reported outcome cannot be inferred from the source data.",
        evidence_gaps="Reproduce with primary data and a preregistered negative control.",
        methodological_divergence="Reviewers assign different evidentiary weight to controls.",
        proposed_next_action=ProposedNextAction.REPLICATE_EXPERIMENT,
    )


def _dispute_check(s, second, policy, head, *, cases=None, case_pins=None, expected_head=None):
    return verify_disagreement_protocol(
        canonical_manifest=s["manifest"],
        canonical_packets=s["original"],
        observed_manifest=s["manifest"],
        observed_packets=s["observed"],
        proposal_refs=s["proposal_refs"],
        left_assessments=s["assessment_refs"],
        right_assessments={RULE: second},
        case_bytes={} if cases is None else cases,
        expected_case_sha256={} if case_pins is None else case_pins,
        store=s["store"],
        run_id=RUN,
        expected_head=head if expected_head is None else expected_head,
        policy=policy,
        verifier=Ed25519ReviewerVerifier(),
        now=NOW,
    )


def test_signed_disagreement_generates_only_a_non_adjudicating_case(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, head = _second_scientist(s, verdict="CONTEST")
    case = _dispute_case(s, second)
    result = _dispute_check(
        s,
        second,
        policy,
        head,
        cases={RULE: case},
        case_pins={RULE: sha256_bytes(case)},
    )
    assert result.checked == 1
    assert result.comparisons == ((RULE, ComparisonStatus.DIVERGENT),)
    assert result.case_rule_ids == (RULE,)
    assert result.missing_case_rule_ids == ()
    assert result.evidence_links_verified
    report = result.to_dict()
    assert report["scientific_adjudications"] == 0
    assert report["training_authorized"] is False
    assert report["source_rights_verified"] is False
    assert "negative control" not in str(report)


def test_missing_disagreement_case_keeps_protocol_open(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, head = _second_scientist(s, verdict="CONTEST")
    result = _dispute_check(s, second, policy, head)
    assert not result.evidence_links_verified
    assert result.missing_case_rule_ids == (RULE,)
    assert result.scientific_adjudications == 0


def test_agreeing_reviewers_still_do_not_adjudicate(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, head = _second_scientist(s, verdict="SUPPORT")
    result = _dispute_check(s, second, policy, head)
    assert result.comparisons == ((RULE, ComparisonStatus.CONCORDANT_SUPPORT),)
    assert result.evidence_links_verified
    assert result.scientific_adjudications == 0


def test_inconclusive_review_is_not_counted_as_agreement(tmp_path: Path):
    s = scenario(tmp_path)
    second, policy, head = _second_scientist(s, verdict="SUPPORT")
    result = _dispute_check(s, second, policy, head)
    assert result.comparisons == ((RULE, ComparisonStatus.INCONCLUSIVE),)
    assert result.missing_case_rule_ids == (RULE,)


def test_same_signed_actor_cannot_review_twice(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, head = _second_scientist(s, same_actor=True)
    with pytest.raises(EvidenceIntegrityError, match="self-comparison"):
        _dispute_check(s, second, policy, head)


def test_revoked_second_scientist_rejected(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    # Sign while authorized; revoke only at verification.
    second, policy, head = _second_scientist(s)
    revoked = ReviewerTrustPolicy(
        grants=tuple(
            ReviewerGrant(
                actor_id=g.actor_id,
                key_id=g.key_id,
                public_key_hex=g.public_key_hex,
                roles=g.roles,
                runs=g.runs,
                subjects=g.subjects,
                valid_from=g.valid_from,
                valid_until=g.valid_until,
                revoked=True if g.actor_id == "scientist-c" else g.revoked,
            )
            for g in policy.grants
        ),
        policy_sha256=policy.policy_sha256,
    )
    with pytest.raises(EvidenceIntegrityError, match="prerequisite"):
        _dispute_check(s, second, revoked, head)


def test_disagreement_case_swapping_or_tampering_is_rejected(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, head = _second_scientist(s)
    case = _dispute_case(s, second)
    with pytest.raises(EvidenceIntegrityError, match="external SHA"):
        _dispute_check(
            s,
            second,
            policy,
            head,
            cases={RULE: case + b"tampered"},
            case_pins={RULE: sha256_bytes(case)},
        )
    changed = case.replace(second[0].encode(), ("event:" + "f" * 64).encode())
    with pytest.raises(EvidenceIntegrityError, match="source/events"):
        _dispute_check(
            s,
            second,
            policy,
            head,
            cases={RULE: changed},
            case_pins={RULE: sha256_bytes(changed)},
        )


def test_stale_ledger_head_blocks_comparison(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, head = _second_scientist(s)
    s["store"].append(
        kind=EvidenceKind.RULE_SUPPORT,
        run_id=RUN,
        subject_id=RULE,
        content=b"later evidence invalidates pinned head",
    )
    with pytest.raises(EvidenceIntegrityError, match="head"):
        _dispute_check(s, second, policy, head)


def test_unapproved_extra_case_is_rejected(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, head = _second_scientist(s, verdict="SUPPORT")
    case = _dispute_case(s, second)
    with pytest.raises(EvidenceIntegrityError, match="extra"):
        _dispute_check(
            s,
            second,
            policy,
            head,
            cases={RULE: case},
            case_pins={RULE: sha256_bytes(case)},
        )


QUAL_POLICY = "e" * 64
QUAL_DOCUMENT = b"independent synthetic documented academic qualification and COI review"


def _arbitrator_policy(existing: ReviewerTrustPolicy, key, actor: str):
    grants = list(existing.grants)
    grants.append(
        ReviewerGrant(
            actor_id=actor,
            key_id=actor + "-key",
            public_key_hex=_public(key),
            roles=frozenset({ReviewerRole.SCIENTIFIC_ARBITER}),
            runs=frozenset({RUN}),
            subjects=frozenset({RULE}),
            valid_from=NOW - 100,
            valid_until=NOW + 100,
            revoked=False,
        )
    )
    policy_bytes = canonical_json_bytes(
        {
            "schema": 1,
            "grants": [
                {
                    "actor_id": g.actor_id,
                    "key_id": g.key_id,
                    "public_key_hex": g.public_key_hex,
                    "roles": sorted(role.value for role in g.roles),
                    "runs": sorted(g.runs),
                    "subjects": sorted(g.subjects),
                    "valid_from": g.valid_from,
                    "valid_until": g.valid_until,
                    "revoked": g.revoked,
                }
                for g in grants
            ],
        }
    )
    return parse_trust_policy(policy_bytes, expected_sha256=sha256_bytes(policy_bytes))


class SyntheticQualificationAuthority:
    """Fake authority exists only in tests, not as a production verifier."""

    def verify(
        self,
        *,
        actor_id,
        excluded_actor_ids,
        requirement_id,
        case_sha256,
        qualification_evidence,
        policy_sha256,
        at_time,
    ) -> None:
        if (
            actor_id not in {"arbiter-d", "arbiter-e"}
            or actor_id in excluded_actor_ids
            or "proposer-a" not in excluded_actor_ids
            or "scientist-b" not in excluded_actor_ids
            or "scientist-c" not in excluded_actor_ids
            or requirement_id != RULE
            or not isinstance(case_sha256, str)
            or qualification_evidence != QUAL_DOCUMENT
            or policy_sha256 != QUAL_POLICY
            or at_time != NOW
        ):
            raise EvidenceIntegrityError("synthetic qualification authority rejects actor")


def _arbitration_scenario(tmp_path: Path):
    s = scenario(tmp_path, verdict="SUPPORT")
    second, policy, _ = _second_scientist(s, verdict="CONTEST")
    case = _dispute_case(s, second)
    key = Ed25519PrivateKey.generate()
    policy = _arbitrator_policy(policy, key, "arbiter-d")
    evidence_ref = s["observed"]["batch-001.json"]["rules"][0]["review_template"]["evidence_ids"][0]
    record = s["store"].append(
        kind=EvidenceKind.SCIENTIFIC_ARBITRATION,
        run_id=RUN,
        subject_id=RULE,
        content=arbitration_payload(
            source_id="aws-3.19.1",
            archive_sha256=SOURCE,
            requirement_id=RULE,
            requirement_sha256=RULE_SHA,
            proposal_ref=s["proposal_refs"][RULE][0],
            left_assessment_ref=s["assessment_refs"][RULE][0],
            right_assessment_ref=second[0],
            case_sha256=sha256_bytes(case),
            arbitrator_actor_id="arbiter-d",
            position=ArbitrationPosition.DEFER,
            reasoned_findings="Insufficient methodological evidence is available to settle the claim.",
            limitations="This is an explicitly synthetic, unqualified scientific assessment.",
            evidence_refs=(evidence_ref,),
        ),
    )
    signed = _attest(
        s["store"],
        key=key,
        actor="arbiter-d",
        key_id="arbiter-d-key",
        role=ReviewerRole.SCIENTIFIC_ARBITER,
        target=record,
        policy=policy,
    )
    return s, second, policy, case, (f"event:{record.digest}", f"event:{signed.digest}")


def _arbitration_check(
    s,
    second,
    policy,
    case,
    pairs,
    *,
    qualifier=None,
    qualification=None,
    pins=None,
    policy_digest=QUAL_POLICY,
    head=None,
    cases=None,
):
    return verify_scientific_arbitration(
        canonical_manifest=s["manifest"],
        canonical_packets=s["original"],
        observed_manifest=s["manifest"],
        observed_packets=s["observed"],
        proposal_refs=s["proposal_refs"],
        left_assessments=s["assessment_refs"],
        right_assessments={RULE: second},
        case_bytes={RULE: case} if cases is None else cases,
        expected_case_sha256={RULE: sha256_bytes(case)},
        rule_id=RULE,
        arbitration_refs=pairs,
        qualification_bytes={} if qualification is None else qualification,
        expected_qualification_sha256={} if pins is None else pins,
        qualification_policy_sha256=policy_digest,
        qualification_verifier=qualifier,
        store=s["store"],
        run_id=RUN,
        expected_head=s["store"].verify().head_digest if head is None else head,
        policy=policy,
        verifier=Ed25519ReviewerVerifier(),
        now=NOW,
    )


def test_arbitration_signed_is_not_automatically_adjudicated(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    result = _arbitration_check(s, second, policy, case, (first,))
    assert result.authenticated_decisions == 1
    assert result.latest_position == ArbitrationPosition.DEFER
    assert result.appeal_count == 0
    assert not result.independently_qualified
    assert not result.procedure_verified
    assert result.scientific_adjudications == 0
    assert result.to_dict()["training_authorized"] is False


def test_synthetic_independent_qualification_allows_procedural_gate_only(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    result = _arbitration_check(
        s,
        second,
        policy,
        case,
        (first,),
        qualifier=SyntheticQualificationAuthority(),
        qualification={"arbiter-d": QUAL_DOCUMENT},
        pins={"arbiter-d": sha256_bytes(QUAL_DOCUMENT)},
    )
    assert result.independently_qualified
    assert result.procedure_verified
    assert result.scientific_adjudications == 0
    assert result.to_dict()["historical_rule_disposition_changed"] is False


def test_fake_qualification_policy_mismatch_cannot_pass(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    with pytest.raises(EvidenceIntegrityError, match="synthetic qualification authority"):
        _arbitration_check(
            s,
            second,
            policy,
            case,
            (first,),
            qualifier=SyntheticQualificationAuthority(),
            qualification={"arbiter-d": QUAL_DOCUMENT},
            pins={"arbiter-d": sha256_bytes(QUAL_DOCUMENT)},
            policy_digest="f" * 64,
        )


def test_arbitration_by_prior_scientist_fails_even_with_valid_signature(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    # Permit a previous scientist's credential to sign as an arbiter; this must still fail.
    scientist = s["scientist_key"]
    promoted_grants = tuple(
        ReviewerGrant(
            actor_id=g.actor_id,
            key_id=g.key_id,
            public_key_hex=g.public_key_hex,
            roles=frozenset({*g.roles, ReviewerRole.SCIENTIFIC_ARBITER})
            if g.actor_id == "scientist-b"
            else g.roles,
            runs=g.runs,
            subjects=g.subjects,
            valid_from=g.valid_from,
            valid_until=g.valid_until,
            revoked=g.revoked,
        )
        for g in policy.grants
    )
    privileged = ReviewerTrustPolicy(grants=promoted_grants, policy_sha256=policy.policy_sha256)
    rec = s["store"].append(
        kind=EvidenceKind.SCIENTIFIC_ARBITRATION,
        run_id=RUN,
        subject_id=RULE,
        content=arbitration_payload(
            source_id="aws-3.19.1",
            archive_sha256=SOURCE,
            requirement_id=RULE,
            requirement_sha256=RULE_SHA,
            proposal_ref=s["proposal_refs"][RULE][0],
            left_assessment_ref=s["assessment_refs"][RULE][0],
            right_assessment_ref=second[0],
            case_sha256=sha256_bytes(case),
            arbitrator_actor_id="scientist-b",
            position=ArbitrationPosition.SUPPORT,
            reasoned_findings="A previous reviewer tries to arbitrate their own source judgement.",
            limitations="This is an adversarial case testing same-person role escalation.",
            evidence_refs=(
                s["observed"]["batch-001.json"]["rules"][0]["review_template"]["evidence_ids"][0],
            ),
        ),
    )
    sig = _attest(
        s["store"],
        key=scientist,
        actor="scientist-b",
        key_id="scientist-key",
        role=ReviewerRole.SCIENTIFIC_ARBITER,
        target=rec,
        policy=privileged,
    )
    with pytest.raises(EvidenceIntegrityError, match="independence"):
        _arbitration_check(
            s, second, privileged, case, ((f"event:{rec.digest}", f"event:{sig.digest}"),)
        )


def test_arbitration_reconsideration_preserves_predecessor(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    support = s["store"].append(
        kind=EvidenceKind.RULE_SUPPORT,
        run_id=RUN,
        subject_id=RULE,
        content=b"synthetic additional verifiable methodological evidence",
    )
    key = Ed25519PrivateKey.generate()
    policy = _arbitrator_policy(policy, key, "arbiter-e")
    second_record = s["store"].append(
        kind=EvidenceKind.SCIENTIFIC_ARBITRATION,
        run_id=RUN,
        subject_id=RULE,
        content=arbitration_payload(
            source_id="aws-3.19.1",
            archive_sha256=SOURCE,
            requirement_id=RULE,
            requirement_sha256=RULE_SHA,
            proposal_ref=s["proposal_refs"][RULE][0],
            left_assessment_ref=s["assessment_refs"][RULE][0],
            right_assessment_ref=second[0],
            case_sha256=sha256_bytes(case),
            arbitrator_actor_id="arbiter-e",
            position=ArbitrationPosition.UNRESOLVED,
            reasoned_findings="Newly supplied methodological evidence still fails to demonstrate validity.",
            limitations="This appeal has simulated evidence but no actual panel review.",
            evidence_refs=(f"event:{support.digest}",),
            supersedes_ref=first[0],
            reconsideration_basis="A recorded new methodological observation challenges the old finding.",
        ),
    )
    sig = _attest(
        s["store"],
        key=key,
        actor="arbiter-e",
        key_id="arbiter-e-key",
        role=ReviewerRole.SCIENTIFIC_ARBITER,
        target=second_record,
        policy=policy,
    )
    pairs = (first, (f"event:{second_record.digest}", f"event:{sig.digest}"))
    result = _arbitration_check(s, second, policy, case, pairs)
    assert result.authenticated_decisions == 2
    assert result.appeal_count == 1
    assert result.latest_position == ArbitrationPosition.UNRESOLVED
    assert not result.procedure_verified


def test_replay_or_wrong_predecessor_is_rejected(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    with pytest.raises(EvidenceIntegrityError, match="order/scope"):
        _arbitration_check(s, second, policy, case, (first, first))
    with pytest.raises(EvidenceIntegrityError, match="order/scope"):
        _arbitration_check(
            s,
            second,
            policy,
            case,
            ((first[1], first[0]),),
        )


def test_missing_case_is_rejected_by_upstream_scientific_inventory(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    with pytest.raises(
        EvidenceIntegrityError, match="incomplete or mismatched scientific inventory"
    ):
        _arbitration_check(s, second, policy, case, (first,), cases={})


def test_qualification_evidence_without_pinned_authority_cannot_authorize(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    assert not _arbitration_check(
        s,
        second,
        policy,
        case,
        (first,),
        qualification={"arbiter-d": QUAL_DOCUMENT},
        pins={"arbiter-d": sha256_bytes(QUAL_DOCUMENT)},
    ).procedure_verified
    with pytest.raises(EvidenceIntegrityError, match="external arbitrator qualifications"):
        _arbitration_check(
            s,
            second,
            policy,
            case,
            (first,),
            qualifier=SyntheticQualificationAuthority(),
            qualification={"arbiter-d": QUAL_DOCUMENT + b"altered"},
            pins={"arbiter-d": sha256_bytes(QUAL_DOCUMENT)},
        )


def test_revoked_arbiter_credential_is_rejected(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    revoked = ReviewerTrustPolicy(
        grants=tuple(
            ReviewerGrant(
                actor_id=g.actor_id,
                key_id=g.key_id,
                public_key_hex=g.public_key_hex,
                roles=g.roles,
                runs=g.runs,
                subjects=g.subjects,
                valid_from=g.valid_from,
                valid_until=g.valid_until,
                revoked=True if g.actor_id == "arbiter-d" else g.revoked,
            )
            for g in policy.grants
        ),
        policy_sha256=policy.policy_sha256,
    )
    with pytest.raises(EvidenceIntegrityError, match="not authorized"):
        _arbitration_check(s, second, revoked, case, (first,))


def test_reconsideration_must_cite_new_evidence(tmp_path: Path):
    s, second, policy, case, first = _arbitration_scenario(tmp_path)
    key = Ed25519PrivateKey.generate()
    policy = _arbitrator_policy(policy, key, "arbiter-e")
    old_ref = s["observed"]["batch-001.json"]["rules"][0]["review_template"]["evidence_ids"][0]
    record = s["store"].append(
        kind=EvidenceKind.SCIENTIFIC_ARBITRATION,
        run_id=RUN,
        subject_id=RULE,
        content=arbitration_payload(
            source_id="aws-3.19.1",
            archive_sha256=SOURCE,
            requirement_id=RULE,
            requirement_sha256=RULE_SHA,
            proposal_ref=s["proposal_refs"][RULE][0],
            left_assessment_ref=s["assessment_refs"][RULE][0],
            right_assessment_ref=second[0],
            case_sha256=sha256_bytes(case),
            arbitrator_actor_id="arbiter-e",
            position=ArbitrationPosition.UNRESOLVED,
            reasoned_findings="No new primary source supports a change to the original finding.",
            limitations="This second review is only an adversarial synthetic test.",
            evidence_refs=(old_ref,),
            supersedes_ref=first[0],
            reconsideration_basis="The appellant challenges the reasoning but supplies no new evidence.",
        ),
    )
    sig = _attest(
        s["store"],
        key=key,
        actor="arbiter-e",
        key_id="arbiter-e-key",
        role=ReviewerRole.SCIENTIFIC_ARBITER,
        target=record,
        policy=policy,
    )
    with pytest.raises(EvidenceIntegrityError, match="newly recorded"):
        _arbitration_check(
            s,
            second,
            policy,
            case,
            (first, (f"event:{record.digest}", f"event:{sig.digest}")),
        )
