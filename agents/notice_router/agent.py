"""Public notice router: route a government notice to each resident, reworded at the right level.

Run (needs `strands-decider serve ... --port 8099` and AWS credentials for Bedrock):
    python -m agents.notice_router.agent
"""

from patterns.notice_relevance import NoticePolicy

from agents.common import bedrock_model, default_gate, load, run_all

SYSTEM_PROMPT = """You reword public notices from a town government for one resident.
You will be told a reading level (plain, standard or detailed): write at that level.
Rules you must follow exactly:
- Copy every date, time, amount, percentage, address, place name and eligibility rule EXACTLY
  as written in the original. Never convert, round, reorder, spell out, or omit them.
- Do not add facts, advice or contact details that are not in the original.
- When done, call the send_message tool once with the full reworded text as `body`.
"""


def build_policy(gate=None) -> NoticePolicy:
    return NoticePolicy(gate or default_gate("notice_router.jsonl"))


def main() -> None:
    run_all(build_policy(), load("residents"), load("notices"), bedrock_model(), SYSTEM_PROMPT,
            results_name="notice_results.json")


if __name__ == "__main__":
    main()
