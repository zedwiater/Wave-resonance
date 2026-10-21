"""standing_sim_ambidex.py — Phase 1 ambidexterity proof rerun.

Runs only configs A (mixed chairs) and D (reversed chairs) through
StandingRunner after the catch prompt was rebuilt in hand-local
coordinates. Plant, spine, schedule, and seed come unchanged from
standing_sim.py; the question is narrow: do sign errors remain
concentrated in one chair once both hands receive the same local
response form?
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from standing_sim import (CONFIGS, GEMMA, QWEN, SEED, StandingRunner,
                          build_schedule, health_ok)


def main():
    profile_path = sys.argv[1] if len(sys.argv) > 1 \
        else "env_profile.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 \
        else "standing_sim_ambidex_results.json"
    profile = json.loads(Path(profile_path).read_text())
    schedule = build_schedule(profile, SEED)
    configs = {
        "A_mixed": CONFIGS["A_mixed"],
        "D_reversal": {"LEFT": QWEN, "RIGHT": GEMMA},
    }
    results = {"seed": SEED,
               "interface": "hand_local_v1",
               "n_gusts": len(schedule["gusts"]),
               "configs": {}}
    for name, servers in configs.items():
        if not all(health_ok(s) for s in set(servers.values())):
            results["configs"][name] = {
                "skipped": "a required server is not healthy"}
            print(f"{name}: SKIPPED (health)", flush=True)
            continue
        print(f"{name}: running 120 s ...", flush=True)
        runner = StandingRunner(name, servers, schedule)
        results["configs"][name] = runner.run()
        c = results["configs"][name]
        print(f"{name}: falls={c['plant']['falls']} "
              f"in-center={c['plant']['time_in_center_pct']:.1f}% "
              f"by_role={c['by_role']} by_hand={c['by_hand']}",
              flush=True)
    Path(out_path).write_text(json.dumps(results, indent=1))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
