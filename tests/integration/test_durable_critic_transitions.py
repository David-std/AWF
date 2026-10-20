"""Synthetic, adversarial recovery for critic/external-cycle journal transitions.

Local evidence identities and declared isolation are *not* scientific validation.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_revision import RevisionConflictError, SQLiteRevisionJournal
from awf.application.commands.bind_evidence import event_reference
from awf.domain.evidence import EvidenceIntegrityError, EvidenceKind
from awf.domain.revision_audit import (
    AuditSlot,
    AuditStatus,
    RevisionPolicy,
    RevisionVerdict,
    decision,
)


def _document(text: str = "Cited claim."):
    return MarkdownAdapter().parse(f"# Study\n\n{text}\n".encode(), source_name="fixture.md")


def _setup(tmp_path: Path, *, audited: bool = True):
    journal = SQLiteRevisionJournal(tmp_path / "critic.sqlite")
    journal.initialize()
    document = _document()
    slot = AuditSlot(document.blocks[1].block_id, "citations", 2)
    journal.create(
        revision_id="revision-a",
        operation_id="start",
        run_id="run-a",
        document=document,
        slots=(slot,),
    )
    if audited:
        journal.record_audit(
            revision_id="revision-a",
            operation_id="audit",
            run_id="run-a",
            document=document,
            expected_version=0,
            slot_key=slot.key,
            status=AuditStatus.CLEAN,
            checks_executed=2,
            observation_ref="fixture:complete-audit",
        )
    return journal, document


def _evidence(
    journal: SQLiteRevisionJournal,
    kind: EvidenceKind,
    *,
    run_id: str = "run-a",
    subject_id: str = "revision-a",
    marker: str = "fixture",
) -> str:
    event = journal.ledger.append(
        kind=kind, run_id=run_id, subject_id=subject_id, content=marker.encode()
    )
    return event_reference(event)


def _sweep(
    journal: SQLiteRevisionJournal,
    document,
    *,
    version: int = 1,
    operation_id: str = "sweep-1",
    critic: str = "critic-1",
    context: str | None = None,
    observation: str | None = None,
    policy: RevisionPolicy | None = None,
    inherited: bool = False,
):
    if context is None:
        context = _evidence(journal, EvidenceKind.CRITIC_CONTEXT, marker=operation_id + ":context")
    if observation is None:
        observation = _evidence(
            journal, EvidenceKind.CRITIC_OBSERVATION, marker=operation_id + ":observation"
        )
    return journal.record_clean_sweep(
        revision_id="revision-a",
        operation_id=operation_id,
        run_id="run-a",
        document=document,
        expected_version=version,
        policy=policy or RevisionPolicy(),
        critic_id=critic,
        isolated_context_ref=context,
        observation_ref=observation,
        inherited_diagnosis=inherited,
    )


def _external(
    journal: SQLiteRevisionJournal,
    *,
    version: int = 1,
    operation_id: str = "external-1",
    observation: str | None = None,
    policy: RevisionPolicy | None = None,
):
    if observation is None:
        observation = _evidence(
            journal,
            EvidenceKind.EXTERNAL_ITERATION_OBSERVATION,
            marker=operation_id + ":observation",
        )
    return journal.record_external_iteration(
        revision_id="revision-a",
        operation_id=operation_id,
        run_id="run-a",
        expected_version=version,
        policy=policy or RevisionPolicy(),
        observation_ref=observation,
    )


def _assert_unchanged(journal: SQLiteRevisionJournal, version: int, event_count: int) -> None:
    assert journal.load(revision_id="revision-a").version == version
    assert journal.ledger.verify().events_checked == event_count


def test_two_distinct_clean_sweeps_survive_restart_and_converge_locally(tmp_path: Path) -> None:
    journal, document = _setup(tmp_path)
    first = _sweep(journal, document)
    assert first.version == 2 and len(first.state.clean_sweeps) == 1
    assert first.state.clean_sweeps[0].evidence_ref.startswith("event:")
    assert decision(first.state, document) == RevisionVerdict.FRESH_CRITIC_REQUIRED
    second = _sweep(journal, document, version=2, operation_id="sweep-2", critic="critic-2")
    assert second.version == 3 and len(second.state.clean_sweeps) == 2
    assert decision(second.state, document) == RevisionVerdict.CONVERGED
    fresh = SQLiteRevisionJournal(journal.ledger.database)
    assert fresh.load(revision_id="revision-a").state == second.state
    assert fresh.verify_all_revisions()[1] == 1
    assert journal.ledger.verify().events_checked == 11


def test_external_iteration_survives_restart_and_retry_is_idempotent(tmp_path: Path) -> None:
    journal, _ = _setup(tmp_path)
    evidence = _evidence(journal, EvidenceKind.EXTERNAL_ITERATION_OBSERVATION)
    first = _external(journal, observation=evidence)
    assert first.version == 2 and first.state.external_iterations == 1
    assert first.state.event_log[-1].startswith("EXTERNAL_ITERATION:event:")
    before = journal.ledger.verify().events_checked
    retry = _external(journal, observation=evidence)
    assert retry.replayed and retry.state == first.state
    assert journal.ledger.verify().events_checked == before
    assert (
        SQLiteRevisionJournal(journal.ledger.database).load(revision_id="revision-a").state
        == first.state
    )
    with pytest.raises(RevisionConflictError, match="different input"):
        _external(journal, observation="event:" + "0" * 64)
    _assert_unchanged(journal, 2, before)


def test_clean_sweep_lost_response_replays_same_commit_after_later_version(
    tmp_path: Path,
) -> None:
    journal, document = _setup(tmp_path)
    context = _evidence(journal, EvidenceKind.CRITIC_CONTEXT)
    observation = _evidence(journal, EvidenceKind.CRITIC_OBSERVATION)
    original = _sweep(journal, document, context=context, observation=observation)
    _external(journal, version=2)
    before = journal.ledger.verify().events_checked
    retry = _sweep(journal, document, context=context, observation=observation)
    assert retry.replayed and retry.version == original.version
    assert retry.state == original.state
    assert journal.load(revision_id="revision-a").version == 3
    assert journal.ledger.verify().events_checked == before


@pytest.mark.parametrize(
    ("kind", "changed"),
    [
        (EvidenceKind.CRITIC_OBSERVATION, "run"),
        (EvidenceKind.CRITIC_OBSERVATION, "subject"),
        (EvidenceKind.AUDIT_RECEIPT, "kind"),
        (EvidenceKind.EXTERNAL_ITERATION_OBSERVATION, "run"),
        (EvidenceKind.EXTERNAL_ITERATION_OBSERVATION, "subject"),
        (EvidenceKind.CRITIC_OBSERVATION, "external-kind"),
    ],
)
def test_foreign_evidence_rejected_atomically(
    tmp_path: Path, kind: EvidenceKind, changed: str
) -> None:
    journal, document = _setup(tmp_path)
    evidence = _evidence(
        journal,
        kind,
        run_id="wrong-run" if changed == "run" else "run-a",
        subject_id="wrong-revision" if changed == "subject" else "revision-a",
    )
    before = journal.ledger.verify().events_checked
    with pytest.raises(EvidenceIntegrityError, match="identity or age"):
        if changed in {"external-kind"} or kind == EvidenceKind.EXTERNAL_ITERATION_OBSERVATION:
            journal.record_external_iteration(
                revision_id="revision-a",
                operation_id="external-invalid",
                run_id="run-a",
                expected_version=1,
                policy=RevisionPolicy(),
                observation_ref=evidence,
            )
        else:
            _sweep(
                journal,
                document,
                observation=evidence if kind == EvidenceKind.CRITIC_OBSERVATION else None,
                context=evidence if changed == "kind" else None,
            )
    # Helper-created counter-evidence is retained, but the failed intent/commit is absent.
    _assert_unchanged(journal, 1, journal.ledger.verify().events_checked)
    assert journal.ledger.verify().events_checked >= before


def test_missing_and_preceding_revision_evidence_rejected(tmp_path: Path) -> None:
    journal, document = _setup(tmp_path)
    context = _evidence(journal, EvidenceKind.CRITIC_CONTEXT)
    bad = "event:" + "0" * 64
    before = journal.ledger.verify().events_checked
    with pytest.raises(EvidenceIntegrityError, match="missing evidence"):
        _sweep(journal, document, context=context, observation=bad)
    _assert_unchanged(journal, 1, before)

    observation = _evidence(journal, EvidenceKind.CRITIC_OBSERVATION)
    _sweep(journal, document, context=context, observation=observation)
    fresh_context = _evidence(journal, EvidenceKind.CRITIC_CONTEXT, marker="fresh-context")
    new_before = journal.ledger.verify().events_checked
    with pytest.raises(EvidenceIntegrityError, match="identity or age"):
        _sweep(
            journal,
            document,
            version=2,
            critic="critic-2",
            operation_id="sweep-old-evidence",
            context=fresh_context,
            observation=observation,
        )
    _assert_unchanged(journal, 2, new_before)


def test_critic_identity_and_context_cannot_be_reused(tmp_path: Path) -> None:
    journal, document = _setup(tmp_path)
    first = _sweep(journal, document)
    first_context = first.state.clean_sweeps[0].isolated_context_ref
    with pytest.raises(ValueError, match="duplicate critic identity"):
        _sweep(journal, document, version=2, operation_id="duplicate")
    with pytest.raises(EvidenceIntegrityError, match="identity or age"):
        _sweep(
            journal,
            document,
            version=2,
            operation_id="old-context",
            critic="critic-2",
            context=first_context,
        )
    assert journal.load(revision_id="revision-a").version == 2


def test_inherited_diagnosis_and_wrong_document_rejected(tmp_path: Path) -> None:
    journal, document = _setup(tmp_path)
    with pytest.raises(ValueError, match="isolated context"):
        _sweep(journal, document, inherited=True)
    with pytest.raises(ValueError, match="bound"):
        _sweep(journal, _document("Replaced manuscript."), operation_id="wrong-doc")
    assert journal.load(revision_id="revision-a").version == 1


def test_dirty_audit_and_material_finding_block_sweeps(tmp_path: Path) -> None:
    dirty, document = _setup(tmp_path / "dirty", audited=False)
    with pytest.raises(ValueError, match="requires complete current audits"):
        _sweep(dirty, document, version=0)
    assert dirty.load(revision_id="revision-a").version == 0
    journal, document = _setup(tmp_path / "open")
    journal.open_finding(
        revision_id="revision-a",
        operation_id="issue",
        run_id="run-a",
        expected_version=1,
        finding_id="missing-source",
        material=True,
        observation_ref="fixture:material-finding",
    )
    with pytest.raises(ValueError, match="requires complete current audits"):
        _sweep(journal, document, version=2)
    assert journal.load(revision_id="revision-a").version == 2


def test_budget_exhaustion_prevents_new_sweeps_and_external_iterations(tmp_path: Path) -> None:
    journal, document = _setup(tmp_path)
    policy = RevisionPolicy(max_external_iterations=1)
    _external(journal, policy=policy)
    with pytest.raises(ValueError, match="budget exhausted"):
        _external(journal, version=2, operation_id="external-2", policy=policy)
    with pytest.raises(ValueError, match="requires complete current audits"):
        _sweep(journal, document, version=2, policy=policy)
    assert journal.load(revision_id="revision-a").version == 2


def test_stale_version_and_reused_operation_key_fail_closed(tmp_path: Path) -> None:
    journal, document = _setup(tmp_path)
    _sweep(journal, document)
    with pytest.raises(RevisionConflictError, match="stale"):
        _external(journal, version=1)
    with pytest.raises(RevisionConflictError, match="different input"):
        _sweep(journal, document, version=2, operation_id="sweep-1", critic="another")
    assert journal.load(revision_id="revision-a").version == 2


def test_concurrent_writers_commit_only_one_version(tmp_path: Path) -> None:
    journal, _ = _setup(tmp_path)
    evidence = _evidence(journal, EvidenceKind.EXTERNAL_ITERATION_OBSERVATION)

    def worker(key: str):
        return _external(journal, version=1, operation_id=key, observation=evidence)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(worker_result, (lambda: worker("worker-a"), lambda: worker("worker-b")))
        )
    assert sorted(outcome[0] for outcome in outcomes) == ["conflict", "success"]
    assert journal.load(revision_id="revision-a").version == 2


def worker_result(fn):
    try:
        return "success", fn()
    except RevisionConflictError:
        return "conflict", None


def test_failed_commit_rolls_back_intent_and_new_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, _ = _setup(tmp_path)
    evidence = _evidence(journal, EvidenceKind.EXTERNAL_ITERATION_OBSERVATION)
    before = journal.ledger.verify().events_checked

    def injected_failure(*_args, **_kwargs):
        raise RuntimeError("synthetic commit interruption")

    with monkeypatch.context() as patch:
        patch.setattr(journal, "_commit", injected_failure)
        with pytest.raises(RuntimeError, match="interruption"):
            _external(journal, observation=evidence)
    _assert_unchanged(journal, 1, before)
    committed = _external(journal, observation=evidence)
    assert committed.version == 2


def test_tampered_intent_detected_at_recovery_even_with_consistent_ledger_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal, _ = _setup(tmp_path)
    _external(journal)
    original = journal._check_intent_link

    def reject_bound_proof(*args, **kwargs):
        original(*args, **kwargs)
        raise EvidenceIntegrityError("synthetic independent replay rejection")

    monkeypatch.setattr(journal, "_check_intent_link", reject_bound_proof)
    with pytest.raises(EvidenceIntegrityError, match="synthetic independent"):
        journal.load(revision_id="revision-a")


def test_external_evidence_fingerprint_is_in_committed_intent(tmp_path: Path) -> None:
    journal, _ = _setup(tmp_path)
    ref = _evidence(journal, EvidenceKind.EXTERNAL_ITERATION_OBSERVATION)
    state = _external(journal, observation=ref)
    digest = state.state.event_log[-1].split("EXTERNAL_ITERATION:", 1)[1][6:]
    event, content = journal.ledger.resolve_event(event_digest=digest)
    assert event.kind == EvidenceKind.REVISION_TRANSITION
    payload = json.loads(content)
    assert payload["operation_kind"] == "EXTERNAL_ITERATION"
    assert payload["details"]["observation_ref"] == ref
