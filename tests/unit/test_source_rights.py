"""S2 source-rights gates with synthetic bytes and a synthetic authority adapter."""

from __future__ import annotations

from dataclasses import replace

import pytest

from awf.application.commands.source_rights import check_source_right, parse_source_rights
from awf.domain.evidence import EvidenceIntegrityError, sha256_bytes
from awf.domain.signed_documents import canonical_json_bytes
from awf.domain.source_rights import RightsOutcome, RightsUse, SourceAsset

DATA = b"abcdefghij"
EVIDENCE = b"synthetic-owner-license-grant-for-evaluation-only"
POLICY = "c" * 64
ASSET = SourceAsset("source-A", "a" * 64, sha256_bytes(DATA), len(DATA))


def _claim(
    *,
    identifier: str = "claim-1",
    start: int = 0,
    end: int = 10,
    uses: list[str] | None = None,
    kind: str = "GRANT_CLAIM",
    revoked: bool = False,
    start_time: int = 10,
    end_time: int = 100,
    owner: str = "owner-A",
    license_name: str = "LicenseRef-TestSynthetic",
) -> dict[str, object]:
    return {
        "claim_id": identifier,
        "start_byte": start,
        "end_byte": end,
        "kind": kind,
        "uses": uses if uses is not None else ["EVALUATE"],
        "owner_id": owner,
        "authority_id": "synthetic-licensor-registry",
        "license_expression": license_name,
        "jurisdiction": "TEST-ONLY",
        "evidence_uri": "https://example.invalid/synthetic-evidence",
        "evidence_sha256": sha256_bytes(EVIDENCE),
        "valid_from": start_time,
        "valid_until": end_time,
        "revoked": revoked,
    }


def _inventory(*rows: dict[str, object], asset: SourceAsset = ASSET):
    data = canonical_json_bytes(
        {
            "schema": 1,
            "asset": {
                "source_id": asset.source_id,
                "archive_sha256": asset.archive_sha256,
                "file_sha256": asset.file_sha256,
                "size_bytes": asset.size_bytes,
            },
            "claims": list(rows),
        }
    )
    return data, parse_source_rights(data, expected_sha256=sha256_bytes(data), expected_asset=asset)


class SyntheticExternalAuthority:
    """Only tests can construct an approved issuer. No production implementation exists."""

    def verify(self, *, claim, evidence, asset, policy_sha256, at_time) -> None:
        assert policy_sha256 == POLICY
        assert at_time == 50
        assert asset == ASSET
        if (
            claim.owner_id != "owner-A"
            or claim.license_expression != "LicenseRef-TestSynthetic"
            or evidence != EVIDENCE
        ):
            raise EvidenceIntegrityError("synthetic external licence authority rejects claim")


def _check(
    inventory, *, use=RightsUse.EVALUATE, start=0, end=10, source=DATA,
    evidence=None, authority=None, now=50, policy=POLICY,
):
    return check_source_right(
        inventory,
        source_bytes=source,
        start_byte=start,
        end_byte=end,
        expected_fragment_sha256=sha256_bytes(source[start:end]),
        use=use,
        evidence_by_sha256={} if evidence is None else evidence,
        authority=authority,
        expected_authority_policy_sha256=policy,
        now=now,
    )


def test_recorded_claim_never_self_authorizes() -> None:
    _, inventory = _inventory(_claim())
    out = _check(inventory)
    assert out.outcome == RightsOutcome.UNKNOWN
    assert not out.rights_scope_verified
    assert not out.training_authorized


def test_explicit_deny_overrides_claimed_grant() -> None:
    _, inventory = _inventory(_claim(), _claim(identifier="claim-2", start=3, end=6,
                                                 kind="DENIAL"))
    out = _check(inventory, authority=SyntheticExternalAuthority())
    assert out.outcome == RightsOutcome.RESTRICTED
    assert not out.rights_scope_verified


@pytest.mark.parametrize("change", [{"revoked": True}, {"start_time": 60},
                                      {"end_time": 50}])
def test_revoked_or_ineffective_claims_fail_closed(change) -> None:
    _, inventory = _inventory(_claim(**change))
    assert _check(inventory, authority=SyntheticExternalAuthority()).outcome == (
        RightsOutcome.RESTRICTED
    )


def test_partial_scope_is_not_entire_file_permission() -> None:
    _, inventory = _inventory(_claim(start=0, end=5))
    assert _check(inventory).outcome == RightsOutcome.UNKNOWN


