"""AWF command-line composition root; provider-independent application logic."""

from __future__ import annotations

import argparse
import json
import sqlite3
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
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.application.commands.compile_knowledge import import_knowledge
from awf.application.commands.ingest_document import ingest_document
from awf.application.commands.prepare_review import prepare_review
from awf.domain.evidence import EvidenceKind
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
    review_plan = operations.add_parser(
        "plan-review", help="prepare private, source-bound review batches (not approvals)"
    )
    review_plan.add_argument("archive", type=Path, help="local original AWS ZIP")
    review_plan.add_argument(
        "--manifest", type=Path, default=Path("provenance/source-manifest.json")
    )
    review_plan.add_argument("--source-id", default="aws-3.19.1")
    review_plan.add_argument("--batch-size", type=int, default=12)
    evidence = commands.add_parser("evidence", help="private, transactional evidence ledger")
    actions = evidence.add_subparsers(dest="evidence_action")
    writer = actions.add_parser("append", help="store evidence locally and bind an event")
    writer.add_argument("source", type=Path, help="local evidence file (max 512 KiB)")
    writer.add_argument("--kind", required=True, choices=[k.value for k in EvidenceKind])
    writer.add_argument("--run-id", required=True)
    writer.add_argument("--subject-id", required=True)
    writer.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    audit = actions.add_parser("verify", help="verify evidence chain and all stored bytes")
    audit.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    audit.add_argument(
        "--expected-head", help="head digest retained independently from this database"
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
        if args.knowledge_action == "plan-review":
            try:
                overview, packets = prepare_review(
                    archive_path=args.archive,
                    manifest_path=args.manifest,
                    reader=PinnedAwsArchive(),
                    source_id=args.source_id,
                    batch_size=args.batch_size,
                )
                # Rooted beside the trusted manifest, never inside tracked docs/.
                parent = args.manifest.resolve().parent
                repo_root = parent.parent if parent.name == "provenance" else parent
                privacy_root = repo_root / ".awf"
                output_dir = (
                    privacy_root
                    / "knowledge"
                    / (f"review-{overview['archive_sha256'][:12]}-b{args.batch_size:02d}")
                )
                for path in (privacy_root, privacy_root / "knowledge", output_dir):
                    if path.is_symlink():
                        raise ValueError("private review path cannot be a symbolic link")
                # Publish manifest only after all private batches have been written.
                for filename, packet in sorted(packets.items()):
                    save_registry(output_dir / filename, packet)
                save_registry(output_dir / "manifest.json", overview)
                print(
                    json.dumps(
                        {
                            "status": "REVIEW_PENDING",
                            "manifest": str(output_dir / "manifest.json"),
                            "batches": len(packets),
                            "requirements_count": overview["requirements_count"],
                            "open_count": overview["open_count"],
                            "priority_counts": overview["priority_counts"],
                            "legacy_verification_class_counts": overview[
                                "legacy_verification_class_counts"
                            ],
                        },
                        ensure_ascii=False,
                    )
                )
                return 0
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                print(f"AWF_ERROR [REVIEW_PLAN_FAILED] {exc}", file=sys.stderr)
                return 2

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

        parser.error("expected knowledge import, knowledge plan-review or knowledge audit")
        return 2

    if args.command == "evidence":
        if args.evidence_action == "append":
            try:
                if args.source.resolve() == args.database.resolve():
                    raise ValueError("evidence input cannot be the ledger database")
                if args.source.is_symlink() or not args.source.is_file():
                    raise ValueError("evidence input must be a regular, non-symlinked file")
                if args.source.stat().st_size > 512 * 1024:
                    raise ValueError("evidence exceeds 512 KiB limit")
                raw = args.source.read_bytes()
                store = SQLiteEvidenceLedger(args.database)
                store.initialize()
                result = store.append(
                    kind=EvidenceKind(args.kind),
                    run_id=args.run_id,
                    subject_id=args.subject_id,
                    content=raw,
                )
                print(
                    json.dumps(
                        {
                            "status": "EVIDENCE_RECORDED",
                            "sequence": result.sequence,
                            "evidence_sha256": result.evidence_sha256,
                            "head_digest": result.digest,
                            "database": str(args.database),
                            "claims_independently_verified": False,
                        }
                    )
                )
                return 0
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                print(f"AWF_ERROR [EVIDENCE_APPEND_FAILED] {exc}", file=sys.stderr)
                return 2

        if args.evidence_action == "verify":
            try:
                store = SQLiteEvidenceLedger(args.database)
                report = store.verify(expected_head=args.expected_head)
                print(
                    json.dumps(
                        {
                            "status": "LEDGER_INTEGRITY_VALID",
                            "events_checked": report.events_checked,
                            "objects_checked": report.evidence_objects_checked,
                            "head_digest": report.head_digest,
                            "external_authenticity_proven": False,
                        }
                    )
                )
                return 0
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                print(f"AWF_ERROR [EVIDENCE_VERIFY_FAILED] {exc}", file=sys.stderr)
                return 2

        parser.error("expected evidence append or evidence verify")
        return 2

    parser.error("unknown command")
    return 2


def run() -> None:
    """Console-script entry point."""
    raise SystemExit(main())


if __name__ == "__main__":
    run()
