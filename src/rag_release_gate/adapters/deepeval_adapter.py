"""Schema-aware DeepEval judge over an explicitly configured compatible endpoint."""

import asyncio

from ..metrics import JUDGES
from ..models import Case, Score, Trace
from ..providers import Endpoint
from . import configure_telemetry


def compatible_judge(endpoint: Endpoint):
    configure_telemetry()
    from deepeval.models import DeepEvalBaseLLM

    class CompatibleJudge(DeepEvalBaseLLM):
        def __init__(self):
            super().__init__(model=endpoint.model)

        def load_model(self):
            return endpoint

        def get_model_name(self):
            return endpoint.model

        def generate(self, prompt: str, schema=None):
            content, _ = endpoint.complete(
                [{"role": "user", "content": prompt}],
                schema.model_json_schema() if schema else None,
            )
            return schema.model_validate_json(content) if schema else content

        async def a_generate(self, prompt: str, schema=None):
            return await asyncio.to_thread(self.generate, prompt, schema)

    return CompatibleJudge()


class DeepEvalAdapter:
    def __init__(self, endpoint: Endpoint, judge=None):
        configure_telemetry()
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric

        self.judge = judge or compatible_judge(endpoint)
        self.classes = (FaithfulnessMetric, AnswerRelevancyMetric)
        self.timeout = endpoint.timeout

    async def score(self, case: Case, trace: Trace) -> list[Score]:
        from deepeval.test_case import LLMTestCase

        names = JUDGES["deepeval"]
        if case.should_abstain:
            return [
                Score(
                    metric=n, applicable=False, reason="Abstention tested by deterministic contract"
                )
                for n in names
            ]
        if trace.error or not trace.contexts:
            return [
                Score(metric=n, error=trace.error or "No retrieved contexts for judge")
                for n in names
            ]
        test = LLMTestCase(
            input=case.question,
            actual_output=trace.answer,
            expected_output=case.reference,
            retrieval_context=[c.text for c in trace.contexts],
        )
        scores = []
        for name, metric_class in zip(names, self.classes, strict=True):
            try:
                metric = metric_class(
                    model=self.judge, include_reason=True, async_mode=True, eval_mode="llm"
                )
                await asyncio.wait_for(
                    metric.a_measure(test, _show_indicator=False), timeout=self.timeout
                )
                scores.append(
                    Score(
                        metric=name,
                        value=float(metric.score),
                        reason=metric.reason or "DeepEval metric",
                    )
                )
            except Exception as exc:
                scores.append(
                    Score(
                        metric=name,
                        error=f"DeepEval failed ({type(exc).__name__}); no substitute score",
                    )
                )
        return scores

    async def close(self):
        return None
