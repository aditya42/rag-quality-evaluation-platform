"""Actual SDK metrics + deterministic HTTP fixtures. These are not model benchmarks."""

import asyncio
import json

import httpx
import pytest

from rag_release_gate.adapters import configure_telemetry
from rag_release_gate.models import Context, Trace
from rag_release_gate.providers import Endpoint


def schema_output(schema, verdict=1):
    props = schema.get("properties", {})
    statement = "Refund requests must be submitted within 30 days."
    if "statements" in props:
        items = props["statements"].get("items", {})
        if items.get("type") == "string":
            return {"statements": [statement]}
        return {
            "statements": [
                {"statement": statement, "reason": "Fixture verdict", "verdict": verdict}
            ]
        }
    if "classifications" in props:
        return {
            "classifications": [
                {"statement": statement, "reason": "Fixture attribution", "attributed": verdict}
            ]
        }
    if "verdict" in props:
        return {"verdict": verdict, "reason": "Fixture context usefulness"}
    if "truths" in props:
        return {"truths": [statement]}
    if "claims" in props:
        return {"claims": [statement]}
    if "verdicts" in props:
        return {"verdicts": [{"verdict": "yes" if verdict else "no", "reason": "Fixture verdict"}]}
    if "reason" in props:
        return {"reason": "Deterministic schema contract fixture, not a real judge"}
    raise AssertionError(f"Unrecognized SDK schema: {sorted(props)}")


class WireFixture:
    def __init__(self, verdict=1, malformed=False):
        self.verdict = verdict
        self.malformed = malformed
        self.calls = []

    def __call__(self, request):
        body = json.loads(request.content)
        self.calls.append(body)
        tools = body.get("tools")
        if tools:
            function = tools[0]["function"]
            output = schema_output(function["parameters"], self.verdict)
            content = "not valid json" if self.malformed else json.dumps(output)
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_fixture",
                        "type": "function",
                        "function": {"name": function["name"], "arguments": content},
                    }
                ],
            }
            finish = "tool_calls"
        else:
            if body["response_format"]["type"] == "json_object":
                system = body["messages"][0]["content"]
                schema = json.JSONDecoder().raw_decode(system[system.index("{") :])[0]
            else:
                schema = body["response_format"]["json_schema"]["schema"]
            output = schema_output(schema, self.verdict)
            message = {
                "role": "assistant",
                "content": "not valid json" if self.malformed else json.dumps(output),
            }
            finish = "stop"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_fixture",
                "object": "chat.completion",
                "created": 0,
                "model": "fixture-model",
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
            },
        )


@pytest.mark.sdk
@pytest.mark.parametrize("verdict", [1, 0])
def test_ragas_actual_metrics_round_trip_the_openai_contract(inputs, verdict):
    pytest.importorskip("ragas")
    configure_telemetry()
    from openai import AsyncOpenAI

    from rag_release_gate.adapters.ragas_adapter import RagasAdapter

    case = inputs[0][0]
    fixture = WireFixture(verdict)
    trace = Trace(
        case_id=case.id,
        answer=case.reference,
        contexts=[Context(id="refund-window", text=case.reference)],
        latency_ms=1,
    )

    async def exercise():
        client = AsyncOpenAI(
            api_key="fixture",
            base_url="http://fixture.invalid/v1",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(fixture)),
            max_retries=0,
        )
        adapter = RagasAdapter(
            Endpoint("http://fixture.invalid/v1", "fixture-model", "fixture", timeout=5),
            client=client,
        )
        try:
            return await adapter.score(case, trace)
        finally:
            await adapter.close()

    scores = asyncio.run(exercise())
    assert all(s.error is None for s in scores), scores
    assert [s.value for s in scores] == pytest.approx([verdict] * 3)
    assert len(fixture.calls) >= 4


@pytest.mark.sdk
@pytest.mark.parametrize("verdict", [1, 0])
def test_deepeval_actual_metrics_round_trip_the_schema_contract(inputs, verdict):
    pytest.importorskip("deepeval")
    from rag_release_gate.adapters.deepeval_adapter import DeepEvalAdapter

    case = inputs[0][0]
    fixture = WireFixture(verdict)
    endpoint = Endpoint(
        "http://fixture.invalid/v1",
        "fixture-model",
        "fixture",
        timeout=5,
        transport=httpx.MockTransport(fixture),
    )
    adapter = DeepEvalAdapter(endpoint)
    trace = Trace(
        case_id=case.id,
        answer=case.reference,
        contexts=[Context(id="refund-window", text=case.reference)],
        latency_ms=1,
    )
    scores = asyncio.run(adapter.score(case, trace))
    assert all(s.error is None for s in scores), scores
    assert [s.value for s in scores] == pytest.approx([verdict] * 2)
    assert all("response_format" in call for call in fixture.calls)
    assert len(fixture.calls) >= 6


@pytest.mark.sdk
def test_malformed_judge_json_is_an_error_and_never_a_passing_score(inputs):
    pytest.importorskip("deepeval")
    from rag_release_gate.adapters.deepeval_adapter import DeepEvalAdapter

    case = inputs[0][0]
    endpoint = Endpoint(
        "http://fixture.invalid/v1",
        "fixture-model",
        "fixture",
        timeout=1,
        transport=httpx.MockTransport(WireFixture(malformed=True)),
    )
    adapter = DeepEvalAdapter(endpoint)
    trace = Trace(
        case_id=case.id,
        answer=case.reference,
        contexts=[Context(id="refund-window", text=case.reference)],
        latency_ms=1,
    )
    scores = asyncio.run(adapter.score(case, trace))
    assert all(s.error and s.value is None for s in scores)


@pytest.mark.sdk
def test_langsmith_runs_real_local_experiments_without_network(root, tmp_path, monkeypatch):
    pytest.importorskip("langsmith")
    from langsmith import Client

    from rag_release_gate.adapters.langsmith_adapter import export
    from rag_release_gate.runner import run

    report = asyncio.run(
        run(
            root / "data/cases.jsonl",
            root / "data/corpus.jsonl",
            root / "configs/offline.yaml",
            tmp_path / "report",
            limit=2,
        )
    )

    def network_forbidden(*args, **kwargs):
        raise AssertionError("Local LangSmith experiment must not make HTTP requests")

    monkeypatch.setattr("requests.Session.request", network_forbidden)
    client = Client(api_url="http://fixture.invalid", api_key="fixture", auto_batch_tracing=False)
    summary = export(report, upload=False, client=client)
    assert summary == {"baseline": {"rows": 2}, "candidate": {"rows": 2}}
