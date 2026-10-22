from tests.conftest import FakeDecider

from patterns.notice_relevance import DecisionGate, NoticePolicy

GOOD = "Your 2026 property tax second payment of $1,284.50 is due by November 15, 2026. Pay at 12 Elm Road, Monday to Friday, 9 a.m. to 4 p.m., or online. Late payments cost 1.5% more each month. Homeowners only."
BAD_DATE = GOOD.replace("November 15", "November 25")


def policy(script, **kw):
    return NoticePolicy(DecisionGate(FakeDecider(script, **kw)))


def test_above_threshold_rewrites_at_chosen_level(residents, notices):
    p = policy({"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)})
    plan = p.plan(residents["r001"], notices["n001"])
    assert plan.send and not plan.use_original and plan.level == "plain" and not plan.attach_original
    final = p.finalize(plan, notices["n001"], GOOD)
    assert final.status == "sent_rewrite" and final.body.startswith(GOOD) and final.attachment is None
    assert "Exact wording from the original notice:\n- $1,284.50" in final.body


def test_relevance_below_threshold_sends_original_unchanged(residents, notices):
    p = policy({"relevance": ("action_required", 0.60), "reading_level": ("plain", 0.95)})
    plan = p.plan(residents["r001"], notices["n001"])
    assert plan.use_original and plan.reason == "relevance_below_threshold"
    final = p.finalize(plan, notices["n001"], GOOD)  # even if an agent drafted a rewrite
    assert final.body == notices["n001"]["body"] and final.status == "sent_original"


def test_level_below_threshold_is_plain_with_original_attached(residents, notices):
    p = policy({"relevance": ("action_required", 0.97), "reading_level": ("detailed", 0.45)})
    plan = p.plan(residents["r002"], notices["n001"])
    assert plan.level == "plain" and plan.attach_original
    final = p.finalize(plan, notices["n001"], GOOD)
    assert final.attachment == notices["n001"]["body"]


def test_not_relevant_is_withheld(residents, notices):
    p = policy({"relevance": ("not_relevant", 0.97), "reading_level": ("plain", 0.95)})
    plan = p.plan(residents["r004"], notices["n001"])
    assert not plan.send and p.finalize(plan, notices["n001"], GOOD).status == "withheld"


def test_rewrite_that_changes_a_date_is_rejected_and_original_sent(residents, notices):
    p = policy({"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)})
    plan = p.plan(residents["r001"], notices["n001"])
    final = p.finalize(plan, notices["n001"], BAD_DATE)
    assert final.status == "rewrite_rejected"
    assert final.body == notices["n001"]["body"]
    assert "november 25, 2026" in final.check.extra  # the invented date is caught
    assert p.gate.events[-1]["event"] == "rewrite_rejected"


# What Nova Lite actually wrote: faithful, but the rule is paraphrased ("only homeowners ...").
NOVA_STYLE = ("Attention Amara, the second payment for your 2026 property tax is $1,284.50, due by November 15, 2026. "
              "Pay at 12 Elm Road, Monday to Friday, 9 a.m. to 4 p.m., or online. After that you owe 1.5% more each month. "
              "Only homeowners need to pay this tax; renters do not.")


def test_paraphrased_eligibility_rule_is_accepted_because_code_pins_the_exact_wording(residents, notices):
    p = policy({"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)})
    plan = p.plan(residents["r001"], notices["n001"])
    final = p.finalize(plan, notices["n001"], NOVA_STYLE)
    assert final.status == "sent_rewrite"
    assert final.body.startswith(NOVA_STYLE)
    for phrase in notices["n001"]["must_preserve"]:
        assert f"- {phrase}" in final.body  # every pinned phrase verbatim, added by code


def test_pinned_block_does_not_excuse_a_changed_figure(residents, notices):
    p = policy({"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)})
    plan = p.plan(residents["r001"], notices["n001"])
    wrong_amount = NOVA_STYLE.replace("$1,284.50", "$1,248.50")
    assert p.finalize(plan, notices["n001"], wrong_amount).status == "rewrite_rejected"


def test_figure_dropped_by_the_model_is_restored_by_the_block(residents, notices):
    p = policy({"relevance": ("action_required", 0.97), "reading_level": ("plain", 0.95)})
    plan = p.plan(residents["r001"], notices["n001"])
    no_place = NOVA_STYLE.replace("Pay at 12 Elm Road, ", "Pay ")
    final = p.finalize(plan, notices["n001"], no_place)
    assert final.status == "sent_rewrite" and "- 12 Elm Road" in final.body
