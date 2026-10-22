"""Threshold sweep over a saved Decider benchmark file (local, no AWS, no server needed).

    python -m bench.sweep bench/results_v2_decider.json
"""

import json
import sys


def main(path: str) -> None:
    rows = json.load(open(path))["rows"]["decider_2b"]
    print(f"{path}: {len(rows)} decisions; agrees with labels on {sum(r['choice'] == r['gold'] for r in rows)}")
    print("threshold  accepted  correct-of-accepted  fallback-rate")
    for t in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.85):
        acc = [r for r in rows if r["confidence"] >= t]
        ok = sum(r["choice"] == r["gold"] for r in acc)
        print(f"  {t:.2f}     {len(acc):>2}/{len(rows)}      {ok:>2}/{len(acc):<2}              {1 - len(acc) / len(rows):.0%}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bench/results_v2_decider.json")
