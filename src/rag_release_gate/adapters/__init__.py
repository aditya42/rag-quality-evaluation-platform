"""Evaluation SDKs are imported only when explicitly selected."""

import os


def configure_telemetry():
    # Disable SDK telemetry before importing SDKs. LangSmith export is a separate explicit action.
    os.environ["RAGAS_DO_NOT_TRACK"] = "true"
    os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["LANGSMITH_TRACING"] = "false"
