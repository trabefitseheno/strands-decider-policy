"""Latency (and agreement) benchmark: the SAME relevance decision made by
(a) Strands Decider 2B on a local server, and (b) an all-Bedrock LLM call.

    python -m bench.latency --runs 3

Needs a running `strands-decider serve` (STRANDS_DECIDER_URL) and AWS credentials for
Bedrock (BEDROCK_MODEL_ID, default amazon.nova-lite-v1:0). Prints a table and writes
bench/results.json. Invented data only. Accuracy is measured against the hand labels in
data/notices.json, a small sample, so treat it as a smoke check, not a benchmark of quality.
"""

import argparse
import json
import statistics
import time
from pathlib import Path

from agents.common import DEFAULT_MODEL_ID, REGION, load
from patterns.notice_relevance import NOTICE_RELEVANCE, DeciderClient
from patterns.notice_relevance.policy import render_state



def cases():
    residents = {r["id"]: r for r in load("residents")}
    for n in load("notices"):
        for rid, gold in n["gold"].items():
            yield rid, n["id"], render_state(residents[rid], n), gold


def decider_call(client: DeciderClient, state: str):
    t0 = time.perf_counter()
    a = client.ask(state, {"relevance": NOTICE_RELEVANCE.to_question()})["relevance"]
    return a["choice"], a["confidence"], (time.perf_counter() - t0) * 1000


def bedrock_call(client, state: str):
    opts = "\n".join(f"- {k}: {v}" for k, v in NOTICE_RELEVANCE.options.items())
    prompt = (f"{state}\n\nQuestion: {NOTICE_RELEVANCE.question}\nOptions:\n{opts}\n"
              "Answer with exactly one option name and nothing else.")
    t0 = time.perf_counter()
    r = client.converse(
        modelId=DEFAULT_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 16, "temperature": 0.0},
    )
    text = r["output"]["message"]["content"][0]["text"].strip().lower()
    choice = next((o for o in NOTICE_RELEVANCE.options if o in text), "unparsed")
    return choice, None, (time.perf_counter() - t0) * 1000


def summarize(rows):
    lat = sorted(r["ms"] for r in rows)
    return {
        "n": len(lat),
        "p50_ms": round(statistics.median(lat), 1),
        "p95_ms": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 1),
        "mean_ms": round(statistics.mean(lat), 1),
        "agree_with_gold": round(sum(r["choice"] == r["gold"] for r in rows) / len(rows), 3),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", choices=["decider_2b", "bedrock"], help="skip the other side (no AWS calls if decider_2b)")
    ap.add_argument("--out", default=str(Path(__file__).parent / "results.json"))
    args = ap.parse_args()
    dec, bed = DeciderClient(), None
    if args.only != "decider_2b":
        import boto3

        bed = boto3.client("bedrock-runtime", region_name=REGION)
    all_cases = list(cases())
    decider_call(dec, all_cases[0][2])  # warm-up, discarded
    results = {"decider_2b": [], "bedrock": []}
    for _ in range(args.runs):
        for rid, nid, state, gold in all_cases:
            for name, fn, c in (("decider_2b", decider_call, dec), ("bedrock", bedrock_call, bed)):
                if args.only and name != args.only:
                    continue
                choice, conf, ms = fn(c, state)
                results[name].append({"resident": rid, "notice": nid, "gold": gold, "choice": choice, "confidence": conf, "ms": ms})
    results = {k: v for k, v in results.items() if v}
    summary = {k: summarize(v) for k, v in results.items()}
    Path(args.out).write_text(json.dumps({"model_id": DEFAULT_MODEL_ID, "summary": summary, "rows": results}, indent=2))
    print(f"{'':12}{'n':>4}{'p50 ms':>9}{'p95 ms':>9}{'mean ms':>9}{'gold agree':>12}")
    for k, s in summary.items():
        print(f"{k:12}{s['n']:>4}{s['p50_ms']:>9}{s['p95_ms']:>9}{s['mean_ms']:>9}{s['agree_with_gold']:>12}")


if __name__ == "__main__":
    main()
