"""Adversarial Ed25519 authorization of historical-rule proposal snapshots.

All rule text and keys are synthetic. Authorization is not adjudication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.security.ed25519_reviewer import Ed25519ReviewerVerifier
from awf.application.commands.authorize_dossiers import (
    parse_dossier_attestation_inventory,
    private_dossier_proposal_payload,
    verify_authorized_dossier_proposals,
)
from awf.application.commands.authorize_review import append_signed_review_claim
from awf.cli.main import main
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import (
    ReviewerClaim,
    ReviewerRole,
    SignedReviewerClaim,
    parse_trust_policy,
)
from awf.domain.signed_documents import canonical_json_bytes

RUN = "research-run-a"
RULE = "DSR-001"
ARCHIVE = "a" * 64
REQUIREMENT = "b" * 64
_NOW = 1_800_000_000


def _policy(key, *, roles=None, revoked=False, subjects=None, until=None):
    pub = (
        key.public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        .hex()
    )
    raw = canonical_json_bytes(
        {
            "schema": 1,
            "grants": [
                {
                    "actor_id": "reviewer-a",
                    "key_id": "key-a",
                    "public_key_hex": pub,
                    "roles": roles or ["KNOWLEDGE_REVIEWER"],
                    "runs": [RUN],
                    "subjects": subjects or [RULE],
                    "valid_from": _NOW - 100,
                    "valid_until": until or _NOW + 100,
                    "revoked": revoked,
                }
            ],
        }
    )
    return parse_trust_policy(raw, expected_sha256=sha256_bytes(raw)), raw


def _signed(key, ref, *, actor="reviewer-a", role=ReviewerRole.KNOWLEDGE_REVIEWER):
    claim = ReviewerClaim(
        actor_id=actor,
        key_id="key-a",
        role=role,
        run_id=RUN,
        subject_id=RULE,
        target_event_ref=ref,
        issued_at=_NOW - 10,
    )
    return SignedReviewerClaim(claim, key.sign(claim.signing_bytes).hex())


def _scenario(tmp_path):
    store = SQLiteEvidenceLedger(tmp_path / "ledger.sqlite")
    store.initialize()
    manifest = {"archive_sha256": ARCHIVE, "source_id": "aws-3.19.1"}
    template = {
        "reviewer": None,
        "reason": None,
        "evidence_ids": [],
        "conflicting_rule_ids": [],
        "desired_disposition": None,
        "proposed_tests": [],
        "source_rights_status": "NOT_EVALUATED",
        "current_model_or_version_evidence": None,
    }
    canonical_rule = {
        "id": RULE,
        "priority": "MUST",
        "requirement_sha256": REQUIREMENT,
        "review_template": template,
    }
    original = {"batch-001.json": {"batch_id": "AWF-REVIEW-001", "rules": [canonical_rule]}}
    support_bytes = canonical_json_bytes(
        {
            "schema_version": "1.0.0",
            "purpose": "knowledge_review_support",
            "archive_sha256": ARCHIVE,
            "source_id": "aws-3.19.1",
            "requirement_id": RULE,
            "requirement_sha256": REQUIREMENT,
        }
    )
    support = store.append(
        kind=EvidenceKind.RULE_SUPPORT, run_id=RUN, subject_id=RULE, content=support_bytes
    )
    review_template = {
        **template,
        "reviewer": "reviewer-a",
        "reason": "A detailed reason for considering this synthetic requirement.",
        "evidence_ids": [f"event:{support.digest}"],
        "desired_disposition": "KEEP_AS_CONTEXT",
        "proposed_tests": ["controlled falsification test"],
        "source_rights_status": "NOT_APPLICABLE",
        "current_model_or_version_evidence": "synthetic scoped version evidence",
    }
    reviewed = {**canonical_rule, "review_template": review_template}
    observed = {"batch-001.json": {"batch_id": "AWF-REVIEW-001", "rules": [reviewed]}}
    claim_bytes = private_dossier_proposal_payload(
        canonical_manifest=manifest, canonical_rule=canonical_rule, observed_rule=reviewed
    )
    proposal = store.append(
        kind=EvidenceKind.KNOWLEDGE_REVIEW_PROPOSAL,
        run_id=RUN,
        subject_id=RULE,
        content=claim_bytes,
    )
    key = Ed25519PrivateKey.generate()
    policy, policy_raw = _policy(key)
    attested = append_signed_review_claim(
        store=store,
        signed=_signed(key, f"event:{proposal.digest}"),
        policy=policy,
        verifier=Ed25519ReviewerVerifier(),
        now=_NOW,
    )
    inventory = {RULE: (f"event:{proposal.digest}", f"event:{attested.digest}")}
    return {
        "store": store,
        "manifest": manifest,
        "original": original,
        "observed": observed,
        "policy": policy,
        "policy_raw": policy_raw,
        "inventory": inventory,
        "key": key,
        "proposal": proposal,
        "attested": attested,
        "support": support,
    }


def _gate(
    s, *, inventory=None, policy=None, observed=None, head=None, now=_NOW, run=RUN, store=None
):
    actual_store = store or s["store"]
    return verify_authorized_dossier_proposals(
        canonical_manifest=s["manifest"],
        canonical_packets=s["original"],
        observed_manifest=s["manifest"],
        observed_packets=observed if observed is not None else s["observed"],
        store=actual_store,
        run_id=run,
        expected_head=head if head is not None else s["store"].verify().head_digest,
        attestation_refs=inventory if inventory is not None else s["inventory"],
        policy=policy if policy is not None else s["policy"],
        verifier=Ed25519ReviewerVerifier(),
        now=now,
    )


def test_signed_exact_snapshot_reopens_without_adjudication(tmp_path: Path) -> None:
    s = _scenario(tmp_path)
    reopened = SQLiteEvidenceLedger(s["store"].database)
    outcome = _gate(s, store=reopened)
    assert outcome.checked == 1
    assert outcome.authorization_verified
    assert outcome.unverified == ()
    assert not outcome.independent_adjudication_proven


@pytest.mark.parametrize(
    "kind", ["missing", "extra", "wrong_proposal", "wrong_attestation", "swapped"]
)
def test_inventory_is_exact_and_signed_to_proposal(tmp_path: Path, kind: str) -> None:
    s = _scenario(tmp_path)
    base = s["inventory"][RULE]
    inventory = {
        "missing": {},
        "extra": {**s["inventory"], "DSR-002": base},
        "wrong_proposal": {RULE: (f"event:{s['support'].digest}", base[1])},
        "wrong_attestation": {RULE: (base[0], f"event:{s['support'].digest}")},
        "swapped": {RULE: (base[1], base[0])},
    }[kind]
    outcome = _gate(s, inventory=inventory)
    assert not outcome.authorization_verified


@pytest.mark.parametrize(
    "change",
    ["reason", "rights", "reviewer", "evidence_ids", "disposition", "proposed_tests", "version"],
)
def test_any_mutation_of_review_template_breaks_old_signature(tmp_path: Path, change: str) -> None:
    s = _scenario(tmp_path)
    packet = s["observed"]["batch-001.json"]
    review = dict(packet["rules"][0]["review_template"])
    updates = {
        "reason": (
            "reason",
            "Different detailed scientific analysis of this synthetic requirement.",
        ),
        "rights": ("source_rights_status", "RESTRICTED"),
        "reviewer": ("reviewer", "reviewer-b"),
        "evidence_ids": ("evidence_ids", [f"event:{s['proposal'].digest}"]),
        "disposition": ("desired_disposition", "EVAL_ONLY"),
        "proposed_tests": ("proposed_tests", ["a different test"]),
        "version": ("current_model_or_version_evidence", "changed version evidence"),
    }
    k, value = updates[change]
    review[k] = value
    observed = {
        "batch-001.json": {
            **packet,
            "rules": [{**packet["rules"][0], "review_template": review}],
        }
    }
    outcome = _gate(s, observed=observed)
    assert not outcome.authorization_verified


@pytest.mark.parametrize(
    "role", [ReviewerRole.CRITIC, ReviewerRole.APPLICABILITY_REVIEWER, ReviewerRole.AUDITOR]
)
def test_other_roles_cannot_sign_a_knowledge_proposal(tmp_path: Path, role: ReviewerRole) -> None:
    s = _scenario(tmp_path)
    with pytest.raises(EvidenceIntegrityError):
        append_signed_review_claim(
            store=s["store"],
            signed=_signed(s["key"], f"event:{s['proposal'].digest}", role=role),
            policy=s["policy"],
            verifier=Ed25519ReviewerVerifier(),
            now=_NOW,
        )


@pytest.mark.parametrize("change", ["revoked", "expired", "different_role", "different_subject"])
def test_authorization_scope_is_rechecked_on_each_read(tmp_path: Path, change: str) -> None:
    s = _scenario(tmp_path)
    settings = {
        "revoked": {"revoked": True},
        "expired": {"until": _NOW - 1},
        "different_role": {"roles": ["CRITIC"]},
        "different_subject": {"subjects": ["DSR-002"]},
    }[change]
    policy, _ = _policy(s["key"], **settings)
    assert not _gate(s, policy=policy).authorization_verified


def test_modified_policy_file_fails_independent_digest_pin(tmp_path: Path) -> None:
    s = _scenario(tmp_path)
    with pytest.raises(EvidenceIntegrityError, match="policy changed"):
        parse_trust_policy(s["policy_raw"], expected_sha256="0" * 64)


def test_wrong_run_and_stale_externally_pinned_head_fail_closed(tmp_path: Path) -> None:
    s = _scenario(tmp_path)
    assert not _gate(s, run="wrong-run").authorization_verified
    old_head = s["store"].verify().head_digest
    s["store"].append(
        kind=EvidenceKind.RULE_SUPPORT, run_id=RUN, subject_id=RULE, content=b"later evidence"
    )
    with pytest.raises(EvidenceIntegrityError, match="head"):
        _gate(s, head=old_head)


def test_unrelated_legacy_unsigned_dossiers_cannot_vacuously_pass(tmp_path: Path) -> None:
    s = _scenario(tmp_path)
    packet = s["observed"]["batch-001.json"]
    observed = {
        "batch-001.json": {**packet, "rules": [s["original"]["batch-001.json"]["rules"][0]]}
    }
    assert not _gate(s, observed=observed, inventory={}).authorization_verified


def test_only_one_complete_ledger_audit_for_signed_dossier(tmp_path: Path, monkeypatch) -> None:
    s = _scenario(tmp_path)
    counts = {"number": 0}
    original = SQLiteEvidenceLedger._audit_transaction.__func__

    def counted(cls, connection):
        counts["number"] += 1
        return original(cls, connection)

    monkeypatch.setattr(SQLiteEvidenceLedger, "_audit_transaction", classmethod(counted))
    # Use a trusted, previously captured head; no extra verify() here.
    expected = s["attested"].digest
    outcome = _gate(s, head=expected)
    assert outcome.authorization_verified
    assert counts["number"] == 1


def test_canonical_private_inventory_rejects_extra_duplicate_and_malformed(tmp_path: Path) -> None:
    s = _scenario(tmp_path)
    pair = s["inventory"][RULE]
    valid = canonical_json_bytes(
        {"schema": 1, "attestations": {RULE: {"proposal_ref": pair[0], "attestation_ref": pair[1]}}}
    )
    assert parse_dossier_attestation_inventory(valid) == s["inventory"]
    for invalid in (
        valid.replace(b'"schema":1', b'"schema":2'),
        valid[:-1] + b" ",
        b'{"schema":1,"schema":1,"attestations":{}}\n',
        b'{"schema":1,"attestations":{"DSR-001":{"proposal_ref":"not-event","attestation_ref":"event:'
        + b"a" * 64
        + b'"}}}\n',
    ):
        with pytest.raises(EvidenceIntegrityError):
            parse_dossier_attestation_inventory(invalid)

def test_private_cli_requires_signed_credentials_without_public_prose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    s = _scenario(tmp_path)
    manifest_path = tmp_path / "provenance" / "source-manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text("{}", encoding="utf-8")
    private = tmp_path / ".awf" / "knowledge" / f"review-{ARCHIVE[:12]}-b12"
    private.mkdir(parents=True)
    (private / "manifest.json").write_text(
        canonical_json_bytes(s["manifest"]).decode("utf-8"), encoding="utf-8"
    )
    (private / "batch-001.json").write_text(
        canonical_json_bytes(s["observed"]["batch-001.json"]).decode("utf-8"),
        encoding="utf-8",
    )
    inventory_file = tmp_path / "private-attestations.json"
    pair = s["inventory"][RULE]
    inventory_file.write_bytes(
        canonical_json_bytes(
            {"schema": 1, "attestations": {RULE: {
                "proposal_ref": pair[0], "attestation_ref": pair[1]
            }}}
        )
    )
    policy_file = tmp_path / "private-policy.json"
    policy_file.write_bytes(s["policy_raw"])
    monkeypatch.setattr(
        "awf.cli.main.prepare_review",
        lambda **_: (s["manifest"], s["original"]),
    )

    class FixedClock:
        @staticmethod
        def now(tz):
            return datetime.fromtimestamp(_NOW, tz)

    monkeypatch.setattr("awf.cli.main.datetime", FixedClock)
    args = [
        "knowledge", "inspect-review", str(tmp_path / "aws-private.zip"),
        "--manifest", str(manifest_path), "--evidence-database",
        str(s["store"].database), "--review-run-id", RUN,
        "--expected-head", s["attested"].digest,
        "--attestation-inventory", str(inventory_file),
        "--reviewer-policy", str(policy_file),
        "--expected-reviewer-policy-sha256", sha256_bytes(s["policy_raw"]),
        "--require-documented",
    ]
    assert main(args) == 0
    output = capsys.readouterr().out
    result = __import__("json").loads(output)
    assert result["signed_review"]["credentials_authorized"] is True
    assert result["signed_review"]["review_attestation_authorized"] is False
    assert result["signed_review"]["training_authorized"] is False
    assert result["all_rules_adjudicated"] is False
    assert "detailed reason" not in output
    assert "reviewer-a" not in output

    wrong_policy = args.copy()
    wrong_policy[wrong_policy.index("--expected-reviewer-policy-sha256") + 1] = "0" * 64
    assert main(wrong_policy) == 2
    assert "DOSSIER_INSPECTION_FAILED" in capsys.readouterr().err
