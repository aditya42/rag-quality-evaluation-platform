# RAG Release Gate

**Evaluate a RAG change before shipping it.** Compare baseline and candidate pipelines on the same versioned cases, inspect retrieval and answer failures, and block releases when quality regresses.

RAGAS · DeepEval · LangSmith · Python · BM25 · GitHub Actions

This repository fills the RAG-specific evaluation gap alongside the existing general LLM evaluation and prompt regression projects.

## What works in v0.1

- A real BM25 retrieval pipeline over a small synthetic enterprise support corpus.
- Baseline retrieval vs. a candidate that filters deprecated and untrusted documents.
- **RAGAS 0.4 collections metrics:** faithfulness, context precision, context recall.
- **DeepEval metrics:** faithfulness and answer relevancy, with an explicit schema-aware custom judge.
- **LangSmith:** local experiments by default; optional explicit export of baseline and candidate experiments to one dataset.
- An OpenAI-compatible generator/judge interface for Ollama, vLLM, and compatible hosted gateways.
- 48 versioned synthetic cases: 20 direct questions, 20 paraphrases, 4 unanswerable questions, 4 provenance/injection distractor cases.
- Absolute release floors, paired regression limits, critical-case checks, application p95 latency budget, and paired topic-cluster bootstrap confidence intervals.
- Replay your application's recorded traces through the same evaluation and policy.
- Self-contained HTML with filters and case evidence, JSON, Markdown, JUnit, and replayable JSONL traces.
- Key-free CI, actual SDK contract tests using deterministic HTTP fixtures, Docker packaging, and a reproducible dependency lock.

## Run the free demo first

Requires Python 3.11, 3.12, or 3.13. Commands run from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
rag-gate demo
```

On Windows, activate with `.venv\Scripts\activate`.

Expected output:

```text
Healthy: PASS; retrieval control: BLOCKED; answer control: BLOCKED
```

Open `reports/demo/healthy/report.html`. The report is a local file; no server is required. Inspect the `broken` and `hallucination` reports to see exactly why their releases were blocked.

**The free demo uses an extractive non-LLM generator and explicitly labeled builtin checks. It does not run RAGAS or DeepEval or claim to measure semantic faithfulness.** The semantic SDK integrations run only when you select them below.

## Run real RAGAS and DeepEval metrics

Install the evaluation SDKs:

```bash
python -m pip install -e '.[eval,dev]'
```

For an exact dependency resolution using [uv](https://docs.astral.sh/uv/):

```bash
uv sync --frozen --all-extras
```

This project pins a compatible LangChain 0.3 dependency family because the tested RAGAS release imports modules removed in newer LangChain releases. Do not upgrade those pins independently.

Start an OpenAI-compatible endpoint that supports JSON object output for RAGAS and JSON Schema output for DeepEval. For example, with an existing Ollama installation:

```bash
ollama pull qwen3:8b
ollama serve
```

`ollama serve` is unnecessary if the Ollama service is already running. Choose an installed instruction model with reliable structured output and sufficient context capacity. Smaller models can produce invalid JSON or weak judgments; those failures block the gate instead of substituting a score.

In a separate terminal:

```bash
export JUDGE_BASE_URL=http://localhost:11434/v1
export JUDGE_MODEL=qwen3:8b
export JUDGE_API_KEY=local-no-key
export JUDGE_TIMEOUT=120

# Start small. Each metric can make multiple model requests.
rag-gate run --engine ragas --limit 2 --concurrency 1 --output reports/ragas-smoke
rag-gate run --engine deepeval --limit 2 --concurrency 1 --output reports/deepeval-smoke

# Evaluate the full suite with both frameworks once the smoke checks work.
rag-gate run --engine both --concurrency 1 --output reports/both
```

Hosted endpoints require their API key in `JUDGE_API_KEY` and may incur model charges. No cloud endpoint is selected implicitly. A supplied endpoint must support the request contract; this is not a universal adapter for every model/provider. Local inference requires adequate memory and a running model server.

RAGAS and DeepEval scores stay separate, even when metrics have similar names. Judge models are not automatically valid: calibrate against human labels before using them as production release evidence.

## Evaluate a real model as the application generator

Use the live profile configuration and set a separate generator endpoint. It may point to the same local server or to a different model.

```bash
export GENERATOR_BASE_URL=http://localhost:11434/v1
export GENERATOR_MODEL=qwen3:8b
export GENERATOR_API_KEY=local-no-key
export GENERATOR_TIMEOUT=120

rag-gate run --config configs/live.yaml --engine both \
  --concurrency 1 --output reports/live
