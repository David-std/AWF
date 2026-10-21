"""Resolve private dossier evidence IDs through one verified ledger snapshot.

Structural/byte provenance only. A valid link never authenticates the reviewer,
confirms scientific truth, resolves licensing, or emits REVIEW_ATTESTED.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from awf.application.ports import EvidenceStorePort
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind

_EVENT = re.compile(r"event:([0-9a-f]{64})\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_PURPOSE = "knowledge_review_support"
_KEYS = frozenset(
    {
        "schema_version",
        "purpose",
        "archive_sha256",
        "source_id",
        "requirement_id",
        "requirement_sha256",
    }
)


@dataclass(frozen=True, slots=True)
class DossierLinkResult:
    referenced_events: int
    verified_events: int
    affected_rule_ids: tuple[str, ...]
    all_declared_links_verified: bool
    independent_adjudication_proven: bool = False
    reviewer_authorized: bool = False
    training_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "referenced_events": self.referenced_events,
            "verified_events": self.verified_events,
            "affected_rule_ids": list(self.affected_rule_ids),
            "all_declared_links_verified": self.all_declared_links_verified,
            "independent_adjudication_proven": self.independent_adjudication_proven,
            "reviewer_authorized": self.reviewer_authorized,
            "training_authorized": self.training_authorized,
            "contains_private_source_text": False,
        }


def _payload_matches(
    payload: bytes,
    *,
    source_sha256: str,
    source_id: str,
    requirement_id: str,
    requirement_sha256: str,
) -> bool:
    if len(payload) > 512 * 1024:
        return False
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, ValueError, TypeError):
        return False
    return (
        isinstance(decoded, dict)
        and set(decoded) == _KEYS
        and decoded
        == {
            "schema_version": "1.0.0",
            "purpose": _PURPOSE,
            "archive_sha256": source_sha256,
            "source_id": source_id,
            "requirement_id": requirement_id,
            "requirement_sha256": requirement_sha256,
        }
    )


def verify_dossier_evidence_links(
    *,
    canonical_manifest: Mapping[str, Any],
    canonical_packets: Mapping[str, Mapping[str, Any]],
    observed_packets: Mapping[str, Mapping[str, Any]],
    store: EvidenceStorePort,
    run_id: str,
    expected_head: str,
) -> DossierLinkResult:
    """Verify only existing, declared links after canonical dossier inspection.

    The caller MUST first run audit_private_dossiers on these same source-bound
    packets. Fail closed if evidence inventory is missing or head not trusted.
    Does not modify dossiers and deliberately does not verify reviewer identity.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("review run ID required")
    if not isinstance(expected_head, str) or _DIGEST.fullmatch(expected_head) is None:
        raise ValueError("an independently retained SHA-256 head is required")
    source_sha = canonical_manifest.get("archive_sha256")
    source_id = canonical_manifest.get("source_id")
    if not isinstance(source_sha, str) or _DIGEST.fullmatch(source_sha) is None:
        raise ValueError("invalid canonical archive digest")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("invalid canonical source identifier")
    if set(canonical_packets) != set(observed_packets):
        raise ValueError("review packet inventory mismatch")

    count = 0
    verified = 0
    bad_rules: set[str] = set()
    # One audit and one coherent SQLite read snapshot, not O(events) per ID.
    with store.verified_read(expected_head=expected_head) as reader:
        for filename in sorted(canonical_packets):
            expected = canonical_packets[filename].get("rules")
            observed = observed_packets[filename].get("rules")
            if not isinstance(expected, list) or not isinstance(observed, list):
                raise TypeError("dossier rules must be arrays")
            if len(expected) != len(observed):
                raise ValueError("source-bound review packet length mismatch")
            for canonical, annotated in zip(expected, observed, strict=True):
                if not isinstance(canonical, dict) or not isinstance(annotated, dict):
                    raise TypeError("dossier rule must be an object")
                rule_id = canonical.get("id")
                sha = canonical.get("requirement_sha256")
                if not isinstance(rule_id, str) or not isinstance(sha, str):
                    raise TypeError("invalid canonical rule identity")
                template = annotated.get("review_template")
                if not isinstance(template, dict):
                    raise TypeError("missing review template")
                references = template.get("evidence_ids")
                if not isinstance(references, list):
                    raise TypeError("evidence IDs must be a list")
                for ref in references:
                    count += 1
                    if not isinstance(ref, str):
                        bad_rules.add(rule_id)
                        continue
                    match = _EVENT.fullmatch(ref)
                    if match is None:
                        bad_rules.add(rule_id)
                        continue
                    try:
                        record, payload = reader.resolve_event(
                            event_digest=match.group(1), expected_head=expected_head
                        )
                        if (
                            record.kind != EvidenceKind.RULE_SUPPORT
                            or record.run_id != run_id
                            or record.subject_id != rule_id
                            or not _payload_matches(
                                payload,
                                source_sha256=source_sha,
                                source_id=source_id,
                                requirement_id=rule_id,
                                requirement_sha256=sha,
                            )
                        ):
                            raise EvidenceIntegrityError("dossier event identity mismatch")
                    except (EvidenceIntegrityError, ValueError):
                        bad_rules.add(rule_id)
                    else:
                        verified += 1
    return DossierLinkResult(
        referenced_events=count,
        verified_events=verified,
        affected_rule_ids=tuple(sorted(bad_rules)),
        all_declared_links_verified=count > 0 and count == verified and not bad_rules,
    )
