"""Canonical, versioned local serialization for immutable revision snapshots.

Only audit metadata is persisted here; source documents remain in their own
content-addressed store. This codec is deliberately strict on recovery.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from awf.domain.evidence import MAX_EVIDENCE_BYTES, EvidenceIntegrityError
from awf.domain.revision_audit import (
    AuditReceipt,
    AuditScope,
    AuditSlot,
    AuditStatus,
    CleanSweep,
    Finding,
    RevisionState,
)


def encode_revision_state(state: RevisionState) -> bytes:
    """Serialize one state in a reproducible encoding, without manuscript text."""
    payload = {
        "schema": 1,
        "artifact_sha256": state.artifact_sha256,
        "slots": [
            {
                "block_id": slot.block_id,
                "axis": slot.axis,
                "required_checks": slot.required_checks,
                "scope": slot.scope.value,
            }
            for slot in state.slots
        ],
        "receipts": [
            {
                **asdict(receipt),
                "status": receipt.status.value,
            }
            for receipt in state.receipts
        ],
        "findings": [asdict(finding) for finding in state.findings],
        "dirty_keys": sorted(state.dirty_keys),
        "clean_sweeps": [asdict(sweep) for sweep in state.clean_sweeps],
        "revision_cycles": state.revision_cycles,
        "external_iterations": state.external_iterations,
        "event_log": list(state.event_log),
    }
    raw = (
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise ValueError("revision snapshot exceeds local evidence size limit")
    return raw


def decode_revision_state(raw: bytes) -> RevisionState:
    """Reject unknown fields, type drift, invalid inventories and noncanonical bytes."""
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("schema") != 1:
            raise ValueError("revision snapshot schema mismatch")
        state = RevisionState(
            artifact_sha256=payload["artifact_sha256"],
            slots=tuple(
                AuditSlot(
                    block_id=item["block_id"],
                    axis=item["axis"],
                    required_checks=item["required_checks"],
                    scope=AuditScope(item["scope"]),
                )
                for item in payload["slots"]
            ),
            receipts=tuple(
                AuditReceipt(
                    slot_key=item["slot_key"],
                    artifact_sha256=item["artifact_sha256"],
                    scope_sha256=item["scope_sha256"],
                    status=AuditStatus(item["status"]),
                    checks_executed=item["checks_executed"],
                    evidence_ref=item["evidence_ref"],
                    carried_from=item["carried_from"],
                )
                for item in payload["receipts"]
            ),
            findings=tuple(Finding(**item) for item in payload["findings"]),
            dirty_keys=frozenset(payload["dirty_keys"]),
            clean_sweeps=tuple(CleanSweep(**item) for item in payload["clean_sweeps"]),
            revision_cycles=payload["revision_cycles"],
            external_iterations=payload["external_iterations"],
            event_log=tuple(payload["event_log"]),
        )
        keys = [slot.key for slot in state.slots]
        if (
            not keys
            or len(keys) != len(set(keys))
            or not state.dirty_keys.issubset(keys)
            or len({receipt.slot_key for receipt in state.receipts}) != len(state.receipts)
            or any(receipt.slot_key not in keys for receipt in state.receipts)
            or type(state.revision_cycles) is not int
            or type(state.external_iterations) is not int
            or min(state.revision_cycles, state.external_iterations) < 0
            or not all(isinstance(item, str) for item in state.event_log)
            or encode_revision_state(state) != raw
        ):
            raise ValueError("revision snapshot has inconsistent inventory or encoding")
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeDecodeError) as exc:
        raise EvidenceIntegrityError("invalid persisted revision snapshot") from exc
    return state
