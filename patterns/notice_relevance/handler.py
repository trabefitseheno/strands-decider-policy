"""Strands wiring: the decision sits in the agent's path as an InterventionHandler.

One handler per delivery (one resident x one document), two hooks:

* before_invocation  -> ask the Decider. Withhold (Deny) if not relevant; otherwise tell the
                        agent which reading level to write at.
* before_tool_call   -> the agent drafted a rewrite and called the delivery tool. Check its
                        figures; Proceed, or Transform the body back to the original.

The guarantee lives here, not in the model's prompt. The delivery tool is bound to the
resident and document by the caller, so the model cannot pick a recipient.
"""

from __future__ import annotations

from typing import Any

from strands.interventions import Deny, InterventionHandler, Proceed, Transform

from .client import DeciderUnavailable
from .policy import BasePolicy, Final, Plan


class DecisionGateHandler(InterventionHandler):
    def __init__(
        self, policy: BasePolicy, tool_name: str, resident: dict, doc: dict, name: str = "decider-gate"
    ) -> None:
        self.policy, self.tool_name = policy, tool_name
        self.resident, self.doc, self._name = resident, doc, name
        self.plan: Plan | None = None
        self.final: Final | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def on_error(self) -> str:
        return "deny"  # fail closed: a broken gate must not let unchecked text out

    def _ensure_plan(self) -> Plan:
        if self.plan is None:
            try:
                self.plan = self.policy.plan(self.resident, self.doc)
            except DeciderUnavailable:
                self.policy.gate.log_event(
                    {"event": "decider_unavailable", "recipient": self.resident["id"], "fallback": "original"}
                )
                self.plan = Plan(True, "decider_unavailable", use_original=True)
        return self.plan

    def before_invocation(self, event: Any, **kwargs: Any):
        plan = self._ensure_plan()
        if not plan.send:
            return Deny(reason=f"withheld: {plan.reason}")
        if plan.use_original:
            # Nothing to rewrite: send the original and skip the model call entirely.
            self.final = self.policy.finalize(plan, self.doc, None)
            return Deny(reason=f"original sent without rewrite: {plan.reason}")
        if plan.level is None:
            return Proceed()
        note = (
            f"[routing decision] Write the message at reading level: {plan.level}. "
            "Copy every date, amount, place and eligibility rule exactly as in the original."
        )

        def apply(ev: Any) -> None:
            if ev.messages:
                ev.messages[-1]["content"].append({"text": note})

        return Transform(apply=apply, reason=f"level={plan.level}")

    def before_tool_call(self, event: Any, **kwargs: Any):
        if event.tool_use["name"] != self.tool_name:
            return Proceed()
        plan = self._ensure_plan()
        tool_input = event.tool_use.get("input") or {}
        self.final = final = self.policy.finalize(plan, self.doc, tool_input.get("body"))
        if final.body is None:
            return Deny(reason=f"withheld: {plan.reason}")
        if final.body == tool_input.get("body") and (final.attachment or "") == tool_input.get("attachment", ""):
            return Proceed()

        def apply(ev: Any) -> None:
            ev.tool_use["input"]["body"] = final.body
            ev.tool_use["input"]["attachment"] = final.attachment or ""

        return Transform(apply=apply, reason=f"{final.status}:{plan.reason}")
