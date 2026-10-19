"""Minimal provider-facing protocols; no parser, storage or ML dependency leaks inward."""

from __future__ import annotations

from typing import Protocol

from awf.domain.document import DocumentIR


class DocumentParserPort(Protocol):
    def parse(self, raw: bytes, *, source_name: str) -> DocumentIR:
        """Return a parsed, hash-bound view or raise a typed parse exception."""
        ...


class BlobStorePort(Protocol):
    def put(self, raw: bytes) -> str:
        """Store immutable bytes by content hash and return their SHA-256."""
        ...
