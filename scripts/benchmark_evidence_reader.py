"""Compare individually audited event resolution with a single verified snapshot.

Uses only synthetic, deterministic bytes and temporary SQLite files. Timing
reports are observations of this machine, not a production SLO or guarantee.
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
from awf.domain.evidence import EvidenceKind


def benchmark(events: int, repeats: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="awf-s2-evidence-bench-") as folder:
        store = SQLiteEvidenceLedger(Path(folder) / "synthetic.sqlite")
        store.initialize()
        known: list[tuple[str, bytes]] = []
        for index in range(events):
            content = b"synthetic:" + index.to_bytes(4, "big")
            event = store.append(
                kind=EvidenceKind.SOURCE_CHUNK,
                run_id="bench-run",
                subject_id=f"bench:{index:05d}",
                content=content,
            )
            known.append((event.digest, content))
        head = store.verify().head_digest
        individual: list[float] = []
        shared: list[float] = []
        for _ in range(repeats):
            start = time.perf_counter_ns()
            for digest, raw in known:
                _, actual = store.resolve_event(event_digest=digest, expected_head=head)
                if actual != raw:
                    raise RuntimeError("individual resolution changed synthetic evidence")
            individual.append((time.perf_counter_ns() - start) / 1_000_000_000)

            start = time.perf_counter_ns()
            with store.verified_read(expected_head=head) as reader:
                for digest, raw in known:
                    _, actual = reader.resolve_event(event_digest=digest, expected_head=head)
                    if actual != raw:
                        raise RuntimeError("snapshot resolution changed synthetic evidence")
            shared.append((time.perf_counter_ns() - start) / 1_000_000_000)

        median_individual = statistics.median(individual)
        median_shared = statistics.median(shared)
        return {
            "events": events,
            "repeats": repeats,
            "individual_audits_median_seconds": round(median_individual, 6),
            "single_snapshot_median_seconds": round(median_shared, 6),
            "observed_speedup": round(median_individual / median_shared, 2),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", nargs="+", type=int, default=[16, 64, 128])
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 10 or any(not 1 <= n <= 512 for n in args.events):
        parser.error("use 1–10 repeats and 1–512 synthetic events per sample")
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
