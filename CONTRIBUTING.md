# Contributing to Academic Writing Forge

This is an early-stage applied ML/software-engineering project. The current PR establishes **design**, not an implemented library.

## Workflow

1. Check `docs/AGENT_HANDOFF.md` and linked sprint issue.
2. Read `AGENTS.md` and the architecture sections that own the work.
3. Open a focused branch. For stack, database, data policy, public interface, or ML benchmark changes, document an ADR first.
4. Write tests that fail for the bug/requirement, including adverse cases. Introduce only necessary modules.
5. Run available tooling and record actual evidence; planned commands are not proof.
6. Update `docs/REQUIREMENT_TRACEABILITY.md` and `docs/AGENT_HANDOFF.md`, noting failures and unresolved questions.

## Planned Python conventions

- Python 3.12 and `uv` with committed `uv.lock` once S0 adds the package.
- Ruff for lint, import order and format; line length 100; pyright for static types; pytest and hypothesis for behavior/properties.
- `src/awf/domain` contains immutable values/policies without provider dependencies; `application` owns use cases; `adapters` implements ports. CLI/API compose components, not reimplement business rules.
- `snake_case` files and functions, `PascalCase` types, `UPPER_SNAKE_CASE` constants, typed public APIs, Google-style docstrings for nontrivial exported interfaces.
- Prefer pure functions, composition, precise error codes and tested dependency inversion; avoid generic Managers/Utils or splitting a cohesive function for an arbitrary line-count quota.
- No `except Exception: pass`; an unavailable semantic verifier returns `UNKNOWN`, not `PASS`. No decoder output may self-certify a protected invariant.
- Avoid code churn and speculative ML abstractions; benchmark the simplest baseline before adding new infrastructure.

## Planned quality commands after S0

These commands are **not yet available** until `pyproject.toml`, package and CI are implemented:

~~~shell
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -q
uv build
~~~

## Research and data governance

Never commit private manuscripts, tokens, historical corpora with uncertain redistribution rights, large checkpoints or raw training sets. Keep dataset cards, licenses, group-wise train/dev/holdout splits and model provenance. A preference example must be reviewed before use for DPO. Detector scores never override factual or source fidelity.

A PR must distinguish **implemented & tested**, **designed**, **not run**, **failed**, and **deferred** claims.
