"""Deterministic checks are labeled honestly; none impersonates a semantic LLM judge."""

import re

from .models import Case, Score, Trace
from .pipeline import REFUSAL
from .retrieval import tokens

BUILTIN = (
    "retrieval.recall",
    "retrieval.precision",
    "retrieval.mrr",
    "builtin.required_facts",
    "builtin.token_support",
    "builtin.safety",
    "builtin.refusal",
)
JUDGES = {
    "ragas": ("ragas.faithfulness", "ragas.context_precision", "ragas.context_recall"),
    "deepeval": ("deepeval.faithfulness", "deepeval.answer_relevancy"),
}


def expected_metrics(engine: str) -> tuple[str, ...]:
    if engine == "builtin":
        return BUILTIN
    if engine == "both":
        return BUILTIN + JUDGES["ragas"] + JUDGES["deepeval"]
    return BUILTIN + JUDGES[engine]


def applies(metric: str, case: Case) -> bool:
    if metric == "builtin.refusal":
        return case.should_abstain
    if metric == "builtin.safety":
        return True
    return not case.should_abstain


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def builtin_scores(case: Case, trace: Trace) -> list[Score]:
    if trace.error:
        return [
            Score(metric=m, error=trace.error)
            if applies(m, case)
            else Score(metric=m, applicable=False)
            for m in BUILTIN
        ]
    retrieved = [c.id for c in trace.contexts]
    relevant = set(case.relevant_doc_ids)
    hits = [i + 1 for i, doc_id in enumerate(retrieved) if doc_id in relevant]
    answer = normalize(trace.answer)
    coverage = sum(normalize(p) in answer for p in case.required_phrases) / max(
        1, len(case.required_phrases)
    )
    stripped = re.sub(r"\[[^\]]+\]", "", trace.answer)
    answer_tokens = set(tokens(stripped))
    context_tokens = set(tokens(" ".join(c.text for c in trace.contexts)))
    forbidden = [p for p in case.forbidden_phrases if normalize(p) in answer]
    values = {
        "retrieval.recall": len(set(retrieved) & relevant) / max(1, len(relevant)),
        "retrieval.precision": len(hits) / max(1, len(retrieved)),
        "retrieval.mrr": 1 / hits[0] if hits else 0,
        "builtin.required_facts": coverage,
        "builtin.token_support": len(answer_tokens & context_tokens) / max(1, len(answer_tokens)),
        "builtin.safety": float(not forbidden),
        "builtin.refusal": float(normalize(trace.answer) == normalize(REFUSAL)),
    }
    reasons = {
        "builtin.required_facts": "Literal normalized required-phrase coverage; not semantic correctness",
        "builtin.token_support": "Answer token containment in retrieved text; not semantic faithfulness",
        "builtin.safety": "Forbidden phrase check: "
        + (", ".join(forbidden) if forbidden else "none found"),
        "builtin.refusal": "Exact normalized abstention contract",
    }
    return [
        Score(metric=m, value=values[m], reason=reasons.get(m, "Gold document ID retrieval check"))
        if applies(m, case)
        else Score(metric=m, applicable=False, reason="Not applicable to this case type")
        for m in BUILTIN
    ]
