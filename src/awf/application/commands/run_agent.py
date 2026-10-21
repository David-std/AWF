"""Measure real adapter invocations; never promote a model's content to truth."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from typing import Any

from awf.application.ports import AgentExecutionPort
from awf.domain.agent_execution import AgentTask


def run_instrumented_agent(
    task: AgentTask,
    executor: AgentExecutionPort,
    *,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> tuple[bytes, dict[str, Any]]:
    """Return output bytes and a content-free receipt from an observed invocation."""
    started = clock_ns()
    observed = executor.generate(task)
    finished = clock_ns()
    if type(started) is not int or type(finished) is not int or finished < started:
        raise ValueError("invalid monotonic execution interval")
    if observed.reported_model_id != task.model_id:
        raise ValueError("provider response model does not match the pinned task")
    prompt_sha256 = hashlib.sha256(task.prompt).hexdigest()
    result_sha256 = hashlib.sha256(observed.output).hexdigest()
    receipt: dict[str, Any] = {
        "schema_version": "1.0.0",
        "task_sha256": prompt_sha256,
        "result_sha256": result_sha256,
        "requested_model_id": task.model_id,
        "reported_model_id": observed.reported_model_id,
        "provider_model_digest_reported": observed.reported_model_digest,
        "execution_transport": observed.transport,
        "network_request_performed": observed.transport == "LOCAL_OLLAMA_HTTP",
        "elapsed_client_ns": finished - started,
        "provider_total_ns": observed.provider_total_ns,
        "provider_load_ns": observed.provider_load_ns,
        "prompt_tokens_reported": observed.prompt_tokens,
        "generated_tokens_reported": observed.generated_tokens,
        "temperature_requested": task.temperature,
        "seed_requested": task.seed,
        "max_output_tokens_requested": task.max_output_tokens,
        "model_weights_verified": False,
        "model_execution_independently_attested": False,
        "independent_context_verified": False,
        "source_rights_verified": False,
        "training_authorized": False,
        "semantic_equivalence_verified": False,
        "document_acceptance": "NEEDS_REVIEW",
        "output_text_in_receipt": False,
    }
    return observed.output, receipt
