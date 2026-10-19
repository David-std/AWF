"""No examples-as-templates, accidental rule pruning, or token-only release PASS."""

from __future__ import annotations

import pytest

from awf.domain.knowledge_integrity import (
    AxisReceipt,
    ChunkReceipt,
    SourceInput,
    assess_coverage,
    build_manifest,
)
from awf.knowledge.calibration_gate import (
    CalibrationCase,
    CalibrationJudgment,
    CaseKind,
    Verdict,
)
from awf.knowledge.usage_policy import (
    KnowledgeCard,
    KnowledgeMaterial,
    MaterialUse,
    ReleaseEvidence,
    assess_release_metrics,
    build_runtime_card,
    operation_readiness_debt,
)


def manifest():
    return build_manifest(
        (
            SourceInput("main", b"RULES", "local:main", dependencies=("foundation",)),
            SourceInput("foundation", b"FULL", "local:foundation", negative_knowledge=True),
            SourceInput("exception", b"RARE", "local:exception", critical=True),
        ),
        version="1",
        expected_axes=("fidelity",),
    )


def test_reversible_card_expands_critical_and_dependency_sources() -> None:
    card = KnowledgeCard(
        "critical-rule",
        ("main",),
        KnowledgeMaterial.PRINCIPLE,
        MaterialUse.PRINCIPLE_BOUNDARY,
        "expert-reviewed",
    )
    resolved = build_runtime_card(manifest(), card)
    assert resolved["source_ids"] == ["exception", "foundation", "main"]
    assert resolved["evidence_pointers"] == {
        "exception": "local:exception",
        "foundation": "local:foundation",
        "main": "local:main",
    }


@pytest.mark.parametrize("material", list(KnowledgeMaterial))
def test_no_style_template_for_any_kind_of_research_material(
    material: KnowledgeMaterial,
) -> None:
    card = KnowledgeCard(
        "style-copy",
        ("main",),
        material,
        MaterialUse.STYLE_TEMPLATE,
        "some-review",
    )
    with pytest.raises(ValueError, match="style templates"):
        build_runtime_card(manifest(), card)


def test_human_control_only_calibrates_legitimate_variation() -> None:
    bad = KnowledgeCard(
        "human",
        ("main",),
        KnowledgeMaterial.HUMAN_CONTROL,
        MaterialUse.PRINCIPLE_BOUNDARY,
        "review",
    )
    with pytest.raises(ValueError, match="human controls"):
        build_runtime_card(manifest(), bad)
    good = KnowledgeCard(
        "human",
        ("main",),
        KnowledgeMaterial.HUMAN_CONTROL,
        MaterialUse.FALSE_POSITIVE_CALIBRATION,
        "review",
    )
    assert build_runtime_card(manifest(), good)["material"] == "HUMAN_CONTROL"


def test_training_never_authorized_by_source_coverage() -> None:
    card = KnowledgeCard(
        "improper-training",
        ("main",),
        KnowledgeMaterial.EXAMPLE,
        MaterialUse.TRAINING_EXAMPLE,
        "review",
    )
    with pytest.raises(ValueError, match="dataset rights"):
        build_runtime_card(manifest(), card)


def test_operation_requires_full_coverage_and_all_challenge_families() -> None:
    m = manifest()
    refs = tuple(
        ChunkReceipt(r.reference_id, c.chunk_id, c.sha256, "reader", "receipt")
        for r in m.sources
        for c in r.chunks
    )
    full = assess_coverage(m, refs, (AxisReceipt("fidelity", "evidence"),))
    missing = assess_coverage(m, (), ())
    cases = tuple(
        CalibrationCase(f"c{n}", "op", kind, f"prompt{n}", f"answer{n}")
        for n, kind in enumerate(CaseKind)
    )
    judgments = tuple(
        CalibrationJudgment(c.case_id, Verdict.PASSED, "expert", "evidence") for c in cases
    )
    assert "missing_canonical_read_coverage" in operation_readiness_debt(
        operation_id="op",
        coverage=missing,
        cases=cases,
        judgments=judgments,
    )
    assert (
        operation_readiness_debt(
            operation_id="op",
            coverage=full,
            cases=cases,
            judgments=judgments,
        )
        == ()
    )
    # The empty debt is a metadata-gate result, not proof the model understands rules.


def test_token_savings_not_equated_to_execution_fidelity() -> None:
    report = assess_release_metrics(
        ReleaseEvidence(
            baseline_tokens=2000,
            runtime_tokens=50,
            required_invariants=("citation", "scope", "causality"),
            verified_invariants=("citation",),
            fidelity_evidence_refs=(),
        )
    )
    assert report["token_savings_fraction"] > 0.9
    assert report["execution_fidelity_coverage"] < 0.5
    assert report["missing_invariants"] == ["causality", "scope"]
    assert report["fidelity_evidence_present"] is False
    assert report["semantic_quality_independently_proven"] is False


def test_zero_denominator_or_unknown_verification_disallowed() -> None:
    with pytest.raises(ValueError, match="token counts"):
        assess_release_metrics(ReleaseEvidence(0, 0, ("x",), ("x",), ("proof",)))
    with pytest.raises(ValueError, match="invariant"):
        assess_release_metrics(ReleaseEvidence(10, 1, (), (), ()))
