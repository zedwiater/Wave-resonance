"""replay_drive_x.py — drive_x replay over the real KV-cube seed history.

Read-only analysis. Loads kv_cube_seed.jsonl (fetched from the PC),
builds as-of snapshots at daily boundaries across the seed's timespan,
and runs drive_x.replay at two joule budgets (100 J and 1 J) to check
arbitration behaviour against real cube history before any live loop
exists (spec section 8: replay first).

Assumptions (also written into the results JSON):
- Cube slice is as-of t: entries with first_seen <= t; stale_frac =
  fraction of those with last_used < t - 7 days; near_threshold =
  SELF_TALK entries with 3 <= use_count < 5.
- daydream_ratio: the seed contains ZERO anticipation entries (all
  520 entries are kind == "interaction"), so daydream_ratio = 0.0 at
  every snapshot. The daydream signal is absent from this data, not
  measured as zero.
- unparsed_bytes = 1.4e9 constant (the known Zak<->Gemini Takeout
  backlog). Replay does not model parse progress, so the backlog
  never shrinks across the window.
- Telemetry neutral: disk_free_frac 0.5, temp_c 50,
  ledger_trend_j_per_h 0 (survival deficit 0 by construction).
- Audit slice neutral-zero: queue 0, computed_faces = as-of count of
  entries with a computed face, disagree_rate None. The seed carries
  no audit history, so logic_alignment deficit is 0 throughout.
- Community: oldest_unchecked_h = hours since window start, capped
  at 96 (no reset events are recorded in the seed; a simple
  documented ramp). family_signal_age_h omitted (deficit function
  tolerates missing keys).
- sensor_nudge = False throughout (no sensor data in the seed).
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import drive_x  # noqa: E402

SEED_PATH = os.path.join(HERE, "replay_data", "kv_cube_seed.jsonl")
OUT_PATH = os.path.join(HERE, "replay_drive_x_results.json")
DAY = 86400.0
STALE_AFTER = 7 * DAY
UNPARSED_BYTES = 1_400_000_000

ASSUMPTIONS = [
    "Cube slice as-of t: entries with first_seen <= t; stale_frac = "
    "fraction with last_used < t - 7 days; near_threshold = SELF_TALK "
    "entries with 3 <= use_count < 5.",
    "daydream_ratio = 0.0 at every snapshot: the seed has ZERO "
    "anticipation entries (all 520 are kind == 'interaction'); the "
    "signal is absent from this data, not measured as zero.",
    "unparsed_bytes = 1.4e9 constant (known Zak-Gemini Takeout "
    "backlog); replay does not model parse progress, so it never "
    "shrinks across the window.",
    "Telemetry neutral: disk_free_frac 0.5, temp_c 50, "
    "ledger_trend_j_per_h 0 -> survival deficit 0 by construction.",
    "Audit slice neutral-zero: queue 0, disagree_rate None; the seed "
    "carries no audit history, so logic_alignment deficit is 0 "
    "throughout and that drive can never fire in this replay.",
    "Community oldest_unchecked_h = hours since window start capped "
    "at 96 (no reset events recorded in the seed); "
    "family_signal_age_h omitted.",
    "sensor_nudge = False throughout (no sensor data in the seed).",
    "Snapshot times: t0 = min(first_seen), then t0 + k*86400 while "
    "<= max(last_used), plus a final snapshot at max(last_used).",
]


def load_seed(path):
    entries, meta_lines = [], 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "_meta" in row:
                meta_lines += 1
                continue
            entries.append(row)
    return entries, meta_lines


def build_snapshots(entries):
    t0 = min(e["first_seen"] for e in entries)
    t_end = max(e["last_used"] for e in entries)
    times = []
    t = t0
    while t <= t_end:
        times.append(t)
        t += DAY
    if times[-1] < t_end:
        times.append(t_end)
    snaps = []
    for t in times:
        live = [e for e in entries if e["first_seen"] <= t]
        stale = sum(1 for e in live if e["last_used"] < t - STALE_AFTER)
        snaps.append({
            "ts": t,
            "telemetry": {"disk_free_frac": 0.5, "temp_c": 50.0,
                          "ledger_trend_j_per_h": 0},
            "cube": {
                "entries": len(live),
                "stale_frac": (stale / len(live)) if live else 0.0,
                "daydream_ratio": 0.0,   # no anticipation entries in seed
                "near_threshold": sum(
                    1 for e in live
                    if e["tier"] == "SELF_TALK" and 3 <= e["use_count"] < 5),
            },
            "audit": {"queue": 0,
                      "computed_faces": sum(1 for e in live if e.get("computed")),
                      "disagree_rate": None},
            "community": {"oldest_unchecked_h": min((t - t0) / 3600.0, 96.0)},
            "sensor_nudge": False,
            "unparsed_bytes": UNPARSED_BYTES,
        })
    return snaps, t0, t_end


def timeline(snaps, decisions):
    out = []
    for s, d in zip(snaps, decisions):
        out.append({
            "ts": s["ts"],
            "ts_iso": datetime.fromtimestamp(s["ts"], timezone.utc).isoformat(),
            "mode": d["mode"], "drive": d["drive"], "task": d["task"],
            "est_joules": d["est_joules"], "deficits": d["deficits"],
            "cube_entries": s["cube"]["entries"],
            "stale_frac": round(s["cube"]["stale_frac"], 3),
            "near_threshold": s["cube"]["near_threshold"],
        })
    return out


def main():
    entries, meta_lines = load_seed(SEED_PATH)
    snaps, t0, t_end = build_snapshots(entries)
    kinds = Counter(e["kind"] for e in entries)
    anticipations = kinds.get("anticipation", 0)

    runs = {}
    for budget in (100.0, 1.0):
        decisions = drive_x.replay(snaps, budget_j=budget)  # raises if broken
        runs[budget] = {
            "mode_distribution": dict(Counter(d["mode"] for d in decisions)),
            "drive_distribution": dict(Counter(str(d["drive"]) for d in decisions)),
            "timeline": timeline(snaps, decisions),
        }

    tl100 = runs[100.0]["timeline"]
    know_def = [row["deficits"]["knowledge"] for row in tl100]
    comm_def = [row["deficits"]["community"] for row in tl100]
    sanity = {
        "knowledge_dominates": {
            "answer": all(k >= 0.99 for k in know_def),
            "note": "Knowledge deficit is pinned at %.3f-%.3f at every "
                    "snapshot: the constant 1.4 GB unparsed backlog "
                    "saturates deficit_knowledge's unparsed term "
                    "(clamp(bytes/1.4e9) = 1.0), masking its other "
                    "sub-signals (stale_frac, near_threshold, daydream)."
                    % (min(know_def), max(know_def)),
        },
        "sleep_occurs": {
            "answer": any(d["mode"] == "SLEEP"
                          for r in runs.values() for d in r["timeline"]),
            "note": "SLEEP requires every deficit < 0.15; the pinned "
                    "knowledge deficit (1.0) makes SLEEP unreachable "
                    "at both budgets for the entire window.",
        },
        "budget1_defers_to_rest": {
            "answer": runs[1.0]["mode_distribution"] == {"REST": len(snaps)},
            "note": "At budget_j=1.0 the 40 J corpus_parse_chunk and "
                    "the 5 J campaign sweep are both unaffordable, so "
                    "every snapshot defers to REST cube_maintenance, "
                    "exactly as arbitrate() is designed to do.",
        },
        "community_shadowed": {
            "answer": all(row["drive"] != "community" for row in tl100),
            "note": "Community deficit ramps to %.2f (saturated from "
                    "48 h) yet never wins a single arbitration at "
                    "budget 100: weighted order puts knowledge "
                    "(1.0 x 1.0) ahead of community (1.0 x 0.8) and "
                    "arbitrate returns on the first affordable task. "
                    "While the backlog saturates, no other drive's "
                    "task can ever fire." % max(comm_def),
        },
        "logic_alignment_no_data": {
            "answer": all(row["deficits"]["logic_alignment"] == 0.0
                          for row in tl100),
            "note": "Logic alignment can never fire in this replay: "
                    "the seed carries no audit history (queue 0, "
                    "disagree_rate None). Coverage gap in the data, "
                    "not an arbitration bug.",
        },
    }

    results = {
        "seed": {
            "path": "replay_data/kv_cube_seed.jsonl",
            "entries": len(entries),
            "meta_lines_skipped": meta_lines,
            "kinds": dict(kinds),
            "anticipation_entries": anticipations,
            "tiers": dict(Counter(e["tier"] for e in entries)),
            "timespan": {
                "start": t0, "end": t_end,
                "start_iso": datetime.fromtimestamp(t0, timezone.utc).isoformat(),
                "end_iso": datetime.fromtimestamp(t_end, timezone.utc).isoformat(),
                "days": round((t_end - t0) / DAY, 2),
            },
        },
        "assumptions": ASSUMPTIONS,
        "snapshot_count": len(snaps),
        "budgets": {str(b): runs[b] for b in runs},
        "sanity": sanity,
    }
    with open(OUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print("snapshots:", len(snaps))
    for b in (100.0, 1.0):
        print("budget", b, "modes:", runs[b]["mode_distribution"],
              "drives:", runs[b]["drive_distribution"])
    for name, s in sanity.items():
        print("sanity", name, "->", s["answer"])
    print("wrote", OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
