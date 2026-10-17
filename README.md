# Academic Writing Forge (AWF)

**AWF Neural Engine** is an engineering and machine-learning project for traceable academic text revision in Spanish and English. The goal is to preserve meaning, citations, evidence, and author intent while comparing pretrained editors, fine-tuned models, and explicit verification policies.

**Status: design baseline v0.1 — implementation not started.** This repository intentionally begins with an architecture specification and research provenance rather than claims of working training or detector performance.

## Start here

- [Architecture specification v0.1](docs/architecture/ARCHITECTURE_SPEC_0_1.md) — authoritative proposed architecture, file ownership, interfaces, tests, datasets, and S0–S8 roadmap.
- [Decision lock](docs/architecture/DECISIONS_LOCK.yaml) — current proposals, invariants, and open decisions.
- [Agent instructions](AGENTS.md) — how to work here without losing the project history.
- [Requirement traceability](docs/REQUIREMENT_TRACEABILITY.md) — requirements, provenance, and verifiability plan.
- [Roadmap](docs/ROADMAP.md) and [current handoff](docs/AGENT_HANDOFF.md).
- [Evidence and source registry](docs/SOURCE_REGISTRY.md) — status and limitations of external references.
- [Compute plan](docs/COMPUTE_AND_TRAINING.md) — RTX 4050, Qwen baseline, and optional Google-hosted GPU.

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

> Note: the GitHub repository slug is `David-std/AWF`; the display name is **Academic Writing Forge**. Internal package and command names are planned as `awf`.
