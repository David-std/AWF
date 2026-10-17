"""Sprint 0 CLI contract: version, help, and argument errors."""

from __future__ import annotations

import subprocess
import sys

import pytest

from awf import __version__
from awf.cli.main import create_parser, main


def test_version_is_declared() -> None:
    assert __version__ == "0.1.0"


def test_version_flag_exits_successfully(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == "awf 0.1.0"


def test_help_flag_exits_successfully(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "Academic Writing Forge" in capsys.readouterr().out


def test_unknown_flag_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--not-a-real-option"])
    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_parser_does_not_modify_external_state() -> None:
    parser = create_parser()
    assert parser.prog == "awf"


def test_module_entrypoint_runs_in_a_clean_subprocess() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "awf.cli.main", "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "awf 0.1.0"
