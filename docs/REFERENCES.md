# Official implementation references

Consulted 23 October 2026. This implementation uses pinned SDK versions; online documentation can describe newer behavior.

- [RAGAS faithfulness, collections API](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)
- [RAGAS context precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)
- [RAGAS context recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)
- [DeepEval faithfulness](https://deepeval.com/docs/metrics-faithfulness)
- [DeepEval answer relevancy](https://deepeval.com/docs/metrics-answer-relevancy)
- [DeepEval custom evaluation LLMs](https://deepeval.com/guides/guides-using-custom-llms)
- [LangSmith evaluation](https://docs.langchain.com/langsmith/evaluate-llm-application)
- [LangSmith local experiment results](https://docs.langchain.com/langsmith/read-local-experiment-results)
- [GitHub checkout action](https://github.com/actions/checkout)
- [GitHub setup-python action](https://github.com/actions/setup-python)
- [GitHub upload-artifact action](https://github.com/actions/upload-artifact)

Installed SDK signatures and source were also inspected, and their behavior is exercised by `tests/test_sdk_contracts.py`.
