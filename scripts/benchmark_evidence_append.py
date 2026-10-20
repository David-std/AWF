"""Measure individual audited writes versus one atomic bounded write batch.

Only deterministic synthetic bytes are written to temporary SQLite databases.
This is a local microbenchmark, not an SLO or a measure of academic validity.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import tempfile
import time
from pathlib import Path

from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.domain.evidence import MAX_BATCH_EVENTS, EvidenceAppend, EvidenceKind


def benchmark(events: int, repeats: int) -> dict[str, object]:
    entries = tuple(
        EvidenceAppend(
            EvidenceKind.SOURCE_CHUNK,
            "benchmark-run",
            f"source:C{index:05d}",
            b"synthetic-batch:" + index.to_bytes(4, "big"),
        )
        for index in range(events)
    )
    individual: list[float] = []
    batched: list[float] = []
    for repeat in range(repeats):
        with tempfile.TemporaryDirectory(prefix="awf-s2-write-bench-") as folder:
            root = Path(folder)
            for mode, samples in (("individual", individual), ("batch", batched)):
                store = SQLiteEvidenceLedger(root / f"{mode}-{repeat}.sqlite")
                store.initialize()
                started = time.perf_counter_ns()
                if mode == "individual":
                    records = tuple(
                        store.append(
                            kind=entry.kind,
                            run_id=entry.run_id,
                            subject_id=entry.subject_id,
                            content=entry.content,
                        )
                        for entry in entries
                    )
                else:
                    records = store.append_batch(entries=entries)
                samples.append((time.perf_counter_ns() - started) / 1_000_000_000)
                report = store.verify(expected_head=records[-1].digest)
                if (
                    report.events_checked != events
                    or report.evidence_objects_checked != events
                    or any(record.sequence != index + 1 for index, record in enumerate(records))
                ):
                    raise RuntimeError("synthetic evidence changed between write modes")
    a = statistics.median(individual)
    b = statistics.median(batched)
    return {
        "events": events,
        "repeats": repeats,
        "individual_append_median_seconds": round(a, 6),
        "atomic_batch_median_seconds": round(b, 6),
        "observed_speedup": round(a / b, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", nargs="+", type=int, default=[16, 64, 128])
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10 or any(
        not 1 <= count <= MAX_BATCH_EVENTS for count in args.events
    ):
        parser.error(f"use 1–10 repeats and 1–{MAX_BATCH_EVENTS} synthetic events per case")
    print(
        json.dumps(
            {
                "platform": platform.system(),
                "python": platform.python_version(),
                "cases": [benchmark(events, args.repeats) for events in args.events],
                "academic_validity_proven": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
