"""Verify dependency inversion and source-reader substitutability in Sprint 2."""

from __future__ import annotations

import ast
from pathlib import Path

from awf.application.commands.compile_knowledge import import_knowledge
from awf.application.dto import LoadedKnowledgeSource
from awf.domain.knowledge import Disposition


class FakeSource:
    def load(
        self, *, archive_path: Path, manifest_path: Path, source_id: str
    ) -> LoadedKnowledgeSource:
        assert archive_path.name == "private.zip"
        assert manifest_path.name == "manifest.json"
        return LoadedKnowledgeSource(
            source_id=source_id,
            archive_sha256="a" * 64,
            suite_version="3.19.1",
            rows=(
                {
                    "id": "DSR-001",
                    "domain": "audit",
                    "priority": "MUST",
                    "requirement": "Preserve immutable source lineage.",
                    "source_ids": ["deep-1"],
                },
            ),
        )


class FakeReview:
    def load(self, path: Path, *, expected_source_sha256: str) -> dict[str, dict[str, object]]:
        assert path.name == "review.json"
        assert expected_source_sha256 == "a" * 64
        return {
            "DSR-001": {
                "disposition": "KEEP_AS_CODE",
                "reviewer": "An independent reviewer",
                "reason": "Hash-bound source lineage can be verified mechanically.",
            }
        }


def test_command_uses_interchangeable_ports_not_zip_reader() -> None:
    result = import_knowledge(
        archive_path=Path("private.zip"),
        manifest_path=Path("manifest.json"),
        archive_reader=FakeSource(),
        review_path=Path("review.json"),
        review_reader=FakeReview(),
    )
    assert result.records[0].disposition == Disposition.KEEP_AS_CODE
    assert result.records[0].review_status == "REVIEW_ATTESTED"


def test_application_layer_never_imports_adapters() -> None:
    project = Path(__file__).resolve().parents[2] / "src" / "awf" / "application"
    for path in project.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("awf.adapters"), str(path)
            if isinstance(node, ast.Import):
                assert all(not a.name.startswith("awf.adapters") for a in node.names), str(path)
