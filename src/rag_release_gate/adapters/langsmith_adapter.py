"""Export precomputed paired experiments; no judge calls or score recomputation."""

import uuid

from . import configure_telemetry


def experiment_data(report):
    from langsmith.schemas import Example

    return [
        Example(
            id=uuid.uuid5(
                uuid.NAMESPACE_URL, report["provenance"]["dataset_sha256"] + row["case"]["id"]
            ),
            dataset_id=uuid.UUID(int=0),
            inputs={"case_id": row["case"]["id"], "question": row["case"]["question"]},
            outputs={"reference": row["case"]["reference"]},
        )
        for row in report["cases"]
    ]


def export(report: dict, upload: bool, client=None):
    configure_telemetry()
    from langsmith import Client

    client = client or Client(auto_batch_tracing=False)
    suffix = uuid.uuid4().hex[:8]
    data = experiment_data(report)
    if upload:
        dataset = client.create_dataset(
            dataset_name=f"rag-release-{report['provenance']['dataset_sha256'][:12]}-{suffix}",
            description="Explicit RAG Release Gate export; includes synthetic questions, references, retrieved contexts, answers, and scores.",
        )
        client.create_examples(
            inputs=[e.inputs for e in data],
            outputs=[e.outputs for e in data],
            dataset_id=dataset.id,
        )
        data = dataset.name
    experiments = {}
    by_id = {row["case"]["id"]: row for row in report["cases"]}
    for stage in ("baseline", "candidate"):

        def target(inputs, stage=stage):
            row = by_id[inputs["case_id"]][stage]
            return {
                "answer": row["trace"]["answer"],
                "contexts": row["trace"]["contexts"],
                "scores": row["scores"],
                "latency_ms": row["trace"]["latency_ms"],
            }

        def evaluator(outputs):
            return {
                "results": [
                    {"key": s["metric"], "score": s["value"], "comment": s["reason"]}
                    for s in outputs["scores"]
                    if s["applicable"] and not s["error"]
                ]
            }

        result = client.evaluate(
            target,
            data=data,
            evaluators=[evaluator],
            experiment_prefix=f"rag-{stage}-{suffix}",
            metadata={
                "engine": report["engine"],
                "dataset_sha256": report["provenance"]["dataset_sha256"],
                "candidate_profile": report["candidate_profile"],
            },
            upload_results=upload,
            max_concurrency=1,
            blocking=True,
        )
        experiments[stage] = list(result)
    return {stage: {"rows": len(rows)} for stage, rows in experiments.items()}
