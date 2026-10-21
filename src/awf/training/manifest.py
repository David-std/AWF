"""Fail-closed training manifest and split reader; stdlib only.

A rights declaration is a recorded owner claim, NOT independently verified rights.
No training reader may open holdout; group IDs are sufficient to check segregation.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}\Z")
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
_MAX_FILE = 16 * 1024 * 1024
_MAX_SAMPLES = 50_000
_MAX_TEXT = 16_384


@dataclass(frozen=True, slots=True)
class TrainingDataset:
    role: str
    manifest_sha256: str
    train_sha256: str
    validation_sha256: str
    holdout_sha256: str
    train: tuple[dict[str, str], ...]
    validation: tuple[dict[str, str], ...]
    rights_claim: dict[str, object]
    independently_reviewed: bool = False


def _read_regular(path: Path, max_bytes: int = _MAX_FILE) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be a regular non-symlink file")
    with path.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if not data or len(data) > max_bytes:
        raise ValueError("input exceeds allowed bounds or is empty")
    return data


def _expected_hash(data: bytes, sha: str) -> None:
    if not isinstance(sha, str) or SHA256.fullmatch(sha) is None:
        raise ValueError("missing valid caller-supplied SHA256")
    if hashlib.sha256(data).hexdigest() != sha:
        raise ValueError("content hash mismatch")


def _strict_json(data: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("input must be JSON object")
    return parsed


def _local_split_path(folder: Path, filename: object) -> Path:
    if not isinstance(filename, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.jsonl", filename
    ):
        raise ValueError("split path must be one local JSONL filename")
    return folder / filename


def _validate_split(
    folder: Path,
    spec: dict[str, Any],
    *,
    split: str,
) -> tuple[tuple[dict[str, str], ...], str, set[str]]:
    if set(spec) != {"file", "sha256", "group_ids"}:
        raise ValueError("unexpected split descriptor")
    groups = spec["group_ids"]
    if (not isinstance(groups, list) or not groups or
        any(not isinstance(x, str) or IDENTIFIER.fullmatch(x) is None for x in groups)
        or len(groups) != len(set(groups))):
        raise ValueError("invalid or repeated group ID in split")
    declared = set(groups)
    if split == "holdout":
        if spec["file"] != "SEALED_NOT_READ":
            raise ValueError("holdout must remain sealed and unread")
        sha = spec["sha256"]
        if not isinstance(sha, str) or SHA256.fullmatch(sha) is None:
            raise ValueError("sealed holdout hash is required")
        return (), sha, declared
    data = _read_regular(_local_split_path(folder, spec["file"]))
    _expected_hash(data, spec["sha256"])
    examples: list[dict[str, str]] = []
    unique_ids: set[str] = set()
    found_groups: set[str] = set()
    for raw in data.splitlines():
        if len(examples) >= _MAX_SAMPLES:
            raise ValueError("too many training examples")
        row = _strict_json(raw)
        if set(row) != {"id", "group_id", "language", "prompt", "completion"}:
            raise ValueError("unknown training sample fields")
        for k in ("id", "group_id", "language", "prompt", "completion"):
            if not isinstance(row[k], str) or not row[k]:
                raise ValueError(f"invalid sample field {k}")
        if (IDENTIFIER.fullmatch(row["id"]) is None or row["id"] in unique_ids
            or row["group_id"] not in declared or row["language"] not in {"es", "en"}
            or max(len(row["prompt"]), len(row["completion"])) > _MAX_TEXT):
            raise ValueError("unsafe or duplicate training example")
        unique_ids.add(row["id"])
        found_groups.add(row["group_id"])
        examples.append(row)
    if not examples or found_groups != declared:
        raise ValueError("split does not match its declared group IDs")
    return tuple(examples), spec["sha256"], declared


def load_training_dataset(
    manifest_path: Path,
    *,
    expected_sha256: str,
    allow_synthetic_smoke: bool,
    owner_authorized: bool,
) -> TrainingDataset:
    """Validate source binding, group isolation and explicit train permissions.

    Rights and independence cannot be proved from a self-authored JSON field.
    Owner-attested text requires an explicit CLI authorization on every run.
    """
    data = _read_regular(manifest_path, max_bytes=64 * 1024)
    _expected_hash(data, expected_sha256)
    manifest = _strict_json(data)
    if set(manifest) != {"schema_version", "dataset_role", "source_rights", "splits"}:
        raise ValueError("unrecognized training manifest")
    if manifest["schema_version"] != "1.0.0":
        raise ValueError("unsupported manifest version")
    role = manifest["dataset_role"]
    if role not in {"SYNTHETIC_SMOKE", "OWNER_AUTHORED"}:
        raise ValueError("unknown or prohibited training dataset role")
    if role == "SYNTHETIC_SMOKE" and not allow_synthetic_smoke:
        raise ValueError("synthetic smoke training requires explicit opt-in")
    if role == "OWNER_AUTHORED" and not owner_authorized:
        raise ValueError("owner-authored training requires explicit authorization")
    rights = manifest["source_rights"]
    if not isinstance(rights, dict) or set(rights) != {
        "origin", "license", "training_permitted", "owner_attestation"
    }:
        raise ValueError("invalid source-rights declaration")
    if (rights["origin"] != role or rights["training_permitted"] is not True
        or rights["owner_attestation"] is not True
        or not isinstance(rights["license"], str) or not rights["license"].strip()):
        raise ValueError("training rights are not explicitly attested")
    descriptors = manifest["splits"]
    if not isinstance(descriptors, dict) or set(descriptors) != {
        "train", "validation", "holdout"
    }:
        raise ValueError("train/validation/sealed holdout are mandatory")
    if any(not isinstance(x, dict) for x in descriptors.values()):
        raise ValueError("invalid split descriptor")
    folder = manifest_path.resolve().parent
    train, train_sha, a = _validate_split(folder, descriptors["train"], split="train")
    validation, valid_sha, b = _validate_split(folder, descriptors["validation"], split="validation")
    _, holdout_sha, c = _validate_split(folder, descriptors["holdout"], split="holdout")
    if a & b or a & c or b & c:
        raise ValueError("group leakage across train/validation/holdout")
    if {row["id"] for row in train} & {row["id"] for row in validation}:
        raise ValueError("example identifier reused across train and validation")
    if (len(train) < 2 or len(validation) < 2):
        raise ValueError("minimum of two training and two validation examples required")
    return TrainingDataset(
        role=role,
        manifest_sha256=expected_sha256,
        train_sha256=train_sha,
        validation_sha256=valid_sha,
        holdout_sha256=holdout_sha,
        train=train,
        validation=validation,
        rights_claim=rights,
    )
