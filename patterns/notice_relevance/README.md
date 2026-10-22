# Pattern: typed question + threshold + fallback, wired as a Strands InterventionHandler

Reusable Strands Decider 2B decision pattern (`#policy`: classify an incoming notice
before the agent acts). The Decider classifies; plain code decides; a deterministic check
guards the model's rewrite.

## The three parts

| Part | File | What it is |
|---|---|---|
| Typed question + option set | [`questions.py`](questions.py) | A `DecisionSpec`: `question`, `options` (name → meaning), `threshold`, `fallback`. |
| Gate | [`decision.py`](decision.py) | `DecisionGate.decide()` asks the Decider (one round trip for several specs), swaps in `fallback` when `confidence < threshold`, and logs every decision. |
| Wiring in the agent's path | [`handler.py`](handler.py) | `DecisionGateHandler`, a Strands `InterventionHandler`. |

## Usage

```python
from strands import Agent
from patterns.notice_relevance import DeciderClient, DecisionGate, NoticePolicy
from patterns.notice_relevance.handler import DecisionGateHandler

gate = DecisionGate(DeciderClient(), log_path="logs/decisions.jsonl")  # needs `strands-decider serve`
policy = NoticePolicy(gate)
handler = DecisionGateHandler(policy, "send_message", resident, document)
agent = Agent(model=..., tools=[send_message], interventions=[handler])
```

Your delivery tool must take `body: str` and `attachment: str = ""`, and you bind the
resident and document yourself, so the model never chooses the recipient.

What the handler does:

1. `before_invocation`: asks the Decider.
   - Not relevant → `Deny` (the model never runs, no Bedrock cost).
   - Confidence below threshold → `Deny` with the **original** document delivered unchanged
     (no model call, because the rewrite would be thrown away).
   - Otherwise → `Transform` the prompt to add the chosen reading level.
2. `before_tool_call`: the model drafted a rewrite and called the tool. The handler appends a
   **pinned block** (the dates, amounts, places and eligibility rules, copied verbatim by code)
   and runs the figure check. Any date, time, amount or number that differs from the source
   → `Transform` the body back to the original. Otherwise → `Transform` to the rewrite plus
   block (and the original attached where the policy asks for it).
3. `on_error` is `deny` (fail closed). If the Decider server is down, the original is sent.

## Adapting it to your own decision

Write a new `DecisionSpec` (question, options with meanings, threshold, fallback) and a
policy class that maps decisions to a `Plan` (see `NoticePolicy` in
[`policy.py`](policy.py), about 15 lines). Everything else is reused. Domain-specific checks on a
rewrite go in `BasePolicy.extra_problems`.

## Things to know before you rely on it

- **Thresholds apply to the Decider's `confidence`**, which for a choice question is
  `(N·p_max − 1)/(N − 1)`, not raw probability. 3 options and p_max 0.86 gives 0.79. Both
  values are logged.
- **Calibrate on your own data.** In our small sample, only 4 of 24 relevance answers reached
  0.80, so most decisions fell back to the original. That is the safe behaviour, but it means
  the rewrite path is rarely taken at the specified thresholds.
- The figure check is conservative: a rewrite that spells "thirty" for "30" is rejected.
