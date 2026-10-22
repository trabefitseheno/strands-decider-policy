"""Plumbing: build one gated agent per delivery and run it."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from strands import Agent, tool

from patterns.notice_relevance import DeciderClient, DecisionGate
from patterns.notice_relevance.handler import DecisionGateHandler
from patterns.notice_relevance.policy import BasePolicy

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TOOL_NAME = "send_message"
DEFAULT_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def load(name: str) -> list[dict]:
    return json.loads((DATA / f"{name}.json").read_text())


def bedrock_model(model_id: str = DEFAULT_MODEL_ID):
    """BedrockModel with a hard cap on model calls (MAX_BEDROCK_CALLS, default 10)."""
    from strands.models import BedrockModel

    class CappedBedrock(BedrockModel):
        calls = 0
        limit = int(os.environ.get("MAX_BEDROCK_CALLS", "10"))

        async def stream(self, *args, **kwargs):
            type(self).calls += 1
            if type(self).calls > type(self).limit:
                raise RuntimeError(f"Bedrock call cap reached ({type(self).limit}); stopping")
            async for event in super().stream(*args, **kwargs):
                yield event

    return CappedBedrock(model_id=model_id, temperature=0.0, region_name=REGION)


def make_tool(outbox: list[dict]):
    @tool(name=TOOL_NAME)
    def send_message(body: str, attachment: str = "") -> str:
        """Deliver the finished message to the resident.

        Args:
            body: The full text of the message to deliver.
            attachment: Leave empty.
        """
        outbox.append({"body": body, "attachment": attachment})
        return "delivered"

    return send_message


def deliver(
    policy: BasePolicy, resident: dict, doc: dict, model: Any, system_prompt: str
) -> dict[str, Any]:
    outbox: list[dict] = []
    handler = DecisionGateHandler(policy, TOOL_NAME, resident, doc)
    agent = Agent(
        model=model,
        tools=[make_tool(outbox)],
        interventions=[handler],
        system_prompt=system_prompt,
        callback_handler=None,
    )
    keep_note = (
        "\n\nNote: the exact wording of the dates, amounts, places and eligibility rules is "
        "appended to your message automatically. Do not repeat that block; write the rest "
        "in your own words and make sure any figure you do write matches the original."
        if doc.get("must_preserve")
        else ""
    )
    agent(f"Resident: {resident['name']}\n\nOriginal text:\n{doc['body']}{keep_note}")
    sent = outbox[-1] if outbox else None
    if sent is None and handler.final and handler.final.body is not None:
        sent = {"body": handler.final.body, "attachment": handler.final.attachment or ""}
    return {
        "recipient": resident["id"],
        "doc": doc["id"],
        "status": handler.final.status if sent and handler.final else "withheld",
        "reason": handler.plan.reason if handler.plan else None,
        "body": sent["body"] if sent else None,
        "attachment": (sent["attachment"] or None) if sent else None,
    }


def run_all(
    policy: BasePolicy, residents, docs, model, system_prompt, out=print, results_name: str | None = None
) -> list[dict]:
    results = []
    for doc in docs:
        for r in residents:
            res = deliver(policy, r, doc, model, system_prompt)
            out(f"{doc['id']} -> {r['id']}: {res['status']} ({res['reason']})")
            results.append(res)
    if results_name:
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "logs" / results_name).write_text(json.dumps(results, indent=2))
    model_calls = getattr(type(model), "calls", None)
    if model_calls is not None:
        out(f"Bedrock model calls made: {model_calls}")
    return results


def default_gate(log_name: str) -> DecisionGate:
    return DecisionGate(DeciderClient(), ROOT / "logs" / log_name)
