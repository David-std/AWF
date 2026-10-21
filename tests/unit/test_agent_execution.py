"""Agent execution is a measured transport event, not self-reported academic validity."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
from pathlib import Path

import pytest

from awf.adapters.models.offline_fake import OfflineFakeAgent
from awf.adapters.models.ollama_local import OllamaLocalAgent
from awf.application.commands.run_agent import run_instrumented_agent
from awf.domain.agent_execution import AgentTask, ProviderObservation

MODEL = "qwen2.5:7b-instruct"
DIGEST = "a" * 64


def _task() -> AgentTask:
    return AgentTask(
        prompt=b"Compute 2 + 2.",
        model_id=MODEL,
        temperature=0,
        seed=42,
        max_output_tokens=12,
    )


def test_fake_execution_measures_observed_bytes_but_is_not_real_inference() -> None:
    times = iter([100, 960])
    output, receipt = run_instrumented_agent(
        _task(), OfflineFakeAgent(b"4"), clock_ns=lambda: next(times)
    )
    assert output == b"4"
    assert receipt["elapsed_client_ns"] == 860
    assert receipt["task_sha256"] == hashlib.sha256(_task().prompt).hexdigest()
    assert receipt["result_sha256"] == hashlib.sha256(b"4").hexdigest()
    assert receipt["network_request_performed"] is False
    assert receipt["model_execution_independently_attested"] is False
    assert receipt["document_acceptance"] == "NEEDS_REVIEW"
    assert receipt["training_authorized"] is False
    assert receipt["semantic_equivalence_verified"] is False
    assert "Compute 2" not in json.dumps(receipt)


@pytest.mark.parametrize(
    "changes",
    [
        {"prompt": b""},
        {"prompt": b"x" * 32769},
        {"prompt": b"\xff"},
        {"model_id": "../qwen"},
        {"model_id": ""},
        {"temperature": math.nan},
        {"temperature": -1},
        {"seed": -1},
        {"seed": 1 << 33},
        {"max_output_tokens": 0},
        {"max_output_tokens": 257},
    ],
)
def test_invalid_agent_task_fails_closed(changes: dict[str, object]) -> None:
    params: dict[str, object] = {
        "prompt": b"Compute 2 + 2.",
        "model_id": MODEL,
        "temperature": 0.0,
        "seed": 42,
        "max_output_tokens": 12,
    }
    params.update(changes)
    with pytest.raises(ValueError):
        AgentTask(**params)


def test_provider_result_must_be_bounded_utf8_and_sane() -> None:
    with pytest.raises(ValueError, match="UTF-8"):
        ProviderObservation(output=b"\xff", reported_model_id=MODEL, transport="OFFLINE_FAKE")
    with pytest.raises(ValueError, match="metric"):
        ProviderObservation(
            output=b"4",
            reported_model_id=MODEL,
            transport="LOCAL_OLLAMA_HTTP",
            generated_tokens=True,
        )
    with pytest.raises(ValueError, match="digest"):
        ProviderObservation(
            output=b"4",
            reported_model_id=MODEL,
            transport="LOCAL_OLLAMA_HTTP",
            reported_model_digest="pretend-proof",
        )


def test_mismatched_provider_model_and_clock_rejected() -> None:
    class BadModel:
        def generate(self, task: AgentTask) -> ProviderObservation:
            return ProviderObservation(
                output=b"4", reported_model_id="other:latest", transport="OFFLINE_FAKE"
            )

    with pytest.raises(ValueError, match="does not match"):
        run_instrumented_agent(_task(), BadModel())
    with pytest.raises(ValueError, match="monotonic"):
        run_instrumented_agent(_task(), OfflineFakeAgent(b"4"), clock_ns=iter([10, 9]).__next__)


class FakeResponse:
    def __init__(self, data: dict[str, object], *, status: int = 200) -> None:
        self.status = status
        self.raw = json.dumps(data).encode("utf-8")

    def read(self, size: int) -> bytes:
        return self.raw[:size]


def _ollama_stub(monkeypatch: pytest.MonkeyPatch, *, second_digest: str = DIGEST) -> list:
    import http.client

    seen: list[tuple[object, ...]] = []

    class FakeConnection:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert (host, port) == ("127.0.0.1", 11434)
            seen.append(("connect", host, port, timeout))

        def request(
            self,
            method: str,
            path: str,
            body: bytes | None = None,
            headers: dict[str, str] | None = None,
        ) -> None:
            seen.append((method, path, body))

        def getresponse(self) -> FakeResponse:
            method, path, body = seen[-1]
            if (method, path) == ("POST", "/api/generate"):
                payload = json.loads(body)
                assert payload["stream"] is False
                assert payload["model"] == MODEL
                assert payload["options"] == {"temperature": 0, "seed": 42, "num_predict": 12}
                return FakeResponse(
                    {
                        "done": True,
                        "model": MODEL,
                        "response": "4",
                        "total_duration": 45000000,
                        "load_duration": 110000,
                        "prompt_eval_count": 13,
                        "eval_count": 2,
                    }
                )
            assert (method, path) == ("GET", "/api/tags")
            times = sum(item[0] == "GET" for item in seen if item[0] != "connect")
            return FakeResponse(
                {"models": [{"name": MODEL, "digest": second_digest if times == 2 else DIGEST}]}
            )

        def close(self) -> None:
            pass

    monkeypatch.setattr(http.client, "HTTPConnection", FakeConnection)
    return seen


def test_local_ollama_http_adapter_observes_real_wire_protocol(monkeypatch) -> None:
    events = _ollama_stub(monkeypatch)
    output, receipt = run_instrumented_agent(
        _task(), OllamaLocalAgent(timeout_seconds=5), clock_ns=iter([100, 500]).__next__
    )
    assert output == b"4"
    assert receipt["execution_transport"] == "LOCAL_OLLAMA_HTTP"
    assert receipt["network_request_performed"] is True
    assert receipt["provider_model_digest_reported"] == DIGEST
    assert receipt["prompt_tokens_reported"] == 13
    assert receipt["generated_tokens_reported"] == 2
    assert receipt["provider_total_ns"] == 45000000
    assert receipt["elapsed_client_ns"] == 400
    assert receipt["model_weights_verified"] is False
    assert [event[0] for event in events if event[0] != "connect"] == ["GET", "POST", "GET"]


def test_local_model_digest_change_blocks_receipt(monkeypatch) -> None:
    _ollama_stub(monkeypatch, second_digest="b" * 64)
    with pytest.raises(ValueError, match="digest changed"):
        OllamaLocalAgent().generate(_task())


def test_cli_requires_explicit_opt_in_without_contacting_model(tmp_path, monkeypatch, capsys):
    cli = importlib.import_module("awf.cli.main")
    monkeypatch.chdir(tmp_path)
    prompt = tmp_path / "task.txt"
    prompt.write_text("Compute 2 + 2.", encoding="utf-8")
    assert cli.main(["agent-run", str(prompt), "--model", MODEL]) == 2
    assert "AWF_ERROR" in capsys.readouterr().err
    assert not (tmp_path / ".awf").exists()


def test_cli_stores_private_blob_and_metadata_without_leaking_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    cli = importlib.import_module("awf.cli.main")
    monkeypatch.chdir(tmp_path)
    prompt = tmp_path / "task.txt"
    prompt.write_text("SENSITIVE-TEST-SENTENCE", encoding="utf-8")

    class FakeLocal:
        def generate(self, task: AgentTask) -> ProviderObservation:
            return ProviderObservation(
                output=b"PRIVATE-SYNTHETIC-ANSWER",
                reported_model_id=task.model_id,
                transport="LOCAL_OLLAMA_HTTP",
                reported_model_digest=DIGEST,
                generated_tokens=2,
            )

    monkeypatch.setattr(cli, "OllamaLocalAgent", FakeLocal)
    assert cli.main(["agent-run", str(prompt), "--model", MODEL, "--allow-local-inference"]) == 0
    out = capsys.readouterr().out
    assert "SENSITIVE-TEST-SENTENCE" not in out
    assert "PRIVATE-SYNTHETIC-ANSWER" not in out
    summary = json.loads(out)
    receipt = json.loads(Path(summary["receipt_file"]).read_text(encoding="utf-8"))
    assert receipt["document_acceptance"] == "NEEDS_REVIEW"
    assert receipt["model_weights_verified"] is False
    store = tmp_path / ".awf" / "agent-execution" / "blobs"
    digest = summary["output_sha256"]
    assert (store / digest[:2] / digest).read_bytes() == b"PRIVATE-SYNTHETIC-ANSWER"


def test_cli_output_directory_symlink_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    cli = importlib.import_module("awf.cli.main")
    monkeypatch.chdir(tmp_path)
    prompt = tmp_path / "task.txt"
    prompt.write_text("Safe synthetic sentence.", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (tmp_path / ".awf").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("local runner cannot create symbolic links")
    assert cli.main(["agent-run", str(prompt), "--model", MODEL, "--allow-local-inference"]) == 2
    assert "AWF_ERROR" in capsys.readouterr().err
