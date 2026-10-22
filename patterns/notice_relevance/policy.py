"""Turns Decisions into a delivery Plan, and checks the Bedrock rewrite against the source."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .decision import Decision, DecisionGate, DecisionSpec
from .figures import CheckResult, check_rewrite
from .questions import NOTICE_LEVEL, NOTICE_RELEVANCE


@dataclass
class Plan:
    send: bool
    reason: str
    use_original: bool = False  # send the original unchanged, no rewrite
    level: str | None = None  # reading level to ask Bedrock for
    attach_original: bool = False
    decisions: dict[str, Decision] = field(default_factory=dict)


@dataclass
class Final:
    body: str | None  # None => nothing is sent
    attachment: str | None  # original text attached, if any
    status: str  # sent_original | sent_rewrite | rewrite_rejected | withheld
    check: CheckResult | None = None
    problems: list[str] = field(default_factory=list)


def render_state(resident: dict, doc: dict) -> str:
    return (
        f"RESIDENT PROFILE: {resident['profile']}\n\n"
        f"DOCUMENT TITLE: {doc['title']}\n\nDOCUMENT:\n{doc['body']}"
    )


class BasePolicy:
    block_title = "Exact wording from the original notice"

    def __init__(self, gate: DecisionGate) -> None:
        self.gate = gate

    def pinned_block(self, doc: dict) -> str:
        """Code, not the model, restates dates, amounts, places and eligibility rules verbatim."""
        phrases = doc.get("must_preserve") or []
        if not phrases:
            return ""
        return f"\n\n{self.block_title}:\n" + "\n".join(f"- {p}" for p in phrases)

    def plan(self, resident: dict, doc: dict) -> Plan:  # pragma: no cover
        raise NotImplementedError

    def extra_problems(self, original: str, rewrite: str) -> list[str]:
        """Extension point: extra, domain-specific checks on a rewrite. Return a list of problems."""
        return []

    def finalize(self, plan: Plan, doc: dict, proposed: str | None) -> Final:
        original = doc["body"]
        if not plan.send:
            return Final(None, None, "withheld")
        if plan.use_original or proposed is None:
            return Final(original, None, "sent_original")
        composed = proposed.rstrip() + self.pinned_block(doc)
        check = check_rewrite(original, composed, tuple(doc.get("must_preserve", ())))
        problems = self.extra_problems(original, composed)
        if not check.ok or problems:
            self.gate.log_event(
                {"event": "rewrite_rejected", "doc": doc["id"], "missing": check.missing,
                 "extra": check.extra, "missing_phrases": check.missing_phrases,
                 "problems": problems, "rejected_rewrite": composed}
            )
            return Final(original, None, "rewrite_rejected", check, problems)
        return Final(composed, original if plan.attach_original else None, "sent_rewrite", check)


class NoticePolicy(BasePolicy):
    """A: relevance (0.80, below => original notice). B: reading level (0.70, below => plain + original)."""

    def plan(self, resident: dict, doc: dict) -> Plan:
        d = self.gate.decide(
            render_state(resident, doc), [NOTICE_RELEVANCE, NOTICE_LEVEL], resident["id"]
        )
        rel, lvl = d["relevance"], d["reading_level"]
        if rel.fallback_used:
            return Plan(True, "relevance_below_threshold", use_original=True, decisions=d)
        if rel.choice == "not_relevant":
            return Plan(False, "not_relevant", decisions=d)
        return Plan(True, rel.choice, level=lvl.choice, attach_original=lvl.fallback_used, decisions=d)
