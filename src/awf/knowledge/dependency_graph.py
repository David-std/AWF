"""Backward-compatible public import for the domain-level dependency graph.

The implementation lives in the domain to avoid inward dependencies on
knowledge application code. Existing callers retain this import location.
"""

from awf.domain.dependencies import KnowledgeDependencyError, dependency_closure

__all__ = ["KnowledgeDependencyError", "dependency_closure"]
