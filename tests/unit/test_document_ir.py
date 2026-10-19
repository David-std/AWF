"""DocumentIR invariants and byte-addressed identities."""

from __future__ import annotations

import hashlib

import pytest

from awf.adapters.document.markdown_adapter import MarkdownAdapter, MarkdownParseError
from awf.domain.document import BlockKind, DocumentBlock, DocumentIR


def test_document_metadata_is_sha256_of_original_bytes() -> None:
    raw = b"# Title\r\n\r\nParagraph one.\r\n"
    document = MarkdownAdapter().parse(raw, source_name="draft.md")
    assert document.sha256 == hashlib.sha256(raw).hexdigest()
    assert document.byte_length == len(raw)
    assert document.document_id == f"doc_{document.sha256}"
    assert document.blocks[0].kind == BlockKind.HEADING
    assert document.blocks[1].text == "Paragraph one."
    assert document.to_dict()["schema_version"] == "1.0.0"


def test_code_fence_keeps_internal_headings_as_code() -> None:
    raw = b"# Main\n\n```python\n# not a heading\n\nprint(1)\n```\n"
    doc = MarkdownAdapter().parse(raw, source_name="x.md")
    assert [b.kind for b in doc.blocks] == [BlockKind.HEADING, BlockKind.FENCED_CODE]
    assert doc.blocks[1].start_line == 3
    assert doc.blocks[1].end_line == 7


@pytest.mark.parametrize("raw", [b"\xff\xfe", b"abc\x00def", b"```python\nunclosed"])
def test_invalid_markdown_rejected(raw: bytes) -> None:
    with pytest.raises(MarkdownParseError):
        MarkdownAdapter().parse(raw, source_name="x.md")


def test_utf8_bom_is_recognized_without_changing_hash() -> None:
    raw = b"\xef\xbb\xbf# H\n"
    doc = MarkdownAdapter().parse(raw, source_name="x.md")
    assert doc.encoding == "utf-8-sig"
    assert doc.sha256 == hashlib.sha256(raw).hexdigest()
    assert doc.blocks[0].text == "H"


def test_block_validation_rejects_invalid_line_range() -> None:
    with pytest.raises(ValueError, match="line range"):
        DocumentBlock("p1", BlockKind.PARAGRAPH, "x", 3, 2)


def test_duplicate_ids_are_rejected() -> None:
    block = DocumentBlock("p1", BlockKind.PARAGRAPH, "x", 1, 1)
    with pytest.raises(ValueError, match="duplicate"):
        DocumentIR("a" * 64, "x.md", 1, "utf-8", (block, block))
