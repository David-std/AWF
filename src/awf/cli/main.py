"""AWF command-line composition root; provider-independent application logic."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from awf import __version__
from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.knowledge.pinned_archive import PinnedAwsArchive
from awf.adapters.knowledge.review_file import JsonReviewReader
from awf.adapters.knowledge.zip_archive import checksum_file
from awf.adapters.persistence.blob_store import FileBlobStore
from awf.adapters.persistence.registry_store import save_registry
from awf.application.commands.compile_knowledge import import_knowledge
from awf.application.commands.ingest_document import ingest_document
from awf.knowledge.audit import audit_registry


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
    knowledge = commands.add_parser("knowledge", help="local-only knowledge registry operations")
    operations = knowledge.add_subparsers(dest="knowledge_action")
    importer = operations.add_parser("import", help="compile a pinned local archive to metadata")
    importer.add_argument("archive", type=Path, help="local AWS 3.19.1 ZIP, never uploaded")
    importer.add_argument("--manifest", type=Path, default=Path("provenance/source-manifest.json"))
    importer.add_argument("--source-id", default="aws-3.19.1")
    importer.add_argument("--review", type=Path, help="optional private, SHA-bound review overlay")
    importer.add_argument("--output", type=Path, help="private JSON report destination")
    auditor = operations.add_parser("audit", help="validate a private registry's consistency")
    auditor.add_argument("registry", type=Path)
    auditor.add_argument(
        "--archive", type=Path, help="optionally compare actual local archive hash"
    )
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

    if args.command == "knowledge":
        if args.knowledge_action == "import":
            output: Path | None = args.output
            protected = [args.archive, args.manifest]
            if args.review is not None:
                protected.append(args.review)
            if output is not None and any(output.resolve() == p.resolve() for p in protected):
                print(
                    "AWF_ERROR [SOURCE_PROTECTED] output conflicts with an input", file=sys.stderr
                )
                return 2
            try:
                registry = import_knowledge(
                    archive_path=args.archive,
                    manifest_path=args.manifest,
                    archive_reader=PinnedAwsArchive(),
                    source_id=args.source_id,
                    review_reader=JsonReviewReader(),
                    review_path=args.review,
                )
                report = registry.to_dict()
                destination = output or Path(
                    f".awf/knowledge/registry_{registry.archive_sha256[:12]}.json"
                )
                save_registry(destination, report)
                print(
                    json.dumps(
                        {
                            "status": "IMPORTED_WITH_OPEN_REVIEWS"
                            if report["unreviewed_count"]
                            else "REVIEW_ATTESTED",
                            "registry": str(destination),
                            "source_id": registry.source_id,
                            "source_sha256": registry.archive_sha256,
                            "requirements_count": len(registry.records),
                            "unreviewed_count": report["unreviewed_count"],
                            "disposition_counts": registry.counts(),
                        },
                        ensure_ascii=False,
                    )
                )
                return 0
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                print(f"AWF_ERROR [KNOWLEDGE_IMPORT_FAILED] {exc}", file=sys.stderr)
                return 2

        if args.knowledge_action == "audit":
            try:
                if args.registry.stat().st_size > 4 * 1024 * 1024:
                    raise ValueError("registry report exceeds maximum size")
                report = json.loads(args.registry.read_text(encoding="utf-8"))
                if not isinstance(report, dict):
                    raise ValueError("registry report must be a JSON object")
                summary = audit_registry(report)
                if args.archive is not None:
                    summary["archive_sha256_verified"] = checksum_file(args.archive) == report.get(
                        "archive_sha256"
                    )
                    if not summary["archive_sha256_verified"]:
                        summary["valid"] = False
                        errors = summary.get("errors")
                        if isinstance(errors, list):
                            errors.append("source archive hash mismatch")
                print(json.dumps(summary, ensure_ascii=False))
                return 0 if summary["valid"] else 2
            except (OSError, ValueError, TypeError, RuntimeError) as exc:
                print(f"AWF_ERROR [KNOWLEDGE_AUDIT_FAILED] {exc}", file=sys.stderr)
                return 2

        parser.error("expected knowledge import or knowledge audit")
        return 2

    parser.error("unknown command")
    return 2


def run() -> None:
    """Console-script entry point."""
    raise SystemExit(main())


if __name__ == "__main__":
    run()
