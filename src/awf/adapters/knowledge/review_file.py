"""Local JSON review overlay adapter, source-hash bound and non-authoritative."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonReviewReader:
    """Read explicit review decisions without claiming independent verification."""

    def load(
        self, path: Path, *, expected_source_sha256: str
    ) -> dict[str, dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("source_sha256") != expected_source_sha256:
            raise ValueError("review overlay is not bound to the exact source archive hash")
        decisions = payload.get("decisions")
        if not isinstance(decisions, list):
            raise ValueError("review overlay requires decisions list")
        result: dict[str, dict[str, Any]] = {}
        for item in decisions:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise ValueError("malformed knowledge review decision")
            identifier = item["id"]
            if identifier in result:
                raise ValueError(f"duplicate review decision ID: {identifier}")
            result[identifier] = item
        return result
