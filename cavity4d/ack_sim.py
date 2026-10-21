"""
ack_sim.py — deterministic demo of the acknowledge call (oracle_ack)
over the ball-balance v2 plant. NO servers, seeded RNG, 120 s.

The plant + spine below replicate ball_balance_v2.py's Plant step for
step (same constants, same integration order: spine PID -> accel ->
x += v*dt -> v += a*dt -> fall reset at |x| > 1.0), stepped
synchronously instead of wall-clock paced so the demo is exact and
fast. The v2 file remains the live-test plant; this is its mirror.

Scripted anomaly script (what the environment does):
  - 3 gusts (t=15 +0.9, t=48 -0.9, t=85 +0.9, 3 s each) on the 'gust'
    event channel — ball-class: must ESCALATE 3/3, mode ACTIVE per gust.
  - 4 cosmetic flickers of a 'wall_light' channel (t=30/55/80/105):
    noticed, assessed as consequence-free, DISMISSed — and repeats
    habituate (importance halves per dismissal).
  - 1 slow sensor drift on the 'imu_drift' metric channel from t=70:
    crosses 2.5 sigma slowly -> MONITOR band, watch level up, no
    interruption.
Work is interrupted ONLY by ESCALATE: the sim's interruption counter
increments on ESCALATE records and nothing else.
"""

from __future__ import annotations

import json
import os
import random

from body_awareness import OrganHistory
from oracle_ack import OracleAck

# --- v2 plant constants (mirror of ball_balance_v2.py) -------------------
DT = 0.01
RUN_SECONDS = 120.0
BEAM_HALF = 1.0
PID_KP, PID_KI, PID_KD = 1.2, 0.1, 1.2
SPINE_TILT_CAP = 6.0
GUST_DURATION = 3.0

GUSTS = [(15.0, +0.9), (48.0, -0.9), (85.0, +0.9)]
FLICKERS = {30, 55, 80, 105}
SEED = 20261020

# Contralateral hand map (v2): gust toward +x -> RIGHT hand -> operated
# by LEFT hemisphere; toward -x -> LEFT hand -> RIGHT hemisphere.
HEMI_FOR_GUST = {+1: "LEFT", -1: "RIGHT"}


def gust_at(t: float) -> float:
    for onset, accel in GUSTS:
        if onset <= t < onset + GUST_DURATION:
            return accel
    return 0.0


def drift_at(t: float) -> float:
    if t < 70.0:
        return 0.0
    return min((t - 70.0) * 0.12, 4.0)


class SimPlant:
    """Synchronous mirror of v2's Plant physics (spine only — in this
    demo the hemispheres are never called; the ack layer's job is to
    decide whether they WOULD be, and the spine rides the gusts out
    or doesn't, exactly as an uncaught gust behaves)."""

    def __init__(self):
        self.x = 0.0
        self.v = 0.0
        self.integral = 0.0
        self.falls = 0
        self.fall_times = []

    def step(self, t: float) -> None:
        err = -self.x
        self.integral += err * DT
        self.integral = max(-3.0, min(3.0, self.integral))
        theta = PID_KP * err + PID_KI * self.integral + PID_KD * (-self.v)
        theta = max(-SPINE_TILT_CAP, min(SPINE_TILT_CAP, theta))
        a = 0.55 * theta - 0.12 * self.v + gust_at(t)
        self.x += self.v * DT
        self.v += a * DT
        if abs(self.x) > BEAM_HALF:
            self.falls += 1
            self.fall_times.append(round(t, 2))
            self.x = 0.0
            self.v = 0.0
            self.integral = 0.0


