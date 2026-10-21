"""Evidence links in private dossiers must resolve to source-bound ledger events.

This module uses synthetic rules and no private AWS material. Passing these
tests never promotes an unreviewed rule to REVIEW_ATTESTED.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.application.commands.verify_dossier_evidence import verify_dossier_evidence_links
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.knowledge.adjudication_dossiers import audit_private_dossiers

SOURCE_SHA = "a" * 64
RULE_SHA = "b" * 64
SOURCE_ID = "aws-3.19.1"
RUN_ID = "knowledge-run-001"
RULE_ID = "DSR-001"
TEMPLATE = {
    "reviewer": "a declared reviewer",
    "reason": "A detailed synthetic justification for this single rule.",
    "evidence_ids": [],
    "conflicting_rule_ids": [],
    "desired_disposition": "KEEP_AS_CONTEXT",
    "proposed_tests": ["verify one synthetic rule's scope"],
    "source_rights_status": "NOT_APPLICABLE",
    "current_model_or_version_evidence": "Synthetic metadata only.",
}


def inputs():
    manifest = {"archive_sha256": SOURCE_SHA, "source_id": SOURCE_ID}
    rule = {
        "id": RULE_ID,
        "priority": "MUST",
        "requirement_sha256": RULE_SHA,
        "review_template": dict(TEMPLATE),
    }
    packet = {"rules": [rule], "batch_id": "B-001"}
    return manifest, {"batch-001.json": packet}


def ledger(tmp_path: Path) -> SQLiteEvidenceLedger:
    store = SQLiteEvidenceLedger(tmp_path / "evidence.sqlite")
    store.initialize()
    return store


def support_payload(
    *,
    archive_sha256: str = SOURCE_SHA,
    source_id: str = SOURCE_ID,
    requirement_id: str = RULE_ID,
    requirement_sha256: str = RULE_SHA,
) -> bytes:
    return json.dumps(
        {
            "schema_version": "1.0.0",
            "purpose": "knowledge_review_support",
            "archive_sha256": archive_sha256,
            "source_id": source_id,
            "requirement_id": requirement_id,
            "requirement_sha256": requirement_sha256,
        },
        sort_keys=True,
    ).encode("utf-8")


def append(
    store: SQLiteEvidenceLedger,
    *,
    kind: EvidenceKind = EvidenceKind.RULE_SUPPORT,
    run_id: str = RUN_ID,
    subject_id: str = RULE_ID,
    content: bytes | None = None,
):
    return store.append(
        kind=kind,
        run_id=run_id,
        subject_id=subject_id,
        content=support_payload() if content is None else content,
    )


def check(
    store: SQLiteEvidenceLedger,
    record_ref: str,
    *,
    run_id: str = RUN_ID,
    expected_head: str,
):
    manifest, packets = inputs()
    actual = {
        name: {
            **packet,
            "rules": [{**packet["rules"][0], "review_template": {**TEMPLATE, "evidence_ids": [record_ref]}}],
        }
        for name, packet in packets.items()
    }
    # The original inspector is still the source-bound structural gate.
    outcome = audit_private_dossiers(
        canonical_manifest=manifest,
        canonical_packets=packets,
        observed_manifest=manifest,
        observed_packets=actual,
    )
    assert outcome["rules"][0]["status"] == "PROPOSAL_DOCUMENTED"
    result = verify_dossier_evidence_links(
        canonical_manifest=manifest,
        canonical_packets=packets,
        observed_packets=actual,
        store=store,
        run_id=run_id,
        expected_head=expected_head,
    )
    return result, outcome


def test_valid_link_is_structural_and_never_attested(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    record = append(store)
    result, inspection = check(store, f"event:{record.digest}", expected_head=record.digest)
    assert result.all_declared_links_verified
    assert result.referenced_events == result.verified_events == 1
    assert result.affected_rule_ids == ()
    assert result.independent_adjudication_proven is False
    assert result.reviewer_authorized is False
    assert result.training_authorized is False
    assert inspection["review_attestation_authorized"] is False
    assert result.to_dict()["contains_private_source_text"] is False


@pytest.mark.parametrize(
    ("event_kind", "event_run", "subject", "payload"),
    [
        (EvidenceKind.AUDIT_RECEIPT, RUN_ID, RULE_ID, None),
        (EvidenceKind.RULE_SUPPORT, "other-run", RULE_ID, None),
        (EvidenceKind.RULE_SUPPORT, RUN_ID, "DSR-002", None),
        (EvidenceKind.RULE_SUPPORT, RUN_ID, RULE_ID, support_payload(archive_sha256="c" * 64)),
        (EvidenceKind.RULE_SUPPORT, RUN_ID, RULE_ID, support_payload(source_id="other-source")),
        (EvidenceKind.RULE_SUPPORT, RUN_ID, RULE_ID, support_payload(requirement_id="DSR-002")),
        (EvidenceKind.RULE_SUPPORT, RUN_ID, RULE_ID, support_payload(requirement_sha256="d" * 64)),
        (EvidenceKind.RULE_SUPPORT, RUN_ID, RULE_ID, b"unstructured raw text"),
        (EvidenceKind.RULE_SUPPORT, RUN_ID, RULE_ID, b'{"schema_version":"1.0.0","unexpected":"x"}'),
    ],
)
def test_cross_scope_or_wrong_payload_never_passes(
    tmp_path: Path,
    event_kind: EvidenceKind,
    event_run: str,
    subject: str,
    payload: bytes | None,
) -> None:
    store = ledger(tmp_path)
    record = append(store, kind=event_kind, run_id=event_run, subject_id=subject, content=payload)
    result, _ = check(store, f"event:{record.digest}", expected_head=record.digest)
    assert result.verified_events == 0
    assert result.affected_rule_ids == (RULE_ID,)
    assert result.all_declared_links_verified is False


@pytest.mark.parametrize("ref", ["sha256:" + "f" * 64, "event:" + "f" * 64, "http://example.test", "event:bad"])
def test_unresolved_or_non_event_references_fail_closed(tmp_path: Path, ref: str) -> None:
    store = ledger(tmp_path)
    head = append(store).digest
    result, _ = check(store, ref, expected_head=head)
    assert result.referenced_events == 1
    assert result.verified_events == 0
    assert result.affected_rule_ids == (RULE_ID,)


def test_post_checkpoint_append_fails_instead_of_accepting_a_new_snapshot(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    original = append(store)
    append(store, content=b"second content")
    with pytest.raises(EvidenceIntegrityError, match="head"):
        check(store, f"event:{original.digest}", expected_head=original.digest)


def test_truncated_history_requires_pinned_head(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    record = append(store)
    with pytest.raises(ValueError, match="independently retained"):
        check(store, f"event:{record.digest}", expected_head="")
    with pytest.raises(EvidenceIntegrityError, match="head"):
        check(store, f"event:{record.digest}", expected_head="0" * 64)


def test_duplicate_event_claim_in_one_rule_rejected_before_binding(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    event = append(store)
    manifest, packets = inputs()
    item = packets["batch-001.json"]["rules"][0]
    observed = {
        "batch-001.json": {
            "batch_id": "B-001",
            "rules": [{**item, "review_template": {**TEMPLATE, "evidence_ids": [f"event:{event.digest}"] * 2}}],
        }
    }
    with pytest.raises(ValueError, match="duplicate"):
        audit_private_dossiers(
            canonical_manifest=manifest,
            canonical_packets=packets,
            observed_manifest=manifest,
            observed_packets=observed,
        )


def test_empty_evidence_inventory_never_passes_by_vacuity(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    manifest, packets = inputs()
    result = verify_dossier_evidence_links(
        canonical_manifest=manifest,
        canonical_packets=packets,
        observed_packets=packets,
        store=store,
        run_id=RUN_ID,
        expected_head="0" * 64,
    )
    assert result.referenced_events == result.verified_events == 0
    assert result.all_declared_links_verified is False
