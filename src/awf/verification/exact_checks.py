"""Deterministic, bounded exact-invariant probe for candidate edits.

This checker proves narrowly scoped literal preservation only. It does NOT
verify citations' meaning, semantic equivalence, model independence, rights,
or scientific correctness; a generator cannot promote its receipt to approval.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_NUMBERS = re.compile(r"(?<![\w])\d+(?:[.,]\d+)*(?:[ \t]*%)?")
_RISK_MARKERS = re.compile(
    r"\b(?:no|not|never|nunca|sin|without|always|siempre|must|debe|"
    r"may|might|podr[ií]a|caus(?:a|[oó]|ed|es)|causal|"
    r"associated|asociad[oa]s?|demuestra|demuestran|proves?|"
    r"suggests?|sugiere|sugieren)\b",
    re.IGNORECASE,
)
_KINDS = frozenset({"QUANTITY", "CITATION", "QUOTE", "SOURCE_ID"})
_MAX_ITEMS = 128
_MAX_LITERAL = 1024


class ProbeStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass(frozen=True, slots=True)
class ProtectedLiteral:
    check_id: str
    kind: str
    value: str
    left_context: str
    right_context: str

    @property
    def anchor(self) -> str:
        return self.left_context + self.value + self.right_context


@dataclass(frozen=True, slots=True)
class InvariantContract:
    baseline_sha256: str
    checks: tuple[ProtectedLiteral, ...]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _value(raw: object, *, key: str) -> str:
    if not isinstance(raw, str) or not raw or len(raw) > _MAX_LITERAL:
        raise ValueError(f"invalid {key} in exact-invariant contract")
    if "\x00" in raw or any(ord(ch) < 32 and ch not in "\t\n" for ch in raw):
        raise ValueError(f"invalid control characters in contract {key}")
    return raw


def parse_contract(raw: object) -> InvariantContract:
    """Validate explicit assertions; never infer coverage from a model response."""
    if not isinstance(raw, dict) or set(raw) != {
        "schema_version", "baseline_sha256", "checks"
    }:
        raise ValueError("invalid exact-invariant contract keys")
    if raw["schema_version"] != "1.0.0":
        raise ValueError("unsupported exact-invariant contract version")
    sha = raw["baseline_sha256"]
    if not isinstance(sha, str) or not _HEX64.fullmatch(sha):
        raise ValueError("invalid baseline SHA-256")
    entries = raw["checks"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= _MAX_ITEMS:
        raise ValueError("exact-invariant contract needs 1..128 checks")
    checks: list[ProtectedLiteral] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "id", "kind", "value", "left_context", "right_context"
        }:
            raise ValueError("invalid protected-literal fields")
        identity = _value(entry["id"], key="check ID")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,79}", identity):
            raise ValueError("invalid check ID syntax")
        if identity in seen:
            raise ValueError("duplicate check ID")
        seen.add(identity)
        kind = entry["kind"]
        if not isinstance(kind, str) or kind not in _KINDS:
            raise ValueError("unsupported exact-invariant check kind")
        value = _value(entry["value"], key="protected value")
        left = _value(entry["left_context"], key="left context")
        right = _value(entry["right_context"], key="right context")
        checks.append(ProtectedLiteral(identity, kind, value, left, right))
    return InvariantContract(sha, tuple(checks))


def _inventory(text: str, pattern: re.Pattern[str]) -> Counter[str]:
    return Counter(match.group(0).casefold() for match in pattern.finditer(text))


def verify_exact_invariants(
    baseline: bytes, candidate: bytes, contract: InvariantContract
) -> dict[str, object]:
    """Check actual UTF-8 bytes and selected local contexts, not LLM claims.

    Missing protected text is FAIL; changed context, duplicated values,
    modified numeric inventory or modal/causal markers require review.
    PASS reports only the listed literal tests, never document acceptance.
    """
    baseline_sha = _sha(baseline)
    candidate_sha = _sha(candidate)
    if baseline_sha != contract.baseline_sha256:
        raise ValueError("baseline bytes do not match externally pinned contract")
    first = baseline.decode("utf-8-sig")
    second = candidate.decode("utf-8-sig")
    items: list[dict[str, object]] = []
    statuses: list[ProbeStatus] = []
    for check in contract.checks:
        if first.count(check.anchor) != 1:
            raise ValueError(f"ambiguous/missing baseline anchor for {check.check_id}")
        original_count = first.count(check.value)
        candidate_count = second.count(check.value)
        anchor_count = second.count(check.anchor)
        if candidate_count < original_count:
            status = ProbeStatus.FAIL
            reason = "PROTECTED_LITERAL_REMOVED"
        elif candidate_count != original_count or anchor_count != 1:
            status = ProbeStatus.NEEDS_REVIEW
            reason = "CHANGED_CONTEXT_OR_DUPLICATE_LITERAL"
        else:
            status = ProbeStatus.PASS
            reason = "EXACT_ANCHOR_UNCHANGED"
        statuses.append(status)
        items.append({
            "check_id": check.check_id,
            "kind": check.kind,
            "status": status.value,
            "reason_code": reason,
            "baseline_occurrences": original_count,
            "candidate_occurrences": candidate_count,
            "anchor_sha256": _sha(check.anchor.encode("utf-8")),
        })

    signals: list[str] = []
    if _inventory(first, _NUMBERS) != _inventory(second, _NUMBERS):
        signals.append("NUMERIC_INVENTORY_DRIFT")
    if _inventory(first, _RISK_MARKERS) != _inventory(second, _RISK_MARKERS):
        signals.append("MODAL_CAUSAL_MARKER_DRIFT")
    scope_status = (
        ProbeStatus.FAIL
        if ProbeStatus.FAIL in statuses
        else ProbeStatus.NEEDS_REVIEW
        if ProbeStatus.NEEDS_REVIEW in statuses or signals
        else ProbeStatus.PASS
    )
    return {
        "schema_version": "1.0.0",
        "checker_id": "exact_invariants:v1",
        "baseline_sha256": baseline_sha,
        "candidate_sha256": candidate_sha,
        "scope_status": scope_status.value,
        "document_acceptance": "NEEDS_REVIEW",
        "source_truth_verified": False,
        "semantic_equivalence_verified": False,
        "rights_verified": False,
        "training_authorized": False,
        "protected_checks_count": len(items),
        "checks": items,
        "review_signals": signals,
    }