```

The runtime passes only the question and retrieved passages to the generator. References, required phrases, and relevant document IDs are evaluator inputs and never enter the application prompt. The literal required-phrase checks are strict and may reject valid paraphrases; adjust domain assertions or add adjudication before applying this policy to a different application.

## Replay your own RAG application's traces

Produce one JSONL file for the baseline and one for the candidate. Each selected dataset case must appear exactly once in each file:

```json
{"case_id":"RAG-001","answer":"Refund requests must be submitted within 30 days of delivery. The order receipt is required.","contexts":[{"id":"refund-window","text":"Refund requests must be submitted within 30 days of delivery. The order receipt is required for a refund."}],"latency_ms":240,"input_tokens":91,"output_tokens":27}
```

```bash
rag-gate evaluate --baseline-traces baseline.jsonl \
  --candidate-traces candidate.jsonl --engine both --output reports/replay
```

Use `--dataset`, `--corpus`, and `--config` for your own labeled corpus and policy. Gold document IDs must match your application's document IDs. Missing cases, duplicate IDs, invalid values, illegal metric skips, and unknown metrics are errors; they are never silently dropped. Failed generation traces must set `error` and may have an empty answer.

## LangSmith experiments

With the evaluation extra installed, run a local experiment from a completed report without uploading anything:

```bash
rag-gate langsmith --report reports/demo/healthy/report.json
```

To upload the paired experiment deliberately:

```bash
export LANGSMITH_API_KEY=your-key
rag-gate langsmith --report reports/both/report.json --upload
```

The upload creates a new dataset and two experiments, including questions, references, retrieved contexts, answers, and precomputed scores. No judge calls are repeated. Each export uses a unique dataset name so previous experiments are preserved. Do not upload sensitive application traces unless that data is approved for your configured LangSmith service. Raw reports remain local until you request export.

## Release behavior

| Exit code | Meaning |
|---|---|
| `0` | Candidate passes the configured policy; `demo` also verified that both negative controls were blocked |
| `1` | Release blocked by quality, critical-case, completeness, evaluation error, or latency checks |
| `2` | Invalid configuration, missing endpoint/SDK, invalid input, or another setup failure |

Policy is in `configs/offline.yaml` and `configs/live.yaml`. A candidate must pass absolute mean floors and avoid an excessive paired mean drop. Critical deterministic checks must pass individually. A bootstrap interval entirely below the allowed drop is also a failure; a wide interval is not proof of equivalence. Errors on either side block comparison. Unanswerable cases use the explicit refusal/safety contract and are excluded from semantic answer/retrieval metric denominators.

Reports preserve input hashes, selected case IDs, profiles, SDK versions, endpoint/model settings, token usage when supplied, application latency, metric reasons, and errors. Token counts are `null` for the extractive demo. No cost or model latency numbers are fabricated.

## Verification and CI

```bash
make check
make demo
```

`make check` runs lint and tests. SDK tests skip when `.[eval]` is absent. CI installs all extras and exercises the real RAGAS, DeepEval, and LangSmith Python SDKs against deterministic fixtures without credentials or model downloads. Wire fixtures validate integration behavior, not the quality of a live model's judgments. A separate manual GitHub Actions workflow runs the hosted judge when you supply its secrets and endpoint settings.

To run in Docker:

```bash
docker build -t rag-release-gate .
docker run --rm -v "$PWD/reports:/app/reports" rag-release-gate demo
```

Use `--build-arg INSTALL_EVAL=true` to include the evaluation SDKs. Container access to a host model server depends on your Docker networking configuration; configure the endpoint accordingly. The image runs as a non-root user, so a mounted reports directory must be writable by UID 10001.

## Repository layout

```text
src/rag_release_gate/   pipeline, retrieval, adapters, metrics, policy, reporting, CLI
data/                  28 synthetic documents and 48 labeled cases
configs/               offline and live profiles plus release floors
tests/                 release/replay invariants and actual SDK contract tests
scripts/               reproducible dataset builder
docs/                  architecture, dataset card, demo, portfolio positioning, validation
.github/workflows/     key-free CI and explicit hosted-judge workflow
```

## Portfolio

Suggested project title: **RAG Evaluation & Release Quality Platform — RAGAS, DeepEval, LangSmith**.

Project Bullet 
> Built a RAG regression evaluation platform integrating RAGAS and DeepEval, with optional LangSmith experiments, versioned evaluation datasets, paired baseline/candidate comparisons, and CI release gates for retrieval quality, groundedness, and critical failures.

Use measured evidence from your own runs for numerical claims. The 48-case synthetic demo and fixture tests do not establish production adoption, validated judge accuracy, security guarantees, or a business-impact improvement.

See [architecture](docs/ARCHITECTURE.md), [dataset card](docs/DATASET_CARD.md), [demo guide](docs/DEMO.md), [portfolio overlap review](docs/PORTFOLIO_REVIEW.md), [validation record](docs/VALIDATION.md), and [official SDK references](docs/REFERENCES.md).

MIT license. Author: aditya42.
