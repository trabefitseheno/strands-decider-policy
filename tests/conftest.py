import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"


def conf(p_max: float, n: int) -> float:
    """Decider's choice confidence: (N*p_max - 1) / (N - 1)."""
    return (n * p_max - 1) / (n - 1)


class FakeDecider:
    """Scripted answers: {question_name: (choice, p_max)}. Mirrors the real wire shape."""

    def __init__(self, script, latency_ms=100.0, fail=False):
        self.script, self.latency, self.fail = script, latency_ms, fail
        self.last_latency_ms = None
        self.calls = []

    def ask(self, state, questions):
        from patterns.notice_relevance.client import DeciderUnavailable

        if self.fail:
            raise DeciderUnavailable("down")
        self.calls.append(list(questions))
        out = {}
        for name, q in questions.items():
            choice, p = self.script[name]
            opts = list(q["criteria"])
            rest = (1 - p) / (len(opts) - 1)
            out[name] = {
                "type": "choice",
                "choice": choice,
                "probabilities": {o: (p if o == choice else rest) for o in opts},
                "confidence": conf(p, len(opts)),
            }
        self.last_latency_ms = self.latency
        return out


@pytest.fixture
def residents():
    return {r["id"]: r for r in json.loads((DATA / "residents.json").read_text())}


@pytest.fixture
def notices():
    return {n["id"]: n for n in json.loads((DATA / "notices.json").read_text())}
