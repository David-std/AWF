"""Adversarial, synthetic authorization of durable critic sweep observations."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.persistence.sqlite_revision import SQLiteRevisionJournal
from awf.adapters.security.ed25519_reviewer import Ed25519ReviewerVerifier
from awf.application.commands.authorize_critics import verify_authorized_critic_sweeps
from awf.application.commands.authorize_review import append_signed_review_claim
from awf.application.commands.bind_evidence import event_reference
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import (
    ReviewerClaim,
    ReviewerRole,
    SignedReviewerClaim,
    parse_trust_policy,
)
from awf.domain.revision_audit import AuditSlot, AuditStatus, RevisionPolicy

_NOW = 1_800_000_000
_RUN = "run-a"
_REVISION = "revision-a"


def _json(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _document(text: str = "Synthetic cited claim."):
    return MarkdownAdapter().parse(f"# Study\n\n{text}\n".encode(), source_name="synthetic.md")


def _setup(tmp_path: Path):
    journal = SQLiteRevisionJournal(tmp_path / "critic-auth.sqlite")
    journal.initialize()
    document = _document()
    slot = AuditSlot(document.blocks[1].block_id, "citations", required_checks=2)
    journal.create(
        revision_id=_REVISION,
        operation_id="start",
        run_id=_RUN,
        document=document,
        slots=(slot,),
    )
    journal.record_audit(
        revision_id=_REVISION,
        operation_id="audit",
        run_id=_RUN,
        document=document,
        expected_version=0,
        slot_key=slot.key,
        status=AuditStatus.CLEAN,
        checks_executed=2,
        observation_ref="synthetic:audit",
    )
    observations = {}
    intents = {}
    for number, actor in enumerate(("critic-a", "critic-b"), start=1):
        context = journal.ledger.append(
            kind=EvidenceKind.CRITIC_CONTEXT,
            run_id=_RUN,
            subject_id=_REVISION,
            content=f"synthetic:context-{number}".encode(),
        )
        observation = journal.ledger.append(
            kind=EvidenceKind.CRITIC_OBSERVATION,
            run_id=_RUN,
            subject_id=_REVISION,
            content=f"synthetic:observation-{number}".encode(),
        )
        committed = journal.record_clean_sweep(
            revision_id=_REVISION,
            operation_id=f"sweep-{number}",
            run_id=_RUN,
            document=document,
            expected_version=number,
            policy=RevisionPolicy(),
            critic_id=actor,
            isolated_context_ref=event_reference(context),
            observation_ref=event_reference(observation),
        )
        observations[actor] = event_reference(observation)
        intents[actor] = committed.state.clean_sweeps[-1].evidence_ref
    keys = {actor: Ed25519PrivateKey.generate() for actor in observations}
    return journal, document, observations, intents, keys


def _policy(keys, *, revoked: str = "", role: ReviewerRole = ReviewerRole.CRITIC):
    grants = []
    for actor, key in sorted(keys.items()):
        public = (
            key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            .hex()
        )
        grants.append(
            {
                "actor_id": actor,
                "key_id": f"key-{actor}",
                "public_key_hex": public,
                "roles": [role.value],
                "runs": [_RUN],
                "subjects": [_REVISION],
                "valid_from": _NOW - 1000,
                "valid_until": _NOW + 1000,
                "revoked": actor == revoked,
            }
        )
    raw = _json({"schema": 1, "grants": grants})
    return parse_trust_policy(raw, expected_sha256=sha256_bytes(raw))


def _signed(
    keys,
    actor: str,
    target_ref: str,
    *,
    role: ReviewerRole = ReviewerRole.CRITIC,
    run_id: str = _RUN,
    subject_id: str = _REVISION,
):
    claim = ReviewerClaim(
        actor_id=actor,
        key_id=f"key-{actor}",
        role=role,
        run_id=run_id,
        subject_id=subject_id,
        target_event_ref=target_ref,
        issued_at=_NOW - 10,
    )
    return SignedReviewerClaim(
        claim=claim, signature_hex=keys[actor].sign(claim.signing_bytes).hex()
    )


def _attest(journal, observations, intents, keys):
    policy = _policy(keys)
    refs = {}
    for actor in ("critic-a", "critic-b"):
        event = append_signed_review_claim(
            store=journal.ledger,
            signed=_signed(keys, actor, observations[actor]),
            policy=policy,
            verifier=Ed25519ReviewerVerifier(),
            now=_NOW,
        )
        refs[intents[actor]] = event_reference(event)
    return policy, refs


def _gate(
    journal,
    document,
    refs,
    policy,
    *,
    head: str | None = None,
    run_id: str = _RUN,
    reader: SQLiteEvidenceLedger | None = None,
    now: int = _NOW,
):
    return verify_authorized_critic_sweeps(
        journal=SQLiteRevisionJournal(journal.ledger.database),
        store=reader or SQLiteEvidenceLedger(journal.ledger.database),
        revision_id=_REVISION,
        run_id=run_id,
        document=document,
        revision_policy=RevisionPolicy(),
        attestation_refs=refs,
        policy=policy,
        verifier=Ed25519ReviewerVerifier(),
        now=now,
        expected_head=head or journal.ledger.verify().head_digest,
    )


def test_distinct_signed_critics_survive_restart_but_do_not_prove_independence(
    tmp_path: Path,
) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    outcome = _gate(journal, document, refs, policy)
    assert outcome.checked == 2
    assert outcome.authorization_verified
    assert outcome.unverified == ()
    assert not outcome.independent_adjudication_proven
    assert (
        SQLiteRevisionJournal(journal.ledger.database)
        .load(revision_id=_REVISION)
        .state.clean_sweeps[1]
        .critic_id
        == "critic-b"
    )


@pytest.mark.parametrize("change", ["missing", "extra", "empty", "duplicate"])
def test_incomplete_or_swapped_attestation_inventory_is_not_authorized(
    tmp_path: Path, change: str
) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    if change == "missing":
        refs.pop(intents["critic-b"])
    elif change == "extra":
        refs["event:" + "0" * 64] = next(iter(refs.values()))
    elif change == "empty":
        refs.clear()
    else:
        refs[intents["critic-b"]] = refs[intents["critic-a"]]
    outcome = _gate(journal, document, refs, policy)
    assert not outcome.authorization_verified


@pytest.mark.parametrize(
    "change",
    ["signature", "target", "role", "actor", "run", "subject"],
)
def test_false_or_misbound_reviewer_claim_fails_closed(tmp_path: Path, change: str) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    actor = "critic-a"
    target = observations[actor]
    role = ReviewerRole.CRITIC
    run_id = _RUN
    subject_id = _REVISION
    if change == "target":
        target = observations["critic-b"]
    elif change == "role":
        role = ReviewerRole.AUDITOR
    elif change == "actor":
        actor = "critic-b"
    elif change == "run":
        run_id = "foreign-run"
    elif change == "subject":
        subject_id = "foreign-revision"
    signed = _signed(keys, actor, target, role=role, run_id=run_id, subject_id=subject_id)
    if change == "signature":
        signed = replace(signed, signature_hex="0" * 128)
    untrusted = journal.ledger.append(
        kind=EvidenceKind.REVIEW_ATTESTATION,
        run_id=run_id,
        subject_id=subject_id,
        content=signed.to_bytes(),
    )
    refs[intents["critic-a"]] = event_reference(untrusted)
    outcome = _gate(journal, document, refs, policy)
    assert not outcome.authorization_verified
    assert intents["critic-a"] in outcome.unverified


def test_revoked_critic_policy_invalidates_previous_signature(tmp_path: Path) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    _, refs = _attest(journal, observations, intents, keys)
    revoked_policy = _policy(keys, revoked="critic-b")
    result = _gate(journal, document, refs, revoked_policy)
    assert not result.authorization_verified
    assert intents["critic-b"] in result.unverified


def test_expired_critic_grant_fails_during_later_verification(tmp_path: Path) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    assert _gate(journal, document, refs, policy).authorization_verified
    outcome = _gate(journal, document, refs, policy, now=_NOW + 2000)
    assert not outcome.authorization_verified
    assert set(outcome.unverified) == set(intents.values())


def test_signed_critic_role_cannot_authorize_context_event(tmp_path: Path) -> None:
    journal, _, _, _, keys = _setup(tmp_path)
    context = journal.ledger.append(
        kind=EvidenceKind.CRITIC_CONTEXT,
        run_id=_RUN,
        subject_id=_REVISION,
        content=b"synthetic:wrong-kind",
    )
    with pytest.raises(EvidenceIntegrityError):
        append_signed_review_claim(
            store=journal.ledger,
            signed=_signed(keys, "critic-a", event_reference(context)),
            policy=_policy(keys),
            verifier=Ed25519ReviewerVerifier(),
            now=_NOW,
        )


def test_policy_digest_must_be_externally_pinned(tmp_path: Path) -> None:
    _, _, _, _, keys = _setup(tmp_path)
    policy = _policy(keys)
    raw = _json(
        {
            "schema": 1,
            "grants": [],
        }
    )
    with pytest.raises(EvidenceIntegrityError):
        parse_trust_policy(raw, expected_sha256=policy.policy_sha256)


def test_document_change_and_open_material_finding_block_authorization(
    tmp_path: Path,
) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    assert not _gate(journal, _document("Changed claim."), refs, policy).authorization_verified
    version = journal.load(revision_id=_REVISION).version
    journal.open_finding(
        revision_id=_REVISION,
        operation_id="material-finding",
        run_id=_RUN,
        expected_version=version,
        finding_id="unsupported-claim",
        material=True,
        observation_ref="synthetic:issue",
    )
    assert not _gate(journal, document, refs, policy).authorization_verified


def test_wrong_run_and_external_head_fail_closed(tmp_path: Path) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    with pytest.raises(EvidenceIntegrityError, match="another run"):
        _gate(journal, document, refs, policy, run_id="foreign-run")
    with pytest.raises(EvidenceIntegrityError):
        _gate(journal, document, refs, policy, head="f" * 64)


def test_concurrent_append_between_replay_and_signature_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    store = SQLiteEvidenceLedger(journal.ledger.database)
    original = store.verified_read

    def concurrent(*, expected_head=None):
        store.append(
            kind=EvidenceKind.CRITIC_OBSERVATION,
            run_id=_RUN,
            subject_id=_REVISION,
            content=b"concurrent-append",
        )
        return original(expected_head=expected_head)

    monkeypatch.setattr(store, "verified_read", concurrent)
    with pytest.raises(EvidenceIntegrityError):
        _gate(journal, document, refs, policy, reader=store)


def test_many_critics_share_one_verified_read_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, document, observations, intents, keys = _setup(tmp_path)
    policy, refs = _attest(journal, observations, intents, keys)
    store = SQLiteEvidenceLedger(journal.ledger.database)
    original = store._audit_transaction
    count = 0

    def counted(conn):
        nonlocal count
        count += 1
        return original(conn)

    monkeypatch.setattr(store, "_audit_transaction", counted)
    assert _gate(journal, document, refs, policy, reader=store).authorization_verified
    assert count == 1
