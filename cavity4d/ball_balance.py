#!/usr/bin/env python3
"""Ball-balancing dual-task test for the bilateral body hypothesis.

Plant (fixed by the test design):
- 1D ball on a tilting beam; state x, v, commanded tilt theta (deg).
- Beam half-length 1.0; a fall is a crossing into |x| > 1.0. No reset rule
  was specified, so none is invented: after a fall the ball remains under
  the same plant equations and can be driven back inside.
- Physics at dt=0.01 s: a = 0.55*theta - 0.12*v + wind(t);
  x += v*dt; v += a*dt (in that order).
- Wind = +0.35 during t in [40, 70]. Target = 0.0 before t=90, +0.30 after.
- Initial state x=0.45, v=0, theta=0. Runs last 120 s of sim time and are
  paced to the wall clock, so server latency is the real constraint.
- Sensor values shown to controllers are quantized to 2 decimals, sampled
  only at control calls. Tilt is zero-order held between calls.
- There is deliberately NO wrapper-side control assistance (no PID, no
  clamping beyond the specified +/-12 deg command clamp): the models are
  the controllers.

Arms:
- S (single): Gemma (:8080) issues reflex calls and thinking calls from
  one sequential loop. While a thinking answer generates, reflex calls
  wait. This serialization is the phenomenon under test.
- B (bilateral): Qwen (:8081) issues reflex calls continuously from a
  thread while Gemma (:8080) answers thinking questions in the main
  thread. At t=55 Gemma also receives a 5-second performance summary and
  may emit one short strategy note; the note text is appended to later
  reflex prompts as "coach note: ...".

Joules are ESTIMATES only: tokens * 0.5 J/token (the harness convention).
"""

import argparse
import json
import math
import re
import subprocess
import sys
import threading
import time
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

GEMMA = "http://127.0.0.1:8080"
QWEN = "http://127.0.0.1:8081"

DT = 0.01
RUN_SECONDS = 120.0
BEAM_HALF = 1.0
CENTER_TOL = 0.15
TILT_CLAMP = 12.0
INITIAL_X = 0.45
JOULES_PER_TOKEN_EST = 0.5

THINKING_SCHEDULE = [
    (20.0, "Explain in ~120 words why a ball on a tilting beam is harder "
           "to balance when corrections are delayed."),
    (50.0, "In ~120 words: what strategy should a balancing controller "
           "use when a steady sideways force appears?"),
    (80.0, "In ~120 words: the target just moved (or is about to) - how "
           "should the controller adapt?"),
]
COACH_T = 55.0

REFLEX_TEMPLATE = """You control a ball on a tilting beam. Positive tilt accelerates the ball toward +x. Reply with ONLY a new tilt number in degrees, from -12 to 12.
Examples:
x=0.40, v=0.30, tilt=0.00, target=0.00 -> -8
x=-0.10, v=-0.30, tilt=0.00, target=0.20 -> 8
x=0.32, v=-0.50, tilt=1.00, target=0.30 -> 5
{coach}Now: x={x}, v={v}, tilt={tilt}, target={target} ->"""

NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def clamp_tilt(value):
    return max(-TILT_CLAMP, min(TILT_CLAMP, float(value)))


def parse_tilt(text):
    """First number in the reply, clamped; None if unparseable."""
    if not text:
        return None
    m = NUMBER_RE.search(text)
    if not m:
        return None
    try:
        return clamp_tilt(float(m.group(0)))
    except ValueError:
        return None


