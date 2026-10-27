# Validation record

Validated locally on 23 October 2026 with CPython 3.12.14 on Linux.

## Executed checks

| Check | Result |
|---|---|
| Full pytest suite with evaluation extras installed | 25 passed; no skipped tests |
| RAGAS actual collections metrics through OpenAI-compatible HTTP fixtures | Passing and failing verdict paths verified |
| DeepEval actual metrics through JSON Schema HTTP fixtures | Passing and failing verdict paths verified |
| Malformed judge JSON | Explicit errors with no numeric fallback |
| LangSmith actual SDK local baseline/candidate experiments | Two rows per side; network calls forbidden by test |
| Offline full 48-case healthy pipeline | PASS |
| Retrieval-drop control | BLOCKED |
| Fabricated-answer control | BLOCKED |
| Recorded trace replay | Preserves release decision and numeric evaluation evidence |
| Input/metric contract failures | Missing cases, duplicates, nonfinite values, illegal skips, missing metrics and unknown metrics rejected |
| Critical-case and application latency budgets | Failure paths verified |
| HTML handling of hostile input | Escaping verified by test |
| Ruff lint and formatting | Pass |
| Exact all-extras dependency sync and dependency consistency | Pass |
| Separate minimal core-only environment | Installed from locked requirements; full demo passes without evaluation SDKs |
| Python wheel and source distribution | Built successfully; source distribution includes corpus, configuration, docs and example reports |
| GitHub workflow YAML | Parses successfully |

The SDK fixture tests call the real installed SDK metric implementations with deterministic schema responses. They verify SDK/request/response wiring and error handling. They are **not** live-model performance or judge-quality validation.

The LangSmith SDK emitted upstream deprecation/beta warnings during the tests. No project test failed as a result.

## Included offline example evidence

All rows below describe the authored synthetic corpus and extractive generator. They are not production impact measurements. Retrieval and fact metrics have 44 applicable answerable cases; safety has 48 cases and refusal has 4.

| Metric | Baseline | Candidate |
|---|---:|---:|
| Gold-document recall | 0.9091 | 1.0000 |
| Gold-document precision | 0.4886 | 0.5682 |
| Mean reciprocal rank | 0.8409 | 1.0000 |
| Literal required-fact coverage | 0.7841 | 1.0000 |
| Token support heuristic | 1.0000 | 1.0000 |
| Forbidden-phrase check | 0.9792 | 1.0000 |
| Explicit refusal contract | 1.0000 | 1.0000 |

The perfect token support score on the weaker baseline illustrates why lexical grounding alone is not enough. See `examples/healthy/report.html` and its JSON evidence for case details, hashes, denominators and confidence intervals.

## Supplied but not executed here

- Live Ollama/vLLM/hosted-model inference and judgment: requires a model server and, for hosted models, a credential.
- LangSmith remote upload: requires a user's explicit export command and credential. The local SDK path was tested.
- Docker image build/run: Docker is unavailable in the build environment.
- GitHub-hosted workflow execution and Python 3.11/3.13 matrix runs: workflow files are provided; no remote push or Actions run was performed.
- Browser-based report rendering/filter interaction: a browser binary was unavailable, and its download failed. HTML generation/escaping was tested; the screenshot is not claimed as verified.

Before adding quantitative resume claims, run the live configuration against independently reviewed application data and retain the resulting reports and model/server settings.
