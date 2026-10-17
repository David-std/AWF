"""Conservative Markdown block parser that preserves original byte identity.

Sprint 1 recognizes ATX headings and fenced code blocks. Other text, including
lists and tables, is preserved as paragraph content rather than guessed into a
richer schema. It never rewrites or reparses the original bytes for export.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from awf.domain.document import BlockKind, DocumentBlock, DocumentIR

_MAX_BYTES = 4 * 1024 * 1024
_HEADING = re.compile(r"^[ ]{0,3}(#{1,6})[ \t]+(.+?)\s*$")
_OPEN_FENCE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})(?:[^\n]*)$")


class MarkdownParseError(ValueError):
    """A byte stream could not be represented under the declared Markdown subset."""


def _closing_fence(line: str, opening: str) -> bool:
    marker = re.escape(opening[0])
    return re.fullmatch(rf"[ ]{{0,3}}{marker}{{{len(opening)},}}[ \t]*", line) is not None


class MarkdownAdapter:
    """Deterministic UTF-8 Markdown parser; no external or model dependency."""

    def parse(self, raw: bytes, *, source_name: str) -> DocumentIR:
        if len(raw) > _MAX_BYTES:
            raise MarkdownParseError("source exceeds the 4 MiB Markdown limit")
        if b"\x00" in raw:
            raise MarkdownParseError("NUL bytes are not supported in Markdown")
        encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError as exc:
            raise MarkdownParseError("Markdown must be UTF-8 encoded") from exc

        lines = text.splitlines()
        blocks: list[DocumentBlock] = []
        counts: dict[BlockKind, int] = defaultdict(int)
        paragraph: list[str] = []
        paragraph_start = 0

        def add(kind: BlockKind, value: str, start: int, end: int, level: int | None = None) -> None:
            counts[kind] += 1
            block_id = f"{kind.value}_{counts[kind]:04d}"
            blocks.append(DocumentBlock(block_id, kind, value, start, end, level))

        def flush_paragraph(end_line: int) -> None:
            nonlocal paragraph_start
            if paragraph:
                add(BlockKind.PARAGRAPH, "\n".join(paragraph), paragraph_start, end_line)
                paragraph.clear()
                paragraph_start = 0

        cursor = 0
        while cursor < len(lines):
            line = lines[cursor]
            number = cursor + 1
            fence = _OPEN_FENCE.match(line)
            heading = _HEADING.match(line)
            if fence:
                flush_paragraph(cursor)
                opening = fence.group(1)
                start = cursor
                cursor += 1
                while cursor < len(lines) and not _closing_fence(lines[cursor], opening):
                    cursor += 1
                if cursor == len(lines):
                    raise MarkdownParseError(f"unclosed code fence at line {number}")
                cursor += 1
                add(BlockKind.FENCED_CODE, "\n".join(lines[start:cursor]), number, cursor)
                continue
            if not line.strip():
                flush_paragraph(cursor)
                cursor += 1
                continue
            if heading:
                flush_paragraph(cursor)
                add(BlockKind.HEADING, heading.group(2), number, number, len(heading.group(1)))
                cursor += 1
                continue
            if not paragraph:
                paragraph_start = number
            paragraph.append(line)
            cursor += 1

        flush_paragraph(len(lines))
        return DocumentIR(
            sha256=hashlib.sha256(raw).hexdigest(),
            source_name=source_name,
            byte_length=len(raw),
            encoding=encoding,
            blocks=tuple(blocks),
        )