def test_distinct_uses_are_never_inferred_from_license_name() -> None:
    _, inventory = _inventory(_claim())
    assert _check(inventory, use=RightsUse.TRAIN).outcome == RightsOutcome.UNKNOWN


def test_verified_evaluation_grant_remains_separate_from_training() -> None:
    _, inventory = _inventory(_claim())
    decision = _check(
        inventory, evidence={sha256_bytes(EVIDENCE): EVIDENCE},
        authority=SyntheticExternalAuthority(),
    )
    assert decision.outcome == RightsOutcome.LICENSED_FOR_EVAL
    assert decision.rights_scope_verified
    assert decision.evidence_checked == 1
    assert not decision.to_dict()["training_authorized"]


def test_positive_training_scope_is_not_training_authorization() -> None:
    _, inventory = _inventory(_claim(uses=["EVALUATE", "TRAIN"]))
    decision = _check(
        inventory, use=RightsUse.TRAIN,
        evidence={sha256_bytes(EVIDENCE): EVIDENCE},
        authority=SyntheticExternalAuthority(),
    )
    assert decision.outcome == RightsOutcome.TRAIN_ALLOWED
    assert decision.rights_scope_verified
    assert decision.training_authorized is False


def test_missing_external_evidence_is_unknown() -> None:
    _, inventory = _inventory(_claim())
    result = _check(inventory, authority=SyntheticExternalAuthority())
    assert result.outcome == RightsOutcome.UNKNOWN
    assert result.reason == "missing_external_evidence"


def test_changed_evidence_bytes_are_rejected() -> None:
    _, inventory = _inventory(_claim())
    with pytest.raises(EvidenceIntegrityError, match="evidence bytes"):
        _check(inventory, authority=SyntheticExternalAuthority(),
               evidence={sha256_bytes(EVIDENCE): b"tampered"})


def test_altered_source_file_cannot_be_verified() -> None:
    _, inventory = _inventory(_claim())
    with pytest.raises(EvidenceIntegrityError, match="source bytes"):
        _check(inventory, source=b"Zbcdefghij")


def test_external_authority_must_not_accept_changed_owner() -> None:
    _, inventory = _inventory(_claim(owner="impostor"))
    with pytest.raises(EvidenceIntegrityError, match="rejects claim"):
        _check(inventory, evidence={sha256_bytes(EVIDENCE): EVIDENCE},
               authority=SyntheticExternalAuthority())


def test_snapshot_hash_and_cross_source_fail() -> None:
    data, _ = _inventory(_claim())
    with pytest.raises(EvidenceIntegrityError, match="external trusted hash"):
        parse_source_rights(data, expected_sha256="f" * 64, expected_asset=ASSET)
    with pytest.raises(EvidenceIntegrityError, match="another source"):
        parse_source_rights(data, expected_sha256=sha256_bytes(data),
                            expected_asset=replace(ASSET, source_id="source-B"))


def test_duplicate_ids_rejected_even_if_license_is_same() -> None:
    with pytest.raises(EvidenceIntegrityError, match="duplicate"):
        _inventory(_claim(), _claim())


def test_invalid_span_and_boolean_timestamps_rejected() -> None:
    with pytest.raises(EvidenceIntegrityError, match="invalid or unscoped"):
        _inventory(_claim(start=5, end=20))
    with pytest.raises(EvidenceIntegrityError, match="invalid or unscoped"):
        _inventory(_claim(start_time=True))


def test_union_of_same_owner_permissions_can_cover_segment() -> None:
    _, inventory = _inventory(_claim(end=5), _claim(identifier="claim-2", start=5))
    result = _check(inventory, authority=SyntheticExternalAuthority(),
                    evidence={sha256_bytes(EVIDENCE): EVIDENCE})
    assert result.outcome == RightsOutcome.LICENSED_FOR_EVAL
    assert result.evidence_checked == 2


def test_noncanonical_or_duplicate_json_fields_are_rejected() -> None:
    raw, _ = _inventory(_claim())
    with pytest.raises(EvidenceIntegrityError):
        parse_source_rights(raw.replace(b'"schema":1', b'"schema":1,"schema":1'),
                            expected_sha256=sha256_bytes(raw.replace(
                                b'"schema":1', b'"schema":1,"schema":1'
                            )), expected_asset=ASSET)
