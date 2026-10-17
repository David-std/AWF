"""Immutable, minimal Markdown document representation for Sprint 1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class BlockKind(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    FENCED_CODE = "fenced_code"


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    """A location-bound block; line coordinates are 1-based and inclusive."""

    block_id: str
    kind: BlockKind
    text: str
    start_line: int
    end_line: int
    heading_level: int | None = None

    def __post_init__(self) -> None:
        if not self.block_id or not self.text:
            raise ValueError("blocks require a stable ID and nonempty text")
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("invalid block line range")
        if self.kind == BlockKind.HEADING:
            if self.heading_level not in range(1, 7):
                raise ValueError("heading level must be between 1 and 6")
        elif self.heading_level is not None:
            raise ValueError("non-heading blocks cannot have a heading level")


@dataclass(frozen=True, slots=True)
class DocumentIR:
    """Parsed view bound to the SHA-256 of the *original bytes*."""

    sha256: str
    source_name: str
    byte_length: int
    encoding: str
    blocks: tuple[DocumentBlock, ...]

    def __post_init__(self) -> None:
        if not _HEX64.fullmatch(self.sha256):
            raise ValueError("invalid original SHA-256")
        if not self.source_name or self.byte_length < 0:
            raise ValueError("invalid document metadata")
        if self.encoding not in {"utf-8", "utf-8-sig"}:
            raise ValueError("unsupported encoding metadata")
        if len({block.block_id for block in self.blocks}) != len(self.blocks):
            raise ValueError("duplicate document block IDs")

    @property
    def document_id(self) -> str:
        """Content-addressed identifier; source path is not an identity."""
        return f"doc_{self.sha256}"

    def to_dict(self) -> dict[str, object]:
        """Emit JSON-compatible metadata without embedding the full original file."""
        return {
            "schema_version": "1.0.0",
            "document_id": self.document_id,
            "sha256": self.sha256,
            "source_name": self.source_name,
            "byte_length": self.byte_length,
            "encoding": self.encoding,
            "blocks": [
                {
                    "block_id": block.block_id,
                    "kind": block.kind.value,
                    "text": block.text,
                    "start_line": block.start_line,
                    "end_line": block.end_line,
                    "heading_level": block.heading_level,
                }
                for block in self.blocks
            ],
        }
