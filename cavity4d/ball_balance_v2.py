#!/usr/bin/env python3
"""Ball-balance v2 — the REFLEX LAW test (Zak's directive 2026-10-20 21:44).

Supersedes v1's model-as-controller design. Zak's reframing: you don't use
arms holding the ball. Both hemispheres WATCH one centered monitor; a
deterministic spine (PID in the wrapper) holds the ball; random drift
(gusts) tips it toward one side or the other; reflex LAW — not a model's
decision — dictates that the hand closest to the fall catches it, under the
contralateral map (left brain moves right hand). The operating hemisphere
pauses its work and adjusts the ball; the other side is never touched.

Architecture:
- CENTERED MONITOR: one function, monitor_state(), produces ONE state
  string consumed identically by both hemispheres. No per-side views.
- SPINE: PID in the wrapper, tilt authority capped at +/-6 deg. It holds
  the ball in calm conditions. Gusts (accel +/-0.9 for 3 s) exceed spine
  authority: uncaught, the ball drifts to a fall. Fall = |x| > 1.0 ->
  reset to center, falls += 1 (v2 has a reset rule; v1 did not).
- REFLEX EVENTS: seeded RNG schedule (~every 15 s). On gust onset the
  monitor declares the falling side S = sign of gust.
- CONTRALATERAL HAND MAP: gust toward +x (right) -> RIGHT hand ->
  operated by LEFT hemisphere (Gemma :8080). Gust toward -x (left) ->
  LEFT hand -> operated by RIGHT hemisphere (Qwen :8081).
- CATCH: the operating hemisphere gets the monitor string + the catch
  sentence, temp 0.2, max 16 tokens, whitespace-tolerant float parsing,
  NO newline stop-token (v1's bug — not repeated). A parseable reply with
  the CORRECT sign (opposing the drift) arriving within 2.5 s of gust
  onset replaces PID tilt for 1.5 s (catch window); then the spine
  resumes. Late / wrong-sign / unparseable = missed catch.
- WORK LOAD: each hemisphere runs a continuous queue of short work tasks
  on its own server (6 rotating questions, ~40-token answers). A catch
  prompt is issued immediately on the assigned side (preempts its queue
  at issue level; an in-flight work call finishing first is a real,
  measured cost). The non-assigned side's queue is never touched.

Arms (identical plant, seed, schedule, prompts, caps):
- R (reflex law): assignment computed from gust sign by the monitor.
  ZERO model calls to decide who catches.
- D (decider): on gust onset LEFT (Gemma) is first asked who catches
  (reply LEFT or RIGHT — naming a HAND, mapped through the same
  contralateral hand map; a wrong ruling still routes to whoever it
  named), THEN the named hemisphere gets the catch prompt. The decider's
  latency stacks inside the same 2.5 s catch window, and LEFT's work
  queue is disrupted for every event regardless of side.

Pre-registered gates: reflex law WINS iff catches_R >= catches_D AND
mean catch latency_R is >= 0.3 s below latency_D AND total work
completed_R >= work_D.

Joules are ESTIMATES only: tokens * 0.5 J/token (harness convention).
"""

import json
import math
import random
import re
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

GEMMA = "http://127.0.0.1:8080"   # LEFT hemisphere
QWEN = "http://127.0.0.1:8081"    # RIGHT hemisphere

SIDES = {
    "LEFT": {"server": GEMMA, "name": "LEFT hemisphere (Gemma :8080)"},
    "RIGHT": {"server": QWEN, "name": "RIGHT hemisphere (Qwen :8081)"},
}
# Contralateral hand map: hand -> operating hemisphere.
HAND_TO_HEMISPHERE = {"RIGHT": "LEFT", "LEFT": "RIGHT"}

# Plant constants (v1 lineage where sensible).
DT = 0.01
RUN_SECONDS = 120.0
BEAM_HALF = 1.0
CENTER_TOL = 0.15
JOULES_PER_TOKEN_EST = 0.5

# Spine PID (wrapper). Authority capped at +/-6 deg. Gains chosen so the
# spine holds the ball in calm air but CANNOT hold against a gust:
# gust equilibrium x_eq = 0.9 / (0.55 * Kp) = 1.36 > beam half-length.
PID_KP = 1.2
PID_KI = 0.1
PID_KD = 1.2
SPINE_TILT_CAP = 6.0

# Gusts / catches.
GUST_ACCEL = 0.9
GUST_DURATION = 3.0
CATCH_TILT_CAP = 12.0
CATCH_WINDOW_S = 1.5      # catch tilt replaces PID tilt for this long
CATCH_DEADLINE_S = 2.5    # reply must arrive within this of gust onset
SEED = 20261020

