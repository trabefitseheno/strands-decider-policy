import json

import pytest
from tests.conftest import FakeDecider

from patterns.notice_relevance import NOTICE_LEVEL, NOTICE_RELEVANCE, DecisionGate, DecisionSpec


def test_above_threshold_keeps_model_choice():
    g = DecisionGate(FakeDecider({"relevance": ("action_required", 0.95), "reading_level": ("standard", 0.9)}))
    d = g.decide("s", [NOTICE_RELEVANCE, NOTICE_LEVEL], "r001")
    assert d["relevance"].choice == "action_required" and not d["relevance"].fallback_used


def test_below_threshold_uses_fallback():
    # p_max 0.6 over 3 options => confidence 0.40 < 0.70
    g = DecisionGate(FakeDecider({"reading_level": ("detailed", 0.6)}))
    d = g.decide("s", [NOTICE_LEVEL], "r001")["reading_level"]
    assert d.fallback_used and d.choice == "plain" and d.model_choice == "detailed"


def test_threshold_is_on_decider_confidence_not_raw_probability():
    # p_max 0.88 over 3 options => confidence 0.82 (passes 0.80); p_max 0.86 => 0.79 (fails)
    ok = DecisionGate(FakeDecider({"relevance": ("action_required", 0.88)}))
    no = DecisionGate(FakeDecider({"relevance": ("action_required", 0.86)}))
    assert not ok.decide("s", [NOTICE_RELEVANCE], "r")["relevance"].fallback_used
    assert no.decide("s", [NOTICE_RELEVANCE], "r")["relevance"].fallback_used


def test_every_decision_is_logged_with_required_fields(tmp_path):
    log = tmp_path / "d.jsonl"
    g = DecisionGate(FakeDecider({"relevance": ("action_required", 0.95), "reading_level": ("detailed", 0.5)}, latency_ms=87.5), log)
    g.decide("s", [NOTICE_RELEVANCE, NOTICE_LEVEL], "r042")
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(rows) == 2
    for row in rows:
        assert {"recipient", "choice", "confidence", "threshold", "fallback_used", "latency_ms"} <= row.keys()
    assert rows[0]["recipient"] == "r042" and rows[0]["latency_ms"] == 87.5
    assert rows[1]["fallback_used"] is True


def test_one_round_trip_for_several_questions():
    d = FakeDecider({"relevance": ("action_required", 0.95), "reading_level": ("plain", 0.95)})
    DecisionGate(d).decide("s", [NOTICE_RELEVANCE, NOTICE_LEVEL], "r")
    assert len(d.calls) == 1


def test_unknown_option_from_decider_raises():
    g = DecisionGate(FakeDecider({"relevance": ("bogus", 0.9)}))
    with pytest.raises(ValueError):
        g.decide("s", [NOTICE_RELEVANCE], "r")


def test_spec_validates_fallback():
    with pytest.raises(ValueError):
        DecisionSpec("x", "q", {"a": "", "b": ""}, 0.5, "c")
