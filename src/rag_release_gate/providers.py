"""Explicit OpenAI-compatible endpoints support Ollama, vLLM, or hosted gateways."""

import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx


@dataclass
class Endpoint:
    base_url: str
    model: str
    api_key: str = field(repr=False)
    timeout: float = 60.0
    max_tokens: int = 2048
    transport: httpx.BaseTransport | None = field(default=None, repr=False)

    @classmethod
    def from_env(cls, prefix: str):
        url = os.environ.get(f"{prefix}_BASE_URL", "").rstrip("/")
        model = os.environ.get(f"{prefix}_MODEL", "")
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or not model:
            raise ValueError(
                f"Set {prefix}_BASE_URL and {prefix}_MODEL explicitly; see .env.example"
            )
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError(
                f"{prefix}_BASE_URL must not contain credentials, query strings, or fragments"
            )
        timeout = float(os.environ.get(f"{prefix}_TIMEOUT", "60"))
        if not 0 < timeout <= 300:
            raise ValueError(f"{prefix}_TIMEOUT must be in (0, 300]")
        return cls(url, model, os.environ.get(f"{prefix}_API_KEY", "local-no-key"), timeout)

    def metadata(self):
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": 0,
            "timeout_seconds": self.timeout,
            "max_tokens": self.max_tokens,
        }

    def complete(self, messages: list[dict], schema: dict | None = None):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "evaluation", "strict": True, "schema": schema},
            }
        # No implicit cloud destination and no retry on ambiguous/billable failures.
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            response = client.post(
                self.base_url + "/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        answer = data["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Provider returned an empty or non-text answer")
        usage = data.get("usage") or {}
        return answer, usage
