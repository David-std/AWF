"""Create owner-authored fictional mini-pairs for a training *smoke test* only.

No third-party sources, legacy AWS rules or manuscript prose are copied.
The generated private material does not establish semantic model quality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_ORIGINALS: tuple[tuple[str, str, str], ...] = (
    ("en", "The sample contained 18 observations in one group.",
     "One group contained 18 observations."),
    ("es", "La muestra estuvo conformada por 18 observaciones en un grupo.",
     "Un grupo reunió 18 observaciones."),
    ("en", "The experiment used two tests over four weeks.",
     "Two tests were conducted over four weeks."),
    ("es", "El experimento utilizó dos pruebas durante cuatro semanas.",
     "Se realizaron dos pruebas durante cuatro semanas."),
    ("en", "Only the first population was included in the evaluation.",
     "The evaluation included only the first population."),
    ("es", "Solo se consideró la primera población en la evaluación.",
     "La evaluación consideró únicamente la primera población."),
    ("en", "The findings remain limited to the selected period.",
     "The findings apply only to the selected period."),
    ("es", "Los hallazgos se limitan al periodo seleccionado.",
     "Los resultados corresponden únicamente al periodo seleccionado."),
    ("en", "Under condition A, the rate was 12 percent.",
     "The rate was 12 percent under condition A."),
    ("es", "Bajo la condición A, la tasa fue del 12 por ciento.",
     "La tasa fue del 12 por ciento bajo la condición A."),
    ("en", "The report did not examine the second condition.",
     "The second condition was not examined in the report."),
    ("es", "El informe no examinó la segunda condición.",
     "La segunda condición no fue examinada en el informe."),
)


def _encode_json(obj: object) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def make_private_smoke_dataset(destination: Path) -> str:
    if destination.is_symlink() or destination.exists():
        raise ValueError("synthetic training folder must not exist")
    destination.mkdir(parents=True, mode=0o700)
    groups: dict[str, list[str]] = {"train": [], "validation": [], "holdout": []}
    splits: dict[str, list[dict[str, str]]] = {"train": [], "validation": []}
    for index, (language, original, edited) in enumerate(_ORIGINALS):
        split = "train" if index < 8 else "validation" if index < 10 else "holdout"
        group_id = f"fictional_doc_{index:02d}"
        groups[split].append(group_id)
        if split != "holdout":
            splits[split].append({
                "id": f"fictional_pair_{index:02d}",
                "group_id": group_id,
                "language": language,
                "prompt": f"Rewrite while preserving quantities and restrictions: {original}",
                "completion": edited,
            })
    descriptors: dict[str, dict[str, object]] = {}
    for name in ("train", "validation"):
        filename = f"{name}.jsonl"
        raw = b"".join(_encode_json(row) for row in splits[name])
        (destination / filename).write_bytes(raw)
        descriptors[name] = {
            "file": filename,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "group_ids": groups[name],
        }
    # Sealed holdout bytes are NOT written to disk and NEVER sent to trainer.
    withheld_digest = hashlib.sha256(
        _encode_json({"role": "SEALED", "groups": groups["holdout"]})
    ).hexdigest()
    descriptors["holdout"] = {
        "file": "SEALED_NOT_READ",
        "sha256": withheld_digest,
        "group_ids": groups["holdout"],
    }
    manifest = {
        "schema_version": "1.0.0",
        "dataset_role": "SYNTHETIC_SMOKE",
        "source_rights": {
            "origin": "SYNTHETIC_SMOKE",
            "license": "AWF_OWNER_ORIGINAL_SYNTHETIC",
            "training_permitted": True,
            "owner_attestation": True,
        },
        "splits": descriptors,
    }
    manifest_bytes = _encode_json(manifest)
    (destination / "manifest.json").write_bytes(manifest_bytes)
    return hashlib.sha256(manifest_bytes).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create private fictional LoRA smoke samples")
    parser.add_argument("--output", type=Path, default=Path(".awf") / "neural-smoke")
    args = parser.parse_args()
    try:
        digest = make_private_smoke_dataset(args.output)
        print(json.dumps({
            "status": "SYNTHETIC_SMOKE_CREATED",
            "path": str(args.output / "manifest.json"),
            "manifest_sha256": digest,
            "source_rights_independently_verified": False,
            "holdout_material_written": False,
        }, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"AWF_ERROR [SYNTHETIC_SETUP_FAILED] {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
