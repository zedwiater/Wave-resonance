"""dweller.py — the resident wrapper. THE CAVITY, running.

Spec: bilateral-dweller-prototype-spec-20261020.md sections 4 + 8,
circadian addendum section 9. Zak's decision (2026-10-20): the
permanent resident is the WRAPPER — telemetry is the cavity, the
models are organs it wakes and sleeps. This daemon is that wrapper's
heartbeat: it owns no model, burns near-nothing idle, and spends its
dwell on maintenance, condensation, and watching — always yielding
the machine to whoever sits down at it.

One tick:
  1. YieldSensor first. A human on the machine -> the tick is logged
     as YIELD and NO work happens (no harvest, no dwell, no bursts —
     the burst-controller discipline, enforced at the wrapper level).
  2. Telemetry snapshot (disk, hottest hwmon temp, cube state,
     today's joules) — the cavity feeling its own walls.
  3. circadian_decision: phase posture x drive deficits x aging ->
     SLEEP / REST / THINK / SCAN, priced against the tick budget.
  4. Execute ONLY what exists: cube_maintenance / condense run the
     cube's idle_cycle, metered. THINK tasks without a handler
     (corpus parse, consistency audit, campaign sweep) are QUEUED in
     the log, never faked. SLEEP/SCAN do nothing but watch.
  5. The tick's metered joules (idle-subtracted) go into the health
     audit: burn the resident cannot explain becomes tomorrow's
     "what happened to the body?"

ClockGovernor DPM stays OFF (HARNESS_DPM_DYNAMIC untouched). The
:8080 server is never touched. Cube persists to its JSONL on an
interval; every tick appends one passport-style JSONL record.

Run modes:
  python3 dweller.py --dry-run     # synthetic day, 12 ticks, no disk
  python3 dweller.py --live        # the real loop (PC, Zak's word)
"""

import argparse
import glob
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import circadian
import drive_x
from burst_controller import YieldSensor
from kv_cube import Cube

TICK_S = 60.0
TICK_BUDGET_J = 120.0        # per-tick ceiling for priced idle work
CUBE_PATH = os.path.expanduser("~/wave-sunday/harness/kv_cube.jsonl")
LOG_PATH = os.path.expanduser("~/wave-sunday/harness/dweller_log.jsonl")
UNPARSED_BYTES = 1_400_000_000   # Zak<->Gemini Takeout backlog (known)


def read_temp_c():
    vals = []
    for p in glob.glob("/sys/class/hwmon/hwmon*/temp*_input"):
        try:
            vals.append(int(open(p).read().strip()) / 1000.0)
        except (OSError, ValueError):
            pass
    return max(vals) if vals else 50.0


def telemetry_snapshot():
    free = shutil.disk_usage("/").free
    total = shutil.disk_usage("/").total
    return {"disk_free_frac": free / total, "temp_c": read_temp_c(),
            "ledger_trend_j_per_h": 0.0}


class Dweller:
    def __init__(self, cube, log_fn, meter_fn=None, yield_fn=None,
                 telemetry_fn=telemetry_snapshot, idle_w=45.0):
        self.cube = cube
        self.log_fn = log_fn            # callable(dict) — one record
        self.meter_fn = meter_fn        # callable(seconds)->joules|None
        self.yield_fn = yield_fn or YieldSensor().yielding
        self.telemetry_fn = telemetry_fn
        self.idle_w = idle_w
        self.state = {"boot_ts": time.time(), "last_served": {}}
        self.cycles = []                # health-audit joule cycles
        self.joules_today = 0.0
        self.ticks = 0

    def tick(self, ts=None, env_events=()):
        ts = ts if ts is not None else time.time()
        self.ticks += 1
        if self.yield_fn():
            rec = {"ts": ts, "mode": "YIELD",
                   "note": "human on the machine — no work"}
            self.log_fn(rec)
            return rec
        snap = {"telemetry": self.telemetry_fn(),
                "joules_today": self.joules_today,
                **drive_x.cube_snapshot(self.cube,
                                        unparsed_bytes=UNPARSED_BYTES)}
        decision = circadian.circadian_decision(
            ts, snap, budget_j=TICK_BUDGET_J, env_events=env_events,
            joule_cycles=self.cycles[-24:], state=self.state)
        if decision["drive"]:
            self.state["last_served"][decision["drive"]] = ts
        metered = None
        if decision["task"] in ("cube_maintenance", "condense"):
            if self.meter_fn:
                metered = self.meter_fn(2.0)
            result = self.cube.idle_cycle(now=ts)
            decision = {**decision, "result": result}
        elif decision["mode"] == "THINK":
            decision = {**decision, "result": "queued_rung"}
        if self.meter_fn:
            tick_j = self.meter_fn(TICK_S) if metered is None else metered
            if tick_j is not None:
                actual = max(0.0, tick_j - self.idle_w * TICK_S)
                self.joules_today += actual
                self.cycles.append(
                    {"ts": ts, "joules_actual": actual,
                     "joules_self": decision.get("est_joules", 0.0)})
        rec = {"ts": ts, **decision}
        self.log_fn(rec)
        return rec


def _meter_factory():
    try:
        from live_verdict import EnergyMeter
    except Exception:
        return None

    def meter(seconds):
        m = EnergyMeter()
        m.start()
        time.sleep(min(seconds, 2.0))
        j, _ = m.stop()
        return j
    return meter


def dry_run():
    """A synthetic day: 12 ticks, 2 h apart, tiny cube, no disk."""
    cube = Cube(model_id="dry-run")
    now = time.time()
    for i in range(30):
        cube.add_interaction(f"seed prompt {i}", f"seed reply {i}",
                             session="seed", ts=now - 86400 * 3)
    records = []
    d = Dweller(cube, records.append, meter_fn=None,
                yield_fn=lambda: False,
                telemetry_fn=lambda: {"disk_free_frac": 0.4,
                                      "temp_c": 55.0,
                                      "ledger_trend_j_per_h": 0.0},
                idle_w=45.0)
    from datetime import datetime
    from zoneinfo import ZoneInfo
    base = datetime(2026, 10, 21, 0, 30,
                    tzinfo=ZoneInfo("America/New_York")).timestamp()
    for k in range(12):
        ts = base + k * 7200.0
        rec = d.tick(ts=ts)
        print(time.strftime("%H:%M", time.localtime(ts)),
              rec.get("phase"), "tired", rec.get("tired"),
              "->", rec["mode"], rec.get("drive"), rec.get("task"))
    print(f"dry run: {len(records)} ticks logged, cube entries "
          f"{len(cube.entries)}")
    return True


def live():
    cube = Cube(model_id="dweller")
    if os.path.exists(CUBE_PATH):
        cube.load(CUBE_PATH)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logf = open(LOG_PATH, "a")

    def log(rec):
        logf.write(json.dumps(rec) + "\n")
        logf.flush()
    d = Dweller(cube, log, meter_fn=_meter_factory())
    print("dweller live: resident wrapper up "
          f"(cube {len(cube.entries)} entries, log {LOG_PATH})")
    while True:
        d.tick()
        if d.ticks % 10 == 0:
            cube.save(CUBE_PATH)
        time.sleep(TICK_S)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        raise SystemExit(0 if dry_run() else 1)
    if a.live:
        live()
    ap.print_help()
