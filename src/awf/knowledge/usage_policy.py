"""Conservative evidence-pointer and example-use policy.

This is a structural boundary. It does not determine a manuscript's author,
assess originality, validate scientific claims, or independently audit models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from awf.domain.knowledge_integrity import (
    CanonicalManifest,
    CoverageAssessment,
    retrieval_closure,
)
from awf.knowledge.calibration_gate import (
    CalibrationCase,
    CalibrationJudgment,
    calibration_debt,
)


class KnowledgeMaterial(StrEnum):
    PRINCIPLE = "PRINCIPLE"
    HUMAN_CONTROL = "HUMAN_CONTROL"
    EXAMPLE = "EXAMPLE"
    NEGATIVE_EVIDENCE = "NEGATIVE_EVIDENCE"


class MaterialUse(StrEnum):
    PRINCIPLE_BOUNDARY = "PRINCIPLE_BOUNDARY"
    FALSE_POSITIVE_CALIBRATION = "FALSE_POSITIVE_CALIBRATION"
    STYLE_TEMPLATE = "STYLE_TEMPLATE"
    TRAINING_EXAMPLE = "TRAINING_EXAMPLE"


@dataclass(frozen=True, slots=True)
class KnowledgeCard:
    card_id: str
    primary_sources: tuple[str, ...]
    material: KnowledgeMaterial
    intended_use: MaterialUse
    review_evidence_ref: str


def build_runtime_card(
    manifest: CanonicalManifest,
    card: KnowledgeCard,
) -> dict[str, object]:
    """Require reversible source pointers and expand dependencies automatically."""
    if not card.card_id.strip() or not card.primary_sources or not card.review_evidence_ref.strip():
        raise ValueError("runtime card needs identifier, sources and review evidence")
    if card.intended_use == MaterialUse.STYLE_TEMPLATE:
        raise ValueError("source or human-control examples cannot become style templates")
    if card.intended_use == MaterialUse.TRAINING_EXAMPLE:
        raise ValueError("training requires separate dataset rights and approval")
    if card.material == KnowledgeMaterial.HUMAN_CONTROL and (
        card.intended_use != MaterialUse.FALSE_POSITIVE_CALIBRATION
    ):
        raise ValueError("human controls may only calibrate legitimate variation")
    resolved_ids = retrieval_closure(manifest, set(card.primary_sources))
    sources = {ref.reference_id: ref for ref in manifest.sources}
    return {
        "card_id": card.card_id,
        "source_ids": list(resolved_ids),
        "evidence_pointers": {
            identifier: sources[identifier].evidence_pointer for identifier in resolved_ids
        },
        "material": card.material.value,
        "intended_use": card.intended_use.value,
        "review_evidence_ref": card.review_evidence_ref,
        "no_authority_inferred_from_retrieval": True,
    }


def operation_readiness_debt(
    *,
    operation_id: str,
    coverage: CoverageAssessment,
    cases: tuple[CalibrationCase, ...],
    judgments: tuple[CalibrationJudgment, ...],
) -> tuple[str, ...]:
    """High-impact operation: incomplete reads or uncalibrated boundaries block review."""
    failures: list[str] = []
    if not operation_id.strip():
        failures.append("missing_operation")
    if not coverage.complete:
        failures.append("missing_canonical_read_coverage")
    failures.extend(calibration_debt(cases, judgments, operation_id=operation_id))
    return tuple(sorted(set(failures)))


@dataclass(frozen=True, slots=True)
class ReleaseEvidence:
    """Efficiency and execution fidelity are independent quantities."""

    baseline_tokens: int
    runtime_tokens: int
    required_invariants: tuple[str, ...]
    verified_invariants: tuple[str, ...]
    fidelity_evidence_refs: tuple[str, ...]


def assess_release_metrics(values: ReleaseEvidence) -> dict[str, object]:
    """Never certify quality merely because a smaller packet is cheaper."""
    if values.baseline_tokens < 1 or values.runtime_tokens < 0:
        raise ValueError("token counts must be valid")
    if not values.required_invariants or len(set(values.required_invariants)) != len(
        values.required_invariants
    ):
        raise ValueError("explicit nonempty invariant inventory required")
    missing = sorted(set(values.required_invariants) - set(values.verified_invariants))
    unexpected = sorted(set(values.verified_invariants) - set(values.required_invariants))
    return {
        "token_savings_fraction": (values.baseline_tokens - values.runtime_tokens)
        / values.baseline_tokens,
        "execution_fidelity_coverage": (
            len(set(values.verified_invariants) & set(values.required_invariants))
            / len(values.required_invariants)
        ),
        "missing_invariants": missing,
        "unexpected_verifications": unexpected,
        "fidelity_evidence_present": bool(values.fidelity_evidence_refs)
        and all(ref.strip() for ref in values.fidelity_evidence_refs),
        "semantic_quality_independently_proven": False,
    }