WORK_QUESTIONS = [
    "Name three primary colors and one short fact about each.",
    "List four animals that live in the ocean and one trait of each.",
    "Give three tips for staying hydrated, one sentence each.",
    "Name three planets and one fact about each.",
    "List three uses for a paperclip other than holding paper.",
    "Name three musical instruments and the sound each makes, briefly.",
]

NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def make_gust_schedule(seed):
    """Seeded gust schedule: first gust ~t=10-15, then every ~12-18 s."""
    rng = random.Random(seed)
    gusts = []
    t = 10.0 + rng.uniform(0.0, 5.0)
    while t < RUN_SECONDS - GUST_DURATION - 2.0:
        side = rng.choice([+1, -1])
        gusts.append({"onset": round(t, 2), "sign": side,
                      "accel": GUST_ACCEL * side,
                      "duration": GUST_DURATION})
        t += rng.uniform(12.0, 18.0)
    return gusts


def llm_call(server, prompt, n_predict, temperature, timeout=60):
    """One llama-server completion. Returns (text, tokens, latency_s,
    error_str). Never raises. NO stop tokens anywhere (v1 bug)."""
    body = json.dumps({
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": temperature,
        "cache_prompt": False,
    }).encode()
    req = urllib.request.Request(
        server.rstrip("/") + "/completion", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except Exception as e:
        return None, 0, time.perf_counter() - t0, repr(e)
    latency = time.perf_counter() - t0
    text = data.get("content")
    if text is None:
        return None, 0, latency, "no content field"
    tokens = None
    timings = data.get("timings") or {}
    if isinstance(timings.get("predicted_n"), int):
        tokens = timings["predicted_n"]
    elif isinstance(data.get("tokens_predicted"), int):
        tokens = data["tokens_predicted"]
    if tokens is None:
        tokens = max(1, len(text) // 4)
    return text, tokens, latency, None


def parse_first_float(text):
    """Whitespace-tolerant: first float anywhere in the reply."""
    if not text:
        return None
    m = NUMBER_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def family_workload_present():
    for pattern in ("[T]S4", "[P]roton"):
        try:
            out = subprocess.run(["pgrep", "-af", pattern],
                                 capture_output=True, text=True, timeout=5)
        except Exception:
            continue
        if out.returncode == 0 and out.stdout.strip():
            return pattern, out.stdout.strip().splitlines()[:3]
    return None


class Plant:
    """Beam + spine PID + gust schedule + catch override + metrics.

    Physics thread paced to wall clock (as v1). The spine computes tilt
    every step unless a catch override is active.
    """

    def __init__(self, gusts):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.abort_reason = None
        self.gusts = gusts
        self.t = 0.0
        self.x = 0.0            # ball starts centered
        self.v = 0.0
        self.theta = 0.0
        self.integral = 0.0
        self.falls = 0
        self.fall_times = []
        self.samples = 0
        self.in_center = 0
        self.catch_tilt = None
        self.catch_until = -1.0     # sim time
        self.fired_gusts = set()    # indices whose onset event fired
        self.on_gust_onset = None   # callback(gust_index, gust, wall_t0)
        self.started_mono = None

    # -- gust helpers ---------------------------------------------------
    def gust_accel_at(self, t):
        for g in self.gusts:
            if g["onset"] <= t < g["onset"] + g["duration"]:
                return g["accel"]
        return 0.0

    def active_gust(self, t):
        for i, g in enumerate(self.gusts):
            if g["onset"] <= t < g["onset"] + g["duration"]:
                return i, g
        return None, None

    # -- physics --------------------------------------------------------
    def _step_locked(self):
        t = self.t
        # Gust onset events: fire callback once per gust (in a thread so
        # model calls never block physics).
        for i, g in enumerate(self.gusts):
            if i not in self.fired_gusts and t >= g["onset"]:
                self.fired_gusts.add(i)
                if self.on_gust_onset is not None:
                    threading.Thread(
                        target=self.on_gust_onset,
                        args=(i, dict(g), time.perf_counter()),
                        daemon=True).start()
        # Spine PID (target = 0) unless a catch override is active.
        if t < self.catch_until and self.catch_tilt is not None:
            theta = self.catch_tilt
        else:
            err = -self.x
            self.integral += err * DT
            self.integral = max(-3.0, min(3.0, self.integral))
            deriv = -self.v
            theta = (PID_KP * err + PID_KI * self.integral
                     + PID_KD * deriv)
            theta = max(-SPINE_TILT_CAP, min(SPINE_TILT_CAP, theta))
        self.theta = theta
        a = 0.55 * theta - 0.12 * self.v + self.gust_accel_at(t)
        self.x += self.v * DT
        self.v += a * DT
        self.t += DT
        self.samples += 1
        if abs(self.x) < CENTER_TOL:
            self.in_center += 1
        if abs(self.x) > BEAM_HALF:
            self.falls += 1
            self.fall_times.append(round(self.t, 2))
            self.x = 0.0        # v2 reset rule: back to center
            self.v = 0.0
            self.integral = 0.0

    def physics_loop(self):
        self.started_mono = time.monotonic()
        while not self.stop_event.is_set():
            with self.lock:
                if self.t >= RUN_SECONDS:
                    break
                self._step_locked()
                t_now = self.t
            wake = self.started_mono + t_now
            delay = wake - time.monotonic()
            if delay > 0:
                time.sleep(min(delay, DT))
        self.stop_event.set()

    # -- accessors ------------------------------------------------------
    def snapshot(self):
        with self.lock:
            gi, g = self.active_gust(self.t)
            return {"t": self.t, "x": self.x, "v": self.v,
                    "theta": self.theta, "falls": self.falls,
                    "gust": g}

    def apply_catch(self, tilt):
        with self.lock:
            self.catch_tilt = max(-CATCH_TILT_CAP,
                                  min(CATCH_TILT_CAP, float(tilt)))
            self.catch_until = self.t + CATCH_WINDOW_S

    def metrics(self):
        with self.lock:
            n = max(1, self.samples)
            return {
                "falls": self.falls,
                "fall_times": list(self.fall_times),
                "time_in_center_pct": 100.0 * self.in_center / n,
                "samples": self.samples,
                "final_t": self.t,
                "final_x": self.x,
            }


def monitor_state(plant):
    """THE centered monitor: ONE state string, identical for both
    hemispheres. No per-side views exist anywhere in this program."""
    s = plant.snapshot()
    x, v, theta = s["x"], s["v"], s["theta"]
    side_word = ("right of center" if x > 0.005 else
                 "left of center" if x < -0.005 else "at center")
    text = (f"Ball monitor: x={x:+.2f} ({side_word}), v={v:+.2f}, "
            f"tilt={theta:+.2f} deg, target=0.00. "
            f"Positive tilt pushes the ball toward +x (right).")
    g = s["gust"]
    if g is not None:
        direction = "+x (right)" if g["sign"] > 0 else "-x (left)"
        text += f" Gust active: ball falling toward {direction}."
    return text


class SideWorker:
    """Continuous short-work queue on one hemisphere's own server."""

    def __init__(self, side, plant):
        self.side = side
        self.server = SIDES[side]["server"]
        self.plant = plant
        self.lock = threading.Lock()
        self.completed = 0
        self.tokens = 0
        self.q_index = 0

    def loop(self):
        while not self.plant.stop_event.is_set():
            if self.plant.snapshot()["t"] >= RUN_SECONDS:
                break
            q = WORK_QUESTIONS[self.q_index % len(WORK_QUESTIONS)]
            self.q_index += 1
            _text, tokens, _lat, err = llm_call(
                self.server, q, n_predict=56, temperature=0.5,
                timeout=60)
            with self.lock:
                self.tokens += tokens
                if err is None:
                    self.completed += 1

    def stats(self):
        with self.lock:
            return {"completed": self.completed, "tokens": self.tokens}


class ArmRunner:
    def __init__(self, arm, gusts):
        self.arm = arm                      # "R" or "D"
        self.plant = Plant(gusts)
        self.workers = {side: SideWorker(side, self.plant)
                        for side in SIDES}
        self.events = []
        self.events_lock = threading.Lock()
        self.tokens_lock = threading.Lock()
        self.catch_tokens = 0
        self.decider_tokens = 0
        self.plant.on_gust_onset = self.handle_gust

    # -- event handling -------------------------------------------------
    def handle_gust(self, gust_index, gust, wall_t0):
        sign = gust["sign"]
        falling_hand = "RIGHT" if sign > 0 else "LEFT"
        record = {
            "gust_index": gust_index,
            "onset_t": gust["onset"],
            "gust_sign": sign,
            "gust_accel": gust["accel"],
            "falling_side": "+x (right)" if sign > 0 else "-x (left)",
            "falling_hand": falling_hand,
            "arm": self.arm,
            "decider": None,
            "assigned_hemisphere": None,
            "catch": None,
            "caught": False,
            "miss_reason": None,
            "fell": None,       # filled at end from fall_times
        }
        if self.arm == "R":
            # Reflex law: monitor assigns by hand map. Zero model calls.
            record["assigned_hemisphere"] = HAND_TO_HEMISPHERE[falling_hand]
        else:
            record["decider"] = self.ask_decider(gust, falling_hand)
            named = record["decider"]["named_hand"]
            if named is None:
                record["miss_reason"] = "decider_failed"
                with self.events_lock:
                    self.events.append(record)
                return
            record["assigned_hemisphere"] = HAND_TO_HEMISPHERE[named]
        self.issue_catch(record, wall_t0)
        with self.events_lock:
            self.events.append(record)

    def ask_decider(self, gust, falling_hand):
        side_word = "right (+x)" if gust["sign"] > 0 else "left (-x)"
        prompt = (monitor_state(self.plant)
                  + f"\nBall falling {side_word}. Who catches it? "
                    "Reply LEFT or RIGHT.")
        text, tokens, latency, err = llm_call(
            GEMMA, prompt, n_predict=8, temperature=0.2, timeout=30)
        with self.tokens_lock:
            self.decider_tokens += tokens
        named = None
        if text:
            m = re.search(r"\b(LEFT|RIGHT)\b", text.upper())
            if m:
                named = m.group(1)
        return {
            "prompt": prompt, "reply": text, "tokens": tokens,
            "latency_s": latency, "error": err,
            "named_hand": named,
            "decider_correct": (named == falling_hand) if named else False,
            "routed_hemisphere": (HAND_TO_HEMISPHERE[named]
                                  if named else None),
        }

    def issue_catch(self, record, wall_t0):
        hemi = record["assigned_hemisphere"]
        server = SIDES[hemi]["server"]
        prompt = (monitor_state(self.plant)
                  + "\nBall falling toward your hand. Reply with ONE "
                    "number: catch tilt in degrees (max +/-12).")
        text, tokens, _lat, err = llm_call(
            server, prompt, n_predict=16, temperature=0.2, timeout=30)
        arrival_wall = time.perf_counter()
        latency = arrival_wall - wall_t0     # from gust onset (wall clock)
        with self.tokens_lock:
            self.catch_tokens += tokens
        tilt = parse_first_float(text)
        caught = False
        reason = None
        if err is not None:
            reason = f"server_error: {err}"
        elif tilt is None:
            reason = "unparseable"
        elif latency > CATCH_DEADLINE_S:
            reason = "late"
        elif tilt == 0 or (tilt > 0) == (record["gust_sign"] > 0):
            # Correct catch tilt must OPPOSE the drift: gust toward +x
            # needs negative tilt (positive tilt pushes toward +x).
            reason = "wrong_sign"
        else:
            caught = True
            if not self.plant.stop_event.is_set():
                self.plant.apply_catch(tilt)
        record["catch"] = {
            "hemisphere": hemi, "server": server, "prompt": prompt,
            "reply": text, "tokens": tokens,
            "latency_from_onset_s": latency, "error": err,
            "parsed_tilt": tilt, "applied": caught,
        }
        record["caught"] = caught
        record["miss_reason"] = reason

    # -- run ------------------------------------------------------------
    def run(self):
        wall0 = time.monotonic()
        phys = threading.Thread(target=self.plant.physics_loop,
                                daemon=True)
        mon = threading.Thread(target=self._family_monitor, daemon=True)
        phys.start()
        mon.start()
        threads = []
        for side in SIDES:
            th = threading.Thread(target=self.workers[side].loop,
                                  daemon=True)
            th.start()
            threads.append(th)
        phys.join(timeout=RUN_SECONDS + 30)
        self.plant.stop_event.set()
        for th in threads:
            th.join(timeout=20)
        # Let any in-flight gust handlers settle, then fill fell flags.
        time.sleep(0.5)
        with self.events_lock:
            events = sorted(self.events, key=lambda e: e["onset_t"])
        fall_times = self.plant.metrics()["fall_times"]
        for ev in events:
            ev["fell"] = any(
                ev["onset_t"] <= ft <= ev["onset_t"] + 6.0
                for ft in fall_times)
        return events, time.monotonic() - wall0

    def _family_monitor(self):
        while not self.plant.stop_event.is_set():
            hit = family_workload_present()
            if hit:
                self.plant.abort_reason = (
                    f"family workload appeared: {hit[0]}")
                self.plant.stop_event.set()
                return
            time.sleep(2.0)

    def result(self, events, wall_s):
        m = self.plant.metrics()
        work = {side: self.workers[side].stats() for side in SIDES}
        with self.tokens_lock:
            catch_tokens = self.catch_tokens
            decider_tokens = self.decider_tokens
        work_tokens = sum(w["tokens"] for w in work.values())
        total_tokens = work_tokens + catch_tokens + decider_tokens
        lat = [e["catch"]["latency_from_onset_s"] for e in events
               if e.get("catch")]
        caught_lat = [e["catch"]["latency_from_onset_s"] for e in events
                      if e.get("catch") and e["caught"]]
        per_side = {}
        for side in SIDES:
            evs = [e for e in events
                   if e["assigned_hemisphere"] == side]
            per_side[side] = {
                "events_assigned": len(evs),
                "catches": sum(1 for e in evs if e["caught"]),
                "misses": sum(1 for e in evs if not e["caught"]),
                "work_completed": work[side]["completed"],
                "work_tokens": work[side]["tokens"],
            }
        return {
            "arm": self.arm,
            "falls": m["falls"],
            "fall_times": m["fall_times"],
            "time_in_center_pct": m["time_in_center_pct"],
            "events_total": len(events),
            "catches": sum(1 for e in events if e["caught"]),
            "misses": sum(1 for e in events if not e["caught"]),
            "catch_latency_mean_s": (
                sum(lat) / len(lat) if lat else None),
            "catch_latency_mean_caught_only_s": (
                sum(caught_lat) / len(caught_lat) if caught_lat else None),
            "work_completed_per_side": {
                side: work[side]["completed"] for side in SIDES},
            "work_completed_total": sum(
                w["completed"] for w in work.values()),
            "per_side": per_side,
            "events": events,
            "tokens": {"work": work_tokens, "catch": catch_tokens,
                       "decider": decider_tokens, "total": total_tokens},
            "joules_est": total_tokens * JOULES_PER_TOKEN_EST,
            "joules_basis": "EST: tokens * 0.5 J/token",
            "wall_time_s": wall_s,
            "aborted": self.plant.abort_reason is not None,
            "abort_reason": self.plant.abort_reason,
        }


def run_arm(arm, gusts):
    runner = ArmRunner(arm, gusts)
    events, wall = runner.run()
    return runner.result(events, wall)


def main():
    out = Path(__file__).resolve().parent / "ball_balance_v2_results.json"
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    gusts = make_gust_schedule(SEED)
    results = {
        "test": "ball_balance v2 — reflex law vs decider",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "gust_schedule": gusts,
        "design": {
            "monitor": "single monitor_state() string, both hemispheres",
            "spine": f"PID Kp={PID_KP} Ki={PID_KI} Kd={PID_KD}, "
                     f"tilt cap +/-{SPINE_TILT_CAP} deg",
            "gust": f"accel +/-{GUST_ACCEL} for {GUST_DURATION} s",
            "hand_map": HAND_TO_HEMISPHERE,
            "catch": f"correct-sign reply within {CATCH_DEADLINE_S} s "
                     f"of onset replaces PID tilt for "
                     f"{CATCH_WINDOW_S} s (cap +/-{CATCH_TILT_CAP} deg)",
            "fall_rule": "|x| > 1.0 -> reset to center, falls += 1",
            "plant": "a = 0.55*theta - 0.12*v + gust; x += v*dt; "
                     "v += a*dt; dt=0.01; real-time paced; "
                     "ball starts centered; target = 0",
        },
        "arms": {},
    }
    for arm in ("R", "D"):
        print(f"=== ARM {arm} starting {datetime.now().isoformat()} ===",
              flush=True)
        res = run_arm(arm, gusts)
        results["arms"][arm] = res
        print(f"=== ARM {arm} done: events={res['events_total']} "
              f"catches={res['catches']} misses={res['misses']} "
              f"falls={res['falls']} "
              f"in_center={res['time_in_center_pct']:.1f}% "
              f"work={res['work_completed_total']} "
              f"tokens={res['tokens']['total']} "
              f"aborted={res['aborted']} ===", flush=True)
    r, d = results["arms"]["R"], results["arms"]["D"]
    lat_r, lat_d = r["catch_latency_mean_s"], d["catch_latency_mean_s"]
    results["gate"] = {
        "catches_condition": r["catches"] >= d["catches"],
        "latency_condition": (
            lat_r is not None and lat_d is not None
            and (lat_d - lat_r) >= 0.3),
        "latency_margin_s": (
            (lat_d - lat_r) if (lat_r is not None and lat_d is not None)
            else None),
        "work_condition": r["work_completed_total"]
        >= d["work_completed_total"],
        "reflex_law_wins": (
            r["catches"] >= d["catches"]
            and lat_r is not None and lat_d is not None
            and (lat_d - lat_r) >= 0.3
            and r["work_completed_total"] >= d["work_completed_total"]),
    }
    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(results, indent=2))
    print(f"results written to {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
