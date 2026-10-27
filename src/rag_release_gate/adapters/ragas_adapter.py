"""RAGAS 0.4 collections API: real framework metrics, kept in their own namespace."""

import asyncio

from ..metrics import JUDGES
from ..models import Case, Score, Trace
from ..providers import Endpoint
from . import configure_telemetry


class RagasAdapter:
    def __init__(self, endpoint: Endpoint, client=None):
        configure_telemetry()
        from openai import AsyncOpenAI
        from ragas.llms import llm_factory
        from ragas.metrics.collections import ContextPrecision, ContextRecall, Faithfulness

        self.client = client or AsyncOpenAI(
            api_key=endpoint.api_key,
            base_url=endpoint.base_url,
            timeout=endpoint.timeout,
            max_retries=0,
        )
        llm = llm_factory(
            endpoint.model, client=self.client, temperature=0, max_tokens=endpoint.max_tokens
        )
        self.metrics = (Faithfulness(llm=llm), ContextPrecision(llm=llm), ContextRecall(llm=llm))
        self.timeout = endpoint.timeout

    async def score(self, case: Case, trace: Trace) -> list[Score]:
        names = JUDGES["ragas"]
        if case.should_abstain:
            return [
                Score(
                    metric=n, applicable=False, reason="Abstention tested by deterministic contract"
                )
                for n in names
            ]
        contexts = [c.text for c in trace.contexts]
        if trace.error or not contexts:
            return [
                Score(metric=n, error=trace.error or "No retrieved contexts for judge")
                for n in names
            ]
        inputs = (
            {"user_input": case.question, "response": trace.answer, "retrieved_contexts": contexts},
            {
                "user_input": case.question,
                "reference": case.reference,
                "retrieved_contexts": contexts,
            },
            {
                "user_input": case.question,
                "reference": case.reference,
                "retrieved_contexts": contexts,
            },
        )
        scores = []
        for name, metric, kwargs in zip(names, self.metrics, inputs, strict=True):
            try:
                result = await asyncio.wait_for(metric.ascore(**kwargs), timeout=self.timeout)
                scores.append(
                    Score(metric=name, value=float(result.value), reason="RAGAS collections metric")
                )
            except Exception as exc:
                scores.append(
                    Score(
                        metric=name,
                        error=f"RAGAS failed ({type(exc).__name__}); no substitute score",
                    )
                )
        return scores

    async def close(self):
        await self.client.close()
