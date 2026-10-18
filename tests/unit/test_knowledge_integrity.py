"""Deterministic, adversarial contracts of Sprint 2 knowledge integrity.

Metadata receipts are deliberately not treated as actual cognitive reading.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from awf.domain.knowledge_integrity import (
    AxisReceipt,
    ChunkReceipt,
    KnowledgeProgress,
    KnowledgeStage,
    SourceInput,
    advance_stage,
    assess_coverage,
    build_manifest,
    preservation_debt,
    retrieval_closure,
)


def sources():
    return (
        SourceInput("core", b"ABCDEFGH", "private:core", dependencies=("foundation",)),
        SourceInput(
            "foundation",
            b"foundation source",
            "private:foundation",
            negative_knowledge=True,
        ),
        SourceInput("rare", b"critical exception", "private:rare", critical=True),
    )


def manifest():
    return build_manifest(
        sources(), version="3.19.1", expected_axes=("truth", "structure"), chunk_bytes=4
    )


def receipts(m):
    return tuple(
        ChunkReceipt(ref.reference_id, chunk.chunk_id, chunk.sha256, "reader-A", "observed")
        for ref in m.sources
        for chunk in ref.chunks
    )


def axes():
    return (AxisReceipt("truth", "evidence-truth"), AxisReceipt("structure", "evidence-structure"))


def test_manifest_real_bytes_and_eof_chunk_boundaries() -> None:
    m = manifest()
    assert len(m.sources) == 3
    assert m.sources[0].byte_length == 8
    assert [(c.offset_start, c.offset_end) for c in m.sources[0].chunks] == [(0, 4), (4, 8)]
    assert m.sources[0].sha256 != m.sources[1].sha256
    assert m.sources[1].negative_knowledge is True


def test_empty_document_still_has_one_explicit_chunk() -> None:
    m = build_manifest(
        (SourceInput("empty", b"", "private:empty"),),
        version="one",
        expected_axes=("truth",),
    )
    assert m.sources[0].chunks[0].offset_start == 0
    assert m.sources[0].chunks[0].offset_end == 0
    assert len(m.sources[0].chunks) == 1


def test_empty_or_duplicate_source_and_axis_inventory_is_rejected() -> None:
    with pytest.raises(ValueError, match="nonempty"):
        build_manifest((), version="v", expected_axes=("x",))
    with pytest.raises(ValueError, match="axes"):
        build_manifest((sources()[0],), version="v", expected_axes=())
    with pytest.raises(ValueError, match="unique"):
        build_manifest((sources()[0], sources()[0]), version="v", expected_axes=("x",))


def test_missing_unknown_and_cyclic_dependencies_rejected() -> None:
    with pytest.raises(ValueError, match="unknown"):
        build_manifest(
            (SourceInput("a", b"a", "ptr", dependencies=("missing",)),),
            version="v",
            expected_axes=("x",),
        )
    with pytest.raises(ValueError, match="cyclic"):
        build_manifest(
            (
                SourceInput("a", b"a", "p1", dependencies=("b",)),
                SourceInput("b", b"b", "p2", dependencies=("a",)),
            ),
            version="v",
            expected_axes=("x",),
        )


def test_missing_receipts_never_count_as_full_read() -> None:
    m = manifest()
    assessed = assess_coverage(m, (), ())
    assert assessed.required_chunks > 0
    assert assessed.accepted_chunks == 0
    assert assessed.missing_chunks
    assert assessed.missing_axes == ("structure", "truth")
    assert assessed.complete is False


def test_exact_receipts_cover_every_chunk_and_axis() -> None:
    m = manifest()
    assessed = assess_coverage(m, receipts(m), axes())
    assert assessed.complete is True
    assert assessed.required_chunks == assessed.accepted_chunks
    assert assessed.invalid_receipts == ()


def test_wrong_hash_unknown_id_duplicate_receipt_rejected() -> None:
    m = manifest()
    good = receipts(m)
    forged = replace(good[0], sha256="0" * 64)
    unknown = replace(good[0], reference_id="missing")
    assert not assess_coverage(m, (forged,) + good[1:], axes()).complete
    assert not assess_coverage(m, good + (good[0],), axes()).complete
    assert not assess_coverage(m, good + (unknown,), axes()).complete


def test_missing_and_duplicate_axes_prevent_pass() -> None:
    m = manifest()
    assert not assess_coverage(m, receipts(m), (axes()[0],)).complete
    assert not assess_coverage(m, receipts(m), axes() + (axes()[0],)).complete
    assert not assess_coverage(
        m, receipts(m), axes() + (AxisReceipt("invented", "evidence"),)
    ).complete


def test_mismatched_source_bytes_invalidate_all_old_receipts() -> None:
    old = manifest()
    updated_sources = (
        replace(sources()[0], original_bytes=b"ABCDEFGX"),
        sources()[1],
        sources()[2],
    )
    changed = build_manifest(
        updated_sources,
        version="3.19.2",
        expected_axes=old.expected_axes,
        chunk_bytes=4,
    )
    assessed = assess_coverage(changed, receipts(old), axes())
    assert not assessed.complete
    assert any(x.startswith("invalid:core:") for x in assessed.invalid_receipts)


def test_claim_stages_cannot_be_conflated_or_skipped() -> None:
    current = KnowledgeProgress(reference_id="core")
    current = advance_stage(
        current,
        stage=KnowledgeStage.AVAILABLE,
        evidence_ref="manifest-source",
        context_ref="run-1",
    )
    with pytest.raises(ValueError, match="READ requires"):
        advance_stage(
            current,
            stage=KnowledgeStage.READ,
            evidence_ref="just-a-summary",
            context_ref="run-1",
        )
    current = advance_stage(
        current,
        stage=KnowledgeStage.READ,
        evidence_ref="full-receipt",
        context_ref="run-1",
        complete_chunk_coverage=True,
    )
    with pytest.raises(ValueError, match="UNDERSTOOD requires"):
        advance_stage(
            current,
            stage=KnowledgeStage.UNDERSTOOD,
            evidence_ref="summary",
            context_ref="run-1",
        )
    current = advance_stage(
        current,
        stage=KnowledgeStage.UNDERSTOOD,
        evidence_ref="calibration:reviewed",
        context_ref="run-1",
        challenge_adjudicated=True,
    )
    with pytest.raises(ValueError, match="scope applicability"):
        advance_stage(
            current,
            stage=KnowledgeStage.APPLICABLE,
            evidence_ref="keyword-match",
            context_ref="run-1",
        )
    current = advance_stage(
        current,
        stage=KnowledgeStage.APPLICABLE,
        evidence_ref="scope-assessment",
        context_ref="run-1",
        applicability_adjudicated=True,
    )
    current = advance_stage(
        current,
        stage=KnowledgeStage.APPLIED,
        evidence_ref="applied-operation",
        context_ref="run-1",
    )
    current = advance_stage(
        current,
        stage=KnowledgeStage.VERIFIED,
        evidence_ref="external-verifier",
        context_ref="run-1",
    )
    assert [claim.stage for claim in current.claims] == list(KnowledgeStage)
    with pytest.raises(ValueError, match="skipped"):
        advance_stage(
            current,
            stage=KnowledgeStage.VERIFIED,
            evidence_ref="repeat",
            context_ref="run-1",
        )


def test_preservation_detects_removed_and_changed_negative_knowledge() -> None:
    initial = manifest()
    new = build_manifest(
        (sources()[0], replace(sources()[1], original_bytes=b"edited")),
        version="new",
        expected_axes=initial.expected_axes,
        chunk_bytes=4,
    )
    assert preservation_debt(initial, new) == ("changed:foundation", "removed:rare")
    assert preservation_debt(initial, initial) == ()


def test_retrieval_preserves_dependencies_and_rare_critical_exception() -> None:
    m = manifest()
    result = retrieval_closure(m, {"core"})
    assert result == ("foundation", "core", "rare")
    with pytest.raises(ValueError, match="unknown"):
        retrieval_closure(m, {"not-present"})


def test_missing_source_pointer_refused() -> None:
    with pytest.raises(ValueError, match="pointer"):
        build_manifest(
            (SourceInput("core", b"x", ""),),
            version="v",
            expected_axes=("x",),
        )
