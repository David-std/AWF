"""Explicit loopback-only Ollama /api/generate adapter, with response boundaries.

See Ollama's documented stream=false endpoint. No arbitrary URLs or remote API
keys. Reported digest/metrics are service observations, not weight attestations.
"""

from __future__ import annotations

import http.client
import json
import re
from typing import Any

from awf.domain.agent_execution import AgentTask, ProviderObservation


class OllamaLocalAgent:
    """Connect only to 127.0.0.1:11434. Never send a private task elsewhere."""

    def __init__(self, *, timeout_seconds: int = 90) -> None:
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 180:
            raise ValueError("invalid Ollama timeout")
        self.timeout_seconds = timeout_seconds

    def _exchange(self, method: str, path: str, body: bytes | None = None) -> dict[str, Any]:
        client = http.client.HTTPConnection("127.0.0.1", 11434, timeout=self.timeout_seconds)
        try:
            headers = {"Content-Type": "application/json"} if body is not None else {}
            client.request(method, path, body=body, headers=headers)
            response = client.getresponse()
            if response.status != 200:
                raise ValueError("local model HTTP request failed")
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError("local model response exceeds 1 MiB limit")
            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("unexpected Ollama response schema")
            return parsed
        except (
            OSError,
            http.client.HTTPException,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError("local model transport or response failed") from exc
        finally:
            client.close()

    def _model_digest(self, model_id: str) -> str:
        tags = self._exchange("GET", "/api/tags")
        models = tags.get("models")
        if not isinstance(models, list):
            raise ValueError("local model inventory unavailable")
        matches = [
            model for model in models if isinstance(model, dict) and model.get("name") == model_id
        ]
        if len(matches) != 1:
            raise ValueError("requested local model missing or ambiguous")
        digest = matches[0].get("digest")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("local model has no pinned reported digest")
        return digest

    def generate(self, task: AgentTask) -> ProviderObservation:
        digest_before = self._model_digest(task.model_id)
        payload = json.dumps(
            {
                "model": task.model_id,
                "prompt": task.prompt.decode("utf-8"),
                "stream": False,
                "options": {
                    "temperature": task.temperature,
                    "seed": task.seed,
                    "num_predict": task.max_output_tokens,
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        report = self._exchange("POST", "/api/generate", payload)
        if report.get("done") is not True:
            raise ValueError("Ollama did not finish the generation")
        if report.get("model") != task.model_id:
            raise ValueError("Ollama returned a different model")
        output = report.get("response")
        if not isinstance(output, str):
            raise ValueError("Ollama response contains no candidate text")
        # Verify the *reported* digest did not change during the request.
        if self._model_digest(task.model_id) != digest_before:
            raise ValueError("local model digest changed during execution")
        return ProviderObservation(
            output=output.encode("utf-8"),
            reported_model_id=task.model_id,
            reported_model_digest=digest_before,
            transport="LOCAL_OLLAMA_HTTP",
            prompt_tokens=report.get("prompt_eval_count"),
            generated_tokens=report.get("eval_count"),
            provider_total_ns=report.get("total_duration"),
            provider_load_ns=report.get("load_duration"),
        )
