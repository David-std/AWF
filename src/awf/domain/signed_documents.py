"""Unambiguous, bounded canonical JSON shared by detached signed contracts."""

from __future__ import annotations

import json

from awf.domain.evidence import EvidenceIntegrityError


def canonical_json_bytes(value: dict[str, object]) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
        + "\n"
    ).encode("utf-8")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise EvidenceIntegrityError("duplicate signed JSON field")
        obj[key] = value
    return obj


def strict_json(data: bytes) -> dict[str, object]:
    """Reject duplicate members, nonfinite numbers, noncanonical or invalid UTF-8."""
    if len(data) > 64 * 1024:
        raise EvidenceIntegrityError("signed document exceeds size limit")

    def reject_constant(_: str) -> object:
        raise EvidenceIntegrityError("nonfinite number in signed JSON")

    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=reject_constant
        )
        if not isinstance(value, dict) or canonical_json_bytes(value) != data:
            raise EvidenceIntegrityError("signed JSON must be a canonical object")
    except EvidenceIntegrityError:
        raise
    except (ValueError, UnicodeError, TypeError) as exc:
        raise EvidenceIntegrityError("invalid signed JSON") from exc
    return value
