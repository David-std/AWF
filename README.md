# Academic Writing Forge (AWF)

**AWF Neural Engine** is an engineering and machine-learning project for traceable academic text revision in Spanish and English. The goal is to preserve meaning, citations, evidence, and author intent while comparing pretrained editors, fine-tuned models, and explicit verification policies.

**Status on the S1 feature branch: Python CLI and conservative Markdown ingestion implemented and CI-tested.** The neural editor, knowledge compiler, semantic verifier, training and external API are **not implemented**. This repository maintains research provenance without claiming detector performance.

## Start here

- [Architecture specification v0.1](docs/architecture/ARCHITECTURE_SPEC_0_1.md) — authoritative proposed architecture, file ownership, interfaces, tests, datasets, and S0–S8 roadmap.
- [Decision lock](docs/architecture/DECISIONS_LOCK.yaml) — current proposals, invariants, and open decisions.
- [Agent instructions](AGENTS.md) — how to work here without losing the project history.
- [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md) — requirements, provenance, and verifiability plan.
- [Roadmap](docs/ROADMAP.md) and [current handoff](docs/AGENT_HANDOFF.md).
- [Evidence and source registry](docs/SOURCE_REGISTRY.md) — status and limitations of external references.
- [Compute plan](docs/COMPUTE_AND_TRAINING.md) — RTX 4050, Qwen baseline, and optional Google-hosted GPU.

## Implemented core (S0–S1)

The feature branch includes an installable Python package, CLI and deterministic Markdown ingestion. For example:

```shell
uv sync --locked
uv run awf --version
uv run awf ingest draft.md
uv run awf ingest draft.md --store .awf --output document-ir.json
```

The ingest command reads **original UTF-8 bytes** and returns a content-addressed DocumentIR (SHA-256, blocks, inclusive line positions). `--store` is opt-in private local storage; the original file is never modified. The initial parser recognizes ATX headings, paragraphs and fenced code only; it is not a full CommonMark parser or a semantic verifier.

S0: [PR #11](https://github.com/David-std/AWF/pull/11) · S1: [PR #12](https://github.com/David-std/AWF/pull/12). Both are stacked upon [architecture PR #10](https://github.com/David-std/AWF/pull/10); changes are **not necessarily present on main until merged**.

## Engineering principles

1. **Verification before claims:** model output does not certify itself. A critical failure rejects the change; a critical unknown requires review.
2. **No destructive migration:** AWS 3.19.1 remains an immutable upstream research baseline, subject to provenance and licensing checks before import.
3. **Models are interchangeable:** start with a deterministic dummy adapter, measure pretrained baselines, then train PEFT adapters only when justified.
4. **Reproducible comparisons:** preserve document-level partitions, benchmark holdouts, source/model licenses, run manifests, adverse cases, and negative results.
5. **Scope first:** modular Python monolith with hexagonal boundaries and lightweight command/query separation; no premature distributed services.

## Planned development

S0: repository, CLI, tooling and CI → S1: immutable DocumentIR → S2: knowledge compiler → S3: independent verification → S4: model baselines → S5: SFT/QLoRA → S6: optional DPO/ablations → S7: API → S8: optional detector research.

No AI-detector bypass rate is claimed. Detector outputs, if studied, remain separate from the primary requirements of academic correctness, fidelity, and citation integrity.

## Research and licenses

Some research datasets, model checkpoints, academic texts, and commercial service outputs have use restrictions. No third-party corpus, provider outputs, model weights, proprietary suite archive, or user manuscript is committed here by default. The project's **code license is intentionally undecided** until reuse constraints are reviewed.

> Note: the GitHub repository slug is `David-std/AWF`; the display name is **Academic Writing Forge**. Internal package and command names are `awf` in the S0–S1 implementation.
