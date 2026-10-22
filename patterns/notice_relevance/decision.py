"""The reusable decision shape: question + options + threshold + fallback.

The model classifies; this code decides. A choice below `threshold` is replaced by
`fallback`, and every decision is logged.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .client import Decider, choice_question


@dataclass(frozen=True)
class DecisionSpec:
    name: str
    question: str
    options: dict[str, str]  # option name -> what it means (read by the model)
    threshold: float  # minimum Decider `confidence` to accept the model's choice
    fallback: str  # option used when confidence < threshold

    def __post_init__(self) -> None:
        if self.fallback not in self.options:
            raise ValueError(f"{self.name}: fallback {self.fallback!r} not in options")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError(f"{self.name}: threshold must be in [0, 1]")

    def to_question(self) -> dict[str, Any]:
        return choice_question(self.question, self.options)


@dataclass
class Decision:
    name: str
    recipient: str
    model_choice: str  # what the model picked
    choice: str  # what the policy will act on (== fallback when fallback_used)
    confidence: float  # Decider's normalised confidence, (N*p_max-1)/(N-1)
    p_max: float  # raw probability of the picked option
    threshold: float
    fallback_used: bool
    latency_ms: float | None  # one HTTP round trip, shared by decisions asked together
    ts: float = field(default_factory=time.time)


class DecisionGate:
    def __init__(self, decider: Decider, log_path: str | Path | None = None) -> None:
        self.decider = decider
        self.log_path = Path(log_path) if log_path else None
        self.records: list[Decision] = []
        self.events: list[dict[str, Any]] = []

    def decide(
        self, state: Any, specs: list[DecisionSpec], recipient: str
    ) -> dict[str, Decision]:
        """Ask all specs in one round trip (the state is encoded once)."""
        answers = self.decider.ask(state, {s.name: s.to_question() for s in specs})
        latency = self.decider.last_latency_ms
        out: dict[str, Decision] = {}
        for s in specs:
            a = answers[s.name]
            picked = a["choice"]
            if picked not in s.options:
                raise ValueError(f"{s.name}: decider returned unknown option {picked!r}")
            conf = float(a["confidence"])
            fallback_used = conf < s.threshold
            d = Decision(
                name=s.name,
                recipient=recipient,
                model_choice=picked,
                choice=s.fallback if fallback_used else picked,
                confidence=conf,
                p_max=float(a["probabilities"][picked]),
                threshold=s.threshold,
                fallback_used=fallback_used,
                latency_ms=latency,
            )
            out[s.name] = d
            self._log(d)
        return out

    def _log(self, d: Decision) -> None:
        self.records.append(d)
        self._write(asdict(d))

    def log_event(self, event: dict[str, Any]) -> None:
        """Non-decision events: rejected rewrites, decider outages."""
        self.events.append(event)
        self._write({**event, "ts": time.time()})

    def _write(self, row: dict[str, Any]) -> None:
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a") as f:
                f.write(json.dumps(row) + "\n")
