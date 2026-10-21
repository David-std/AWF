"""Offline fake used only for contract tests, never for real-model evidence."""

from __future__ import annotations

from awf.domain.agent_execution import AgentTask, ProviderObservation


class OfflineFakeAgent:
    def __init__(self, response: bytes = b"SIMULATED_RESULT") -> None:
        self.response = response

    def generate(self, task: AgentTask) -> ProviderObservation:
        return ProviderObservation(
            output=self.response,
            reported_model_id=task.model_id,
            transport="OFFLINE_FAKE",
            prompt_tokens=None,
            generated_tokens=None,
        )
