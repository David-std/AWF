"""Verify source-specific rights over byte ranges, with external authority custody.

This only returns permission-specific *rights evidence* conclusions, not formal
scientific adjudication, dataset selection or permission to start model training.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Protocol, cast

from awf.domain.evidence import EvidenceIntegrityError, sha256_bytes
from awf.domain.signed_documents import strict_json
from awf.domain.source_rights import (
    RightsClaim,
    RightsClaimKind,
    RightsDecision,
    RightsInventory,
    RightsOutcome,
    RightsUse,
    SourceAsset,
)

_SOURCE_FIELDS = frozenset({"source_id", "archive_sha256", "file_sha256", "size_bytes"})
_CLAIM_FIELDS = frozenset(
    {
        "claim_id",
        "start_byte",
        "end_byte",
        "kind",
        "uses",
        "owner_id",
        "authority_id",
        "license_expression",
        "jurisdiction",
        "evidence_uri",
        "evidence_sha256",
        "valid_from",
        "valid_until",
        "revoked",
    }
)


class RightsAuthorityPort(Protocol):
    """External *independent* verifier; do not implement using claim metadata alone."""

    def verify(
        self,
        *,
        claim: RightsClaim,
        evidence: bytes,
        asset: SourceAsset,
        policy_sha256: str,
        at_time: int,
    ) -> None:
        """Raise if the issuer, chain of authority, grant scope or terms are unverified."""
        ...


def parse_source_rights(
    data: bytes, *, expected_sha256: str, expected_asset: SourceAsset
) -> RightsInventory:
    """Reject unpinned, duplicate-key or inconsistent local rights metadata."""
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64:
        raise EvidenceIntegrityError("missing pinned rights inventory hash")
    if sha256_bytes(data) != expected_sha256:
        raise EvidenceIntegrityError("rights inventory differs from external trusted hash")
    raw = strict_json(data)
    if (
        set(raw) != {"schema", "asset", "claims"}
        or type(raw["schema"]) is not int
        or raw["schema"] != 1
    ):
        raise EvidenceIntegrityError("invalid rights inventory version")
    asset_data = raw["asset"]
    if not isinstance(asset_data, dict) or set(asset_data) != _SOURCE_FIELDS:
        raise EvidenceIntegrityError("invalid rights asset identity")
    a = cast(dict[str, object], asset_data)
    if any(type(a[k]) is not str for k in _SOURCE_FIELDS - {"size_bytes"}):
        raise EvidenceIntegrityError("invalid rights source strings")
    asset = SourceAsset(
        source_id=cast(str, a["source_id"]),
        archive_sha256=cast(str, a["archive_sha256"]),
        file_sha256=cast(str, a["file_sha256"]),
        size_bytes=cast(int, a["size_bytes"]),
    )
    if asset != expected_asset:
        raise EvidenceIntegrityError("rights inventory refers to another source")
    rows = raw["claims"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1024:
        raise EvidenceIntegrityError("invalid rights record count")
    parsed: list[RightsClaim] = []
    for obj in rows:
        if not isinstance(obj, dict) or set(obj) != _CLAIM_FIELDS:
            raise EvidenceIntegrityError("invalid rights claim fields")
        row = cast(dict[str, object], obj)
        uses = row["uses"]
        if not isinstance(uses, list) or not uses or len(uses) != len(set(str(x) for x in uses)):
            raise EvidenceIntegrityError("empty or repeated usage rights")
        try:
            kind = RightsClaimKind(cast(str, row["kind"]))
            rights = frozenset(RightsUse(cast(str, x)) for x in uses)
        except (ValueError, TypeError) as exc:
            raise EvidenceIntegrityError("unknown source rights kind/use") from exc
        parsed.append(
            RightsClaim(
                claim_id=cast(str, row["claim_id"]),
                start_byte=cast(int, row["start_byte"]),
                end_byte=cast(int, row["end_byte"]),
                kind=kind,
                uses=rights,
                owner_id=cast(str, row["owner_id"]),
                authority_id=cast(str, row["authority_id"]),
                license_expression=cast(str, row["license_expression"]),
                jurisdiction=cast(str, row["jurisdiction"]),
                evidence_uri=cast(str, row["evidence_uri"]),
                evidence_sha256=cast(str, row["evidence_sha256"]),
                valid_from=cast(int, row["valid_from"]),
                valid_until=cast(int, row["valid_until"]),
                revoked=cast(bool, row["revoked"]),
            )
        )
    return RightsInventory(asset, tuple(parsed), expected_sha256)


def _covers(intervals: list[tuple[int, int]], start: int, end: int) -> bool:
    """Check union coverage without assuming that records are non-overlapping."""
    cursor = start
    for left, right in sorted(intervals):
        if left > cursor:
            return False
        cursor = max(cursor, right)
        if cursor >= end:
            return True
    return False


def check_source_right(
    inventory: RightsInventory,
    *,
    source_bytes: bytes,
    start_byte: int,
    end_byte: int,
    expected_fragment_sha256: str,
    use: RightsUse,
    evidence_by_sha256: Mapping[str, bytes],
    authority: RightsAuthorityPort | None = None,
    expected_authority_policy_sha256: str | None = None,
    now: int,
) -> RightsDecision:
    """Evaluate *one* requested purpose, not every downstream use.

    Absence of an independently trusted authority verifier must never produce
    an affirmative rights decision. Negative/revoked claims veto regardless.
    """
    if (
        not isinstance(source_bytes, bytes)
        or len(source_bytes) != inventory.asset.size_bytes
        or sha256_bytes(source_bytes) != inventory.asset.file_sha256
        or type(start_byte) is not int
        or type(end_byte) is not int
        or not 0 <= start_byte < end_byte <= len(source_bytes)
        or not isinstance(expected_fragment_sha256, str)
        or sha256_bytes(source_bytes[start_byte:end_byte]) != expected_fragment_sha256
        or not isinstance(use, RightsUse)
        or type(now) is not int
        or now < 0
    ):
        raise EvidenceIntegrityError("source bytes, segment or trusted time do not match")

    relevant = [
        c
        for c in inventory.claims
        if c.start_byte < end_byte and c.end_byte > start_byte and use in c.uses
    ]
    if any(
        c.kind == RightsClaimKind.DENIAL or c.revoked or not c.valid_from <= now < c.valid_until
        for c in relevant
    ):
        return RightsDecision(use, RightsOutcome.RESTRICTED, "denial_or_invalid_grant", 0, False)
    grants = [c for c in relevant if c.kind == RightsClaimKind.GRANT_CLAIM]
    for i, left in enumerate(grants):
        for right in grants[i + 1 :]:
            if (
                left.start_byte < right.end_byte
                and right.start_byte < left.end_byte
                and (left.owner_id, left.authority_id, left.license_expression, left.jurisdiction)
                != (
                    right.owner_id,
                    right.authority_id,
                    right.license_expression,
                    right.jurisdiction,
                )
            ):
                return RightsDecision(
                    use, RightsOutcome.UNKNOWN, "conflicting_overlapping_grants", 0, False
                )
    intervals = [
        (max(c.start_byte, start_byte), min(c.end_byte, end_byte))
        for c in relevant
        if c.kind == RightsClaimKind.GRANT_CLAIM
    ]
    if not _covers(intervals, start_byte, end_byte):
        return RightsDecision(use, RightsOutcome.UNKNOWN, "uncovered_source_bytes", 0, False)
    if authority is None or expected_authority_policy_sha256 is None:
        return RightsDecision(
            use, RightsOutcome.UNKNOWN, "external_authority_not_verified", 0, False
        )
    if len(expected_authority_policy_sha256) != 64 or any(
        ch not in "0123456789abcdef" for ch in expected_authority_policy_sha256
    ):
        raise EvidenceIntegrityError("externally pinned rights authority policy required")
    checked = 0
    for claim in relevant:
        if claim.kind != RightsClaimKind.GRANT_CLAIM:
            continue
        evidence = evidence_by_sha256.get(claim.evidence_sha256)
        if evidence is None:
            return RightsDecision(
                use, RightsOutcome.UNKNOWN, "missing_external_evidence", checked, False
            )
        if (
            not isinstance(evidence, bytes)
            or hashlib.sha256(evidence).hexdigest() != claim.evidence_sha256
        ):
            raise EvidenceIntegrityError("rights evidence bytes do not match claim digest")
        authority.verify(
            claim=claim,
            evidence=evidence,
            asset=inventory.asset,
            policy_sha256=expected_authority_policy_sha256,
            at_time=now,
        )
        checked += 1
    outcome = {
        RightsUse.EVALUATE: RightsOutcome.LICENSED_FOR_EVAL,
        RightsUse.TRAIN: RightsOutcome.TRAIN_ALLOWED,
    }.get(use, RightsOutcome.RIGHTS_SUPPORTED)
    return RightsDecision(use, outcome, "independent_rights_evidence_verified", checked, True)
