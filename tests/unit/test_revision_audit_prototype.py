"""Adversarial checks for AWF's proposed stateful audit kernel.

Receipts represent recorded evidence, not independent quality certification.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.domain.revision_audit import (
    AuditScope,
    AuditSlot,
    AuditStatus,
    RevisionPolicy,
    RevisionVerdict,
    accept_edit,
    add_clean_sweep,
    coverage,
    decision,
    open_finding,
    record_audit,
    resolve_finding,
    scope_fingerprint,
    start_revision,
)


def _doc(text: str):
    return MarkdownAdapter().parse(text.encode("utf-8"), source_name="paper.md")


def _documents():
    original = _doc(
        "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n\nFourth paragraph.\n\nFifth paragraph."
    )
    updated = _doc(
        "First paragraph.\n\nSecond paragraph.\n\nThird paragraph CHANGED.\n\nFourth paragraph.\n\nFifth paragraph."
    )
    return original, updated


def _slot(block: str, axis: str, scope: AuditScope = AuditScope.DOCUMENT) -> AuditSlot:
    return AuditSlot(block, axis, required_checks=2, scope=scope)


def _audited(doc, slots):
    state = start_revision(doc, slots)
    for slot in slots:
        state = record_audit(
            state,
            doc,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=slot.required_checks,
            evidence_ref=f"local-test-receipt:{slot.key}",
        )
    return state


def test_empty_inventory_cannot_claim_complete_coverage() -> None:
    doc = _doc("A paragraph.")
    with pytest.raises(ValueError, match="nonempty"):
        start_revision(doc, ())
    with pytest.raises(ValueError, match="unique"):
        start_revision(doc, (_slot("paragraph_0001", "evidence"),) * 2)


def test_missing_current_receipts_prevent_convergence() -> None:
    doc = _doc("A paragraph.")
    state = start_revision(doc, (_slot("paragraph_0001", "evidence"),))
    assert coverage(state, doc) == 0.0
    assert decision(state, doc) == RevisionVerdict.AUDIT_REQUIRED
    with pytest.raises(ValueError, match="complete current audits"):
        add_clean_sweep(
            state,
            doc,
            critic_id="A",
            evidence_ref="receipt-1",
            isolated_context_ref="fresh-isolation-1",
        )


def test_clean_requires_all_work_and_evidence() -> None:
    doc = _doc("A paragraph.")
    slot = _slot("paragraph_0001", "evidence")
    state = start_revision(doc, (slot,))
    with pytest.raises(ValueError, match="every declared"):
        record_audit(
            state,
            doc,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=1,
            evidence_ref="test-receipt",
        )
    with pytest.raises(ValueError, match="invalid evidence"):
        record_audit(
            state,
            doc,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=2,
            evidence_ref="",
        )
    with pytest.raises(ValueError, match="unregistered"):
        record_audit(
            state,
            doc,
            slot_key="unknown",
            status=AuditStatus.CLEAN,
            checks_executed=2,
            evidence_ref="evidence",
        )


def test_partial_work_with_open_status_does_not_count_as_pass() -> None:
    doc = _doc("A paragraph.")
    slot = _slot("paragraph_0001", "claim_force")
    state = start_revision(doc, (slot,))
    state = record_audit(
        state,
        doc,
        slot_key=slot.key,
        status=AuditStatus.OPEN,
        checks_executed=1,
        evidence_ref="review-needs-second-check",
    )
    assert state.dirty_keys == {slot.key}
    assert coverage(state, doc) == 0.0
    assert decision(state, doc) == RevisionVerdict.AUDIT_REQUIRED


def test_document_hash_change_invalidates_global_checks() -> None:
    original, updated = _documents()
    slot = _slot("paragraph_0001", "source_truth")
    state = _audited(original, (slot,))
    modified = accept_edit(
        state, original, updated, policy=RevisionPolicy(), operation_ref="edit-1"
    )
    assert modified.clean_sweeps == ()
    assert modified.dirty_keys == {slot.key}
    assert modified.receipts == ()
    assert coverage(modified, updated) == 0.0
    assert decision(modified, updated) == RevisionVerdict.AUDIT_REQUIRED
    with pytest.raises(ValueError, match="bound"):
        coverage(modified, original)


def test_local_neighbor_reuse_requires_unchanged_dependency_fingerprint() -> None:
    original, updated = _documents()
    distant = _slot("paragraph_0001", "lexical", AuditScope.LOCAL_NEIGHBORS)
    nearby = _slot("paragraph_0004", "lexical", AuditScope.LOCAL_NEIGHBORS)
    global_slot = _slot("paragraph_0005", "source_truth")
    state = _audited(original, (distant, nearby, global_slot))
    assert scope_fingerprint(original, distant) == scope_fingerprint(updated, distant)
    assert scope_fingerprint(original, nearby) != scope_fingerprint(updated, nearby)
    next_state = accept_edit(
        state, original, updated, policy=RevisionPolicy(), operation_ref="changed-P3"
    )
    assert [r.slot_key for r in next_state.receipts] == [distant.key]
    assert next_state.receipts[0].carried_from == original.sha256
    assert next_state.receipts[0].artifact_sha256 == updated.sha256
    assert next_state.dirty_keys == {nearby.key, global_slot.key}
    assert 0 < coverage(next_state, updated) < 1
    assert next_state.revision_cycles == 1


def test_findings_survive_narrative_and_edits_until_explicit_resolution() -> None:
    original, updated = _documents()
    slot = _slot("paragraph_0001", "source_truth")
    state = _audited(original, (slot,))
    state = open_finding(state, finding_id="F-001", material=True, evidence_ref="source")
    assert decision(state, original) == RevisionVerdict.EDIT_REVIEW_REQUIRED
    changed = accept_edit(
        state, original, updated, policy=RevisionPolicy(), operation_ref="editing"
    )
    assert changed.findings[0].status == "OPEN"
    changed = record_audit(
        changed,
        updated,
        slot_key=slot.key,
        status=AuditStatus.CLEAN,
        checks_executed=2,
        evidence_ref="new-audit",
    )
    assert decision(changed, updated) == RevisionVerdict.EDIT_REVIEW_REQUIRED
    with pytest.raises(ValueError, match="explicit evidence"):
        resolve_finding(changed, finding_id="F-001", resolution_evidence_ref="")
    solved = resolve_finding(
        changed, finding_id="F-001", resolution_evidence_ref="human-resolution"
    )
    assert solved.findings[0].resolution_evidence_ref == "human-resolution"
    assert decision(solved, updated) == RevisionVerdict.FRESH_CRITIC_REQUIRED


def test_two_distinct_clean_critics_bound_to_current_hash() -> None:
    doc = _doc("Paragraph.")
    state = _audited(doc, (_slot("paragraph_0001", "syntax"),))
    state = add_clean_sweep(
        state,
        doc,
        critic_id="critic-A",
        evidence_ref="sweep-A",
        isolated_context_ref="context-A",
    )
    assert decision(state, doc) == RevisionVerdict.FRESH_CRITIC_REQUIRED
    with pytest.raises(ValueError, match="duplicate critic identity"):
        add_clean_sweep(
            state,
            doc,
            critic_id="critic-A",
            evidence_ref="again",
            isolated_context_ref="context-A2",
        )
    with pytest.raises(ValueError, match="isolated"):
        add_clean_sweep(
            state,
            doc,
            critic_id="critic-B",
            evidence_ref="sweep-B",
            isolated_context_ref="context-B",
            inherited_diagnosis=True,
        )
    state = add_clean_sweep(
        state,
        doc,
        critic_id="critic-B",
        evidence_ref="sweep-B",
        isolated_context_ref="context-B",
    )
    assert decision(state, doc) == RevisionVerdict.CONVERGED
    with pytest.raises(ValueError, match="complete current audits"):
        add_clean_sweep(
            state,
            doc,
            critic_id="critic-C",
            evidence_ref="sweep-C",
            isolated_context_ref="context-C",
        )


def test_new_audit_or_accepted_edit_resets_clean_streak() -> None:
    original, updated = _documents()
    slot = _slot("paragraph_0001", "claim_force")
    state = _audited(original, (slot,))
    state = add_clean_sweep(
        state, original, critic_id="A", evidence_ref="A", isolated_context_ref="fresh-A"
    )
    changed = accept_edit(
        state, original, updated, policy=RevisionPolicy(), operation_ref="new-version"
    )
    assert changed.clean_sweeps == ()
    changed = record_audit(
        changed,
        updated,
        slot_key=slot.key,
        status=AuditStatus.CLEAN,
        checks_executed=2,
        evidence_ref="new-proof",
    )
    assert decision(changed, updated) == RevisionVerdict.FRESH_CRITIC_REQUIRED


def test_unverified_document_or_forged_receipt_cannot_converge() -> None:
    doc = _doc("Paragraph.")
    other = _doc("Paragraph changed.")
    slot = _slot("paragraph_0001", "evidence")
    state = _audited(doc, (slot,))
    with pytest.raises(ValueError, match="bound"):
        decision(state, other)
    bad = replace(
        state,
        receipts=(replace(state.receipts[0], scope_sha256="0" * 64),),
        dirty_keys=frozenset(),
    )
    assert decision(bad, doc) == RevisionVerdict.AUDIT_REQUIRED
    assert coverage(bad, doc) == 0.0


def test_budget_exhaustion_never_grants_pass() -> None:
    original, updated = _documents()
    state = start_revision(original, (_slot("paragraph_0001", "syntax"),))
    exhausted = replace(state, revision_cycles=8)
    assert decision(exhausted, original) == RevisionVerdict.BUDGET_EXHAUSTED
    with pytest.raises(ValueError, match="budget exhausted"):
        accept_edit(
            exhausted,
            original,
            updated,
            policy=RevisionPolicy(),
            operation_ref="unauthorized-extra-edit",
        )


def test_source_and_target_must_have_real_changed_bytes() -> None:
    doc = _doc("Paragraph.")
    state = start_revision(doc, (_slot("paragraph_0001", "syntax"),))
    with pytest.raises(ValueError, match="changed bytes"):
        accept_edit(state, doc, doc, policy=RevisionPolicy(), operation_ref="fake-change")


def test_local_fingerprint_is_not_a_global_semantic_certification() -> None:
    original, updated = _documents()
    scope = _slot("paragraph_0001", "evidence", AuditScope.LOCAL_NEIGHBORS)
    global_scope = _slot("paragraph_0001", "evidence", AuditScope.DOCUMENT)
    assert scope_fingerprint(original, scope) == scope_fingerprint(updated, scope)
    assert scope_fingerprint(original, global_scope) != scope_fingerprint(updated, global_scope)
