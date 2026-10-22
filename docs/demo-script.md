# Demo script (target 2:40, hard limit 3:00)

**Before recording** (nothing below needs live AWS):
- Start the Decider server and send one warm-up request first. On this laptop the first
  request at a new input length can take many seconds, so **do not record the waiting**.
- Pre-run the agent and record from `logs/` and `examples/run_logs/`, or cut the pauses.
  Say that you sped up or trimmed waits (the on-screen latency numbers come from the benchmark).
- No-AWS walkthrough you can run live or pre-record: `python -m demo.trace_delivery r006 r004`
  (real local Decider, scripted Bedrock; shows a confident rewrite, a low-confidence fallback and a
  rejected date change). Use it for the 1:05–2:00 section if you don't want to spend Bedrock calls.
- Terminal font large. Two panes: left terminal, right editor with `handler.py`.

| Time | On screen | Say |
|---|---|---|
| 0:00–0:15 | README diagram | "Town notices go to everyone the same way. An LLM can reword them, but a rewrite that changes a date is dangerous. So a small model decides, a big model writes, and code checks." |
| 0:15–0:40 | `questions.py` (the two specs) | "Each decision is a typed question with options, a threshold and a fallback. Below the threshold, we send the original notice unchanged." |
| 0:40–1:05 | `handler.py`, highlight `before_invocation` / `before_tool_call` | "It's wired in as a Strands InterventionHandler. Before the model runs, Decider 2B classifies. After the model drafts, code checks the figures." |
| 1:05–1:35 | Terminal: notice run output | "24 deliveries. 20 fell back to the original, because the Decider wasn't confident enough at 0.80. That's the safe behaviour. Four reached Bedrock." |
| 1:35–2:00 | `examples/run_logs/notice_run3_decisions.jsonl` line, then the `rewrite_rejected` event | "Every decision is logged with confidence, threshold, fallback and latency. Here a rewrite was rejected and the original went out." |
| 2:00–2:20 | Delivered message with the pinned block | "Nova Lite paraphrased the eligibility rule, so code now pins the exact wording. Dates and amounts are copied by code, not trusted to the model." |
| 2:20–2:40 | Terminal: `pytest` (33 passed), then results table | "A rewrite that changes November 15 to 25 is rejected, in a test. Honest numbers: on my small laptop the Decider was slower than Nova Lite, 1.4 seconds versus 0.6. The value here is the safe, checkable decision, not speed." |
| 2:40–2:50 | Repo URL + tags | "Repo and article linked below. Hashtags: strands-decider-2b and policy." |

**Don't claim:** faster than Bedrock; high accuracy; that the pinned block was tested
at scale (one live delivery plus an offline replay of 3 real rewrites).