def llm_call(server, prompt, n_predict, temperature, timeout=120):
    """One llama-server completion. Returns (text, tokens, latency_s,
    error_str). Never raises."""
    body = json.dumps({
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": temperature,
        "cache_prompt": False,
        "stop": ["\n"] if n_predict <= 40 else [],
    }).encode()
    req = urllib.request.Request(
        server.rstrip("/") + "/completion", data=body,
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except Exception as e:  # server error / timeout: caller holds tilt
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


def target_at(t):
    return 0.30 if t >= 90.0 else 0.0


def wind_at(t):
    return 0.35 if 40.0 <= t <= 70.0 else 0.0


def q2(value):
    """Quantize to 2 decimals for the sensor readout / prompts."""
    v = round(float(value) + 1e-12, 2)
    return 0.0 if v == 0 else v


def family_workload_present():
    """Bracket-pattern checks for family workloads (Sims / Proton)."""
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
    """The beam, its physics thread, and streaming metrics."""

    def __init__(self):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.abort_reason = None
        self.t = 0.0
        self.x = INITIAL_X
        self.v = 0.0
        self.theta = 0.0
        self.outside = False
        self.falls = 0
        self.samples = 0
        self.in_center = 0
        self.sq_err_sum = 0.0
        self.max_abs_x = abs(INITIAL_X)
        self.recent = deque(maxlen=int(5.0 / DT) + 2)  # last ~5 s
        self.coach_note = ""
        self.started_mono = None

    # -- physics ------------------------------------------------------
    def _step_locked(self):
        wind = wind_at(self.t)
        a = 0.55 * self.theta - 0.12 * self.v + wind
        self.x += self.v * DT
        self.v += a * DT
        self.t += DT
        target = target_at(self.t)
        err = self.x - target
        self.samples += 1
        if abs(err) < CENTER_TOL:
            self.in_center += 1
        self.sq_err_sum += err * err
        if abs(self.x) > self.max_abs_x:
            self.max_abs_x = abs(self.x)
        if abs(self.x) > BEAM_HALF and not self.outside:
            self.falls += 1
            self.outside = True
        elif abs(self.x) <= BEAM_HALF:
            self.outside = False
        self.recent.append((self.t, self.x, target))

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

    # -- accessors ----------------------------------------------------
    def snapshot(self):
        with self.lock:
            return {
                "t": self.t, "x": self.x, "v": self.v,
                "theta": self.theta, "target": target_at(self.t),
                "falls": self.falls,
            }

    def set_theta(self, value):
        with self.lock:
            self.theta = clamp_tilt(value)

    def set_coach_note(self, note):
        with self.lock:
            self.coach_note = note

    def get_coach_note(self):
        with self.lock:
            return self.coach_note

    def summary_5s(self):
        with self.lock:
            recent = list(self.recent)
            snap = {
                "t": self.t, "x": self.x, "falls": self.falls,
                "target": target_at(self.t),
                "wind_active": wind_at(self.t) != 0.0,
            }
        if recent:
            mean_x = sum(r[1] for r in recent) / len(recent)
            rms = math.sqrt(
                sum((r[1] - r[2]) ** 2 for r in recent) / len(recent))
        else:
            mean_x, rms = snap["x"], abs(snap["x"] - snap["target"])
        snap["mean_x_5s"] = mean_x
        snap["rms_err_5s"] = rms
        return snap

    def metrics(self):
        with self.lock:
            n = max(1, self.samples)
            return {
                "falls": self.falls,
                "time_in_center_pct": 100.0 * self.in_center / n,
                "rms_abs_error": math.sqrt(self.sq_err_sum / n),
                "max_abs_x": self.max_abs_x,
                "samples": self.samples,
                "final_t": self.t,
                "final_x": self.x,
                "final_v": self.v,
            }


class ArmStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.reflex_calls = 0
        self.reflex_tokens = 0
        self.reflex_latencies = []
        self.reflex_unparseable = 0
        self.reflex_errors = 0
        self.thinking = []       # full answer records
        self.thinking_tokens = 0
        self.coach = None        # B arm only
        self.coach_tokens = 0

    def add_reflex(self, tokens, latency, parsed, error):
        with self.lock:
            self.reflex_calls += 1
            self.reflex_tokens += tokens
            self.reflex_latencies.append(latency)
            if error:
                self.reflex_errors += 1
            if not parsed:
                self.reflex_unparseable += 1

    def totals(self):
        with self.lock:
            total_tokens = (self.reflex_tokens + self.thinking_tokens
                            + self.coach_tokens)
            lat = sorted(self.reflex_latencies)
            if lat:
                mean_lat = sum(lat) / len(lat)
                p95 = lat[max(0, math.ceil(0.95 * len(lat)) - 1)]
            else:
                mean_lat, p95 = None, None
            return {
                "control_calls": self.reflex_calls,
                "control_latency_mean_s": mean_lat,
                "control_latency_p95_s": p95,
                "control_unparseable": self.reflex_unparseable,
                "control_errors": self.reflex_errors,
                "tokens": {
                    "reflex": self.reflex_tokens,
                    "thinking": self.thinking_tokens,
                    "coach": self.coach_tokens,
                    "total": total_tokens,
                },
                "joules_est": total_tokens * JOULES_PER_TOKEN_EST,
                "joules_basis": "EST: tokens * 0.5 J/token",
            }


def reflex_prompt(snap, coach_note):
    coach = ""
    if coach_note:
        flat = " ".join(str(coach_note).split())
        coach = f"coach note: {flat}\n"
    return REFLEX_TEMPLATE.format(
        coach=coach,
        x=f"{q2(snap['x']):.2f}", v=f"{q2(snap['v']):.2f}",
        tilt=f"{q2(snap['theta']):.2f}",
        target=f"{q2(snap['target']):.2f}")


def do_reflex(server, plant, stats):
    snap = plant.snapshot()
    prompt = reflex_prompt(snap, plant.get_coach_note())
    text, tokens, latency, error = llm_call(
        server, prompt, n_predict=12, temperature=0.2, timeout=60)
    tilt = parse_tilt(text) if text else None
    if tilt is not None and not plant.stop_event.is_set():
        plant.set_theta(tilt)
    stats.add_reflex(tokens, latency, parsed=tilt is not None, error=error)
    return tilt


def do_thinking(server, plant, stats, scheduled_t, question):
    started = plant.snapshot()["t"]
    text, tokens, latency, error = llm_call(
        server, question, n_predict=180, temperature=0.5, timeout=120)
    record = {
        "scheduled_t": scheduled_t,
        "started_t": started,
        "finished_t": plant.snapshot()["t"],
        "question": question,
        "answer": text if text is not None else "",
        "tokens": tokens,
        "latency_s": latency,
        "error": error,
    }
    with stats.lock:
        stats.thinking.append(record)
        stats.thinking_tokens += tokens
    return record


def do_coach(plant, stats):
    s = plant.summary_5s()
    prompt = (
        "You are the LEFT hemisphere of a balancing robot. Your RIGHT "
        "hemisphere is busy issuing tilt reflexes. Here is a 5-second "
        "performance summary: current x={x:.2f}, mean x over last 5 s = "
        "{mx:.2f}, RMS error over last 5 s = {rms:.2f}, falls so far = "
        "{falls}, target = {tg:.2f}, steady sideways wind force active = "
        "{wind}. Output ONE short strategy note (at most 40 tokens) that "
        "will be appended to the reflex controller's prompts. Note only, "
        "no analysis.").format(
            x=q2(s["x"]), mx=q2(s["mean_x_5s"]), rms=q2(s["rms_err_5s"]),
            falls=s["falls"], tg=q2(s["target"]),
            wind="yes" if s["wind_active"] else "no")
    text, tokens, latency, error = llm_call(
        GEMMA, prompt, n_predict=40, temperature=0.5, timeout=120)
    note = (text or "").strip()
    record = {
        "scheduled_t": COACH_T,
        "started_t": s["t"],
        "summary": {
            "current_x": s["x"], "mean_x_5s": s["mean_x_5s"],
            "rms_err_5s": s["rms_err_5s"], "falls_so_far": s["falls"],
            "target": s["target"], "wind_active": s["wind_active"],
        },
        "note": note,
        "tokens": tokens,
        "latency_s": latency,
        "error": error,
    }
    with stats.lock:
        stats.coach = record
        stats.coach_tokens += tokens
    if note:
        plant.set_coach_note(note)
    return record


def monitor_family_workload(plant):
    while not plant.stop_event.is_set():
        hit = family_workload_present()
        if hit:
            plant.abort_reason = f"family workload appeared: {hit[0]}"
            plant.stop_event.set()
            return
        time.sleep(2.0)


def run_arm_s():
    plant = Plant()
    stats = ArmStats()
    phys = threading.Thread(target=plant.physics_loop, daemon=True)
    mon = threading.Thread(target=monitor_family_workload, args=(plant,),
                           daemon=True)
    wall0 = time.monotonic()
    phys.start()
    mon.start()
    events = [(t, q) for t, q in THINKING_SCHEDULE]
    idx = 0
    while not plant.stop_event.is_set():
        snap_t = plant.snapshot()["t"]
        if snap_t >= RUN_SECONDS:
            break
        if idx < len(events) and snap_t >= events[idx][0]:
            do_thinking(GEMMA, plant, stats, events[idx][0], events[idx][1])
            idx += 1
            continue
        do_reflex(GEMMA, plant, stats)
    plant.stop_event.set()
    phys.join(timeout=5)
    return plant, stats, time.monotonic() - wall0


def run_arm_b():
    plant = Plant()
    stats = ArmStats()
    phys = threading.Thread(target=plant.physics_loop, daemon=True)
    mon = threading.Thread(target=monitor_family_workload, args=(plant,),
                           daemon=True)
    wall0 = time.monotonic()
    phys.start()
    mon.start()

    def reflex_loop():
        while not plant.stop_event.is_set():
            if plant.snapshot()["t"] >= RUN_SECONDS:
                break
            do_reflex(QWEN, plant, stats)

    refl = threading.Thread(target=reflex_loop, daemon=True)
    refl.start()
    events = [(t, "think", q) for t, q in THINKING_SCHEDULE]
    events.append((COACH_T, "coach", None))
    events.sort(key=lambda e: e[0])
    idx = 0
    while not plant.stop_event.is_set():
        snap_t = plant.snapshot()["t"]
        if snap_t >= RUN_SECONDS:
            break
        if idx < len(events) and snap_t >= events[idx][0]:
            when, kind, payload = events[idx]
            if kind == "think":
                do_thinking(GEMMA, plant, stats, when, payload)
            else:
                do_coach(plant, stats)
            idx += 1
            continue
        time.sleep(0.01)
    plant.stop_event.set()
    phys.join(timeout=5)
    refl.join(timeout=15)
    return plant, stats, time.monotonic() - wall0


def arm_result(plant, stats, wall_s):
    result = plant.metrics()
    totals = stats.totals()
    result.update(totals)
    result["wall_time_s"] = wall_s
    result["aborted"] = plant.abort_reason is not None
    result["abort_reason"] = plant.abort_reason
    with stats.lock:
        result["thinking_answers"] = list(stats.thinking)
        result["coach_note"] = (
            stats.coach["note"] if stats.coach else None)
        result["coach_record"] = stats.coach
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["S", "B", "both"], default="both")
    ap.add_argument("--out", default=str(
        Path(__file__).resolve().parent / "ball_balance_results.json"))
    args = ap.parse_args()

    results = {
        "test": "ball_balance dual-task bilateral test",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "plant": {
            "dt": DT, "run_seconds": RUN_SECONDS, "initial_x": INITIAL_X,
            "physics": "a = 0.55*theta - 0.12*v + wind; x += v*dt; "
                       "v += a*dt",
            "wind": "+0.35 for t in [40, 70]",
            "target": "0.0 before t=90; +0.30 from t=90",
            "fall_rule": "crossing into |x| > 1.0; no reset (none "
                         "specified)",
            "reflex_prompt_template": REFLEX_TEMPLATE,
            "thinking_schedule": [
                {"t": t, "question": q} for t, q in THINKING_SCHEDULE],
        },
        "arms": {},
    }

    order = ["S", "B"] if args.arm == "both" else [args.arm]
    for arm in order:
        print(f"=== ARM {arm} starting "
              f"{datetime.now().isoformat()} ===", flush=True)
        if arm == "S":
            plant, stats, wall = run_arm_s()
        else:
            plant, stats, wall = run_arm_b()
        res = arm_result(plant, stats, wall)
        results["arms"][arm] = res
        print(f"=== ARM {arm} done: falls={res['falls']} "
              f"in_center={res['time_in_center_pct']:.1f}% "
              f"rms={res['rms_abs_error']:.3f} calls={res['control_calls']} "
              f"tokens={res['tokens']['total']} "
              f"aborted={res['aborted']} ===", flush=True)

    if "S" in results["arms"] and "B" in results["arms"]:
        s, b = results["arms"]["S"], results["arms"]["B"]
        results["gate"] = {
            "falls_condition": b["falls"] <= s["falls"],
            "in_center_condition": (
                b["time_in_center_pct"] >= s["time_in_center_pct"] + 10.0),
            "in_center_diff_points": (
                b["time_in_center_pct"] - s["time_in_center_pct"]),
            "falls_diff": b["falls"] - s["falls"],
            "thinking_quality": "parent judges from full answers in "
                                "this file",
            "balance_gate_pass": (
                b["falls"] <= s["falls"]
                and b["time_in_center_pct"]
                >= s["time_in_center_pct"] + 10.0),
        }
    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"results written to {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
