import os
from pathlib import Path

import pytest

os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["RAGAS_DO_NOT_TRACK"] = "true"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"


@pytest.fixture
def root():
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs(root):
    from rag_release_gate.io import load_inputs

    return load_inputs(
        root / "data/cases.jsonl", root / "data/corpus.jsonl", root / "configs/offline.yaml"
    )
