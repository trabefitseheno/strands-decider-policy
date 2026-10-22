"""Typed questions and option sets for the notice router. Thresholds/fallbacks are the spec."""

from .decision import DecisionSpec

NOTICE_RELEVANCE = DecisionSpec(
    name="relevance",
    question="Does this notice require an action from this resident by a deadline?",
    options={
        "action_required": "the notice applies to this resident and they must do something (pay, apply, register, attend) by a stated deadline",
        "information_only": "the notice applies to this resident but requires no action from them",
        "not_relevant": "the notice does not apply to this resident (wrong street, age, income, or housing situation), even if it would need no action",
    },
    threshold=0.80,
    fallback="information_only",  # unused for routing: below threshold => ORIGINAL notice is sent
)

NOTICE_LEVEL = DecisionSpec(
    name="reading_level",
    question="Which reading level suits this resident for this notice?",
    options={
        "plain": "short sentences, everyday words; for limited literacy, limited English, or a first language other than English",
        "standard": "ordinary newspaper-level prose",
        "detailed": "full detail and legal or technical terms retained; for residents who want specifics",
    },
    threshold=0.70,
    fallback="plain",  # plus the original is attached
)
