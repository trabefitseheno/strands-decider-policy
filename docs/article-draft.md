# Let the small model route, let the big model write, let code decide what goes out

`#strands-decider-2b` `#policy`

*A notice router built on Strands Decider 2B and Amazon Bedrock. Everything here uses invented
residents and invented notices.*

Repo: https://github.com/trabefitseheno/strands-decider-policy
Demo (under 3 minutes): `<paste video link>`

## The problem

A town sends the same property-tax notice to everyone. Renters, who don't pay it, get it
anyway. Residents who read English as a second language get legal prose. An LLM can reword a
notice for each person, but a rewrite that quietly changes "November 15" to "November 25" is
worse than no rewrite at all.

So where should the decision live: *who gets this, at what reading level, and is the rewrite
safe to send?*

## The idea: three jobs, three owners

- **Decider 2B decides.** Strands Decider 2B is a small open model (Apache-2.0, built on
  Qwen3.5-2B) that cannot write text. It answers a typed question over a set of options and
  returns a choice with a confidence.
- **Bedrock writes.** The one thing a classifier can't do is rewrite. Amazon Bedrock does that.
- **Code decides what goes out.** Plain Python owns the threshold, the fallback and the
  checks. Below the threshold, the agent sends the **original notice unchanged** and logs it.

```
notice + resident → Decider 2B → confident enough? → yes → Bedrock rewrites → figure check → deliver
                                         ↓ no                                    ↓ fails
                                 send the ORIGINAL, log it  ←←←←←←←←←←←←←←←←←←←←←←←
```

## The reusable pattern

The pattern has three parts, all in `patterns/notice_relevance/`:

1. **A typed question and option set**: a `DecisionSpec` with the question, the options (each
   with a meaning the model reads), a `threshold` and a `fallback`.
2. **A gate** that asks the Decider, swaps in the fallback when confidence is below the
   threshold, and logs recipient, choice, confidence, threshold, fallback used and latency.
3. **A Strands `InterventionHandler`** that puts the decision in the agent's path:
   `before_invocation` asks the Decider (deny if the notice isn't relevant, send the original
   if the model isn't confident, otherwise tell the agent which reading level to write at),
   and `before_tool_call` checks the draft before it is delivered.

The agent has two decisions:

| Decision | Options | Threshold | Below threshold |
|---|---|---|---|
| Relevance: "Does this notice require an action from this resident by a deadline?" | `action_required` / `information_only` / `not_relevant` | 0.80 | send the original notice |
| Reading level | `plain` / `standard` / `detailed` | 0.70 | `plain` + original attached |

One detail worth knowing: for a choice question the Decider's `confidence` is
`(N·p_max − 1)/(N − 1)`, not the raw probability. With three options, a top probability of
0.86 is only 0.79 confidence, so it fails a 0.80 threshold. I log both numbers.

## The check step, and what it taught me

Every date, amount, place and eligibility rule must be copied exactly. A check step extracts
the dates, times, amounts and numbers from the original, plus a list of must-keep phrases, and
rejects any rewrite that adds, drops or changes one. A changed date is a unit test.

Then I ran it on a real model (Amazon Nova Lite). It kept every date, amount and address, but
**reworded the eligibility rule**: "Homeowners only" became "only homeowners need to pay this
tax; renters do not". Same meaning, different words, and the strict check rejected the
rewrite. The first run rejected 4 of 4 rewrites. I then told the model to quote the phrase word
for word: the second run rejected 4 of 4 again and the third rejected 3 of 4. The original went
out each time, which is the right failure mode, but not a useful rewriter.

The fix was to move the guarantee out of the prompt and into code. Now code appends an
"Exact wording from the original notice" block with the dates, amounts, places and rules
verbatim, and the model rewrites freely around it. Replaying the three rejected real rewrites
through the new code, all three pass. Changed or invented figures are still rejected.
(I replayed these offline, then ran one live delivery with the block: Nova's rewrite passed the
check. That is a single delivery, not a full re-run.)

**Lesson: put guarantees in code, not in the prompt.**

## Results, honestly

I tested on a MacBook M1 with 8 GB of RAM, serving Decider 2B with MLX, against Nova Lite on
Bedrock. The sample is 24 decisions (4 invented notices × 6 invented residents) that I
labelled by hand.

| | Decider 2B (local) | Nova Lite (Bedrock) |
|---|---|---|
| Median latency | 1,443 ms | 589 ms |
| p95 latency | 13,972 ms | 904 ms |
| Agreement with my labels | 12/24 (50%) | 17/24 (71%) |

**I did not get a latency win.** The Decider's documentation reports about 115 ms on an RTX
3090. I did not test a GPU. On a small laptop under memory pressure it was slower than a
Bedrock call, so I'm not claiming speed.

**Part of the first result was my fault.** Some labels depended on facts (age, income) that
the resident profiles never stated, and "not relevant" versus "information only" was
ambiguous in my option text. After fixing the profiles and the option descriptions, the
Decider matched 19 of 24 (79%). I made that fix on the same 24 cases, so treat 79% as
optimistic. The first-run files are in the repo.

**Confidence is a useful signal.** After the fix, every answer at confidence 0.70 or higher
was correct (7 of 7), and every wrong answer was below 0.70.

**At the specified thresholds, most decisions fall back.** Only 4 of 24 relevance answers
reached 0.80. In the agent run, 20 of 24 deliveries sent the original notice unchanged and
only 4 reached Bedrock. That is the safe behaviour, and it is also the cost: with thresholds I
hadn't calibrated, the rewrite path is rarely taken.

## Reusing it

To use the pattern for your own decision: write a `DecisionSpec` (question, options with
meanings, threshold, fallback), write a short policy that maps decisions to a delivery plan,
and reuse the handler. Bind the recipient and document in your delivery tool so the model
can't choose them. A usage note is in the repo.

## What I'd do next

- Run the Decider on a GPU and re-measure latency.
- Calibrate the thresholds on a larger, independently labelled set.
- Re-run all 24 deliveries live with the pinned block (so far I've done one).

## Limits

n = 24, invented data, hand-labelled by me. Decider 2B is a 2B classifier and is weaker than
reasoning models on complex tasks. The figure check is deliberately conservative: a rewrite
that spells "thirty" for "30" is rejected. The Decider server has no authentication and is
for local use. 33 tests pass without AWS or a GPU.

*Disclosure: I built this with AI coding assistance (Claude Code). I directed the design and
approved every AWS call; the numbers above come from runs saved in the repo.*
