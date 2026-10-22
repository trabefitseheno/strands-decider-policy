# Public notice router on Strands Decider 2B

An agent on AWS that routes government notices to residents and rewrites them at the right
reading level, built around **one reusable Strands Decider 2B decision pattern**.

Built for the Agent Experience Hackathon (Strands Decider). Tags: `#strands-decider-2b` `#policy`.

> All data is **invented**: no real residents or notices.

## The idea

A small local classifier (Strands Decider 2B) makes the routing decision. Amazon Bedrock does
the one thing a classifier can't: rewrite text. Plain code sits between them:

```
 notice + resident ──► Decider 2B (local) ──► confidence ≥ threshold? ──yes──► Bedrock rewrites
                         typed question                      │                     │
                         + options                           no                    ▼
                                                             │            figure check (code)
                                                             ▼              │         │
                                                   send ORIGINAL unchanged ◄─ fail      pass
                                                      (and log it)                      ▼
                                                                             pinned exact wording
                                                                             + deliver
```

| Decision | Options | Threshold | Below threshold |
|---|---|---|---|
| A. Relevance: "Does this notice require an action from this resident by a deadline?" | `action_required` / `information_only` / `not_relevant` | 0.80 | send the original notice unchanged |
| B. Reading level | `plain` / `standard` / `detailed` | 0.70 | `plain` + original attached |

Every decision is logged: recipient, choice, confidence, threshold, fallback used, latency.

**Guarantee on rewrites:** every date, amount, place and eligibility rule must be copied
exactly. A check step rejects any rewrite whose figures differ from the source, and code (not
the model) appends the exact wording of those facts.

The reusable pattern is in [`patterns/notice_relevance/`](patterns/notice_relevance/README.md)
(typed question + option set, `InterventionHandler` wiring, usage note).

## What we measured (honestly)

Hardware: **MacBook M1, 8 GB RAM**, Decider 2B served with MLX. Bedrock: Amazon Nova Lite
(`amazon.nova-lite-v1:0`, `us-east-1`). Sample: 4 invented notices × 6 invented residents = 24
relevance decisions, hand-labelled by us.

| | Decider 2B (local) | Nova Lite (Bedrock) |
|---|---|---|
| Median latency | 1,443 ms | 589 ms |
| p95 latency | 13,972 ms | 904 ms |
| Agreement with our labels | 12/24 (50%) | 17/24 (71%) |

- **No latency win on this hardware.** The Decider docs report ~115 ms median on an RTX 3090;
  we did not test a GPU. Our run was on a small laptop and some calls were slowed by memory
  pressure, so treat our latency as "small machine", not as the model's speed.
- **Our first labels and profiles were flawed.** Some labels depended on facts (age, income)
  that the resident profiles didn't state, and "not relevant" vs "information only" was
  ambiguous in the option text. After fixing profiles and option wording, the Decider matched
  19/24 (79%). **That fix was made on the same 24 cases, so treat 79% as optimistic.** The
  first-run files are kept in [`bench/v1/`](bench/v1/) (results and the profiles before the fix).
- **Confidence is informative.** After the fix, every answer at confidence ≥ 0.70 was correct
  (7/7), and every wrong answer had confidence below 0.70. But **at the specified thresholds,
  most decisions fall back**: only 4 of 24 relevance answers reached 0.80 (83% fell back).
  That is the safe behaviour, and the agent run showed it: 20 of 24 deliveries sent the
  original unchanged. Reproduce the sweep with `python -m bench.sweep`.
- **The check step earned its keep.** Nova Lite's first rewrites kept every date, amount and
  address but reworded the eligibility rule "Homeowners only", so the strict check rejected
  them and the original went out (run 1: 4 of 4 rejected; after we told the model to quote the
  phrase word for word, run 2: 4 of 4 and run 3: 3 of 4 rejected). We then had code append a **pinned block** with
  the exact wording, so exactness no longer depends on the model. Replaying the 3 rejected real
  rewrites offline, all pass. One later live delivery (resident r006, real Decider + real Nova Lite, 2 Bedrock calls) passed the
  check with the pinned block: [`examples/run_logs/live_trace_r006.txt`](examples/run_logs/live_trace_r006.txt).
  That is one delivery, not a full re-run. Real logs: [`examples/run_logs/`](examples/run_logs/).

## Limitations

- Small, invented, hand-labelled sample (n = 24). Not a benchmark of the model.
- Decider 2B is a 2B classifier; its docs say it is weaker than reasoning models on complex tasks.
- The figure check is deliberately conservative (a rewrite that spells "thirty" for "30" is rejected).
- The Decider server has no authentication and is for local use.
- Thresholds are the hackathon spec's, not calibrated.

## Run it

Needs Python 3.10+ (we used 3.12).

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install "strands-decider[mlx] @ git+https://github.com/strands-labs/strands-decider"  # Apple silicon; see its README for cuda/cpu
strands-decider serve StrandsAgents/strands-decider-2B-qwen3.5-v1-2610 --device mlx --port 8099
```

First start downloads ~5 GB of weights. Then, with AWS credentials that can call Bedrock:

```bash
export AWS_PROFILE=<your-profile> AWS_REGION=us-east-1   # BEDROCK_MODEL_ID defaults to amazon.nova-lite-v1:0
MAX_BEDROCK_CALLS=10 python -m agents.notice_router.agent
python -m bench.latency --runs 1       # Decider vs Bedrock; add --only decider_2b for no AWS calls
python -m demo.trace_delivery r006 r004 # step-by-step trace, real Decider + scripted Bedrock (no AWS)
pytest                                  # 33 tests, no AWS or GPU needed
```

`MAX_BEDROCK_CALLS` is a hard cap enforced in code. Runs create no AWS resources; they only
call Bedrock `Converse` and write to `logs/` and `bench/`.

## Layout

```
patterns/notice_relevance/   the reusable pattern (questions, gate, figure check, handler, usage note)
agents/notice_router/        the agent (prompt + policy)
data/                        invented residents and notices
demo/                        no-AWS step-by-step trace of one delivery
tests/                       33 tests: above/below threshold, changed-date rejection, handler wiring,
                             real strands.Agent runs with a scripted model
bench/                       latency + agreement benchmark, threshold sweep, first-run files (v1/)
examples/run_logs/           real decision logs and results from the Nova Lite run
docs/                        article outline, demo script, submission checklist
```

## Built with AI assistance

This project was built with AI coding assistance (Claude Code). The author directed the design
and approved every AWS call; all numbers in this README come from runs saved in `bench/` and
`examples/run_logs/`.

## Credits

Built on [Strands Agents](https://strandsagents.com) and
[Strands Decider](https://github.com/strands-labs/strands-decider) (Apache-2.0). The HTTP
client in `patterns/notice_relevance/client.py` is our own, written against the wire shapes
in Decider's `schema.py`.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
