"""Profile verified revision recovery on temporary, synthetic SQLite histories.

This is a diagnostic microbenchmark, not a latency SLO. Database setup and
warm-up are excluded from the measurements; no real manuscripts are read.
"""

from __future__ import annotations

import argparse
import cProfile
import json
import platform
import pstats
import sqlite3
import statistics
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.sqlite_revision import SQLiteRevisionJournal
from awf.domain.revision_audit import AuditSlot, AuditStatus


def _populate(folder: Path, revisions: int, audits: int) -> SQLiteRevisionJournal:
    journal = SQLiteRevisionJournal(folder / "synthetic.sqlite")
    journal.initialize()
    document = MarkdownAdapter().parse(
        b"Synthetic citation and attribution.", source_name="bench.md"
    )
    slot = AuditSlot(document.blocks[0].block_id, "attribution", 1)
    for revision_index in range(revisions):
        revision_id = f"revision-{revision_index:04d}"
        journal.create(
            revision_id=revision_id,
            operation_id="start",
            run_id="synthetic-run",
            document=document,
            slots=(slot,),
        )
        for index in range(audits):
            journal.record_audit(
                revision_id=revision_id,
                operation_id=f"audit-{index:04d}",
                run_id="synthetic-run",
                document=document,
                expected_version=index,
                slot_key=slot.key,
                status=AuditStatus.CLEAN,
                checks_executed=1,
                observation_ref=f"synthetic:review:{revision_index}:{index}",
            )
    return journal


def _measure(action: Callable[[], object], repeats: int) -> dict[str, object]:
    action()  # Warm-up; leave schema validation and actual verification enabled.
    durations: list[float] = []
    for _ in range(repeats):
        before = time.perf_counter_ns()
        action()
        durations.append((time.perf_counter_ns() - before) / 1_000_000)
    tracemalloc.start()
    try:
        action()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "median_ms": round(statistics.median(durations), 3),
        "min_ms": round(min(durations), 3),
        "max_ms": round(max(durations), 3),
        "peak_traced_bytes": peak,
    }


def benchmark(revisions: int, audits: int, repeats: int) -> dict[str, object]:
    """Profile full ledger audit, one revision replay, and all-revision recovery."""
    with tempfile.TemporaryDirectory(prefix="awf-s2-revision-profile-") as temporary:
        store = _populate(Path(temporary), revisions, audits)
        head = store.ledger.verify().head_digest
        # This is an intentionally trusted per-revision identifier, not a random sample.
        revision_id = f"revision-{revisions - 1:04d}"

        def replay_only() -> int:
            # Internal diagnostic: deliberately separate replay from ledger verification.
            # Public callers must always use load()/verify_all_revisions().
            with store.ledger._open() as connection:
                connection.execute("BEGIN")
                try:
                    history = store._recover(connection, revision_id, head)
                    connection.execute("COMMIT")
                finally:
                    if connection.in_transaction:
                        connection.execute("ROLLBACK")
            if len(history) != audits + 1:
                raise RuntimeError("the benchmark history was not recovered fully")
            return len(history)

        def load_one() -> int:
            state = store.load(revision_id=revision_id, expected_head=head)
            if state.version != audits or state.ledger_head != head:
                raise RuntimeError("verified load returned an unexpected snapshot")
            return state.version

        def verify_all() -> int:
            report, count = store.verify_all_revisions(expected_head=head)
            if count != revisions or report.head_digest != head:
                raise RuntimeError("full database recovery returned an unexpected result")
            return count

        profile = cProfile.Profile()
        profile.enable()
        load_one()
        profile.disable()
        stat = pstats.Stats(profile)
        sql_calls = sum(
            calls
            for (_, _, name), (calls, _, _, _, _) in stat.stats.items()
            if "sqlite3.Connection" in name and ("execute" in name or "fetch" in name)
        )
        hotspots = sorted(
            (
                (round(cumulative * 1000, 3), calls, f"{Path(file).name}:{line}:{name}")
                for (file, line, name), (calls, _, _, cumulative, _) in stat.stats.items()
                if file.endswith(("sqlite_revision.py", "sqlite_evidence.py", "revision_codec.py"))
            ),
            reverse=True,
        )[:8]
        return {
            "revisions": revisions,
            "audits_per_revision": audits,
            "ledger_events": store.ledger.verify().events_checked,
            "sqlite_file_bytes": store.ledger.database.stat().st_size,
            "load_one_sql_calls_profiled": sql_calls,
            "replay_only": _measure(replay_only, repeats),
            "verified_load_one": _measure(load_one, repeats),
            "verified_all_revisions": _measure(verify_all, repeats),
            "load_one_profile_top": [
                {"cumulative_ms": duration, "calls": calls, "function": name}
                for duration, calls, name in hotspots
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", default=["1:8", "1:32", "4:16"])
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    cases: list[tuple[int, int]] = []
    try:
        for case in args.cases:
            revisions, audits = (int(value) for value in case.split(":"))
            if not (1 <= revisions <= 32 and 1 <= audits <= 128 and revisions * audits <= 512):
                raise ValueError("case out of range")
            cases.append((revisions, audits))
    except ValueError:
        parser.error("cases must be R:A (1–32 revisions, 1–128 audits, R×A ≤ 512)")
    if not 1 <= args.repeats <= 10:
        parser.error("repeats must be between 1 and 10")
    print(
        json.dumps(
            {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version,
                "repeats": args.repeats,
                "cases": [
                    benchmark(revisions, audits, args.repeats) for revisions, audits in cases
                ],
                "realistic_workload_proven": False,
                "academic_validity_proven": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
