"""Diagnostic benchmark contract: synthetic-only, complete and non-optimistic."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_revision_replay.py"


def test_profile_replays_all_synthetic_versions() -> None:
    process = subprocess.run(
        [sys.executable, str(SCRIPT), "--cases", "1:2", "2:2", "--repeats", "1"],
        capture_output=True,
        text=True,
        check=True,
    )
    single, multiple = json.loads(process.stdout)["cases"]
    assert single["ledger_events"] == 5
    assert multiple["ledger_events"] == 10
    assert single["load_one_sql_calls_profiled"] > 0
    for result in (single, multiple):
        assert result["sqlite_file_bytes"] > 0
        for operation in ("replay_only", "verified_load_one", "verified_all_revisions"):
            measurement = result[operation]
            assert isinstance(measurement, dict)
            assert measurement["median_ms"] >= 0
            assert measurement["peak_traced_bytes"] > 0


@pytest.mark.parametrize("case", ["0:8", "1:0", "100:1", "x:4", "1:2:3", "32:128"])
def test_profile_rejects_invalid_scope(case: str) -> None:
    process = subprocess.run(
        [sys.executable, str(SCRIPT), "--cases", case],
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 2
