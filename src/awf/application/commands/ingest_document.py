"""Ingest a Markdown source without modifying it or trusting path-derived identifiers."""

from __future__ import annotations

from pathlib import Path

from awf.application.ports import BlobStorePort, DocumentParserPort
from awf.domain.document import DocumentIR

_MARKDOWN_EXTENSIONS = {".md", ".markdown"}


def ingest_document(
    source: Path,
    *,
    parser: DocumentParserPort,
    blob_store: BlobStorePort | None = None,
) -> DocumentIR:
    """Parse the original bytes, then optionally store a content-addressed copy.

    Unsupported input and parser failures are raised before a blob is written.
    No model, network call or silent format conversion is performed.
    """
    if source.suffix.lower() not in _MARKDOWN_EXTENSIONS:
        raise ValueError("only .md and .markdown files are supported in Sprint 1")
    raw = source.read_bytes()
    document = parser.parse(raw, source_name=source.name)
    if blob_store is not None:
        stored_sha256 = blob_store.put(raw)
        if stored_sha256 != document.sha256:
            raise RuntimeError("blob store reported a mismatched original hash")
    return document
