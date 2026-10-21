"""AWF command-line composition root; provider-independent application logic."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from awf import __version__
from awf.adapters.document.markdown_adapter import MarkdownAdapter
from awf.adapters.knowledge.pilot_evidence import inspect_historical_evidence
from awf.adapters.knowledge.pinned_archive import PinnedAwsArchive
from awf.adapters.knowledge.review_file import JsonReviewReader
from awf.adapters.knowledge.zip_archive import checksum_file
from awf.adapters.models.ollama_local import OllamaLocalAgent
from awf.adapters.persistence.blob_store import FileBlobStore
from awf.adapters.persistence.registry_store import save_registry, save_review_workbench
from awf.adapters.persistence.sqlite_evidence import SQLiteEvidenceLedger
from awf.adapters.persistence.sqlite_snapshots import SQLiteSnapshotWriter
from awf.adapters.security.ed25519_reviewer import Ed25519ReviewerVerifier
from awf.application.commands.authorize_dossiers import (
    parse_dossier_attestation_inventory,
    verify_authorized_dossier_proposals,
)
from awf.application.commands.authorize_review import (
    append_signed_review_claim,
    verify_signed_review_event,
)
from awf.application.commands.checkpoints import (
    propose_checkpoint,
    verify_signed_checkpoint,
)
from awf.application.commands.compile_knowledge import import_knowledge
from awf.application.commands.ingest_document import ingest_document
from awf.application.commands.prepare_review import prepare_review
from awf.application.commands.run_agent import run_instrumented_agent
from awf.application.commands.verified_snapshot import create_verified_snapshot
from awf.application.commands.verify_dossier_evidence import verify_dossier_evidence_links
from awf.domain.agent_execution import AgentTask
from awf.domain.checkpoints import SignedLedgerCheckpoint, parse_checkpoint_policy
from awf.domain.evidence import EvidenceKind
from awf.domain.reviewer_auth import (
    ReviewerRole,
    SignedReviewerClaim,
    parse_trust_policy,
)
from awf.knowledge.adjudication_dossiers import audit_private_dossiers
from awf.knowledge.audit import audit_registry
from awf.verification.exact_checks import parse_contract, verify_exact_invariants
from awf.verification.historical_pilot import PILOT_IDS, run_historical_pilot


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
    pilot_parser = operations.add_parser(
        "pilot", help="measure exact-invariant scope on pinned private historical ledger"
    )
    pilot_parser.add_argument("archive", type=Path)
    pilot_parser.add_argument(
        "--manifest", type=Path, default=Path("provenance/source-manifest.json")
    )
    pilot_parser.add_argument("--source-id", default="aws-3.19.1")
    review_plan = operations.add_parser(
        "plan-review",
        help="prepare private, source-bound review batches (not approvals)",
    )
    review_plan.add_argument("archive", type=Path, help="local original AWS ZIP")
    review_plan.add_argument(
        "--manifest", type=Path, default=Path("provenance/source-manifest.json")
    )
    review_plan.add_argument("--source-id", default="aws-3.19.1")
    review_plan.add_argument("--batch-size", type=int, default=12)
    dossiers = operations.add_parser(
        "inspect-review",
        help="inspect local review annotations without approving rules",
    )
    dossiers.add_argument("archive", type=Path, help="original SHA-pinned private AWS ZIP")
    dossiers.add_argument("--manifest", type=Path, default=Path("provenance/source-manifest.json"))
    dossiers.add_argument("--source-id", default="aws-3.19.1")
    dossiers.add_argument("--batch-size", type=int, default=12)
    dossiers.add_argument(
        "--require-documented",
        action="store_true",
        help="fail if any proposal is open, partial, conflicted or unsupported",
    )
    dossiers.add_argument("--evidence-database", type=Path, help="private SQLite evidence ledger")
    dossiers.add_argument("--review-run-id", help="expected ledger run for supporting evidence")
    dossiers.add_argument(
        "--expected-head", help="independently retained 64-character ledger head digest"
    )
    dossiers.add_argument(
        "--attestation-inventory",
        type=Path,
        help="private JSON of signed proposal and attestation event refs",
    )
    dossiers.add_argument(
        "--reviewer-policy",
        type=Path,
        help="private SHA-pinned reviewer authorization policy",
    )
    dossiers.add_argument("--expected-reviewer-policy-sha256")
    evidence = commands.add_parser("evidence", help="private, transactional evidence ledger")
    actions = evidence.add_subparsers(dest="evidence_action")
    writer = actions.add_parser("append", help="store evidence locally and bind an event")
    writer.add_argument("source", type=Path, help="local evidence file (max 512 KiB)")
    writer.add_argument(
        "--kind",
        required=True,
        choices=[k.value for k in EvidenceKind if k != EvidenceKind.REVIEW_ATTESTATION],
    )
    writer.add_argument("--run-id", required=True)
    writer.add_argument("--subject-id", required=True)
    writer.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    audit = actions.add_parser("verify", help="verify evidence chain and all stored bytes")
    audit.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    audit.add_argument(
        "--expected-head", help="head digest retained independently from this database"
    )
    attestor = actions.add_parser(
        "attest", help="verify and store an offline-signed reviewer claim"
    )
    attestor.add_argument("source", type=Path, help="canonical signed JSON, never a private key")
    attestor.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    attestor.add_argument("--policy-file", type=Path, required=True)
    attestor.add_argument("--expected-policy-sha256", required=True)
    attestor.add_argument("--expected-head", help="optional externally held current ledger head")
    reviewer = actions.add_parser("attest-verify", help="recheck role, signature and event binding")
    reviewer.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    reviewer.add_argument("--policy-file", type=Path, required=True)
    reviewer.add_argument("--expected-policy-sha256", required=True)
    reviewer.add_argument("--attestation-ref", required=True)
    reviewer.add_argument("--target-ref", required=True)
    reviewer.add_argument("--role", required=True, choices=[role.value for role in ReviewerRole])
    reviewer.add_argument("--run-id", required=True)
    reviewer.add_argument("--subject-id", required=True)
    reviewer.add_argument("--expected-head", help="optional externally held current ledger head")
    proposal = actions.add_parser(
        "checkpoint-propose",
        help="prepare unsigned ledger head for offline custodian signing",
    )
    proposal.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    proposal.add_argument("--ledger-id", required=True)
    proposal.add_argument("--key-id", required=True)
    proposal.add_argument("--previous-file", type=Path, help="prior signed checkpoint, if any")
    proposal.add_argument(
        "--history-file",
        type=Path,
        action="append",
        default=[],
        help="older signed checkpoint; repeat in chronological order",
    )
    proposal.add_argument("--expected-previous-sha256", help="independent witness of prior file")
    proposal.add_argument("--policy-file", type=Path, help="trusted checkpoint signer policy")
    proposal.add_argument("--expected-policy-sha256", help="independent trusted policy digest")
    checkpoint = actions.add_parser(
        "checkpoint-verify",
        help="verify externally anchored signature and ledger ancestry",
    )
    checkpoint.add_argument("source", type=Path, help="signed canonical checkpoint JSON")
    checkpoint.add_argument("--database", type=Path, default=Path(".awf/evidence/ledger.sqlite"))
    checkpoint.add_argument("--expected-checkpoint-sha256", required=True)
    checkpoint.add_argument("--policy-file", type=Path, required=True)
    checkpoint.add_argument("--expected-policy-sha256", required=True)
    checkpoint.add_argument(
        "--history-file",
        type=Path,
        action="append",
        default=[],
        help="ancestor checkpoint; repeat oldest to newest",
    )
    checkpoint.add_argument("--require-current-head", action="store_true")
    for action_name, explanation in (
        (
            "snapshot-create",
            "create a new online SQLite backup bound to a signed current head",
        ),
        ("snapshot-restore", "restore a signed SQLite snapshot to a NEW empty path"),
    ):
        snapshot = actions.add_parser(action_name, help=explanation)
        snapshot.add_argument("source", type=Path, help="live SQLite or prior snapshot")
        snapshot.add_argument("destination", type=Path, help="must be a nonexistent SQLite path")
        snapshot.add_argument("--checkpoint-file", type=Path, required=True)
        snapshot.add_argument("--expected-checkpoint-sha256", required=True)
        snapshot.add_argument("--policy-file", type=Path, required=True)
        snapshot.add_argument("--expected-policy-sha256", required=True)
        snapshot.add_argument(
            "--timeout-seconds",
            type=float,
            default=120,
            help="bounded online backup transfer time (1–3600 seconds)",
        )
        snapshot.add_argument(
            "--history-file",
            type=Path,
            action="append",
            default=[],
            help="complete signed ancestors, oldest first",
        )
    agent = commands.add_parser(
        "agent-run", help="explicitly execute a bounded localhost model and store a private receipt"
    )
    agent.add_argument("prompt_file", type=Path)
    agent.add_argument("--model", required=True)
    agent.add_argument("--temperature", type=float, default=0.0)
    agent.add_argument("--seed", type=int, default=42)
    agent.add_argument("--max-output-tokens", type=int, default=128)
    agent.add_argument("--allow-local-inference", action="store_true")
    exact = commands.add_parser(
        "verify-exact", help="verify SHA-pinned protected literals without semantic approval"
    )
    exact.add_argument("baseline", type=Path)
    exact.add_argument("candidate", type=Path)
    exact.add_argument("--contract", type=Path, required=True)
    exact.add_argument("--expected-contract-sha256", required=True)
    return parser


def _read_private_auth_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 * 1024:
        raise ValueError("authorization input must be a bounded regular non-symlinked file")
    return path.read_bytes()


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
        try:
            if output is not None and (
                output.resolve() == source.resolve()
                or (output.exists() and source.exists() and output.samefile(source))
            ):
                print(
                    "AWF_ERROR [SOURCE_PROTECTED] output cannot overwrite source",
                    file=sys.stderr,
                )
                return 2
            store = FileBlobStore(args.store) if args.store is not None else None
            document = ingest_document(source, parser=MarkdownAdapter(), blob_store=store)
            representation = json.dumps(document.to_dict(), ensure_ascii=False, indent=2) + "\n"
            if output is not None:
                output.parent.mkdir(parents=True, exist_ok=True)
                # A crash while writing must leave the prior output complete.
                fd, temporary_name = tempfile.mkstemp(prefix=".awf-", dir=output.parent)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(representation)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary_name, output)
                finally:
                    Path(temporary_name).unlink(missing_ok=True)
            else:
                print(representation, end="")
            return 0
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"AWF_ERROR [INGEST_FAILED] {exc}", file=sys.stderr)
            return 2

    if args.command == "agent-run":
        try:
            if not args.allow_local_inference:
                raise ValueError("explicit --allow-local-inference is required")
            task_path: Path = args.prompt_file
            if (
                task_path.is_symlink()
                or not task_path.is_file()
                or not 1 <= task_path.stat().st_size <= 32 * 1024
            ):
                raise ValueError("agent task must be a bounded, regular non-symlinked file")
            task = AgentTask(
                prompt=task_path.read_bytes(),
                model_id=args.model,
                temperature=args.temperature,
                seed=args.seed,
                max_output_tokens=args.max_output_tokens,
            )
            privacy_root = Path(".awf") / "agent-execution"
            for path in (
                privacy_root.parent,
                privacy_root,
                privacy_root / "blobs",
                privacy_root / "receipts",
            ):
                if path.is_symlink():
                    raise ValueError("agent output directories cannot be symbolic links")
            output, receipt = run_instrumented_agent(task, OllamaLocalAgent())
            if receipt["execution_transport"] != "LOCAL_OLLAMA_HTTP":
                raise ValueError("model transport is not a local HTTP execution")
            digest = FileBlobStore(privacy_root / "blobs").put(output)
            if digest != receipt["result_sha256"]:
                raise ValueError("stored candidate hash mismatch")
            destination = privacy_root / "receipts" / f"{uuid4().hex}.json"
            if destination.exists() or destination.is_symlink():
                raise ValueError("generated receipt path already exists")
            save_registry(destination, receipt)
            print(
                json.dumps(
                    {
                        "status": "LOCAL_GENERATION_OBSERVED",
                        "receipt_file": str(destination),
                        "output_sha256": digest,
                        "prompt_sha256": receipt["task_sha256"],
                        "model_id": receipt["reported_model_id"],
                        "generated_tokens_reported": receipt["generated_tokens_reported"],
                        "elapsed_client_ns": receipt["elapsed_client_ns"],
                        "document_acceptance": "NEEDS_REVIEW",
                        "model_weights_verified": False,
                        "training_authorized": False,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0
        except (OSError, ValueError, RuntimeError, TypeError) as exc:
            print(f"AWF_ERROR [AGENT_EXECUTION_FAILED] {type(exc).__name__}", file=sys.stderr)
            return 2

    if args.command == "verify-exact":
        try:
            import hashlib

            def checked_bytes(path: Path, bound: int) -> bytes:
                if path.is_symlink() or not path.is_file() or path.stat().st_size > bound:
                    raise ValueError("verification requires a bounded regular non-symlinked file")
                return path.read_bytes()

            raw_contract = checked_bytes(args.contract, 64 * 1024)
            digest = hashlib.sha256(raw_contract).hexdigest()
            if (
                not isinstance(args.expected_contract_sha256, str)
                or len(args.expected_contract_sha256) != 64
                or digest != args.expected_contract_sha256
            ):
                raise ValueError("externally pinned contract SHA-256 mismatch")
            policy = parse_contract(json.loads(raw_contract.decode("utf-8")))
            baseline = checked_bytes(args.baseline, 2 * 1024 * 1024)
            candidate = checked_bytes(args.candidate, 2 * 1024 * 1024)
            result = verify_exact_invariants(baseline, candidate, policy)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0 if result["scope_status"] == "PASS" else 1
        except (ValueError, OSError, TypeError) as exc:
            print(f"AWF_ERROR [EXACT_VERIFICATION_FAILED] {type(exc).__name__}", file=sys.stderr)
            return 2

    if args.command == "knowledge":
        if args.knowledge_action == "pilot":
            try:
                loaded_knowledge = PinnedAwsArchive().load(
                    archive_path=args.archive,
                    manifest_path=args.manifest,
                    source_id=args.source_id,
                )
                report = run_historical_pilot(
                    loaded_knowledge.rows,
                    source_sha256=loaded_knowledge.archive_sha256,
                    suite_version=loaded_knowledge.suite_version,
                )
                selected = [row for row in loaded_knowledge.rows if row.get("id") in PILOT_IDS]
                report["evidence_presence"] = inspect_historical_evidence(
                    args.archive,
                    expected_sha256=loaded_knowledge.archive_sha256,
                    rows=selected,
                )
                print(json.dumps(report, ensure_ascii=False, sort_keys=True))
                return 0
            except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
                print(
                    f"AWF_ERROR [HISTORICAL_PILOT_FAILED] {type(exc).__name__}",
                    file=sys.stderr,
                )
                return 2

        if args.knowledge_action == "inspect-review":
            try:
                canonical, packets = prepare_review(
                    archive_path=args.archive,
                    manifest_path=args.manifest,
                    reader=PinnedAwsArchive(),
                    source_id=args.source_id,
                    batch_size=args.batch_size,
                )
                parent = args.manifest.resolve().parent
                repo_root = parent.parent if parent.name == "provenance" else parent
                privacy_root = repo_root / ".awf"
                output_dir = (
                    privacy_root
                    / "knowledge"
                    / f"review-{canonical['archive_sha256'][:12]}-b{args.batch_size:02d}"
                )
                for path in (privacy_root, privacy_root / "knowledge", output_dir):
                    if path.is_symlink() or not path.is_dir():
                        raise ValueError("private workbench path is missing or a symbolic link")

                def read_private(path: Path) -> dict[str, object]:
                    if (
                        path.is_symlink()
                        or not path.is_file()
                        or path.stat().st_size > 4 * 1024 * 1024
                    ):
                        raise ValueError("private workbench file missing, linked or oversized")
                    value = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(value, dict):
                        raise ValueError("private workbench JSON must contain an object")
                    return value

                observed = read_private(output_dir / "manifest.json")
                actual_packets = {name: read_private(output_dir / name) for name in packets}
                report = audit_private_dossiers(
                    canonical_manifest=canonical,
                    canonical_packets=packets,
                    observed_manifest=observed,
                    observed_packets=actual_packets,
                )
                linking_options = (
                    args.evidence_database,
                    args.review_run_id,
                    args.expected_head,
                )
                links_verified: bool | None = None
                authorization_options = (
                    args.attestation_inventory,
                    args.reviewer_policy,
                    args.expected_reviewer_policy_sha256,
                )
                if any(value is not None for value in authorization_options):
                    if not all(
                        value is not None for value in (*authorization_options, *linking_options)
                    ):
                        raise ValueError(
                            "signed review requires inventory, policy and all evidence flags"
                        )
                    reviewer_policy = parse_trust_policy(
                        _read_private_auth_file(args.reviewer_policy),
                        expected_sha256=args.expected_reviewer_policy_sha256,
                    )
                    inventory = parse_dossier_attestation_inventory(
                        _read_private_auth_file(args.attestation_inventory)
                    )
                    credential_result = verify_authorized_dossier_proposals(
                        canonical_manifest=canonical,
                        canonical_packets=packets,
                        observed_manifest=observed,
                        observed_packets=actual_packets,
                        store=SQLiteEvidenceLedger(args.evidence_database),
                        run_id=args.review_run_id,
                        expected_head=args.expected_head,
                        attestation_refs=inventory,
                        policy=reviewer_policy,
                        verifier=Ed25519ReviewerVerifier(),
                        now=int(datetime.now(UTC).timestamp()),
                    )
                    report["signed_review"] = {
                        "checked": credential_result.checked,
                        "unverified_rule_ids": list(credential_result.unverified),
                        "credentials_authorized": credential_result.authorization_verified,
                        "independent_adjudication_proven": False,
                        "review_attestation_authorized": False,
                        "training_authorized": False,
                    }
                    links_verified = credential_result.authorization_verified
                elif any(option is not None for option in linking_options):
                    if not all(option is not None for option in linking_options):
                        raise ValueError(
                            "evidence linking requires database, run ID and independently held head"
                        )
                    ledger = SQLiteEvidenceLedger(args.evidence_database)
                    links = verify_dossier_evidence_links(
                        canonical_manifest=canonical,
                        canonical_packets=packets,
                        observed_packets=actual_packets,
                        store=ledger,
                        run_id=args.review_run_id,
                        expected_head=args.expected_head,
                    )
                    report["evidence_links"] = links.to_dict()
                    links_verified = links.all_declared_links_verified
                print(json.dumps(report, ensure_ascii=False))
                counts = report["status_counts"]
                if not isinstance(counts, dict):
                    raise ValueError("invalid dossier status counts")
                documented = counts.get("PROPOSAL_DOCUMENTED", 0)
                documented_pass = (
                    not args.require_documented or documented == report["requirements_count"]
                )
                if links_verified is not None:
                    return 0 if documented_pass and links_verified else 2
                return 0 if documented_pass else 2
            except (OSError, ValueError, RuntimeError, KeyError, TypeError, sqlite3.Error) as exc:
                print(f"AWF_ERROR [DOSSIER_INSPECTION_FAILED] {exc}", file=sys.stderr)
                return 2

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
                save_review_workbench(output_dir, overview=overview, packets=packets)
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
                    "AWF_ERROR [SOURCE_PROTECTED] output conflicts with an input",
                    file=sys.stderr,
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

        parser.error("expected knowledge import, plan-review, inspect-review or audit")
        return 2

    if args.command == "evidence":
        if args.evidence_action in {"snapshot-create", "snapshot-restore"}:
            try:
                protected = (
                    args.source,
                    args.checkpoint_file,
                    args.policy_file,
                    *args.history_file,
                )
                if any(args.destination.resolve() == path.resolve() for path in protected):
                    raise ValueError("snapshot destination would overwrite an input")
                signed = SignedLedgerCheckpoint.from_bytes(
                    _read_private_auth_file(args.checkpoint_file)
                )
                history = tuple(
                    SignedLedgerCheckpoint.from_bytes(_read_private_auth_file(path))
                    for path in args.history_file
                )
                policy = parse_checkpoint_policy(
                    _read_private_auth_file(args.policy_file),
                    expected_sha256=args.expected_policy_sha256,
                )
                result = create_verified_snapshot(
                    store=SQLiteEvidenceLedger(args.source),
                    writer=SQLiteSnapshotWriter(args.source, timeout_seconds=args.timeout_seconds),
                    destination=args.destination,
                    signed=signed,
                    expected_signed_sha256=args.expected_checkpoint_sha256,
                    policy=policy,
                    verifier=Ed25519ReviewerVerifier(),
                    now=int(datetime.now(UTC).timestamp()),
                    history=history,
                )
                print(
                    json.dumps(
                        {
                            "status": "SNAPSHOT_BACKUP_CREATED"
                            if args.evidence_action == "snapshot-create"
                            else "SNAPSHOT_RESTORED_TO_NEW_PATH",
                            "destination": str(result.destination),
                            "event_count": result.event_count,
                            "head_digest": result.head_digest,
                            "snapshot_file_sha256": result.file_sha256,
                            "external_custody_proven": result.independently_custodied,
                        }
                    )
                )
                return 0
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                print(f"AWF_ERROR [SNAPSHOT_FAILED] {exc}", file=sys.stderr)
                return 2

        if args.evidence_action in {"checkpoint-propose", "checkpoint-verify"}:
            try:
                store = SQLiteEvidenceLedger(args.database)
                now = int(datetime.now(UTC).timestamp())
                previous = None
                history = tuple(
                    SignedLedgerCheckpoint.from_bytes(_read_private_auth_file(path))
                    for path in args.history_file
                )
                if args.evidence_action == "checkpoint-propose":
                    has_previous = args.previous_file is not None
                    # A linked proposal must prove that its parent was actually
                    # authorized, pinned and present in the ledger.
                    provided = (
                        args.expected_previous_sha256 is not None,
                        args.policy_file is not None,
                        args.expected_policy_sha256 is not None,
                    )
                    if has_previous != all(provided) or (
                        not has_previous and (any(provided) or history)
                    ):
                        raise ValueError(
                            "a previous checkpoint requires its external digest and policy"
                        )
                    if has_previous:
                        previous = SignedLedgerCheckpoint.from_bytes(
                            _read_private_auth_file(args.previous_file)
                        )
                        policy = parse_checkpoint_policy(
                            _read_private_auth_file(args.policy_file),
                            expected_sha256=args.expected_policy_sha256,
                        )
                        verify_signed_checkpoint(
                            store=store,
                            signed=previous,
                            expected_signed_sha256=args.expected_previous_sha256,
                            policy=policy,
                            verifier=Ed25519ReviewerVerifier(),
                            now=now,
                            history=history,
                        )
                    claim = propose_checkpoint(
                        store=store,
                        ledger_id=args.ledger_id,
                        key_id=args.key_id,
                        issued_at=now,
                        previous=previous,
                    )
                    # Include exact signed bytes for an independent offline signer.
                    print(
                        json.dumps(
                            {
                                "status": "CHECKPOINT_UNSIGNED_PROPOSAL",
                                "claim": claim.payload(),
                                "signing_message_hex": claim.signing_bytes.hex(),
                                "signature_verified": False,
                                "external_custody_proven": False,
                            }
                        )
                    )
                else:
                    if args.source.resolve() in {
                        args.database.resolve(),
                        args.policy_file.resolve(),
                    }:
                        raise ValueError("signed checkpoint file must differ from inputs")
                    signed = SignedLedgerCheckpoint.from_bytes(_read_private_auth_file(args.source))
                    policy = parse_checkpoint_policy(
                        _read_private_auth_file(args.policy_file),
                        expected_sha256=args.expected_policy_sha256,
                    )
                    result = verify_signed_checkpoint(
                        store=store,
                        signed=signed,
                        expected_signed_sha256=args.expected_checkpoint_sha256,
                        policy=policy,
                        verifier=Ed25519ReviewerVerifier(),
                        now=now,
                        history=history,
                        require_current_head=args.require_current_head,
                    )
                    print(
                        json.dumps(
                            {
                                "status": "SIGNED_CHECKPOINT_VALID",
                                "ledger_id": signed.claim.ledger_id,
                                "checkpoint_event_count": result.checkpoint_event_count,
                                "current_event_count": result.current_event_count,
                                "checkpoint_is_current_head": result.checkpoint_is_current_head,
                                "external_custody_proven": result.external_custody_proven,
                            }
                        )
                    )
                return 0
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                print(f"AWF_ERROR [CHECKPOINT_FAILED] {exc}", file=sys.stderr)
                return 2

        if args.evidence_action in {"attest", "attest-verify"}:
            try:
                if args.evidence_action == "attest" and args.source.resolve() in {
                    args.database.resolve(),
                    args.policy_file.resolve(),
                }:
                    raise ValueError("signed statement must not overwrite another input")
                policy = parse_trust_policy(
                    _read_private_auth_file(args.policy_file),
                    expected_sha256=args.expected_policy_sha256,
                )
                store = SQLiteEvidenceLedger(args.database)
                verifier = Ed25519ReviewerVerifier()
                now = int(datetime.now(UTC).timestamp())
                if args.evidence_action == "attest":
                    signed = SignedReviewerClaim.from_bytes(_read_private_auth_file(args.source))
                    record = append_signed_review_claim(
                        store=store,
                        signed=signed,
                        policy=policy,
                        verifier=verifier,
                        now=now,
                        expected_head=args.expected_head,
                    )
                    print(
                        json.dumps(
                            {
                                "status": "REVIEWER_ATTESTATION_RECORDED",
                                "attestation_ref": f"event:{record.digest}",
                                "actor_id": signed.claim.actor_id,
                                "policy_sha256": policy.policy_sha256,
                                "independent_adjudication_proven": False,
                            }
                        )
                    )
                else:
                    actor_id = verify_signed_review_event(
                        store=store,
                        attestation_ref=args.attestation_ref,
                        target_ref=args.target_ref,
                        expected_role=ReviewerRole(args.role),
                        run_id=args.run_id,
                        subject_id=args.subject_id,
                        policy=policy,
                        verifier=verifier,
                        now=now,
                        expected_head=args.expected_head,
                    )
                    print(
                        json.dumps(
                            {
                                "status": "REVIEWER_AUTHORIZATION_VERIFIED",
                                "actor_id": actor_id,
                                "policy_sha256": policy.policy_sha256,
                                "independent_adjudication_proven": False,
                            }
                        )
                    )
                return 0
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                print(f"AWF_ERROR [REVIEWER_AUTH_FAILED] {exc}", file=sys.stderr)
                return 2

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
