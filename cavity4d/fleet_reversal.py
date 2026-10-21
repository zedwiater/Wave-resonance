"""
fleet_reversal.py — Part 4 of the standing body sim (Zak 2026-10-20
23:19 EDT): is the win the LOGIC or the MODELS?

4a ROLE REVERSAL (config D): the organs swap chairs — LEFT role is
   served by Qwen :8081, RIGHT role by Gemma :8080. Same schedule,
   same prompts, same wrapper. If asymmetry follows the chair it's
   role; if it follows the model it's identity.
4b FLEET: 3 bodies in parallel threads, each with its own plant,
   env schedule (different seeds), ack stream and work queues — one
   wrapper codebase, the SAME two live servers (config-A pair).
   Contention is part of the test: one operator stack, several
   robots. Catch-latency degradation is measured against config A.
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from standing_sim import (CONFIGS, GEMMA, QWEN, SEED, StandingRunner,
                          build_schedule)


def run_config_d(profile):
    schedule = build_schedule(profile, SEED)
    servers = {"LEFT": QWEN, "RIGHT": GEMMA}     # swapped chairs
    runner = StandingRunner("D_reversal", servers, schedule)
    return runner.run()


def run_fleet(profile):
    servers = CONFIGS["A_mixed"]
    runners = []
    for i in range(3):
        schedule = build_schedule(profile, SEED + 101 + i)
        runners.append(StandingRunner(f"FLEET_body{i + 1}", servers,
                                      schedule))
    results = {}

    def go(r):
        results[r.name] = r.run()

    threads = [threading.Thread(target=go, args=(r,)) for r in runners]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def main():
    profile = json.loads(Path(sys.argv[1]).read_text()) \
        if len(sys.argv) > 1 else {}
    out_path = sys.argv[2] if len(sys.argv) > 2 \
        else "fleet_reversal_results.json"
    out = {}
    print("D_reversal: running 120 s ...", flush=True)
    out["D_reversal"] = run_config_d(profile)
    d = out["D_reversal"]
    print(f"D_reversal: falls={d['plant']['falls']} "
          f"in-center={d['plant']['time_in_center_pct']:.1f}% "
          f"work L/R={d['by_role']['LEFT']['work_completed']}/"
          f"{d['by_role']['RIGHT']['work_completed']} "
          f"acks={d['ack_counts']}", flush=True)
    print("FLEET: 3 bodies x 120 s in parallel ...", flush=True)
    out["fleet"] = run_fleet(profile)
    for name, c in sorted(out["fleet"].items()):
        print(f"{name}: falls={c['plant']['falls']} "
              f"in-center={c['plant']['time_in_center_pct']:.1f}% "
              f"work L/R={c['by_role']['LEFT']['work_completed']}/"
              f"{c['by_role']['RIGHT']['work_completed']} "
              f"acks={c['ack_counts']}", flush=True)
    Path(out_path).write_text(json.dumps(out, indent=1))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
