"""Validated contracts shared by retrieval, evaluation, replay, and reporting."""

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Document(StrictModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    status: Literal["active", "deprecated"] = "active"
    trusted: bool = True


class Case(StrictModel):
    id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    relevant_doc_ids: list[str] = Field(default_factory=list)
    required_phrases: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    category: str = Field(min_length=1)
    severity: Literal["normal", "critical"] = "normal"
    should_abstain: bool = False

    @model_validator(mode="after")
    def meaningful_gold(self):
        if self.should_abstain:
            if self.relevant_doc_ids or self.required_phrases:
                raise ValueError(
                    "Abstention cases must not have relevant documents or required facts"
                )
        elif not self.relevant_doc_ids or not self.required_phrases:
            raise ValueError("Answerable cases need relevant_doc_ids and required_phrases")
        if len(set(self.relevant_doc_ids)) != len(self.relevant_doc_ids):
            raise ValueError("Duplicate relevant document IDs")
        if any(not phrase.strip() for phrase in self.required_phrases + self.forbidden_phrases):
            raise ValueError("Fact and safety phrases cannot be blank")
        return self


class Context(StrictModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class Trace(StrictModel):
    case_id: str = Field(min_length=1)
    answer: str = ""
    contexts: list[Context] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def trace_integrity(self):
        if not self.answer.strip() and not self.error:
            raise ValueError("An empty answer must record a generation error")
        if len({c.id for c in self.contexts}) != len(self.contexts):
            raise ValueError("Duplicate context IDs would inflate retrieval metrics")
        return self


class Score(StrictModel):
    metric: str
    value: float | None = Field(default=None, ge=0, le=1)
    reason: str = ""
    error: str | None = None
    applicable: bool = True

    @model_validator(mode="after")
    def valid_score(self):
        if self.applicable and self.value is None and not self.error:
            raise ValueError("An applicable metric needs a score or an explicit error")
        if self.error and self.value is not None:
            raise ValueError("An errored metric cannot also have a numeric score")
        if not self.applicable and (self.value is not None or self.error):
            raise ValueError("A non-applicable metric cannot have a score or error")
        return self


class Profile(StrictModel):
    top_k: int = Field(default=2, ge=1, le=20)
    active_only: bool = True
    trusted_only: bool = True
    generator: Literal["extractive", "openai-compatible"] = "extractive"
    min_query_coverage: float = Field(default=0.20, ge=0, le=1)
    fault: Literal["none", "drop_context", "fabricate"] = "none"


class Policy(StrictModel):
    minimums: dict[str, float]
    judge_minimums: dict[str, float]
    max_mean_drop: float = Field(default=0.03, ge=0, le=1)
    critical_metrics: list[str] = Field(
        default_factory=lambda: ["builtin.required_facts", "builtin.safety", "builtin.refusal"]
    )
    critical_minimum: float = Field(default=1.0, ge=0, le=1)
    max_p95_latency_ms: float = Field(default=5000, gt=0)
    bootstrap_samples: int = Field(default=2000, ge=100, le=10000)
    seed: int = 42

    @field_validator("minimums", "judge_minimums")
    @classmethod
    def bounded_thresholds(cls, value):
        if not value or any(not math.isfinite(v) or not 0 <= v <= 1 for v in value.values()):
            raise ValueError("Threshold maps must be nonempty and within [0, 1]")
        return value


class Config(StrictModel):
    profiles: dict[str, Profile]
    policy: Policy

    @model_validator(mode="after")
    def baseline_present(self):
        if "baseline" not in self.profiles or "candidate" not in self.profiles:
            raise ValueError("Profiles must include baseline and candidate")
        if self.profiles["baseline"].fault != "none" or self.profiles["candidate"].fault != "none":
            raise ValueError(
                "Fault injection is only permitted in explicitly named control profiles"
            )
        return self
