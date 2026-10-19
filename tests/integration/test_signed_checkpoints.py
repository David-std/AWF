"""Adversarial checkpoints use only synthetic ledgers and throwaway Ed25519 keys."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from hypothesis import given, settings
from hypothesis import strategies as st

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.security.ed25519_reviewer import Ed25519Verifier
from awf.application.commands.checkpoints import propose_checkpoint, verify_signed_checkpoint
from awf.cli.main import main
from awf.domain.checkpoints import (
    CheckpointClaim,
    SignedLedgerCheckpoint,
    parse_checkpoint_policy,
)
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.signed_documents import canonical_json_bytes

_NOW = 1_790_000_000
_LEDGER = "research-ledger-a"


def _store(path: Path) -> SQLiteEvidenceLedger:
    store = SQLiteEvidenceLedger(path)
    store.initialize()
    return store


def _append(store: SQLiteEvidenceLedger, content: bytes = b"synthetic event") -> None:
    store.append(
        kind=EvidenceKind.AUDIT_RECEIPT, run_id="run-a", subject_id="item-a", content=content
    )


def _trust(
    key: Ed25519PrivateKey,
    *,
    ledger: str = _LEDGER,
    revoked: bool = False,
    from_time: int = _NOW - 100,
    until: int = _NOW + 100,
) -> tuple[bytes, str]:
    public_key_hex = (
        key.public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        .hex()
    )
    policy = canonical_json_bytes(
        {
            "schema": 1,
            "grants": [
                {
                    "key_id": "witness-a",
                    "public_key_hex": public_key_hex,
                    "ledger_ids": [ledger],
                    "valid_from": from_time,
                    "valid_until": until,
                    "revoked": revoked,
                }
            ],
        }
    )
    return policy, sha256_bytes(policy)


def _sign(key: Ed25519PrivateKey, claim: CheckpointClaim) -> SignedLedgerCheckpoint:
    return SignedLedgerCheckpoint(claim, key.sign(claim.signing_bytes).hex())


def _verify(
    store: SQLiteEvidenceLedger,
    signed: SignedLedgerCheckpoint,
    key: Ed25519PrivateKey,
    *,
    previous: SignedLedgerCheckpoint | None = None,
    now: int = _NOW,
    expected: str | None = None,
    **policy_options,
):
    raw, digest = _trust(key, **policy_options)
    return verify_signed_checkpoint(
        store=store,
        signed=signed,
        expected_signed_sha256=expected if expected is not None else signed.sha256,
        policy=parse_checkpoint_policy(raw, expected_sha256=digest),
        verifier=Ed25519Verifier(),
        now=now,
        previous=previous,
    )


def _first(tmp_path: Path):
    store = _store(tmp_path / "evidence.sqlite")
    _append(store)
    key = Ed25519PrivateKey.generate()
    claim = propose_checkpoint(
        store=store, ledger_id=_LEDGER, key_id="witness-a", issued_at=_NOW - 5
    )
    return store, key, _sign(key, claim)


def test_roundtrip_pinned_checkpoint_survives_restart_and_legitimate_append(tmp_path: Path):
    store, key, signed = _first(tmp_path)
    assert SignedLedgerCheckpoint.from_bytes(signed.to_bytes()) == signed
    reopened = SQLiteEvidenceLedger(store.database)
    report = _verify(reopened, signed, key)
    assert report.checkpoint_event_count == report.current_event_count == 1
    assert report.checkpoint_is_current_head
    assert not report.external_custody_proven
    _append(reopened, b"later legitimate append")
    report = _verify(reopened, signed, key)
    assert report.current_event_count == 2
    assert not report.checkpoint_is_current_head
    with pytest.raises(EvidenceIntegrityError, match="current ledger head"):
        raw, digest = _trust(key)
        verify_signed_checkpoint(
            store=reopened,
            signed=signed,
            expected_signed_sha256=signed.sha256,
            policy=parse_checkpoint_policy(raw, expected_sha256=digest),
            verifier=Ed25519Verifier(),
            now=_NOW,
            require_current_head=True,
        )


def test_signed_checkpoint_detects_rebuilt_shorter_valid_sqlite_chain(tmp_path: Path):
    store, key, first = _first(tmp_path)
    # Use SQLite's coherent snapshot API to retain a known, valid older database.
    older_db = tmp_path / "older.sqlite"
    with sqlite3.connect(store.database) as source, sqlite3.connect(older_db) as dest:
        source.backup(dest)
    _append(store, b"second")
    latest = _sign(
        key,
        propose_checkpoint(
            store=store,
            ledger_id=_LEDGER,
            key_id="witness-a",
            issued_at=_NOW - 3,
            previous=first,
        ),
    )
    truncated = SQLiteEvidenceLedger(older_db)
    assert truncated.verify().events_checked == 1  # the local hash chain remains valid
    with pytest.raises(EvidenceIntegrityError, match="truncated"):
        _verify(truncated, latest, key, previous=first)
    assert _verify(store, latest, key, previous=first).checkpoint_is_current_head


def test_same_count_rebuilt_ledger_with_different_bytes_is_rejected(tmp_path: Path):
    _, key, signed = _first(tmp_path)
    counterfeit = _store(tmp_path / "counterfeit.sqlite")
    _append(counterfeit, b"other content, same sequence")
    assert counterfeit.verify().events_checked == signed.claim.event_count
    with pytest.raises(EvidenceIntegrityError):
        _verify(counterfeit, signed, key)


@given(st.lists(st.binary(min_size=1, max_size=24), min_size=1, max_size=14))
@settings(max_examples=18, deadline=None)
def test_property_all_random_prefixes_remain_verifiable_and_wrong_digest_fails(
    content_items: list[bytes],
):
    with tempfile.TemporaryDirectory(prefix="awf-checkpoint-property-") as directory:
        store = _store(Path(directory) / "property.sqlite")
        key = Ed25519PrivateKey.generate()
        first: SignedLedgerCheckpoint | None = None
        for i, data in enumerate(content_items):
            _append(store, data)
            if i == 0:
                first = _sign(
                    key,
                    propose_checkpoint(
                        store=store,
                        ledger_id=_LEDGER,
                        key_id="witness-a",
                        issued_at=_NOW - 1,
                    ),
                )
        assert first is not None
        report = _verify(store, first, key)
        assert report.current_event_count == len(content_items)
        assert report.checkpoint_is_current_head == (len(content_items) == 1)
        fake = _sign(key, replace(first.claim, head_digest="f" * 64))
        with pytest.raises(EvidenceIntegrityError):
            _verify(store, fake, key)


@pytest.mark.parametrize(
    "anchors",
    [
        (),
        ((True, "0" * 64),),
        ((0, "0" * 64),),
        ((1, "F" * 64),),
        ((1, "x" * 64),),
        tuple((1, "f" * 64) for _ in range(1025)),
    ],
)
def test_verifier_rejects_invalid_or_unbounded_anchor_batches(
    tmp_path: Path,
    anchors: tuple[tuple[int, str], ...],
):
    store, _, _ = _first(tmp_path)
    with pytest.raises(ValueError):
        store.verify_anchors(anchors=anchors)


@pytest.mark.parametrize(
    "change",
    [
        "bad_signature",
        "head_digest",
        "count",
        "key_id",
        "ledger_id",
        "issue_time",
        "wrong_witness",
        "wrong_policy",
        "wrong_previous",
        "revoked",
        "expired",
        "wrong_ledger",
        "future_issue",
        "not_yet_valid",
    ],
)
def test_signature_policy_and_claim_mismatch_fails_closed(tmp_path: Path, change: str):
    store, key, signed = _first(tmp_path)
    other = Ed25519PrivateKey.generate()
    tampered = signed
    options = {}
    expected = signed.sha256
    verification_key = key
    now = _NOW
    if change == "bad_signature":
        tampered = replace(signed, signature_hex="0" * 128)
        expected = tampered.sha256
    elif change == "head_digest":
        tampered = _sign(key, replace(signed.claim, head_digest="f" * 64))
        expected = tampered.sha256
    elif change == "count":
        tampered = _sign(key, replace(signed.claim, event_count=2))
        expected = tampered.sha256
    elif change == "key_id":
        tampered = _sign(key, replace(signed.claim, key_id="impostor"))
        expected = tampered.sha256
    elif change == "ledger_id":
        tampered = _sign(key, replace(signed.claim, ledger_id="other-ledger"))
        expected = tampered.sha256
    elif change == "issue_time":
        tampered = replace(signed, claim=replace(signed.claim, issued_at=_NOW - 4))
        expected = tampered.sha256
    elif change == "wrong_witness":
        verification_key = other
    elif change == "wrong_policy":
        expected = "f" * 64
    elif change == "wrong_previous":
        tampered = _sign(key, replace(signed.claim, previous_checkpoint_sha256="f" * 64))
        expected = tampered.sha256
    elif change == "revoked":
        options["revoked"] = True
    elif change == "expired":
        options["until"] = _NOW - 1
    elif change == "wrong_ledger":
        options["ledger"] = "different-ledger"
    elif change == "future_issue":
        now = signed.claim.issued_at - 1
    elif change == "not_yet_valid":
        options["from_time"] = _NOW
    with pytest.raises(EvidenceIntegrityError):
        _verify(store, tampered, verification_key, expected=expected, now=now, **options)


def test_lineage_rejects_substitution_same_or_backward_sequence_and_time(tmp_path: Path):
    store, key, first = _first(tmp_path)
    _append(store, b"advance")
    second = _sign(
        key,
        propose_checkpoint(
            store=store,
            ledger_id=_LEDGER,
            key_id="witness-a",
            issued_at=_NOW,
            previous=first,
        ),
    )
    assert _verify(store, second, key, previous=first).checkpoint_event_count == 2
    for changed in (
        replace(second.claim, previous_checkpoint_sha256="f" * 64),
        replace(second.claim, event_count=1),
        replace(second.claim, issued_at=first.claim.issued_at - 1),
    ):
        adversarial = _sign(key, changed)
        with pytest.raises(EvidenceIntegrityError):
            _verify(store, adversarial, key, previous=first)
    with pytest.raises(EvidenceIntegrityError, match="complete checkpoint history"):
        _verify(store, second, key)
    with pytest.raises(EvidenceIntegrityError):
        propose_checkpoint(
            store=store,
            ledger_id=_LEDGER,
            key_id="witness-a",
            issued_at=_NOW,
            previous=second,
        )


def test_three_checkpoint_chain_verifies_complete_history_and_cli_proposes_fourth(
    tmp_path: Path,
    capsys,
):
    store, key, first = _first(tmp_path)
    _append(store, b"two")
    second = _sign(
        key,
        propose_checkpoint(
            store=store,
            ledger_id=_LEDGER,
            key_id="witness-a",
            issued_at=_NOW - 4,
            previous=first,
        ),
    )
    _append(store, b"three")
    third = _sign(
        key,
        propose_checkpoint(
            store=store,
            ledger_id=_LEDGER,
            key_id="witness-a",
            issued_at=_NOW - 3,
            previous=second,
        ),
    )
    with pytest.raises(EvidenceIntegrityError, match="complete checkpoint history"):
        _verify(store, third, key, previous=second)
    raw, digest = _trust(key, from_time=1_700_000_000, until=2_300_000_000)
    policy = parse_checkpoint_policy(raw, expected_sha256=digest)
    assert verify_signed_checkpoint(
        store=store,
        signed=third,
        expected_signed_sha256=third.sha256,
        history=(first, second),
        policy=policy,
        verifier=Ed25519Verifier(),
        now=_NOW,
    ).checkpoint_is_current_head
    paths = [tmp_path / f"checkpoint-{i}.json" for i in (1, 2, 3)]
    for path, signed in zip(paths, (first, second, third), strict=True):
        path.write_bytes(signed.to_bytes())
    policy_file = tmp_path / "policy.json"
    policy_file.write_bytes(raw)
    assert (
        main(
            [
                "evidence",
                "checkpoint-verify",
                str(paths[2]),
                "--database",
                str(store.database),
                "--history-file",
                str(paths[0]),
                "--history-file",
                str(paths[1]),
                "--expected-checkpoint-sha256",
                third.sha256,
                "--policy-file",
                str(policy_file),
                "--expected-policy-sha256",
                digest,
            ]
        )
        == 0
    )
    capsys.readouterr()
    _append(store, b"four")
    assert (
        main(
            [
                "evidence",
                "checkpoint-propose",
                "--database",
                str(store.database),
                "--ledger-id",
                _LEDGER,
                "--key-id",
                "witness-a",
                "--history-file",
                str(paths[0]),
                "--history-file",
                str(paths[1]),
                "--previous-file",
                str(paths[2]),
                "--expected-previous-sha256",
                third.sha256,
                "--policy-file",
                str(policy_file),
                "--expected-policy-sha256",
                digest,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["claim"]["event_count"] == 4


def test_empty_ledger_and_wrong_ledger_identity_fail(tmp_path: Path):
    store = _store(tmp_path / "empty.sqlite")
    with pytest.raises(EvidenceIntegrityError, match="empty"):
        propose_checkpoint(store=store, ledger_id=_LEDGER, key_id="witness-a", issued_at=_NOW)
    _append(store)
    key = Ed25519PrivateKey.generate()
    first = _sign(
        key,
        propose_checkpoint(
            store=store,
            ledger_id=_LEDGER,
            key_id="witness-a",
            issued_at=_NOW - 1,
        ),
    )
    _append(store, b"next")
    with pytest.raises(EvidenceIntegrityError, match="identities"):
        propose_checkpoint(
            store=store,
            ledger_id="other-ledger",
            key_id="witness-a",
            issued_at=_NOW,
            previous=first,
        )


@pytest.mark.parametrize(
    "attack",
    [
        "duplicate_claim",
        "noncanonical",
        "new_field",
        "bad_schema",
        "nonfinite",
        "bad_utf8",
        "unpaired_surrogate",
        "oversized",
        "invalid_signature",
    ],
)
def test_signed_checkpoint_rejects_malformed_serialization(tmp_path: Path, attack: str):
    _, _, signed = _first(tmp_path)
    raw = signed.to_bytes()
    body = json.loads(raw)
    if attack == "duplicate_claim":
        raw = raw.replace(b'"claim":', b'"claim":null,"claim":')
    elif attack == "noncanonical":
        raw = raw.replace(b'"claim":', b' "claim":')
    elif attack == "new_field":
        body["unexpected"] = "unexpected"
        raw = canonical_json_bytes(body)
    elif attack == "bad_schema":
        body["claim"]["schema"] = 2
        raw = canonical_json_bytes(body)
    elif attack == "nonfinite":
        raw = raw.replace(b'"event_count":1', b'"event_count":NaN')
    elif attack == "bad_utf8":
        raw = raw[:-1] + b"\xff"
    elif attack == "unpaired_surrogate":
        raw = raw.replace(b'"ledger_id":"', b'"ledger_id":"\\ud800')
    elif attack == "oversized":
        raw = raw + b" " * (64 * 1024)
    else:
        body["signature_hex"] = "not-hex"
        raw = canonical_json_bytes(body)
    with pytest.raises(EvidenceIntegrityError):
        SignedLedgerCheckpoint.from_bytes(raw)


def test_checkpoint_policy_pin_duplicate_keys_and_invalid_grants():
    key = Ed25519PrivateKey.generate()
    raw, digest = _trust(key)
    assert parse_checkpoint_policy(raw, expected_sha256=digest).policy_sha256 == digest
    with pytest.raises(EvidenceIntegrityError, match="mismatch"):
        parse_checkpoint_policy(raw, expected_sha256="f" * 64)
    body = json.loads(raw)
    grant = dict(body["grants"][0])
    body["grants"].append({**grant, "key_id": "second-key"})
    duplicate = canonical_json_bytes(body)
    with pytest.raises(EvidenceIntegrityError, match="ambiguous"):
        parse_checkpoint_policy(duplicate, expected_sha256=sha256_bytes(duplicate))
    body["grants"] = [{**grant, "ledger_ids": ["same", "same"]}]
    duplicate = canonical_json_bytes(body)
    with pytest.raises(EvidenceIntegrityError, match="duplicate"):
        parse_checkpoint_policy(duplicate, expected_sha256=sha256_bytes(duplicate))


def test_cli_propose_and_verify_pinned_checkpoint(tmp_path: Path, capsys):
    store, key, signed = _first(tmp_path)
    raw, digest = _trust(key, from_time=1_700_000_000, until=2_300_000_000)
    policy_file = tmp_path / "policy.json"
    policy_file.write_bytes(raw)
    checkpoint_file = tmp_path / "checkpoint.json"
    checkpoint_file.write_bytes(signed.to_bytes())
    base = ["--database", str(store.database)]
    assert (
        main(
            [
                "evidence",
                "checkpoint-verify",
                str(checkpoint_file),
                *base,
                "--policy-file",
                str(policy_file),
                "--expected-policy-sha256",
                digest,
                "--expected-checkpoint-sha256",
                signed.sha256,
            ]
        )
        == 0
    )
    verified = json.loads(capsys.readouterr().out)
    assert verified["status"] == "SIGNED_CHECKPOINT_VALID"
    assert verified["external_custody_proven"] is False
    assert (
        main(
            [
                "evidence",
                "checkpoint-propose",
                *base,
                "--ledger-id",
                _LEDGER,
                "--key-id",
                "witness-a",
            ]
        )
        == 0
    )
    proposal = json.loads(capsys.readouterr().out)
    assert proposal["status"] == "CHECKPOINT_UNSIGNED_PROPOSAL"
    assert bytes.fromhex(proposal["signing_message_hex"]).startswith(
        b"AWF/ledger-checkpoint/v1\x00"
    )
    assert proposal["signature_verified"] is False


def test_cli_rejects_invalid_witness_and_incomplete_lineage_flags(tmp_path: Path, capsys):
    store, key, signed = _first(tmp_path)
    raw, digest = _trust(key, from_time=1_700_000_000, until=2_300_000_000)
    policy_file = tmp_path / "policy.json"
    policy_file.write_bytes(raw)
    checkpoint_file = tmp_path / "checkpoint.json"
    checkpoint_file.write_bytes(signed.to_bytes())
    args = [
        "evidence",
        "checkpoint-verify",
        str(checkpoint_file),
        "--database",
        str(store.database),
        "--policy-file",
        str(policy_file),
        "--expected-policy-sha256",
        digest,
        "--expected-checkpoint-sha256",
        "f" * 64,
    ]
    assert main(args) == 2
    assert "CHECKPOINT_FAILED" in capsys.readouterr().err
    args = [
        "evidence",
        "checkpoint-propose",
        "--database",
        str(store.database),
        "--ledger-id",
        _LEDGER,
        "--key-id",
        "witness-a",
        "--previous-file",
        str(checkpoint_file),
    ]
    assert main(args) == 2
    assert "requires its external digest" in capsys.readouterr().err


def test_cli_lineage_requires_pinned_previous_but_never_publishes_secret(tmp_path: Path, capsys):
    store, key, signed = _first(tmp_path)
    _append(store, b"secret synthetic payload not for stdout")
    raw, digest = _trust(key, from_time=1_700_000_000, until=2_300_000_000)
    policy_file = tmp_path / "policy.json"
    policy_file.write_bytes(raw)
    previous_file = tmp_path / "previous.json"
    previous_file.write_bytes(signed.to_bytes())
    args = [
        "evidence",
        "checkpoint-propose",
        "--database",
        str(store.database),
        "--ledger-id",
        _LEDGER,
        "--key-id",
        "witness-a",
        "--previous-file",
        str(previous_file),
        "--expected-previous-sha256",
        signed.sha256,
        "--policy-file",
        str(policy_file),
        "--expected-policy-sha256",
        digest,
    ]
    assert main(args) == 0
    output = capsys.readouterr().out
    assert "secret synthetic payload" not in output
    assert json.loads(output)["claim"]["previous_checkpoint_sha256"] == signed.sha256
