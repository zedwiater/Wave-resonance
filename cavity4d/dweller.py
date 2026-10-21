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
STATE_PATH = os.path.expanduser(
    "~/wave-sunday/harness/community_state.json")
UNPARSED_BYTES = 1_400_000_000   # Zak<->Gemini Takeout backlog (known)

# -- toddler-proofing: deterministic guards, checked before any work --
# The resident may never run wild: these are hard code limits, not
# model judgment. A tripped guard logs one line and the tick does
# nothing else.
TEMP_HOLD_C = 85.0           # at/above: no work at all (THERMAL_HOLD)
TEMP_MAINT_ONLY_C = 78.0     # at/above: maintenance only, no THINK
DISK_FLOOR_FRAC = 0.15       # below: no cube saves (DISK_HOLD)
DISK_WARN_FRAC = 0.20        # below: disk_warn flag on tick records
WORK_PER_HOUR = 6            # max maintenance executions per hour
LOG_MAX_BYTES = 10_000_000   # dweller log rotation ceiling
RSS_CAP_KB = 1_000_000       # self memory ceiling (~1 GB): exit if hit


def read_temp_c():
    vals = []
    for p in glob.glob("/sys/class/hwmon/hwmon*/temp*_input"):
        try:
            vals.append(int(open(p).read().strip()) / 1000.0)
        except (OSError, ValueError):
            pass
    return max(vals) if vals else 50.0


def read_vram_used_frac():
    """GPU VRAM occupancy (RX 6600 XT = card2) — the resident feeling
    whether its organs are loaded. None when the sysfs files are
    absent (dry-run VM, different card index)."""
    try:
        used = int(open("/sys/class/drm/card2/device/"
                        "mem_info_vram_used").read().strip())
        total = int(open("/sys/class/drm/card2/device/"
                         "mem_info_vram_total").read().strip())
        return used / total if total else None
    except (OSError, ValueError):
        return None


def _health_ok(port):
    import urllib.request
    try:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False


def read_organs():
    """Which model organs are awake: Gemma on :8080, the second
    (bilateral partner) on :8081."""
    return {"gemma_8080": _health_ok(8080),
            "second_8081": _health_ok(8081)}


def telemetry_snapshot():
    free = shutil.disk_usage("/").free
    total = shutil.disk_usage("/").total
    return {"disk_free_frac": free / total, "temp_c": read_temp_c(),
            "ledger_trend_j_per_h": 0.0,
            "vram_used_frac": read_vram_used_frac(),
            "organs": read_organs()}


