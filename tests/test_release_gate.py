import asyncio
import copy
import json

import pytest
from pydantic import ValidationError

from rag_release_gate.cli import main
from rag_release_gate.gate import assess, paired_interval
from rag_release_gate.io import load_jsonl, load_traces
from rag_release_gate.metrics import builtin_scores
from rag_release_gate.models import Case, Score, Trace
from rag_release_gate.pipeline import Pipeline
from rag_release_gate.retrieval import BM25
from rag_release_gate.runner import run


def run_profile(root, tmp_path, candidate="candidate"):
    return asyncio.run(
        run(
            root / "data/cases.jsonl",
            root / "data/corpus.jsonl",
            root / "configs/offline.yaml",
            tmp_path / candidate,
            candidate=candidate,
        )
    )


def test_full_pipeline_passes_and_writes_replayable_evidence(root, tmp_path):
    report = run_profile(root, tmp_path)
    assert report["gate"]["passed"], report["gate"]["violations"]
    assert report["gate"]["case_count"] == 48
    assert report["gate"]["metrics"]["retrieval.recall"]["candidate"] == 1
    assert len(report["provenance"]["dataset_sha256"]) == 64
    assert report["provenance"]["judge"] is None
    assert all(not name.startswith(("ragas.", "deepeval.")) for name in report["gate"]["metrics"])
    assert {
        "report.html",
        "report.json",
        "summary.md",
        "junit.xml",
        "baseline.jsonl",
        "candidate.jsonl",
    } <= {p.name for p in (tmp_path / "candidate").iterdir()}


@pytest.mark.parametrize("profile", ["broken", "hallucination"])
def test_intentionally_bad_candidates_block_release(root, tmp_path, profile):
    report = run_profile(root, tmp_path, profile)
    assert not report["gate"]["passed"]
    assert any("critical" in reason for reason in report["gate"]["violations"])


def test_pipeline_does_not_read_gold_labels(inputs):
    cases, docs, cfg = inputs
    pipeline = Pipeline(BM25(docs), cfg.profiles["candidate"])
    case = cases[0]
    before = pipeline.answer(case.id, case.question)
    case.reference = "The moon is made of cheese."
    case.required_phrases = ["cheese"]
    after = pipeline.answer(case.id, case.question)
    assert before.answer == after.answer
    assert before.contexts == after.contexts


def test_replay_preserves_scores_and_rejects_partial_sets(root, tmp_path):
    first = run_profile(root, tmp_path)
    replay = asyncio.run(
        run(
            root / "data/cases.jsonl",
            root / "data/corpus.jsonl",
            root / "configs/offline.yaml",
            tmp_path / "replay",
            replay=(tmp_path / "candidate/baseline.jsonl", tmp_path / "candidate/candidate.jsonl"),
        )
    )
    assert first["gate"] == replay["gate"]
    cases, _, _ = __import__("rag_release_gate.io", fromlist=["load_inputs"]).load_inputs(
        root / "data/cases.jsonl", root / "data/corpus.jsonl", root / "configs/offline.yaml"
    )
    with pytest.raises(ValueError, match="exactly match"):
        load_traces(tmp_path / "candidate/candidate.jsonl", cases[:1])


def sample_scores(inputs):
    cases, docs, cfg = inputs
    cases = cases[:2]
    pipeline = Pipeline(BM25(docs), cfg.profiles["candidate"])
    traces = {c.id: pipeline.answer(c.id, c.question) for c in cases}
    scores = {c.id: builtin_scores(c, traces[c.id]) for c in cases}
    return (
        cases,
        {"baseline": traces, "candidate": copy.deepcopy(traces)},
        {"baseline": scores, "candidate": copy.deepcopy(scores)},
        cfg.policy,
    )


