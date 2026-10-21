"""replay_drive_x_v2.py — v2 calibration judged on the same seed
history as v1, but STATEFUL (aging active) and with parse progress
simulated: each corpus_parse_chunk decision drains 150 MB from the
backlog for later snapshots, and a community sweep resets the
unchecked-age clock. Question: does SLEEP/REST become reachable, does
community win cycles, does knowledge decline as the backlog drains?"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drive_x

seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "replay_data", "kv_cube_seed.jsonl")
entries = [json.loads(l) for l in open(seed_path)
           if l.strip() and '"_meta"' not in l]
t0 = min(e["first_seen"] for e in entries)
t1 = max(e["last_used"] for e in entries)
times = [t0 + k * 86400.0 for k in range(int((t1 - t0) // 86400) + 1)]
if times[-1] < t1:
    times.append(t1)

backlog = 1_400_000_000
unchecked_h = 0.0
state = {"boot_ts": t0, "last_served": {}}
timeline = []
for t in times:
    live = [e for e in entries if e["first_seen"] <= t]
    stale = sum(1 for e in live if e["last_used"] < t - 7 * 86400)
    snap = {"ts": t,
            "telemetry": {"disk_free_frac": 0.5, "temp_c": 50.0,
                          "ledger_trend_j_per_h": 0.0},
            "cube": {"entries": len(live),
                     "stale_frac": (stale / len(live)) if live else 0.0,
                     "daydream_ratio": 0.0,
                     "near_threshold": sum(
                         1 for e in live if e["tier"] == "SELF_TALK"
                         and 3 <= e["use_count"] < 5)},
            "audit": {"queue": 0, "computed_faces":
                      sum(1 for e in live if e.get("computed"))},
            "community": {"oldest_unchecked_h": min(unchecked_h, 96.0)},
            "unparsed_bytes": backlog}
    d = drive_x.arbitrate(snap, budget_j=100.0, state=state)
    if d["drive"]:
        state["last_served"][d["drive"]] = t
    timeline.append({"ts": t, "backlog_mb": round(backlog / 1e6),
                     "unchecked_h": round(min(unchecked_h, 96.0)),
                     **d})
    if d["task"] == "corpus_parse_chunk":
        backlog = max(0, backlog - 150_000_000)
    if d["task"] == "campaign_signal_sweep":
        unchecked_h = 0.0
    else:
        unchecked_h += 24.0

modes = {}
for d in timeline:
    modes[d["mode"]] = modes.get(d["mode"], 0) + 1
out = {"snapshots": len(timeline), "modes": modes,
       "community_wins": sum(1 for d in timeline
                             if d["drive"] == "community"),
       "knowledge_deficit_first": timeline[0]["deficits"]["knowledge"],
       "knowledge_deficit_last": timeline[-1]["deficits"]["knowledge"],
       "timeline": timeline}
json.dump(out, open(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "replay_drive_x_v2_results.json"), "w"),
    indent=1)
print(json.dumps({k: out[k] for k in
                  ("snapshots", "modes", "community_wins",
                   "knowledge_deficit_first",
                   "knowledge_deficit_last")}, indent=1))
for d in timeline:
    print(time.strftime("%m-%d", time.gmtime(d["ts"])), d["mode"],
          d["drive"], d["task"], "backlog", d["backlog_mb"], "MB")
