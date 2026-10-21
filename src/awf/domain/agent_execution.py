"""Types for observed model execution, not declarations of semantic correctness."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

_MODEL_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
_MAX_INPUT = 32 * 1024
_MAX_OUTPUT = 128 * 1024


@dataclass(frozen=True, slots=True)
class AgentTask:
    prompt: bytes
    model_id: str
    temperature: float = 0.0
    seed: int = 42
    max_output_tokens: int = 128

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, bytes) or not 1 <= len(self.prompt) <= _MAX_INPUT:
            raise ValueError("agent prompt must have 1..32768 UTF-8 bytes")
        try:
            self.prompt.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("agent prompt is not UTF-8") from exc
        if not isinstance(self.model_id, str) or _MODEL_ID.fullmatch(self.model_id) is None:
            raise ValueError("invalid model identifier")
        if (
            not isinstance(self.temperature, (float, int))
            or not math.isfinite(self.temperature)
            or not 0 <= self.temperature <= 2
        ):
            raise ValueError("temperature must be between 0 and 2")
        if type(self.seed) is not int or not 0 <= self.seed <= 4294967295:
            raise ValueError("invalid sampler seed")
        if type(self.max_output_tokens) is not int or not 1 <= self.max_output_tokens <= 256:
            raise ValueError("max_output_tokens must be between 1 and 256")


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    output: bytes
    reported_model_id: str
    transport: str
    reported_model_digest: str | None = None
    prompt_tokens: int | None = None
    generated_tokens: int | None = None
    provider_total_ns: int | None = None
    provider_load_ns: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.output, bytes) or not 1 <= len(self.output) <= _MAX_OUTPUT:
            raise ValueError("provider output must have 1..131072 bytes")
        try:
            self.output.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("provider output is not UTF-8") from exc
        if self.transport not in {"OFFLINE_FAKE", "LOCAL_OLLAMA_HTTP"}:
            raise ValueError("unsupported execution transport")
        if not isinstance(self.reported_model_id, str) or not self.reported_model_id:
            raise ValueError("provider model identifier is missing")
        if (
            self.reported_model_digest is not None
            and re.fullmatch(r"[0-9a-f]{64}", self.reported_model_digest) is None
        ):
            raise ValueError("invalid reported model digest")
        for name in ("prompt_tokens", "generated_tokens", "provider_total_ns", "provider_load_ns"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"invalid provider metric: {name}")
