"""Answer-key-free challenge packets and evidence-bound calibration judgments.

A pass is a recorded adjudication with an external reference, not an
independent claim that a model understands the topic or performs well.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CaseKind(StrEnum):
    POSITIVE = "POSITIVE"
    NEAR_MISS = "NEAR_MISS"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    HOLDOUT = "HOLDOUT"


class Verdict(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    case_id: str
    operation_id: str
    kind: CaseKind
    prompt_ref: str
    answer_key_ref: str


@dataclass(frozen=True, slots=True)
class CalibrationJudgment:
    case_id: str
    verdict: Verdict
    evaluator_ref: str
    evidence_ref: str


def challenge_packet(cases: tuple[CalibrationCase, ...], *, operation_id: str) -> dict[str, object]:
    """Return challenge metadata without reference answers or evaluator decisions."""
    selected = [case for case in cases if case.operation_id == operation_id]
    if not selected:
        raise ValueError("operation has no registered challenge cases")
    if len({case.case_id for case in selected}) != len(selected):
        raise ValueError("duplicate challenge case identifiers")
    if any(
        not case.prompt_ref.strip()
        or not case.answer_key_ref.strip()
        or case.prompt_ref == case.answer_key_ref
        for case in selected
    ):
        raise ValueError("challenge requires separate prompt and private answer references")
    return {
        "schema_version": "1.0.0",
        "operation_id": operation_id,
        "cases": [
            {"case_id": case.case_id, "kind": case.kind.value, "prompt_ref": case.prompt_ref}
            for case in sorted(selected, key=lambda c: c.case_id)
        ],
        "answer_keys_disclosed": False,
    }


def calibration_debt(
    cases: tuple[CalibrationCase, ...],
    judgments: tuple[CalibrationJudgment, ...],
    *,
    operation_id: str,
) -> tuple[str, ...]:
    """Require all four case families and resolved, separately adjudicated verdicts."""
    selected = {c.case_id: c for c in cases if c.operation_id == operation_id}
    relevant = [j for j in judgments if j.case_id in selected]
    errors: list[str] = []
    if len(selected) != len([c for c in cases if c.operation_id == operation_id]):
        errors.append("duplicate_case_id")
    for kind in CaseKind:
        if not any(c.kind == kind for c in selected.values()):
            errors.append(f"missing_case_family:{kind.value}")
    seen: set[str] = set()
    for item in relevant:
        if item.case_id in seen:
            errors.append(f"duplicate_judgment:{item.case_id}")
        seen.add(item.case_id)
        if not isinstance(item.verdict, Verdict) or item.verdict != Verdict.PASSED:
            errors.append(f"not_passed:{item.case_id}")
        if not item.evaluator_ref.strip() or not item.evidence_ref.strip():
            errors.append(f"missing_adjudication:{item.case_id}")
    for case_id in selected.keys() - seen:
        errors.append(f"unreviewed:{case_id}")
    if any(j.case_id not in selected for j in judgments):
        errors.append("unknown_judgment_case")
    return tuple(sorted(set(errors)))
