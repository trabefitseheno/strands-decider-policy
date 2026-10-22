# Submission checklist

Deadline: **Oct 23, 2026, 11:59 PM PDT** (Sat Oct 24, 09:59 East Africa Time).
Tags required: `#strands-decider-2b` and `#policy`.
This is **one submission: the public notice router.**

## Hackathon requirements

| Requirement | Status | Evidence / what's left |
|---|---|---|
| Agent uses Decider 2B for a meaningful decision, paired with Bedrock | Done | Notice router; Nova Lite runs logged in `examples/run_logs/` |
| Public repo with source | **You** | Local commit ready; push and make sure the repo is public |
| Reusable pattern: typed question + option set | Done | `patterns/notice_relevance/questions.py` |
| Reusable pattern: wiring in the agent's path | Done | `patterns/notice_relevance/handler.py` (`InterventionHandler`) |
| Reusable pattern: short usage note | Done | `patterns/notice_relevance/README.md` |
| Builder Center article | **You** | Outline in `docs/article-outline.md`; needs writing and publishing |
| Demo video under 3 minutes | **You** | Script in `docs/demo-script.md` (2:50); needs recording |
| Original agent, not published before | Done | Built for this hackathon; not published |
| Both hashtags (`#strands-decider-2b`, `#policy`) | **You** | Add to the article and submission form |

## Repo (public-ready)

- [x] No secrets, AWS account IDs or personal paths found (scanned source, docs, data, examples)
- [x] Invented data only; no real people
- [x] `.gitignore` covers `.venv/`, `logs/`, caches, `.DS_Store`
- [x] 33 tests pass without AWS or a GPU (`pytest`)
- [x] First-run evidence kept under `bench/v1/`; real run logs under `examples/run_logs/`
- [x] LICENSE (Apache-2.0) and NOTICE added. **Check the copyright name in `NOTICE`** (I used the name from your home folder).
- [x] Local git repo, one commit, `origin` = `https://github.com/trabefitseheno/strands-decider-policy.git`
- [ ] **Push** (you authenticate): `git push -u origin main`
- [ ] Confirm the repo is **public**, the README renders and the LICENSE is detected.

## Before you record / publish

- [ ] Re-read README claims; each number comes from `bench/` or `examples/run_logs/`.
- [ ] Don't claim: faster than Bedrock; high accuracy; that the pinned block was tested at scale
      (one live delivery + offline replay of 3 real Nova rewrites).
- [ ] Optional, needs your approval (AWS): a full 24-delivery live run with the pinned block
      (~8 Converse calls, under $0.01).
- [ ] Optional: re-measure the Decider on a GPU. Not done; our latency is from an 8 GB M1.
- [ ] Record the demo with the Decider server warmed up (first request at a new length is slow here).

## Known gaps (state them, don't hide them)

- n = 24 invented, hand-labelled cases; fixes to profiles and wording were made on the same cases.
- At the specified thresholds, 83% of notice decisions fell back to the original.
- Decider was slower than Nova Lite on this machine (p50 1.4 s vs 0.6 s).
- Bedrock model used for all reported runs: `amazon.nova-lite-v1:0` (Anthropic models need a use-case form your account hasn't submitted).

## Cleanup to do on your machine

- The Decider server may still be running on port 8099 (`pkill -f strands_decider`).
- ~5 GB of model weights are in `~/.cache/huggingface`; delete after submitting if you need the space.
- AWS usage was Bedrock `Converse` calls only; no resources were created in your account.
