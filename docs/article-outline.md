# Builder Center article outline

**Working title:** Let the small model route, let the big model write, let code decide what goes out
**Tags:** `#strands-decider-2b` `#policy`
**Length target:** ~900–1,200 words + 2 diagrams + 1 results table

## 1. The problem (100 words)
Town notices reach everyone the same way. Residents miss deadlines or tune out. An LLM can
reword them, but a rewrite that changes a date or an amount is worse than no rewrite. Where
should the *decision* live?

## 2. The pattern (200 words)
- Decider 2B answers a **typed question** over an option set and returns a choice with a
  **confidence**. It cannot write text, so Bedrock does the rewriting.
- Code owns the policy: `threshold` and `fallback` per decision. Below threshold, send the
  **original, unchanged**, and log it.
- Wiring: a Strands `InterventionHandler`: `before_invocation` (decide, deny, or add the
  reading level) and `before_tool_call` (check the draft, transform it back to the original).
- Diagram: flow from the README.
- Two decisions: relevance (0.80) and reading level (0.70). One reusable pattern.

## 3. The guardrail that mattered: the check step (250 words)
- Code extracts dates, times, amounts, numbers and must-keep phrases from the source; a rewrite
  that adds, drops or changes any is rejected.
- **What we saw:** Nova Lite kept every figure but reworded "Homeowners only". The strict check
  rejected 4 of 4 rewrites in run 1; after the model was told to quote the phrase, 4 of 4 in run 2 and 3 of 4 in run 3.
- **What we changed:** code now appends a pinned "Exact wording from the original notice"
  block. Exactness no longer depends on the model. Replay of the 3 rejected real rewrites:
  all pass. Changed or invented figures are still rejected (unit-tested).
- Lesson: put guarantees in code, not in the prompt.

## 4. Results, honestly (250 words + table)
Table: latency and agreement, Decider vs Nova Lite (README numbers).
- Decider was **slower on an 8 GB M1** (p50 1.4 s vs 0.6 s). The docs' ~115 ms is for an
  RTX 3090, which we didn't test. No latency win claimed.
- First run agreed with our labels 50% vs 71%. Part of that was **our** labels and profiles
  (facts the model couldn't see) and option wording; after fixing, 79%, on the same cases, so
  optimistic.
- **Confidence works as a signal:** ≥ 0.70 → 7/7 correct, and every wrong answer was below 0.70.
  At the specified 0.80, **83% of decisions fall back** to the original. That is the safety
  behaviour, and also the cost: the rewrite path is rarely taken without calibration.

## 5. How to reuse it (100 words)
Write a `DecisionSpec`, a ~15-line policy, reuse the handler. Link to the pattern README.

## 6. What I'd do next (100 words)
- Run the Decider on a GPU and re-measure latency.
- Calibrate thresholds on a larger, independently labelled set (ours was tuned on its own test cases).
- Rerun all 24 deliveries live with the pinned block (one live delivery done so far).

## 7. Compliance box (for the submission)
- Agent uses Decider 2B for the routing decisions, paired with Amazon Bedrock
  (Nova Lite for the runs reported here).
- Public repo with source + reusable pattern (typed question + options, InterventionHandler
  wiring, usage note).
- Original agent, not published before. Invented data only.
- Hashtags: `#strands-decider-2b` `#policy`.

## Assets to prepare
- [ ] Flow diagram (export from README ASCII or redraw)
- [ ] Results table screenshot
- [ ] Screenshot: `rewrite_rejected` log line (`examples/run_logs/notice_run3_decisions.jsonl`)
- [ ] Screenshot: the pinned block in a delivered message
- [ ] Link to demo video and repo
