"""Authorize cryptographic credentials for exact historical-rule review proposals.

The output is deliberately NOT an adjudication or permission for model training.
Signed event provenance cannot establish scientific correctness or independence.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from awf.application.commands.authorize_review import (
    AuthorizationGateResult,
    verify_signed_review_event,
)
from awf.application.commands.verify_dossier_evidence import resolve_rule_support_event
from awf.application.ports import (
    EvidenceStorePort,
    ReviewerSignatureVerifierPort,
)
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind, sha256_bytes
from awf.domain.reviewer_auth import ReviewerRole, ReviewerTrustPolicy
from awf.domain.signed_documents import canonical_json_bytes
from awf.knowledge.adjudication_dossiers import audit_private_dossiers

_EVENT = re.compile(r"event:([a-f0-9]{64})\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")


def private_dossier_proposal_payload(
    *,
    canonical_manifest: Mapping[str, Any],
    canonical_rule: Mapping[str, Any],
    observed_rule: Mapping[str, Any],
) -> bytes:
    """Deterministically bind every mutable review field without exposing prose.

    Call only after the source-bound audit has verified the original packets
    and marked this rule PROPOSAL_DOCUMENTED.
    """
    template = observed_rule["review_template"]
    if not isinstance(template, dict):
        raise EvidenceIntegrityError("private review template is invalid")
    rule_id = canonical_rule["id"]
    requirement_sha = canonical_rule["requirement_sha256"]
    archive_sha = canonical_manifest["archive_sha256"]
    source_id = canonical_manifest["source_id"]
    if not all(isinstance(item, str) for item in (rule_id, requirement_sha, archive_sha, source_id)):
        raise EvidenceIntegrityError("canonical review identities are invalid")
    reviewer = template.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer:
        raise EvidenceIntegrityError("reviewer actor must be declared")
    return canonical_json_bytes(
        {
            "schema": 1,
            "type": "private_dossier_review_proposal",
            "source_id": source_id,
            "archive_sha256": archive_sha,
            "requirement_id": rule_id,
            "requirement_sha256": requirement_sha,
            "reviewer_actor_id": reviewer,
            "review_template_sha256": sha256_bytes(canonical_json_bytes(template)),
            "review_status": "PROPOSAL_DOCUMENTED",
        }
    )


def _event_digest(ref: str) -> str:
    if not isinstance(ref, str):
        raise EvidenceIntegrityError("signed dossier reference must be a ledger event")
    match = _EVENT.fullmatch(ref)
    if match is None:
        raise EvidenceIntegrityError("signed dossier reference must be a ledger event")
    return match.group(1)



def parse_dossier_attestation_inventory(data: bytes) -> dict[str, tuple[str, str]]:
    """Parse a bounded, canonical private event map with no ambiguous JSON."""
    from awf.domain.signed_documents import strict_json

    body = strict_json(data)
    if set(body) != {"schema", "attestations"} or body["schema"] != 1:
        raise EvidenceIntegrityError("invalid dossier attestation inventory schema")
    records = body["attestations"]
    if not isinstance(records, dict) or not 1 <= len(records) <= 184:
        raise EvidenceIntegrityError("invalid dossier attestation inventory size")
    result: dict[str, tuple[str, str]] = {}
    for identifier, references in records.items():
        if (
            not isinstance(identifier, str)
            or not identifier
            or not isinstance(references, dict)
            or set(references) != {"proposal_ref", "attestation_ref"}
        ):
            raise EvidenceIntegrityError("invalid dossier attestation inventory entry")
        result[identifier] = (
            f"event:{_event_digest(references['proposal_ref'])}",
            f"event:{_event_digest(references['attestation_ref'])}",
        )
    return result



def verify_authorized_dossier_proposals(
    *,
    canonical_manifest: Mapping[str, Any],
    canonical_packets: Mapping[str, Mapping[str, Any]],
    observed_manifest: Mapping[str, Any],
    observed_packets: Mapping[str, Mapping[str, Any]],
    store: EvidenceStorePort,
    run_id: str,
    expected_head: str,
    attestation_refs: Mapping[str, tuple[str, str]],
    policy: ReviewerTrustPolicy,
    verifier: ReviewerSignatureVerifierPort,
    now: int,
) -> AuthorizationGateResult:
    """Authenticate ALL structurally documented dossier proposals in one snapshot.

    Attestation inventory maps rule ID to (proposal_event_ref, signature_event_ref).
    An authorized signer attests the *exact review template digest*; they do not
    attest scientific correctness. Non-documented rules remain unresolved.
    """
    if not isinstance(expected_head, str) or _DIGEST.fullmatch(expected_head) is None:
        raise EvidenceIntegrityError("an independently retained ledger head is required")
    if not isinstance(run_id, str) or not run_id:
        raise EvidenceIntegrityError("review run ID is required")
    audit = audit_private_dossiers(
        canonical_manifest=canonical_manifest,
        canonical_packets=canonical_packets,
        observed_manifest=observed_manifest,
        observed_packets=observed_packets,
    )
    documented = {
        str(item["id"])
        for item in audit["rules"]
        if item["status"] == "PROPOSAL_DOCUMENTED"
    }
    if not documented or set(attestation_refs) != documented:
        return AuthorizationGateResult(
            checked=len(documented),
            unverified=("dossier_attestation_inventory_mismatch",),
            authorization_verified=False,
        )
    expected_source = canonical_manifest["archive_sha256"]
    expected_source_id = canonical_manifest["source_id"]
    if not isinstance(expected_source, str) or not isinstance(expected_source_id, str):
        raise EvidenceIntegrityError("canonical source metadata is invalid")
    invalid: set[str] = set()
    # The support events, the reviewed template and its signature share ONE
    # fully audited snapshot, avoiding time-of-check/time-of-use ledger drift.
    with store.verified_read(expected_head=expected_head) as reader:
        for filename in sorted(canonical_packets):
            canonical_rules = canonical_packets[filename]["rules"]
            observed_rules = observed_packets[filename]["rules"]
            for original, annotated in zip(canonical_rules, observed_rules, strict=True):
                rule_id = original["id"]
                if rule_id not in documented:
                    continue
                try:
                    proposal_ref, attestation_ref = attestation_refs[rule_id]
                    proposal_record, proposal_bytes = reader.resolve_event(
                        event_digest=_event_digest(proposal_ref),
                        expected_head=expected_head,
                    )
                    if (
                        proposal_record.kind != EvidenceKind.KNOWLEDGE_REVIEW_PROPOSAL
                        or proposal_record.run_id != run_id
                        or proposal_record.subject_id != rule_id
                        or proposal_bytes
                        != private_dossier_proposal_payload(
                            canonical_manifest=canonical_manifest,
                            canonical_rule=original,
                            observed_rule=annotated,
                        )
                    ):
                        raise EvidenceIntegrityError("proposal is not bound to current dossier")
                    template = annotated["review_template"]
                    for support_ref in template["evidence_ids"]:
                        support_event = resolve_rule_support_event(
                            reader,
                            reference=support_ref,
                            run_id=run_id,
                            rule_id=rule_id,
                            archive_sha256=expected_source,
                            source_id=expected_source_id,
                            requirement_sha256=original["requirement_sha256"],
                            expected_head=expected_head,
                        )
                        if support_event.sequence >= proposal_record.sequence:
                            raise EvidenceIntegrityError("review proposal predates its support")
                    actor = verify_signed_review_event(
                        store=reader,
                        attestation_ref=attestation_ref,
                        target_ref=proposal_ref,
                        expected_role=ReviewerRole.KNOWLEDGE_REVIEWER,
                        run_id=run_id,
                        subject_id=rule_id,
                        policy=policy,
                        verifier=verifier,
                        now=now,
                        expected_head=expected_head,
                    )
                    attestation, _ = reader.resolve_event(
                        event_digest=_event_digest(attestation_ref),
                        expected_head=expected_head,
                    )
                    if (
                        attestation.sequence <= proposal_record.sequence
                        or actor != template["reviewer"]
                    ):
                        raise EvidenceIntegrityError("reviewer/proposal signature binding failed")
                except (EvidenceIntegrityError, ValueError, TypeError, KeyError):
                    invalid.add(rule_id)
    return AuthorizationGateResult(
        checked=len(documented),
        unverified=tuple(sorted(invalid)),
        authorization_verified=bool(documented) and not invalid,
        independent_adjudication_proven=False,
    )
