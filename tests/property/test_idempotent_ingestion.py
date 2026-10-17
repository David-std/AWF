"""Property-based tests for deterministic parsing and original-byte identity."""

from __future__ import annotations

import hashlib

from hypothesis import given
from hypothesis import strategies as st

from awf.adapters.document.markdown_adapter import MarkdownAdapter


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"), max_size=300))
def test_utf8_plain_text_is_idempotent(value: str) -> None:
    raw = value.encode("utf-8")
    parser = MarkdownAdapter()
    try:
        first = parser.parse(raw, source_name="test.md")
    except ValueError:
        # Unclosed Markdown code fences are intentionally rejected.
        return
    second = parser.parse(raw, source_name="test.md")
    assert first == second
    assert first.sha256 == hashlib.sha256(raw).hexdigest()
