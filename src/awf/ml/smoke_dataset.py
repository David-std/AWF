"""Strict local data boundary for non-scientific LoRA smoke training.

A self-labelled synthetic file is NOT proof of legal rights, authorship, or
independent annotation. This interface deliberately refuses real training.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,79}\Z")
_MAX_FILE_BYTES = 256 * 1024
_MAX_TEXT_BYTES = 4096


@dataclass(frozen=True, slots=True)
class SmokeExample:
    example_id: str
    group_id: str
    language: str
    split: str
    prompt: str
    completion: str


@dataclass(frozen=True, slots=True)
class SmokeDataset:
    source_sha256: str
    train: tuple[SmokeExample, ...]
    evaluation: tuple[SmokeExample, ...]

    def summary(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "dataset_role": "LOCAL_SYNTHETIC_SMOKE_ONLY",
            "dataset_sha256": self.source_sha256,
            "train_count": len(self.train),
            "evaluation_count": len(self.evaluation),
            "language_counts": dict(sorted(Counter(
                example.language for example in (*self.train, *self.evaluation)
            ).items())),
            "group_isolation_verified": True,
            "input_provenance_independently_verified": False,
            "rights_independently_verified": False,
            "independent_gold_verified": False,
            "training_scope": "SYNTHETIC_SMOKE_ONLY",
            "academic_quality_verified": False,
            "source_text_exported": False,
        }


def _bounded_text(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.encode("utf-8")) > _MAX_TEXT_BYTES
        or "\x00" in value
    ):
        raise ValueError(f"invalid synthetic example {field}")
    return value


def load_synthetic_smoke_dataset(path: Path, expected_sha256: str) -> SmokeDataset:
    """Bind dataset to an external hash and enforce split/duplicate constraints."""
    if not isinstance(expected_sha256, str) or _SHA.fullmatch(expected_sha256) is None:
        raise ValueError("independent SHA-256 pin required")
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= _MAX_FILE_BYTES:
        raise ValueError("dataset must be a bounded regular non-symlinked file")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("dataset SHA-256 mismatch")
    try:
        source = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 dataset JSON") from exc
    if not isinstance(source, dict) or set(source) != {
        "schema_version", "dataset_role", "examples"
    } or source["schema_version"] != "1.0.0":
        raise ValueError("unsupported smoke dataset schema")
    if source["dataset_role"] != "LOCAL_SYNTHETIC_SMOKE_ONLY":
        raise ValueError("dataset role cannot authorize academic/real training")
    items = source["examples"]
    if not isinstance(items, list) or not 3 <= len(items) <= 128:
        raise ValueError("synthetic smoke dataset must contain 3..128 examples")
    examples: list[SmokeExample] = []
    groups: dict[str, str] = {}
    ids: set[str] = set()
    pairs: set[str] = set()
    for row in items:
        if not isinstance(row, dict) or set(row) != {
            "example_id", "source_group_id", "language", "split",
            "prompt", "completion", "annotation_provenance"
        }:
            raise ValueError("unexpected training example keys")
        identity = _bounded_text(row["example_id"], "ID")
        group_id = _bounded_text(row["source_group_id"], "source group")
        if _ID.fullmatch(identity) is None or identity in ids:
            raise ValueError("invalid or duplicate training example ID")
        if _ID.fullmatch(group_id) is None:
            raise ValueError("invalid source group ID")
        ids.add(identity)
        language = row["language"]
        split = row["split"]
        if language not in ("es", "en") or split not in ("train", "eval"):
            raise ValueError("invalid language or split")
        if row["annotation_provenance"] != "DEVELOPER_SYNTHETIC":
            raise ValueError("synthetic smoke cannot claim independent annotations")
        if group_id in groups and groups[group_id] != split:
            raise ValueError("source group leakage across train/eval")
        groups[group_id] = split
        prompt = _bounded_text(row["prompt"], "prompt")
        completion = _bounded_text(row["completion"], "completion")
        # Block exact normalized duplicate examples across *all* splits.
        fingerprint = hashlib.sha256((
            prompt.casefold().strip() + "\x00" + completion.casefold().strip()
        ).encode("utf-8")).hexdigest()
        if fingerprint in pairs:
            raise ValueError("duplicate prompt/completion across dataset")
        pairs.add(fingerprint)
        examples.append(SmokeExample(identity, group_id, language, split, prompt, completion))
    train = tuple(e for e in examples if e.split == "train")
    evaluation = tuple(e for e in examples if e.split == "eval")
    if len(train) < 2 or len(evaluation) < 1:
        raise ValueError("smoke dataset requires at least two train and one eval cases")
    return SmokeDataset(expected_sha256, train, evaluation)
