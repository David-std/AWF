"""Calibration cases are data contracts, not detector-score manipulation recipes."""

from __future__ import annotations

import pytest

from awf.knowledge.calibration_gate import (
    CalibrationCase,
    CalibrationJudgment,
    CaseKind,
    Verdict,
    calibration_debt,
    challenge_packet,
)


def cases():
    return tuple(
        CalibrationCase(
            f"K-{index}",
            "preserve_causality",
            kind,
            f"private-prompt-{index}",
            f"private-answer-{index}",
        )
        for index, kind in enumerate(CaseKind)
    )


def results():
    return tuple(
        CalibrationJudgment(case.case_id, Verdict.PASSED, "external-reviewer", "evidence-ref")
        for case in cases()
    )


def test_challenge_packet_includes_all_case_kinds_without_answers() -> None:
    packet = challenge_packet(cases(), operation_id="preserve_causality")
    assert packet["answer_keys_disclosed"] is False
    assert len(packet["cases"]) == 4
    assert all("answer" not in row for row in packet["cases"])
    assert "private-answer" not in str(packet)
    assert {row["kind"] for row in packet["cases"]} == {kind.value for kind in CaseKind}


def test_missing_families_cannot_be_marked_calibrated() -> None:
    c = cases()[:-1]
    errors = calibration_debt(c, results()[:-1], operation_id="preserve_causality")
    assert "missing_case_family:HOLDOUT" in errors


def test_positive_is_not_sufficient_without_hard_negative_and_holdout() -> None:
    c = cases()
    errors = calibration_debt(
        c,
        (CalibrationJudgment(c[0].case_id, Verdict.PASSED, "reviewer", "proof"),),
        operation_id="preserve_causality",
    )
    assert len(errors) == 3
    assert all(x.startswith("unreviewed:") for x in errors)


def test_failed_unresolved_or_missing_evidence_blocks() -> None:
    c = cases()
    for judgment in [
        CalibrationJudgment(c[2].case_id, Verdict.FAILED, "reviewer", "proof"),
        CalibrationJudgment(c[2].case_id, Verdict.UNRESOLVED, "reviewer", "proof"),
        CalibrationJudgment(c[2].case_id, Verdict.PASSED, "", ""),
    ]:
        updated = tuple(judgment if x.case_id == judgment.case_id else x for x in results())
        assert calibration_debt(c, updated, operation_id="preserve_causality")


def test_unreviewed_judgments_never_pass() -> None:
    assert calibration_debt(cases(), (), operation_id="preserve_causality")


def test_exactly_adjudicated_cases_clear_only_structural_debt() -> None:
    assert calibration_debt(cases(), results(), operation_id="preserve_causality") == ()


def test_duplicate_cases_or_judgments_rejected() -> None:
    assert "duplicate_case_id" in calibration_debt(
        cases() + (cases()[0],), results(), operation_id="preserve_causality"
    )
    assert any(
        err.startswith("duplicate_judgment:")
        for err in calibration_debt(
            cases(), results() + (results()[0],), operation_id="preserve_causality"
        )
    )
    with pytest.raises(ValueError, match="duplicate"):
        challenge_packet(cases() + (cases()[0],), operation_id="preserve_causality")


def test_prompt_and_answer_key_cannot_share_pointer() -> None:
    bad = CalibrationCase("case", "op", CaseKind.HOLDOUT, "same", "same")
    with pytest.raises(ValueError, match="separate"):
        challenge_packet((bad,), operation_id="op")


def test_foreign_judgment_does_not_authenticate_operation() -> None:
    alien = CalibrationJudgment("other-case", Verdict.PASSED, "reviewer", "proof")
    assert "unknown_judgment_case" in calibration_debt(
        cases(), results() + (alien,), operation_id="preserve_causality"
    )
