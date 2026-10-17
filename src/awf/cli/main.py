"""Initial CLI composition root.

Sprint 0 provides a deliberately small, dependency-free command. Ingestion
and model-dependent workflows are introduced only after their domain contracts
and tests exist. The CLI never authorizes a revision.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from awf import __version__


def create_parser() -> argparse.ArgumentParser:
    """Return the stable, side-effect-free Sprint 0 CLI parser."""
    parser = argparse.ArgumentParser(
        prog="awf",
        description="Academic Writing Forge — traceable academic revision",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"awf {__version__}",
        help="show the installed package version and exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the current CLI contract with no filesystem or network side effects."""
    parser = create_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


def run() -> None:
    """Entrypoint used by the installed `awf` console script."""
    raise SystemExit(main())


if __name__ == "__main__":
    run()
