"""Fail-closed release policy and paired cluster bootstrap, with explicit denominators."""

import math
import random
from collections import defaultdict
from statistics import mean

from .metrics import applies, expected_metrics
from .models import Case, Policy, Score, Trace


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot compute percentile of empty values")
    index = (len(ordered) - 1) * quantile
    lower = math.floor(index)
    upper = math.ceil(index)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def paired_interval(pairs: list[tuple[str, float, float]], samples=2000, seed=42):
    """Resample topic groups, preserving paired baseline/candidate rows within each group."""
    groups = defaultdict(list)
    for group_id, baseline, candidate in pairs:
        groups[group_id].append(candidate - baseline)
    keys = sorted(groups)
    if not keys:
        return None
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        selected = [rng.choice(keys) for _ in keys]
        deltas.append(mean(v for key in selected for v in groups[key]))
    return {
        "low": percentile(deltas, 0.025),
        "high": percentile(deltas, 0.975),
        "confidence": 0.95,
        "groups": len(keys),
        "method": "paired topic-cluster percentile bootstrap",
    }


def assess(
    cases: list[Case],
    traces: dict[str, dict[str, Trace]],
    scores: dict[str, dict[str, list[Score]]],
    policy: Policy,
    engine: str,
):
    names = expected_metrics(engine)
    unknown = (
        set(policy.minimums) | set(policy.critical_metrics) | set(policy.judge_minimums)
    ) - set(expected_metrics("both"))
    if unknown:
        raise ValueError(f"Policy contains unknown metric(s): {sorted(unknown)}")
    if any(not name.startswith(("ragas.", "deepeval.")) for name in policy.judge_minimums):
        raise ValueError("judge_minimums may contain only framework judge metrics")
    if any(name.startswith(("ragas.", "deepeval.")) for name in policy.minimums):
        raise ValueError("Use judge_minimums for optional framework metrics")
    floors = dict(policy.minimums)
    floors.update({n: v for n, v in policy.judge_minimums.items() if n in names})
    if not set(names) <= set(floors):
        raise ValueError(f"Missing release floor(s): {sorted(set(names) - set(floors))}")
    violations = []
    aggregates = {}
    slices = defaultdict(dict)
    indexed = {stage: {} for stage in ("baseline", "candidate")}
    for stage in indexed:
        for case in cases:
            if traces[stage][case.id].error:
                violations.append(f"{stage}/{case.id}: generation error")
            row = scores[stage][case.id]
            by_name = {s.metric: s for s in row}
            if len(row) != len(by_name) or set(by_name) != set(names):
                raise ValueError(f"{stage}/{case.id}: evaluator metric contract mismatch")
            indexed[stage][case.id] = by_name
            for name, score in by_name.items():
                if score.applicable != applies(name, case):
                    raise ValueError(f"{stage}/{case.id}/{name}: illegal metric skip")
                if score.error:
                    violations.append(f"{stage}/{case.id}/{name}: evaluation error")
                if (
                    stage == "candidate"
                    and case.severity == "critical"
                    and score.applicable
                    and name in policy.critical_metrics
                    and (score.value is None or score.value < policy.critical_minimum)
                ):
                    violations.append(
                        f"critical {case.id}/{name}: below {policy.critical_minimum:.3f}"
                    )
    for name in names:
        applicable = [c for c in cases if applies(name, c)]
        valid = [
            c
            for c in applicable
            if indexed["baseline"][c.id][name].value is not None
            and indexed["candidate"][c.id][name].value is not None
        ]
        base_values = [indexed["baseline"][c.id][name].value for c in valid]
        cand_values = [indexed["candidate"][c.id][name].value for c in valid]
        if not applicable:
            aggregates[name] = {
                "baseline": None,
                "candidate": None,
                "delta": None,
                "n": 0,
                "expected": 0,
                "ci": None,
                "floor": floors[name],
            }
            continue
        if len(valid) != len(applicable):
            violations.append(f"{name}: incomplete paired scores {len(valid)}/{len(applicable)}")
        base_mean = mean(base_values) if valid else None
        cand_mean = mean(cand_values) if valid else None
        delta = cand_mean - base_mean if valid else None
        ci = paired_interval(
            [(c.group_id, b, a) for c, b, a in zip(valid, base_values, cand_values, strict=True)],
            policy.bootstrap_samples,
            policy.seed,
        )
        aggregates[name] = {
            "baseline": base_mean,
            "candidate": cand_mean,
            "delta": delta,
            "n": len(valid),
            "expected": len(applicable),
            "ci": ci,
            "floor": floors[name],
        }
        if cand_mean is None or cand_mean + 1e-12 < floors[name]:
            violations.append(f"{name}: candidate mean below {floors[name]:.3f}")
        if delta is not None and delta < -policy.max_mean_drop - 1e-12:
            violations.append(f"{name}: mean drop exceeds {policy.max_mean_drop:.3f}")
        if ci and ci["high"] < -policy.max_mean_drop - 1e-12:
            violations.append(f"{name}: bootstrap interval entirely below allowed drop")
        for category in sorted({c.category for c in valid}):
            selected = [c for c in valid if c.category == category]
            slices[category][name] = {
                "n": len(selected),
                "candidate": mean(indexed["candidate"][c.id][name].value for c in selected),
            }
    p95 = {
        stage: percentile([t.latency_ms for t in rows.values()], 0.95)
        for stage, rows in traces.items()
    }
    if p95["candidate"] > policy.max_p95_latency_ms:
        violations.append(f"candidate p95 latency exceeds {policy.max_p95_latency_ms:g} ms")
    return {
        "passed": not violations,
        "violations": violations,
        "metrics": aggregates,
        "slices": dict(slices),
        "p95_latency_ms": p95,
        "policy": policy.model_dump(),
        "case_count": len(cases),
    }