def test_judge_or_generation_errors_never_become_success(inputs):
    cases, traces, scores, policy = sample_scores(inputs)
    scores["baseline"][cases[0].id][0] = Score(metric="retrieval.recall", error="Judge failed")
    result = assess(cases, traces, scores, policy, "builtin")
    assert not result["passed"]
    assert result["metrics"]["retrieval.recall"]["n"] == 1
    assert result["metrics"]["retrieval.recall"]["expected"] == 2


def test_illegal_metric_skip_and_unknown_policy_fail_closed(inputs):
    cases, traces, scores, policy = sample_scores(inputs)
    scores["candidate"][cases[0].id][0] = Score(metric="retrieval.recall", applicable=False)
    with pytest.raises(ValueError, match="illegal metric skip"):
        assess(cases, traces, scores, policy, "builtin")
    policy.minimums["ragas.imaginary_metric"] = 0.9
    with pytest.raises(ValueError, match="unknown metric"):
        assess(cases, traces, scores, policy, "builtin")


def test_missing_and_duplicate_metrics_are_not_averaged_away(inputs):
    cases, traces, scores, policy = sample_scores(inputs)
    scores["candidate"][cases[0].id].pop()
    with pytest.raises(ValueError, match="contract mismatch"):
        assess(cases, traces, scores, policy, "builtin")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_scores_rejected(value):
    with pytest.raises(ValidationError):
        Score(metric="test", value=value)


def test_missing_score_needs_explicit_error():
    with pytest.raises(ValidationError):
        Score(metric="test")


def test_duplicate_contexts_and_nonfinite_latency_rejected():
    with pytest.raises(ValidationError):
        Trace(
            case_id="x",
            answer="x",
            latency_ms=1,
            contexts=[{"id": "a", "text": "one"}, {"id": "a", "text": "two"}],
        )
    with pytest.raises(ValidationError):
        Trace(case_id="x", answer="x", latency_ms=float("nan"))


def test_bootstrap_keeps_pairs_and_is_reproducible():
    pairs = [("a", 0.1, 0.3), ("a", 0.2, 0.4), ("b", 0.7, 0.9)]
    interval = paired_interval(pairs, samples=200, seed=41)
    assert interval == paired_interval(pairs, samples=200, seed=41)
    assert interval["low"] == pytest.approx(0.2)
    assert interval["high"] == pytest.approx(0.2)
    assert interval["groups"] == 2


def test_duplicate_dataset_id_rejected(root, tmp_path):
    line = (root / "data/cases.jsonl").read_text().splitlines()[0]
    path = tmp_path / "duplicate.jsonl"
    path.write_text(line + "\n" + line)
    with pytest.raises(ValueError, match="Duplicate IDs"):
        load_jsonl(path, Case)


def test_report_escapes_user_supplied_html(root, tmp_path):
    cases = [json.loads(line) for line in (root / "data/cases.jsonl").read_text().splitlines()]
    cases[0]["question"] += " <img src=x onerror=alert(1)>"
    path = tmp_path / "cases.jsonl"
    path.write_text("\n".join(json.dumps(c) for c in cases))
    asyncio.run(
        run(path, root / "data/corpus.jsonl", root / "configs/offline.yaml", tmp_path / "report")
    )
    text = (tmp_path / "report/report.html").read_text()
    assert "<img src=x onerror" not in text
    assert "&lt;img src=x onerror" in text


def test_cli_exit_codes(root, tmp_path, monkeypatch):
    monkeypatch.chdir(root)
    assert main(["run", "--output", str(tmp_path / "pass")]) == 0
    assert main(["run", "--candidate", "broken", "--output", str(tmp_path / "fail")]) == 1
    assert main(["run", "--limit", "0"]) == 2
    assert (
        main(["run", "--engine", "ragas", "--limit", "1", "--output", str(tmp_path / "no-env")])
        == 2
    )


def test_candidate_p95_latency_is_a_release_budget(inputs):
    cases, traces, scores, policy = sample_scores(inputs)
    for trace in traces["candidate"].values():
        trace.latency_ms = policy.max_p95_latency_ms + 1
    assert not assess(cases, traces, scores, policy, "builtin")["passed"]
