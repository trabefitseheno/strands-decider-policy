"""A scripted Strands model: first turn calls the delivery tool with `body`, then says done.
Lets us exercise the real Agent + InterventionHandler path with no AWS."""

import json
from typing import Any

from strands.models import Model


class ScriptedModel(Model):
    def __init__(self, body: str, tool_name: str = "send_message") -> None:
        self.body, self.tool_name = body, tool_name
        self.turns = 0
        self.seen_messages: list[Any] = []

    def update_config(self, **kw): ...
    def get_config(self): return {}
    async def structured_output(self, *a, **kw):  # pragma: no cover
        raise NotImplementedError
        yield

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kw):
        self.turns += 1
        self.seen_messages.append(json.loads(json.dumps(messages)))
        usage = {"metadata": {"usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}, "metrics": {"latencyMs": 1}}}
        yield {"messageStart": {"role": "assistant"}}
        if self.turns == 1:
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": "t1", "name": self.tool_name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps({"body": self.body})}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": "done"}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield usage