def main() -> dict:
    rng = random.Random(SEED)
    plant = SimPlant()
    layer = OracleAck(stand_down_dwell=3)
    layer.register("gust", "event", asset_risk=0.9, body_asset=True,
                   edge_level=0.1)
    layer.register("wall_light", "event", asset_risk=0.05,
                   edge_level=130.0)
    layer.register("imu_drift", "metric", asset_risk=0.4,
                   baseline=(0.0, 1.0))
    # Seed organ history (labelled: plausible records in the v2 range,
    # LEFT slower than RIGHT, as the v2 replay found).
    for lat in (2.0, 1.8, 2.2):
        layer.history.add("LEFT", lat)
    for lat in (1.2, 1.4, 1.1):
        layer.history.add("RIGHT", lat)

    work_interruptions = 0
    prev_gust_obs = 0.0
    steps = int(RUN_SECONDS / DT)
    for step in range(steps + 1):
        t = step * DT
        plant.step(t)

        # gust channel every 0.1 s; the onset observation carries the
        # ball context so the ack's assessment is real feasibility
        # arithmetic on the state at the moment of noticing.
        if step % 10 == 0:
            g = gust_at(t)
            ctx = None
            if prev_gust_obs == 0.0 and g != 0.0:
                ctx = {"ball": {
                           "state": {"x": plant.x, "v": plant.v},
                           "gust_accel": g,
                           "hemisphere": HEMI_FOR_GUST[1 if g > 0 else -1]},
                       "event_value_j": 100.0, "catch_cost_j": 10.0}
            rec = layer.process("gust", g, ts=round(t, 2), ctx=ctx)
            if rec is not None and rec.disposition == "ESCALATE":
                work_interruptions += 1
            prev_gust_obs = g

        # cosmetic + drift channels at 1 Hz
        if step % 100 == 0:
            light = 165.0 if int(round(t)) in FLICKERS else 100.0
            light += rng.uniform(-0.5, 0.5)
            rec = layer.process("wall_light", light, ts=round(t, 2))
            if rec is not None and rec.disposition == "ESCALATE":
                work_interruptions += 1
            imu = rng.gauss(0.0, 0.5) + drift_at(t)
            rec = layer.process("imu_drift", imu, ts=round(t, 2))
            if rec is not None and rec.disposition == "ESCALATE":
                work_interruptions += 1

    records = [r.to_dict() for r in layer.records]
    gust_recs = [r for r in records if r["channel"] == "gust"]
    light_recs = [r for r in records if r["channel"] == "wall_light"]
    imu_recs = [r for r in records if r["channel"] == "imu_drift"]
    counters = dict(layer.counters)
    counters["work_interruptions"] = work_interruptions
    active_entries = [m for m in layer.mode_log if m["to"] == "ACTIVE"]

    assertions = {
        "gusts_escalated_3_of_3":
            len(gust_recs) == 3
            and all(r["disposition"] == "ESCALATE" for r in gust_recs),
        "cosmetics_dismissed_4_of_4":
            len(light_recs) == 4
            and all(r["disposition"] == "DISMISS" for r in light_recs),
        "cosmetic_habituation_visible":
            len(light_recs) == 4
            and all(r["habituated"] for r in light_recs[1:])
            and light_recs[-1]["importance"]
            < light_recs[0]["importance"],
        "drift_monitored":
            any(r["disposition"] == "MONITOR" for r in imu_recs),
        "interruptions_equal_escalations":
            work_interruptions == counters["escalated"],
        "mode_active_once_per_gust": len(active_entries) == 3,
        "mode_watch_at_end": layer.mode == "WATCH",
    }

    out = {
        "demo": "ack_sim — acknowledge-call layer over the v2 plant "
                "mirror; deterministic, seeded, no servers",
        "seed": SEED,
        "script": {
            "gusts": [{"onset": o, "accel": a} for o, a in GUSTS],
            "cosmetic_flickers_t": sorted(FLICKERS),
            "drift": "imu_drift from t=70, ramp 0.12/s capped 4.0, "
                     "baseline (0, 1.0), sensor noise sigma 0.5",
        },
        "plant_outcome_spine_only": {
            "falls": plant.falls, "fall_times": plant.fall_times,
            "note": "no hemisphere was ever called in this demo; "
                    "falls are what an uncaught gust does — the ack "
                    "layer's ESCALATE is the decision to call one",
        },
        "counters": counters,
        "mode_log": layer.mode_log,
        "records": records,
        "assertions": assertions,
        "all_assertions_pass": all(assertions.values()),
    }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "ack_sim_results.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    return out


if __name__ == "__main__":
    out = main()
    print("COUNTERS:", json.dumps(out["counters"]))
    print("PLANT (spine only): falls =", out["plant_outcome_spine_only"]["falls"],
          "at", out["plant_outcome_spine_only"]["fall_times"])
    print("MODE LOG:")
    for m in out["mode_log"]:
        print(f"  t={m['ts']:>6} {m['from']} -> {m['to']} ({m['channel']})")
    print("GUST ACKS:")
    for r in out["records"]:
        if r["channel"] == "gust":
            f = r["assessment"]["feasibility"]
            print(f"  t={r['ts']:>6} {r['disposition']} action={r['action']} "
                  f"hemi={r['assessment']['hemisphere']} "
                  f"feasibility={f['verdict']} margin={f['margin_s']:+.2f}s")
    print("ASSERTIONS:", json.dumps(out["assertions"], indent=1))
    print("ALL PASS:", out["all_assertions_pass"])
