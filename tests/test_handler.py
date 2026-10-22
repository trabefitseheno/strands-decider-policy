from types import SimpleNamespace

from tests.conftest import FakeDecider
from strands.interventions import Deny, Proceed, Transform

from patterns.notice_relevance import DecisionGate, NoticePolicy
from patterns.notice_relevance.handler import DecisionGateHandler

GOOD = "Your 2026 property tax second payment of $1,284.50 is due by November 15, 2026. Pay at 12 Elm Road, Monday to Friday, 9 a.m. to 4 p.m., or online. Late payments cost 1.5% more each month. Homeowners only."


def make(residents, notices, script=None, fail=False, rid="r001"):
    policy = NoticePolicy(DecisionGate(FakeDecider(script or {}, fail=fail)))
    return DecisionGateHandler(policy, "send_notice", residents[rid], notices["n001"])


def event(name="send_notice", body=GOOD, rid="r001"):
    return SimpleNamespace(tool_use={"name": name, "input": {"resident_id": rid, "notice_id": "n001", "body": body}})


def test_good_rewrite_gets_the_pinned_block_appended(residents, notices):
    h = make(residents, notices, {"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)})
    ev = event()
    action = h.before_tool_call(ev)
    assert isinstance(action, Transform) and action.reason.startswith("sent_rewrite")
    action.apply(ev)
    assert ev.tool_use["input"]["body"].startswith(GOOD)
    assert "Exact wording from the original notice:" in ev.tool_use["input"]["body"]


def test_other_tools_are_ignored(residents, notices):
    assert isinstance(make(residents, notices).before_tool_call(event(name="other")), Proceed)


def test_bad_date_is_transformed_to_original(residents, notices):
    h = make(residents, notices, {"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)})
    ev = event(body=GOOD.replace("November 15", "November 25"))
    action = h.before_tool_call(ev)
    assert isinstance(action, Transform) and "rewrite_rejected" in action.reason
    action.apply(ev)
    assert ev.tool_use["input"]["body"] == notices["n001"]["body"]


def test_not_relevant_is_denied_before_the_model_runs(residents, notices):
    h = make(residents, notices, {"relevance": ("not_relevant", 0.97), "reading_level": ("plain", 0.95)}, rid="r004")
    assert isinstance(h.before_invocation(SimpleNamespace(messages=[])), Deny)


def test_before_invocation_adds_reading_level_note(residents, notices):
    h = make(residents, notices, {"relevance": ("action_required", 0.97), "reading_level": ("detailed", 0.95)})
    ev = SimpleNamespace(messages=[{"role": "user", "content": [{"text": "hi"}]}])
    action = h.before_invocation(ev)
    assert isinstance(action, Transform)
    action.apply(ev)
    assert "reading level: detailed" in ev.messages[-1]["content"][-1]["text"]


def test_decider_down_sends_original_and_logs(residents, notices):
    h = make(residents, notices, fail=True)
    ev = event()
    action = h.before_tool_call(ev)
    assert isinstance(action, Transform)
    action.apply(ev)
    assert ev.tool_use["input"]["body"] == notices["n001"]["body"]
    assert h.policy.gate.events[0]["event"] == "decider_unavailable"


def test_handler_fails_closed_on_error(residents, notices):
    assert make(residents, notices).on_error == "deny"
