"""Minimal client for a running `strands-decider serve` endpoint (POST /v1/systemone).

Wire shapes follow strands_decider/schema.py in strands-labs/strands-decider:
a `choice` answer is {"type", "choice", "probabilities", "confidence"}.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Mapping, Protocol

DEFAULT_URL = os.environ.get("STRANDS_DECIDER_URL", "http://127.0.0.1:8099")


class DeciderUnavailable(RuntimeError):
    pass


class Decider(Protocol):
    """Anything that answers typed questions about a state. Tests use a fake."""

    last_latency_ms: float | None

    def ask(self, state: Any, questions: Mapping[str, dict[str, Any]]) -> dict[str, Any]: ...


def choice_question(instructions: str, criteria: Mapping[str, str]) -> dict[str, Any]:
    return {"type": "choice", "instructions": instructions, "criteria": dict(criteria)}


class DeciderClient:
    def __init__(self, url: str = DEFAULT_URL, timeout: float = 120.0) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.last_latency_ms: float | None = None  # wall-clock, includes HTTP

    def ask(self, state: Any, questions: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
        body = json.dumps(
            {"state": state, "model": "strands-decider-latest", "questions": dict(questions)}
        ).encode()
        req = urllib.request.Request(
            f"{self.url}/v1/systemone", data=body, headers={"content-type": "application/json"}
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read())
        except urllib.error.URLError as exc:
            raise DeciderUnavailable(
                f"no decider at {self.url} ({exc}); start one: "
                "strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --port 8099"
            ) from exc
        self.last_latency_ms = (time.perf_counter() - t0) * 1000
        return payload["answers"]
