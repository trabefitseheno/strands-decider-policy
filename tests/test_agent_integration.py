"""Real strands.Agent + InterventionHandler, scripted model, fake Decider: no AWS, no GPU."""

from agents.common import deliver
from patterns.notice_relevance import DecisionGate, NoticePolicy
from tests.conftest import FakeDecider
from tests.scripted_model import ScriptedModel

GOOD = ("Your 2026 property tax second payment of $1,284.50 is due by November 15, 2026. Pay at 12 Elm Road, "
        "Monday to Friday, 9 a.m. to 4 p.m., or online. Late payments cost 1.5% more each month. Homeowners only.")
OK = {"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)}


def run(policy, resident, doc, body):
    model = ScriptedModel(body)
    return deliver(policy, resident, doc, model, "sys"), model


def test_faithful_rewrite_is_delivered_and_level_is_passed_to_the_model(residents, notices):
    res, model = run(NoticePolicy(DecisionGate(FakeDecider(OK))), residents["r001"], notices["n001"], GOOD)
    assert res["status"] == "sent_rewrite" and res["body"].startswith(GOOD)
    assert "Exact wording from the original notice:" in res["body"]
    texts = [b.get("text", "") for m in model.seen_messages[0] for b in m["content"]]
    assert any("reading level: plain" in t for t in texts)


def test_rewrite_with_changed_date_is_replaced_by_original_before_delivery(residents, notices):
    res, _ = run(NoticePolicy(DecisionGate(FakeDecider(OK))), residents["r001"], notices["n001"],
                 GOOD.replace("November 15", "November 25"))
    assert res["status"] == "rewrite_rejected" and res["body"] == notices["n001"]["body"]


def test_below_threshold_relevance_delivers_original(residents, notices):
    script = {"relevance": ("action_required", 0.55), "reading_level": ("plain", 0.95)}
    res, model = run(NoticePolicy(DecisionGate(FakeDecider(script))), residents["r001"], notices["n001"], GOOD)
    assert res["status"] == "sent_original" and res["body"] == notices["n001"]["body"]
    assert model.turns == 0  # no Bedrock call is spent on a rewrite that would be discarded


def test_not_relevant_never_reaches_the_model_or_the_tool(residents, notices):
    script = {"relevance": ("not_relevant", 0.97), "reading_level": ("plain", 0.95)}
    res, model = run(NoticePolicy(DecisionGate(FakeDecider(script))), residents["r004"], notices["n001"], GOOD)
    assert res["status"] == "withheld" and res["body"] is None and model.turns == 0
