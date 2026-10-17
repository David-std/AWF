"""AWF command-line composition root; provider-independent application logic."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from awf import __version__
from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.persistence.blob_store import FileBlobStore
from awf.application.commands.ingest_document import ingest_document


def create_parser() -> argparse.ArgumentParser:
    """Build the CLI and keep supported commands explicit."""
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
    commands = parser.add_subparsers(dest="command")
    ingest = commands.add_parser("ingest", help="parse UTF-8 Markdown to immutable DocumentIR")
    ingest.add_argument("source", type=Path, help="input .md/.markdown source")
    ingest.add_argument("--output", type=Path, help="optional JSON output path")
    ingest.add_argument("--store", type=Path, help="optional private content-addressed blob root")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run supported actions, returning stable process exit codes."""
    parser = create_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "ingest":
        source: Path = args.source
        output: Path | None = args.output
        if output is not None and output.resolve() == source.resolve():
            print("AWF_ERROR [SOURCE_PROTECTED] output cannot overwrite source", file=sys.stderr)
            return 2
        try:
            store = FileBlobStore(args.store) if args.store is not None else None
            document = ingest_document(source, parser=MarkdownAdapter(), blob_store=store)
            representation = json.dumps(document.to_dict(), ensure_ascii=False, indent=2) + "\n"
            if output is not None:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(representation, encoding="utf-8")
            else:
                print(representation, end="")
            return 0
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"AWF_ERROR [INGEST_FAILED] {exc}", file=sys.stderr)
            return 2

    parser.error("unknown command")
    return 2


def run() -> None:
    """Console-script entry point."""
    raise SystemExit(main())


if __name__ == "__main__":
    run()
