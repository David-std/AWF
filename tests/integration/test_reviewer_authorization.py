"""Negative-first identity/role verification with synthetic, ephemeral Ed25519 keys."""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.security.ed25519_reviewer import Ed25519ReviewerVerifier
from awf.application.commands.authorize_review import (
    append_signed_review_claim,
    verify_authorized_audit_receipts,
    verify_authorized_knowledge_progress,
    verify_signed_review_event,
)
from awf.application.commands.bind_evidence import (
    event_reference,
    record_evidenced_audit,
    record_evidenced_chunk,
    record_stage_claim,
)
from awf.cli.main import main
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.knowledge_integrity import (
    AxisReceipt,
    KnowledgeProgress,
    KnowledgeStage,
    SourceInput,
    build_manifest,
)
from awf.domain.reviewer_auth import (
    ReviewerClaim,
    ReviewerRole,
    SignedReviewerClaim,
    parse_trust_policy,
)
from awf.domain.revision_audit import AuditSlot, AuditStatus, start_revision

_TIME = 1_800_000_000


def _json(value: dict[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _policy(
    key: Ed25519PrivateKey,
    *,
    role: ReviewerRole = ReviewerRole.AUDITOR,
    run: str = "run-a",
    subject: str = "p1:claims",
    revoked: bool = False,
    until: int = _TIME + 3600,
) -> tuple[bytes, str]:
    public = (
        key.public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        .hex()
    )
    raw = _json(
        {
            "schema": 1,
            "grants": [
                {
                    "actor_id": "critic-a",
                    "key_id": "key-a",
                    "public_key_hex": public,
                    "roles": [role.value],
                    "runs": [run],
                    "subjects": [subject],
                    "valid_from": _TIME - 3600,
                    "valid_until": until,
                    "revoked": revoked,
                }
            ],
        }
    )
    return raw, sha256_bytes(raw)


def _signed(key: Ed25519PrivateKey, event, *, role=ReviewerRole.AUDITOR):
    claim = ReviewerClaim(
        actor_id="critic-a",
        key_id="key-a",
        role=role,
        run_id=event.run_id,
        subject_id=event.subject_id,
        target_event_ref=event_reference(event),
        issued_at=_TIME - 10,
    )
    return SignedReviewerClaim(claim, key.sign(claim.signing_bytes).hex())


def _store(tmp_path: Path) -> SQLiteEvidenceLedger:
    store = SQLiteEvidenceLedger(tmp_path / "private" / "evidence.sqlite")
    store.initialize()
    return store


def _setup(tmp_path: Path):
    store = _store(tmp_path)
    document = MarkdownAdapter().parse(b"A claim with a citation.\n", source_name="paper.md")
    slot = AuditSlot(document.blocks[0].block_id, "claims", 2)
    state = record_evidenced_audit(
        start_revision(document, (slot,)),
        document,
        store=store,
        run_id="run-a",
        slot_key=slot.key,
        status=AuditStatus.CLEAN,
        checks_executed=2,
        observation_ref="synthetic-note",
    )
    event, _ = store.resolve_event(event_digest=state.receipts[0].evidence_ref[6:])
    return store, document, slot, state, event


def test_signature_is_bound_to_exact_event_and_recovered_after_restart(tmp_path: Path) -> None:
    store, doc, slot, state, event = _setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    raw, digest = _policy(key, subject=slot.key)
    policy = parse_trust_policy(raw, expected_sha256=digest)
    verifier = Ed25519ReviewerVerifier()
    signed = _signed(key, event)
    added = append_signed_review_claim(
        store=store, signed=signed, policy=policy, verifier=verifier, now=_TIME
    )
    reopened = SQLiteEvidenceLedger(store.database)
    head = reopened.verify().head_digest
    outcome = verify_authorized_audit_receipts(
        state,
        doc,
        store=reopened,
        run_id="run-a",
        policy=policy,
        verifier=verifier,
        attestation_refs={event_reference(event): event_reference(added)},
        now=_TIME,
        expected_head=head,
    )
    assert outcome.authorization_verified
    assert outcome.checked == 1
    assert not outcome.independent_adjudication_proven
    assert not verify_authorized_audit_receipts(
        state,
        doc,
        store=reopened,
        run_id="run-a",
        policy=policy,
        verifier=verifier,
        attestation_refs={},
        now=_TIME,
    ).authorization_verified


@pytest.mark.parametrize("tamper", ["signature", "role", "run", "subject", "target", "key"])
def test_forged_or_recontextualized_claim_fails_before_append(tmp_path: Path, tamper: str) -> None:
    store, _, slot, _, event = _setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    raw, digest = _policy(key, subject=slot.key)
    policy = parse_trust_policy(raw, expected_sha256=digest)
    signed = _signed(key, event)
    claim = signed.claim
    if tamper == "signature":
        signed = replace(signed, signature_hex="0" * 128)
    elif tamper == "role":
        signed = replace(signed, claim=replace(claim, role=ReviewerRole.CALIBRATOR))
    elif tamper == "run":
        signed = replace(signed, claim=replace(claim, run_id="run-b"))
    elif tamper == "subject":
        signed = replace(signed, claim=replace(claim, subject_id="p2:claims"))
    elif tamper == "target":
        other = store.append(
            kind=EvidenceKind.AUDIT_RECEIPT,
            run_id="run-a",
            subject_id=slot.key,
            content=b"unrelated record",
        )
        signed = replace(signed, claim=replace(claim, target_event_ref=event_reference(other)))
    else:
        signed = replace(signed, claim=replace(claim, key_id="different-key"))
    before = store.verify().events_checked
    with pytest.raises(EvidenceIntegrityError):
        append_signed_review_claim(
            store=store,
            signed=signed,
            policy=policy,
            verifier=Ed25519ReviewerVerifier(),
            now=_TIME,
        )
    assert store.verify().events_checked == before


@pytest.mark.parametrize(
    "change", ["revoked", "expired", "wrong_role", "wrong_run", "wrong_subject"]
)
def test_revocation_scope_and_validity_fail_closed(tmp_path: Path, change: str) -> None:
    store, _, slot, _, event = _setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    args = {"subject": slot.key}
    if change == "revoked":
        args["revoked"] = True
    elif change == "expired":
        args["until"] = _TIME - 1
    elif change == "wrong_role":
        args["role"] = ReviewerRole.CALIBRATOR
    elif change == "wrong_run":
        args["run"] = "run-b"
    else:
        args["subject"] = "another:slot"
    raw, digest = _policy(key, **args)
    with pytest.raises(EvidenceIntegrityError):
        append_signed_review_claim(
            store=store,
            signed=_signed(key, event),
            policy=parse_trust_policy(raw, expected_sha256=digest),
            verifier=Ed25519ReviewerVerifier(),
            now=_TIME,
        )


def test_signed_claim_cannot_be_swapped_between_attestations(tmp_path: Path) -> None:
    store, _, slot, _, event = _setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    raw, digest = _policy(key, subject=slot.key)
    policy = parse_trust_policy(raw, expected_sha256=digest)
    verifier = Ed25519ReviewerVerifier()
    signed = _signed(key, event)
    attestation = append_signed_review_claim(
        store=store, signed=signed, policy=policy, verifier=verifier, now=_TIME
    )
    other = store.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="run-a",
        subject_id=slot.key,
        content=b"other audit",
    )
    with pytest.raises(EvidenceIntegrityError, match="exact operation"):
        verify_signed_review_event(
            store=store,
            attestation_ref=event_reference(attestation),
            target_ref=event_reference(other),
            expected_role=ReviewerRole.AUDITOR,
            run_id="run-a",
            subject_id=slot.key,
            policy=policy,
            verifier=verifier,
            now=_TIME,
        )


def test_noncanonical_duplicate_fields_and_wrong_trust_anchor_are_rejected() -> None:
    key = Ed25519PrivateKey.generate()
    raw, digest = _policy(key)
    with pytest.raises(EvidenceIntegrityError, match="substituted"):
        parse_trust_policy(raw, expected_sha256="f" * 64)
    with pytest.raises(EvidenceIntegrityError, match="duplicate"):
        parse_trust_policy(
            b'{"schema":1,"schema":1,"grants":[]}\n',
            expected_sha256=sha256_bytes(b'{"schema":1,"schema":1,"grants":[]}\n'),
        )
    assert parse_trust_policy(raw, expected_sha256=digest).grants[0].actor_id == "critic-a"


@pytest.mark.parametrize(
    "malformed",
    [
        b'{"grants":[],"schema":1}',
        b'{"grants":[],"schema":1}\r\n',
        b'{"grants":[],"schema":NaN}\n',
        b'{"grants":[],"schema":1,"unknown":0}\n',
        b'{"grants":[],"schema":1,"actor_id":"\\ud800"}\n',
    ],
)
def test_policy_parser_rejects_noncanonical_or_unexpected_bytes(malformed: bytes) -> None:
    with pytest.raises(EvidenceIntegrityError):
        parse_trust_policy(malformed, expected_sha256=sha256_bytes(malformed))


def test_same_public_key_cannot_be_assigned_two_reviewer_personas() -> None:
    key = Ed25519PrivateKey.generate()
    raw, _ = _policy(key)
    body = json.loads(raw)
    impostor = dict(body["grants"][0])
    impostor["actor_id"] = "critic-b"
    impostor["key_id"] = "key-b"
    body["grants"].append(impostor)
    duplicated = _json(body)
    with pytest.raises(EvidenceIntegrityError, match="ambiguous"):
        parse_trust_policy(duplicated, expected_sha256=sha256_bytes(duplicated))


def test_event_checkpoint_mismatch_blocks_signed_review(tmp_path: Path) -> None:
    store, _, slot, _, event = _setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    raw, digest = _policy(key, subject=slot.key)
    policy = parse_trust_policy(raw, expected_sha256=digest)
    verifier = Ed25519ReviewerVerifier()
    attestation = append_signed_review_claim(
        store=store,
        signed=_signed(key, event),
        policy=policy,
        verifier=verifier,
        now=_TIME,
    )
    with pytest.raises(EvidenceIntegrityError):
        verify_signed_review_event(
            store=store,
            attestation_ref=event_reference(attestation),
            target_ref=event_reference(event),
            expected_role=ReviewerRole.AUDITOR,
            run_id="run-a",
            subject_id=slot.key,
            policy=policy,
            verifier=verifier,
            now=_TIME,
            expected_head="f" * 64,
        )


def test_valid_signed_claim_without_local_evidence_integrity_cannot_pass(tmp_path: Path) -> None:
    store, doc, slot, state, event = _setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    raw, digest = _policy(key, subject=slot.key)
    policy = parse_trust_policy(raw, expected_sha256=digest)
    verifier = Ed25519ReviewerVerifier()
    signed = _signed(key, event)
    appended = append_signed_review_claim(
        store=store, signed=signed, policy=policy, verifier=verifier, now=_TIME
    )
    modified = replace(state, receipts=(replace(state.receipts[0], scope_sha256="0" * 64),))
    report = verify_authorized_audit_receipts(
        modified,
        doc,
        store=store,
        run_id="run-a",
        policy=policy,
        verifier=verifier,
        attestation_refs={event_reference(event): event_reference(appended)},
        now=_TIME,
    )
    assert not report.authorization_verified
    assert slot.key in report.unverified


def test_knowledge_stages_require_correct_distinct_signed_roles(tmp_path: Path) -> None:
    store = _store(tmp_path)
    manifest = build_manifest(
        (SourceInput("ref-1", b"abcdef", "private:source"),),
        version="v1",
        expected_axes=("meaning",),
        chunk_bytes=3,
    )
    chunks = tuple(
        record_evidenced_chunk(
            store=store,
            run_id="session",
            reader_ref="local-reader",
            reference_id="ref-1",
            chunk_id=f"C{index:04d}",
            chunk_bytes=part,
        )
        for index, part in enumerate((b"abc", b"def"), start=1)
    )
    axis = store.append(
        kind=EvidenceKind.AUDIT_RECEIPT,
        run_id="session",
        subject_id="axis:meaning",
        content=b"axis observation",
    )
    axes = (AxisReceipt("meaning", event_reference(axis)),)
    available = record_stage_claim(
        KnowledgeProgress("ref-1"),
        store=store,
        stage=KnowledgeStage.AVAILABLE,
        context_ref="session",
    )
    read = record_stage_claim(
        available,
        store=store,
        stage=KnowledgeStage.READ,
        context_ref="session",
        manifest=manifest,
        chunks=chunks,
        axes=axes,
    )
    calibration = store.append(
        kind=EvidenceKind.CALIBRATION_JUDGMENT,
        run_id="session",
        subject_id="ref-1:calibration",
        content=b"reviewed synthetic calibration",
    )
    understood = record_stage_claim(
        read,
        store=store,
        stage=KnowledgeStage.UNDERSTOOD,
        context_ref="session",
        adjudication_ref=event_reference(calibration),
    )
    applicability = store.append(
        kind=EvidenceKind.REVIEW_DECISION,
        run_id="session",
        subject_id="ref-1:applicability",
        content=b"reviewed synthetic applicability",
    )
    progress = record_stage_claim(
        understood,
        store=store,
        stage=KnowledgeStage.APPLICABLE,
        context_ref="session",
        adjudication_ref=event_reference(applicability),
    )
    key = Ed25519PrivateKey.generate()
    raw, _ = _policy(key, run="session", subject="ref-1:UNDERSTOOD")
    body = json.loads(raw)
    body["grants"][0]["roles"] = ["CALIBRATOR", "APPLICABILITY_REVIEWER"]
    body["grants"][0]["subjects"] = ["ref-1:UNDERSTOOD", "ref-1:APPLICABLE"]
    raw = _json(body)
    policy = parse_trust_policy(raw, expected_sha256=sha256_bytes(raw))
    verifier = Ed25519ReviewerVerifier()
    signed_events = {}
    for stage, role in (
        (KnowledgeStage.UNDERSTOOD, ReviewerRole.CALIBRATOR),
        (KnowledgeStage.APPLICABLE, ReviewerRole.APPLICABILITY_REVIEWER),
    ):
        stage_ref = next(c.evidence_ref for c in progress.claims if c.stage == stage)
        event, _ = store.resolve_event(event_digest=stage_ref[6:])
        attestation = append_signed_review_claim(
            store=store,
            signed=_signed(key, event, role=role),
            policy=policy,
            verifier=verifier,
            now=_TIME,
        )
        signed_events[stage_ref] = event_reference(attestation)
    params = dict(
        store=store,
        manifest=manifest,
        chunks=chunks,
        axes=axes,
        policy=policy,
        verifier=verifier,
        now=_TIME,
    )
    gate = verify_authorized_knowledge_progress(progress, attestation_refs=signed_events, **params)
    assert gate.authorization_verified and gate.checked == 2
    assert gate.independent_adjudication_proven is False
    swapped = dict(signed_events)
    first, second = tuple(swapped)
    swapped[first], swapped[second] = swapped[second], swapped[first]
    assert not verify_authorized_knowledge_progress(
        progress, attestation_refs=swapped, **params
    ).authorization_verified
    body["grants"][0]["revoked"] = True
    revoked_raw = _json(body)
    revoked = parse_trust_policy(revoked_raw, expected_sha256=sha256_bytes(revoked_raw))
    assert not verify_authorized_knowledge_progress(
        progress,
        attestation_refs=signed_events,
        **{**params, "policy": revoked},
    ).authorization_verified


def test_cli_attest_roundtrip_and_unpinned_policy_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store, _, slot, _, event = _setup(tmp_path)
    key = Ed25519PrivateKey.generate()
    now = int(time.time())
    raw, _ = _policy(key, subject=slot.key)
    body = json.loads(raw)
    body["grants"][0]["valid_from"] = now - 100
    body["grants"][0]["valid_until"] = now + 100
    raw = _json(body)
    digest = sha256_bytes(raw)
    policy_path = tmp_path / "trusted_policy.json"
    policy_path.write_bytes(raw)
    claim = replace(_signed(key, event).claim, issued_at=now - 10)
    source = tmp_path / "signed.json"
    source.write_bytes(SignedReviewerClaim(claim, key.sign(claim.signing_bytes).hex()).to_bytes())
    common = [
        "--database",
        str(store.database),
        "--policy-file",
        str(policy_path),
        "--expected-policy-sha256",
        digest,
    ]
    assert main(["evidence", "attest", str(source), *common]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "REVIEWER_ATTESTATION_RECORDED"
    assert result["independent_adjudication_proven"] is False
    assert (
        main(
            [
                "evidence",
                "attest-verify",
                *common,
                "--attestation-ref",
                result["attestation_ref"],
                "--target-ref",
                event_reference(event),
                "--role",
                "AUDITOR",
                "--run-id",
                "run-a",
                "--subject-id",
                slot.key,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["actor_id"] == "critic-a"
    assert (
        main(
            [
                "evidence",
                "attest-verify",
                "--database",
                str(store.database),
                "--policy-file",
                str(policy_path),
                "--expected-policy-sha256",
                "f" * 64,
                "--attestation-ref",
                result["attestation_ref"],
                "--target-ref",
                event_reference(event),
                "--role",
                "AUDITOR",
                "--run-id",
                "run-a",
                "--subject-id",
                slot.key,
            ]
        )
        == 2
    )
    assert "REVIEWER_AUTH_FAILED" in capsys.readouterr().err
