"""Paired execution, bounded judge concurrency, artifact provenance, and no silent fallback."""

import asyncio
import importlib.metadata
from datetime import UTC, datetime
from pathlib import Path

from .gate import assess
from .io import digest, load_inputs, load_traces
from .metrics import builtin_scores
from .pipeline import Pipeline
from .providers import Endpoint
from .reporting import write_reports
from .retrieval import BM25


async def run(
    dataset: Path,
    corpus: Path,
    config: Path,
    output: Path,
    engine="builtin",
    candidate="candidate",
    limit: int | None = None,
    category: str | None = None,
    concurrency=2,
    replay: tuple[Path, Path] | None = None,
):
    cases, documents, cfg = load_inputs(dataset, corpus, config)
    if candidate not in cfg.profiles:
        raise ValueError(f"Unknown candidate profile: {candidate}")
    if category:
        cases = [c for c in cases if c.category == category]
    if limit:
        cases = cases[:limit]
    if not cases:
        raise ValueError("Selection has no cases")
    adapters = []
    endpoint = None
    if engine != "builtin":
        endpoint = Endpoint.from_env("JUDGE")
        if engine in {"ragas", "both"}:
            from .adapters.ragas_adapter import RagasAdapter

            adapters.append(RagasAdapter(endpoint))
        if engine in {"deepeval", "both"}:
            from .adapters.deepeval_adapter import DeepEvalAdapter

            adapters.append(DeepEvalAdapter(endpoint))
    semaphore = asyncio.Semaphore(concurrency)
    traces = {}
    all_scores = {}
    generator_metadata = {}
    try:
        retriever = BM25(documents)
        for stage, profile_name in (("baseline", "baseline"), ("candidate", candidate)):
            if replay:
                stage_traces = load_traces(replay[0 if stage == "baseline" else 1], cases)
                generator_metadata[stage] = {
                    "mode": "recorded traces",
                    "sha256": digest(replay[0 if stage == "baseline" else 1]),
                }
            else:
                pipeline = Pipeline(retriever, cfg.profiles[profile_name])
                generator_metadata[stage] = (
                    pipeline.endpoint.metadata()
                    if pipeline.endpoint
                    else {"mode": "extractive non-LLM demo"}
                )

                async def generate(case, pipeline=pipeline):
                    async with semaphore:
                        return await asyncio.to_thread(pipeline.answer, case.id, case.question)

                generated = await asyncio.gather(*(generate(c) for c in cases))
                stage_traces = {t.case_id: t for t in generated}
            traces[stage] = stage_traces

            async def evaluate(case, stage_traces=stage_traces):
                async with semaphore:
                    trace = stage_traces[case.id]
                    scores = builtin_scores(case, trace)
                    for adapter in adapters:
                        scores.extend(await adapter.score(case, trace))
                    return case.id, scores

            all_scores[stage] = dict(await asyncio.gather(*(evaluate(c) for c in cases)))
    finally:
        for adapter in adapters:
            await adapter.close()
    result = assess(cases, traces, all_scores, cfg.policy, engine)
    versions = {}
    for package in ("rag-release-gate", "ragas", "deepeval", "langsmith", "openai", "pydantic"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "engine": engine,
        "candidate_profile": candidate,
        "provenance": {
            "dataset_sha256": digest(dataset),
            "corpus_sha256": digest(corpus),
            "config_sha256": digest(config),
            "case_ids": [c.id for c in cases],
            "versions": versions,
            "judge": endpoint.metadata() if endpoint else None,
            "generators": generator_metadata,
            "profiles": {
                "baseline": cfg.profiles["baseline"].model_dump(),
                "candidate": cfg.profiles[candidate].model_dump(),
            },
            "selection": {"category": category, "limit": limit},
        },
        "gate": result,
        "cases": [
            {
                "case": c.model_dump(),
                **{
                    stage: {
                        "trace": traces[stage][c.id].model_dump(),
                        "scores": [s.model_dump() for s in all_scores[stage][c.id]],
                    }
                    for stage in traces
                },
            }
            for c in cases
        ],
    }
    write_reports(output, report, traces)
    return report
