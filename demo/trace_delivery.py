"""Step-by-step trace of the notice router on real decisions. No AWS needed.

Uses the REAL local Decider (`strands-decider serve ... --port 8099`) and a scripted stand-in
for Bedrock, so you can see every step of the handler without spending a call.

    python -m demo.trace_delivery r006 r004     # one faithful rewrite per resident, then a bad-date rewrite for the first
    python -m demo.trace_delivery --no-bad r004
    python -m demo.trace_delivery --live r006   # REAL Bedrock calls (needs AWS creds; MAX_BEDROCK_CALLS caps them)
"""

import sys

from agents.common import bedrock_model, deliver, load
from agents.notice_router.agent import SYSTEM_PROMPT
from patterns.notice_relevance import DeciderClient, DecisionGate, NoticePolicy
from tests.scripted_model import ScriptedModel

GOOD = ("Your 2026 property tax second payment of $1,284.50 is due by November 15, 2026. "
        "Pay at 12 Elm Road, Monday to Friday, 9 a.m. to 4 p.m., or online. "
        "Late payments cost 1.5% more each month. Only homeowners need to pay this tax; renters do not.")
BAD = GOOD.replace("November 15", "November 25")


def trace(resident: dict, notice: dict, draft: str, label: str, live: bool = False) -> None:
    gate = DecisionGate(DeciderClient())
    model = bedrock_model() if live else ScriptedModel(draft)
    res = deliver(NoticePolicy(gate), resident, notice, model, SYSTEM_PROMPT)
    print(f"\n=== {label} | {resident['id']}: {resident['profile'][len('Invented resident. '):][:70]}... ===")
    print("1. Decider (local):")
    for d in gate.records:
        verdict = f"FALLBACK -> {d.choice}" if d.fallback_used else "accepted"
        print(f"     {d.name:14} {d.model_choice:16} confidence {d.confidence:.2f} / threshold {d.threshold:.2f}  {verdict}")
    calls = getattr(type(model), "calls", None) if live else model.turns
    print(f"2. Bedrock ({'LIVE' if live else 'scripted stand-in'}) calls made: {calls}")
    print("3. Check step:")
    if gate.events:
        for e in gate.events:
            print(f"     {e['event']}: missing={e['missing']} extra={e['extra']}")
    elif res["status"] == "sent_rewrite":
        print("     passed: no figure added, dropped or changed")
    else:
        print("     skipped (original sent, nothing to check)")
    print(f"4. Result: {res['status']} ({res['reason']}); original attached: {bool(res['attachment'])}")
    body = res["body"] or ""
    print("   message: " + (body if live else body[:140] + "...").replace("\n", " "))
    if "Exact wording" in body:
        print("   pinned by code: " + body.split("Exact wording from the original notice:")[1].strip().replace("\n", " | "))


def main() -> None:
    live = "--live" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    residents = {r["id"]: r for r in load("residents")}
    notice = {n["id"]: n for n in load("notices")}["n001"]
    if not args or any(a not in residents for a in args):
        sys.exit(f"usage: python -m demo.trace_delivery [--no-bad] <resident id> ...  (ids: {', '.join(residents)})")
    for rid in args:
        trace(residents[rid], notice, GOOD, "live Bedrock rewrite" if live else "faithful rewrite", live)
    if "--no-bad" not in sys.argv and not live:
        trace(residents[args[0]], notice, BAD, "rewrite that CHANGES the date")


if __name__ == "__main__":
    main()
