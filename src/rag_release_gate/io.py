"""Content-addressed JSONL inputs; reject partial and ambiguous evaluation sets."""

import hashlib
import json
from pathlib import Path

import yaml

from .models import Case, Config, Document, StrictModel, Trace


def load_jsonl(path: Path, model: type[StrictModel]):
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(model.model_validate(json.loads(line)))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid {path.name} line {number}: {exc}") from exc
    if not rows:
        raise ValueError(f"Empty input: {path}")
    ids = [r.case_id if isinstance(r, Trace) else r.id for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate IDs in {path.name}")
    return rows


def load_inputs(dataset: Path, corpus: Path, config: Path):
    cases = load_jsonl(dataset, Case)
    documents = load_jsonl(corpus, Document)
    cfg = Config.model_validate(yaml.safe_load(config.read_text(encoding="utf-8")))
    by_id = {d.id: d for d in documents}
    for case in cases:
        for doc_id in case.relevant_doc_ids:
            if doc_id not in by_id:
                raise ValueError(f"{case.id}: unknown relevant document {doc_id}")
            if by_id[doc_id].status != "active" or not by_id[doc_id].trusted:
                raise ValueError(f"{case.id}: gold document must be active and trusted")
    return cases, documents, cfg


def load_traces(path: Path, cases: list[Case]) -> dict[str, Trace]:
    traces = {t.case_id: t for t in load_jsonl(path, Trace)}
    expected = {c.id for c in cases}
    if set(traces) != expected:
        raise ValueError(
            f"Trace IDs must exactly match selected cases; missing={sorted(expected - set(traces))}, extra={sorted(set(traces) - expected)}"
        )
    return traces


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows):
    path.write_text(
        "".join(
            json.dumps(r.model_dump(), ensure_ascii=False, allow_nan=False) + "\n" for r in rows
        ),
        encoding="utf-8",
    )