def community_snapshot(path=STATE_PATH, now=None):
    """Community drive source (Zak, 2026-10-20): the MHD Transduction
    campaign — spreading and developing the theory — monitored by the
    daily update and engagement report. State file carries the last
    report/check timestamps; deficits age from them. Missing or
    unreadable file -> neutral (deficit 0), never a crash."""
    now = now if now is not None else time.time()
    try:
        st = json.load(open(path))
    except (OSError, ValueError):
        return {"oldest_unchecked_h": 0.0, "family_signal_age_h": 0.0}
    def age_h(key):
        ts = st.get(key)
        return max(0.0, (now - ts) / 3600.0) if ts else 0.0
    return {"oldest_unchecked_h": age_h("last_campaign_check_ts"),
            "family_signal_age_h": age_h("last_engagement_report_ts")}


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
        self.work_times = []            # maintenance execution times

    def tick(self, ts=None, env_events=()):
        ts = ts if ts is not None else time.time()
        self.ticks += 1
        if self.yield_fn():
            rec = {"ts": ts, "mode": "YIELD",
                   "note": "human on the machine — no work"}
            self.log_fn(rec)
            return rec
        tel = self.telemetry_fn()
        # hard guards before any decision: heat and disk are the body
        if tel.get("temp_c", 0.0) >= TEMP_HOLD_C:
            rec = {"ts": ts, "mode": "THERMAL_HOLD",
                   "temp_c": tel["temp_c"]}
            self.log_fn(rec)
            return rec
        if tel.get("disk_free_frac", 1.0) < DISK_FLOOR_FRAC:
            rec = {"ts": ts, "mode": "DISK_HOLD",
                   "disk_free_frac": tel["disk_free_frac"]}
            self.log_fn(rec)
            return rec
        snap = {"telemetry": tel,
                "joules_today": self.joules_today,
                "community": community_snapshot(now=ts),
                "organs": tel.get("organs"),
                **drive_x.cube_snapshot(self.cube,
                                        unparsed_bytes=UNPARSED_BYTES)}
        decision = circadian.circadian_decision(
            ts, snap, budget_j=TICK_BUDGET_J, env_events=env_events,
            joule_cycles=self.cycles[-24:], state=self.state)
        if decision["drive"]:
            self.state["last_served"][decision["drive"]] = ts
        # thermal demotion: hot body does maintenance, never THINK
        if tel.get("temp_c", 0.0) >= TEMP_MAINT_ONLY_C \
                and decision["mode"] == "THINK":
            decision = {**decision, "mode": "REST",
                        "task": "cube_maintenance",
                        "note": "thermal demotion"}
        # rate cap: maintenance executions per hour are hard-capped
        self.work_times = [t for t in self.work_times if ts - t < 3600]
        if decision["task"] in ("cube_maintenance", "condense") \
                and len(self.work_times) >= WORK_PER_HOUR:
            decision = {**decision, "mode": "SLEEP", "task": None,
                        "note": "rate_capped"}
        metered = None
        if decision["task"] in ("cube_maintenance", "condense"):
            self.work_times.append(ts)
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
        # body sense passthrough: the tick log shows the resident its
        # own VRAM and which organs are awake (deficits don't use
        # these yet — feeling precedes acting)
        rec["organs"] = tel.get("organs")
        rec["vram_used_frac"] = tel.get("vram_used_frac")
        if tel.get("disk_free_frac", 1.0) < DISK_WARN_FRAC:
            rec["disk_warn"] = True
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


def _rss_kb():
    try:
        for line in open("/proc/self/status"):
            if line.startswith("VmRSS"):
                return int(line.split()[1])
    except OSError:
        pass
    return 0


def _rotate_log():
    if os.path.exists(LOG_PATH) \
            and os.path.getsize(LOG_PATH) > LOG_MAX_BYTES:
        for i in (2, 1):
            src = f"{LOG_PATH}.{i}"
            if os.path.exists(src):
                os.replace(src, f"{LOG_PATH}.{i + 1}")
        os.replace(LOG_PATH, f"{LOG_PATH}.1")


def live():
    import fcntl
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    # one resident only: a second instance is a toddler with a twin
    lockf = open(os.path.join(os.path.dirname(LOG_PATH),
                              "dweller.lock"), "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("dweller already running — refusing a second resident")
        return
    cube = Cube(model_id="dweller")
    if os.path.exists(CUBE_PATH):
        cube.load(CUBE_PATH)
    _rotate_log()
    logf = open(LOG_PATH, "a")

    def log(rec):
        logf.write(json.dumps(rec) + "\n")
        logf.flush()
    d = Dweller(cube, log, meter_fn=_meter_factory())
    print("dweller live: resident wrapper up "
          f"(cube {len(cube.entries)} entries, log {LOG_PATH})")
    errors = 0
    while True:
        try:
            d.tick()
            errors = 0
            if d.ticks % 10 == 0:
                _rotate_log()
                if _rss_kb() > RSS_CAP_KB:
                    log({"mode": "EXIT", "note": "rss cap — leak guard"})
                    return
                tel = telemetry_snapshot()
                if tel["disk_free_frac"] >= DISK_FLOOR_FRAC:
                    cube.save(CUBE_PATH)
            time.sleep(TICK_S)
        except Exception as e:  # a bad tick must never kill the body
            errors += 1
            try:
                log({"mode": "ERROR", "error": str(e)[:200],
                     "streak": errors})
            except Exception:
                pass
            time.sleep(min(1800.0, 30.0 * (2 ** errors)))


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
