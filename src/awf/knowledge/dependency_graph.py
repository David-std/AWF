"""Explicit dependency closure with cycle and unknown-ID rejection."""

from __future__ import annotations


class KnowledgeDependencyError(ValueError):
    """Dependency metadata is invalid; execution must stop."""


def dependency_closure(selected: set[str], dependencies: dict[str, set[str]]) -> tuple[str, ...]:
    """Return prerequisites-before-dependents in deterministic sorted order.

    Dependencies are curated input; the engine must never guess edges from
    textual similarity, source order, or source citation overlap.
    """
    ordered: list[str] = []
    states: dict[str, int] = {}

    def visit(node: str) -> None:
        if node not in dependencies:
            raise KnowledgeDependencyError(f"unknown knowledge dependency: {node}")
        if states.get(node) == 1:
            raise KnowledgeDependencyError(f"cyclic knowledge dependency at {node}")
        if states.get(node) == 2:
            return
        states[node] = 1
        for required in sorted(dependencies[node]):
            visit(required)
        states[node] = 2
        ordered.append(node)

    for name in sorted(selected):
        visit(name)
    return tuple(ordered)
