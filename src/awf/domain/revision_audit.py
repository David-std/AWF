"""A bounded, fail-closed revision audit prototype for AWF.

This module is a clean-room *proposal*, informed by the historic DSR-001..015
contracts. It does not import or execute any legacy AWS source, run critics,
certify semantic quality, or persist confidential document text.

Coverage is anchored to an explicit inventory; a missing inventory cannot PASS.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from enum import StrEnum

from awf.domain.document import DocumentIR


class AuditScope(StrEnum):
    DOCUMENT = "DOCUMENT"
    LOCAL_NEIGHBORS = "LOCAL_NEIGHBORS"


class AuditStatus(StrEnum):
    CLEAN = "CLEAN"
    OPEN = "OPEN"
    UNKNOWN = "UNKNOWN"


class RevisionVerdict(StrEnum):
    AUDIT_REQUIRED = "AUDIT_REQUIRED"
    EDIT_REVIEW_REQUIRED = "EDIT_REVIEW_REQUIRED"
    FRESH_CRITIC_REQUIRED = "FRESH_CRITIC_REQUIRED"
    CONVERGED = "CONVERGED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class AuditSlot:
    """One mandatory audit task; local scope is an explicit, reviewed exception."""

    block_id: str
    axis: str
    required_checks: int
    scope: AuditScope = AuditScope.DOCUMENT

    def __post_init__(self) -> None:
        if not self.block_id or not self.axis or self.required_checks < 1:
            raise ValueError("audit slot requires an identity and positive work budget")

    @property
    def key(self) -> str:
        return f"{self.block_id}:{self.axis}"


@dataclass(frozen=True, slots=True)
class RevisionPolicy:
    """One policy source, historically motivated; not an old runtime alias."""

    max_revision_cycles: int = 8
    max_external_iterations: int = 12
    clean_sweeps_required: int = 2

    def __post_init__(self) -> None:
        if (
            min(
                self.max_revision_cycles,
                self.max_external_iterations,
                self.clean_sweeps_required,
            )
            < 1
        ):
            raise ValueError("revision limits must be positive")


@dataclass(frozen=True, slots=True)
class AuditReceipt:
    slot_key: str
    artifact_sha256: str
    scope_sha256: str
    status: AuditStatus
    checks_executed: int
    evidence_ref: str
    carried_from: str | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    material: bool
    status: str
    evidence_ref: str
    resolution_evidence_ref: str | None = None


@dataclass(frozen=True, slots=True)
class CleanSweep:
    critic_id: str
    artifact_sha256: str
    evidence_ref: str
    isolated_context_ref: str


@dataclass(frozen=True, slots=True)
class RevisionState:
    """Immutable snapshot: acceptance depends on checked data, not model narrative."""

    artifact_sha256: str
    slots: tuple[AuditSlot, ...]
    receipts: tuple[AuditReceipt, ...]
    findings: tuple[Finding, ...]
    dirty_keys: frozenset[str]
    clean_sweeps: tuple[CleanSweep, ...]
    revision_cycles: int = 0
    external_iterations: int = 0
    event_log: tuple[str, ...] = ()


def _sha(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def scope_fingerprint(doc: DocumentIR, slot: AuditSlot) -> str:
    """Hash real current text/dependencies; reject stale/missing block IDs.

    DOCUMENT is safe default. LOCAL_NEIGHBORS may only be selected when the
    axis truly lacks long-range dependencies, an assumption outside this check.
    """
    blocks = doc.blocks
    matches = [i for i, block in enumerate(blocks) if block.block_id == slot.block_id]
    if len(matches) != 1:
        raise ValueError("audit slot refers to missing/ambiguous current block")
    if slot.scope == AuditScope.DOCUMENT:
        return _sha({"axis": slot.axis, "artifact_sha256": doc.sha256})
    if slot.scope != AuditScope.LOCAL_NEIGHBORS:
        raise ValueError("unsupported scope type")
    i = matches[0]
    return _sha(
        {
            "axis": slot.axis,
            "block_kind": blocks[i].kind.value,
            "block": blocks[i].text,
            "previous": blocks[i - 1].text if i > 0 else None,
            "next": blocks[i + 1].text if i + 1 < len(blocks) else None,
        }
    )


def start_revision(doc: DocumentIR, slots: tuple[AuditSlot, ...]) -> RevisionState:
    """Require and freeze complete explicit work before accepting any clean claim."""
    keys = [slot.key for slot in slots]
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("audit inventory must be nonempty and unique")
    for slot in slots:
        scope_fingerprint(doc, slot)
    return RevisionState(
        artifact_sha256=doc.sha256,
        slots=slots,
        receipts=(),
        findings=(),
        dirty_keys=frozenset(keys),
        clean_sweeps=(),
        event_log=(f"START:{doc.sha256}",),
    )


def _assert_document(state: RevisionState, doc: DocumentIR) -> None:
    if doc.sha256 != state.artifact_sha256:
        raise ValueError("document bytes are not those bound to the revision state")


def record_audit(
    state: RevisionState,
    doc: DocumentIR,
    *,
    slot_key: str,
    status: AuditStatus,
    checks_executed: int,
    evidence_ref: str,
) -> RevisionState:
    """Record an observation; CLEAN is impossible on missing work or evidence."""
    _assert_document(state, doc)
    slot = next((s for s in state.slots if s.key == slot_key), None)
    if slot is None:
        raise ValueError("unregistered audit task")
    if not evidence_ref.strip() or checks_executed < 0 or checks_executed > slot.required_checks:
        raise ValueError("invalid evidence or executed-check count")
    if status == AuditStatus.CLEAN and checks_executed != slot.required_checks:
        raise ValueError("CLEAN requires every declared check to execute")
    if not isinstance(status, AuditStatus):
        raise ValueError("unsupported audit disposition")
    receipt = AuditReceipt(
        slot_key=slot_key,
        artifact_sha256=doc.sha256,
        scope_sha256=scope_fingerprint(doc, slot),
        status=status,
        checks_executed=checks_executed,
        evidence_ref=evidence_ref,
    )
    receipts = tuple(r for r in state.receipts if r.slot_key != slot_key) + (receipt,)
    dirty = (
        state.dirty_keys - {slot_key}
        if status == AuditStatus.CLEAN
        else state.dirty_keys | {slot_key}
    )
    return replace(
        state,
        receipts=receipts,
        dirty_keys=frozenset(dirty),
        clean_sweeps=(),
        event_log=state.event_log + (f"AUDIT:{slot_key}:{status.value}:{doc.sha256}",),
    )


def accept_edit(
    state: RevisionState,
    old: DocumentIR,
    new: DocumentIR,
    *,
    policy: RevisionPolicy,
    operation_ref: str,
) -> RevisionState:
    """Accept a changed artifact and conservatively rebind unchanged local checks.

    Any DOCUMENT-scoped check becomes dirty on text change. No prior clean
    critic sweep survives. Reuse is recorded with old artifact lineage.
    """
    _assert_document(state, old)
    if new.sha256 == old.sha256 or not operation_ref.strip():
        raise ValueError("accept_edit requires changed bytes and an operation reference")
    if state.revision_cycles >= policy.max_revision_cycles:
        raise ValueError("revision budget exhausted; cannot silently accept another edit")
    old_receipts = {r.slot_key: r for r in state.receipts}
    carried: list[AuditReceipt] = []
    dirty: set[str] = set()
    for slot in state.slots:
        new_fp = scope_fingerprint(new, slot)
        old_receipt = old_receipts.get(slot.key)
        if (
            old_receipt is not None
            and old_receipt.status == AuditStatus.CLEAN
            and slot.key not in state.dirty_keys
            and old_receipt.scope_sha256 == scope_fingerprint(old, slot)
            and old_receipt.scope_sha256 == new_fp
            and old_receipt.artifact_sha256 == old.sha256
        ):
            carried.append(
                replace(old_receipt, artifact_sha256=new.sha256, carried_from=old.sha256)
            )
        else:
            dirty.add(slot.key)
    return replace(
        state,
        artifact_sha256=new.sha256,
        receipts=tuple(carried),
        dirty_keys=frozenset(dirty),
        clean_sweeps=(),
        revision_cycles=state.revision_cycles + 1,
        event_log=state.event_log + (f"ACCEPT_EDIT:{old.sha256}:{new.sha256}:{operation_ref}",),
    )


def open_finding(
    state: RevisionState, *, finding_id: str, material: bool, evidence_ref: str
) -> RevisionState:
    if not finding_id.strip() or not evidence_ref.strip():
        raise ValueError("finding requires ID and evidence")
    if any(f.finding_id == finding_id for f in state.findings):
        raise ValueError("finding IDs are immutable; explicit resolution is required")
    finding = Finding(finding_id, material, "OPEN", evidence_ref)
    return replace(
        state,
        findings=state.findings + (finding,),
        clean_sweeps=(),
        event_log=state.event_log + (f"FINDING_OPEN:{finding_id}",),
    )


def resolve_finding(
    state: RevisionState, *, finding_id: str, resolution_evidence_ref: str
) -> RevisionState:
    if not resolution_evidence_ref.strip():
        raise ValueError("resolution requires explicit evidence")
    if not any(f.finding_id == finding_id and f.status == "OPEN" for f in state.findings):
        raise ValueError("only recorded OPEN findings can be resolved")
    findings = tuple(
        replace(f, status="RESOLVED", resolution_evidence_ref=resolution_evidence_ref)
        if f.finding_id == finding_id
        else f
        for f in state.findings
    )
    return replace(
        state,
        findings=findings,
        clean_sweeps=(),
        event_log=state.event_log + (f"FINDING_RESOLVED:{finding_id}",),
    )


def coverage(state: RevisionState, doc: DocumentIR) -> float:
    """Strict declared-check ratio: zero slots cannot yield 100% coverage."""
    _assert_document(state, doc)
    total = sum(slot.required_checks for slot in state.slots)
    if total == 0:
        return 0.0
    receipts = {r.slot_key: r for r in state.receipts}
    done = 0
    for slot in state.slots:
        r = receipts.get(slot.key)
        if (
            r is not None
            and r.artifact_sha256 == doc.sha256
            and r.scope_sha256 == scope_fingerprint(doc, slot)
            and slot.key not in state.dirty_keys
        ):
            done += min(r.checks_executed, slot.required_checks)
    return done / total


def add_clean_sweep(
    state: RevisionState,
    doc: DocumentIR,
    *,
    critic_id: str,
    evidence_ref: str,
    isolated_context_ref: str,
    inherited_diagnosis: bool = False,
    policy: RevisionPolicy | None = None,
) -> RevisionState:
    """Distinct critic receipts; identities do not prove actual independence."""
    _assert_document(state, doc)
    if decision(state, doc, policy) != RevisionVerdict.FRESH_CRITIC_REQUIRED:
        raise ValueError("a clean sweep requires complete current audits and zero open findings")
    if inherited_diagnosis or not all(
        value.strip() for value in (critic_id, evidence_ref, isolated_context_ref)
    ):
        raise ValueError("critic sweep requires isolated context and documented evidence")
    if any(s.critic_id == critic_id for s in state.clean_sweeps):
        raise ValueError("duplicate critic identity is not an independent clean sweep")
    if any(s.isolated_context_ref == isolated_context_ref for s in state.clean_sweeps):
        raise ValueError("reused isolation receipt cannot support independent sweep")
    return replace(
        state,
        clean_sweeps=state.clean_sweeps
        + (CleanSweep(critic_id, doc.sha256, evidence_ref, isolated_context_ref),),
        event_log=state.event_log + (f"CLEAN_SWEEP:{critic_id}:{doc.sha256}",),
    )


def record_external_iteration(
    state: RevisionState,
    *,
    policy: RevisionPolicy,
    evidence_ref: str,
) -> RevisionState:
    """Record one explicitly evidenced external cycle without granting PASS."""
    if not evidence_ref.strip():
        raise ValueError("external iteration requires evidence")
    if state.external_iterations >= policy.max_external_iterations:
        raise ValueError("external iteration budget exhausted")
    return replace(
        state,
        external_iterations=state.external_iterations + 1,
        event_log=state.event_log + (f"EXTERNAL_ITERATION:{evidence_ref}",),
    )


def decision(
    state: RevisionState, doc: DocumentIR, policy: RevisionPolicy | None = None
) -> RevisionVerdict:
    """Recheck the live document and every registered slot before convergence."""
    _assert_document(state, doc)
    selected = policy or RevisionPolicy()
    receipts = {r.slot_key: r for r in state.receipts}
    all_clean = (
        bool(state.slots)
        and not state.dirty_keys
        and all(
            (r := receipts.get(slot.key)) is not None
            and r.status == AuditStatus.CLEAN
            and r.checks_executed == slot.required_checks
            and r.artifact_sha256 == doc.sha256
            and r.scope_sha256 == scope_fingerprint(doc, slot)
            for slot in state.slots
        )
    )
    if not all_clean:
        result = RevisionVerdict.AUDIT_REQUIRED
    elif any(f.material and f.status == "OPEN" for f in state.findings):
        result = RevisionVerdict.EDIT_REVIEW_REQUIRED
    elif (
        len(state.clean_sweeps) >= selected.clean_sweeps_required
        and len({c.critic_id for c in state.clean_sweeps}) >= selected.clean_sweeps_required
        and all(c.artifact_sha256 == doc.sha256 for c in state.clean_sweeps)
    ):
        return RevisionVerdict.CONVERGED
    else:
        result = RevisionVerdict.FRESH_CRITIC_REQUIRED
    if (
        state.revision_cycles >= selected.max_revision_cycles
        or state.external_iterations >= selected.max_external_iterations
    ):
        return RevisionVerdict.BUDGET_EXHAUSTED
    return result
