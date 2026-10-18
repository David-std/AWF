# Academic Writing Forge (AWF)

**AWF Neural Engine** is an engineering and machine-learning project for traceable academic text revision in Spanish and English. The goal is to preserve meaning, citations, evidence, and author intent while comparing pretrained editors, fine-tuned models, and explicit verification policies.

**Status on the S2 feature branch: S0–S1 core and the first local-only knowledge compiler slice are implemented.** The 168 mandatory historic rules are **not yet adjudicated**; the neural editor, independent semantic verifier, training and external API are **not implemented**. This repository maintains research provenance without claiming detector performance.

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

## Knowledge Compiler (Sprint 2, initial implementation)

```shell
uv run awf knowledge import "/private/path/academic_writing_suite_v3_19_1_product(1).zip" \\
  --manifest provenance/source-manifest.json \\
  --output .awf/knowledge/registry.json
uv run awf knowledge audit .awf/knowledge/registry.json \\
  --archive "/private/path/academic_writing_suite_v3_19_1_product(1).zip"
```

The source ZIP remains local. Only SHA-bound metadata is written to a private ignored directory, not the rule descriptions. The first import is deliberately conservative: **168 MUST → UNRESOLVED** and **16 DEFERRED_LAB → EVAL_ONLY**, with all 184 IDs retained. Rules are not silently made executable or admitted into training. [Read the S2 contract](docs/KNOWLEDGE_COMPILER_S2.md).

This is an initial S2 slice, **not** completed semantic adjudication. [Implementation PR #13](https://github.com/David-std/AWF/pull/13) is stacked upon [#12](https://github.com/David-std/AWF/pull/12), [#11](https://github.com/David-std/AWF/pull/11) and [#10](https://github.com/David-std/AWF/pull/10).

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

## Stateful audit prototype (Sprint 2, not a production verifier)

[PR #15](https://github.com/David-std/AWF/pull/15) introduces a pure, model-independent revision-state prototype covering candidate transfers of historic DSR-001..015. It requires an explicit nonempty audit inventory, binds receipts to current hashes, invalidates dependent checks after edits, tracks open findings, and gates convergence on distinct documented clean sweeps and budgets. See the [15-rule review](docs/reviews/STATEFUL_RUNTIME_DSR001_015.md) and [ADR-0010](docs/adr/0010-revision-audit-prototype.md).

The prototype does **not** establish semantic correctness, genuine independent critic isolation, source permissions, persistent audit proofs, a neural model, or finished migration of AWS rules. It is stacked on PRs #10–#14 and is not necessarily in `main` until merged.

## Knowledge integrity gates — Sprint 2 prototype

[PR #16](https://github.com/David-std/AWF/pull/16) adds source-byte and chunk-to-EOF inventories, nonempty expected coverage, explicit AVAILABLE/READ/UNDERSTOOD/APPLICABLE/APPLIED/VERIFIED evidence stages, calibration with positive/near-miss/counterexample/holdout cases, source-pinned cards, critical dependency closure and separately reported token efficiency vs fidelity evidence. See [the 17-rule audit](docs/reviews/KNOWLEDGE_INTEGRITY_DSR016_032.md) and [ADR-0011](docs/adr/0011-knowledge-integrity-gates.md).

**Boundary:** a valid receipt is *not* proof that a person or model read and understood the material. Nor is it a license to reuse private texts, an academic-correctness certificate, a fine-tuned neural model, or a verified detector result. The historical corpus stays private.
