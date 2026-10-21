"""
standing_sim.py — the STANDING BODY SIM (Zak 2026-10-20 23:09 EDT).

The whole wrapper stack stands in a simulated environment: v2 plant +
spine + reflex law (geometry assigns, contralateral hand map) +
oracle_ack v2 (two-laws caring spectrum) + body_awareness feasibility.
Disturbances are SAMPLED from env_profile.json — the environment
forged from the PC's real telemetry error weather (env_forge.py) —
not from v2's fixed gust script.

Configs (same seed, same schedule, one 120 s run each):
  A mixed  LEFT role = Gemma :8080, RIGHT role = Qwen :8081
           (the current resident pair — two different "people")
  B twins  LEFT role = Gemma :8080, RIGHT role = Qwen twin :8082
           (same model in the right seat; identity readout =
           cross-side variance vs A)
  C single LEFT role = Gemma :8080, RIGHT role = Gemma :8080
           (one model carries both seats, sequentially)

Thermal events (SELF class): the ack must ESCALATE them and the body
sheds work — both work queues pause until the event clears.
Cosmetic flickers (DISCRETIONARY): noticed, gated, never interrupt.
Gusts ride the reflex law exactly as in v2.

Est joules = tokens x 0.5, labelled EST everywhere.
"""

from __future__ import annotations

import json
import random
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from body_awareness import BodySpec, OrganHistory          # noqa: E402
from oracle_ack import OracleAckV2                          # noqa: E402

GEMMA = "http://127.0.0.1:8080"
QWEN = "http://127.0.0.1:8081"
QWEN_TWIN = "http://127.0.0.1:8082"

CONFIGS = {
    "A_mixed": {"LEFT": GEMMA, "RIGHT": QWEN},
    "B_twins": {"LEFT": GEMMA, "RIGHT": QWEN_TWIN},
    "C_single": {"LEFT": GEMMA, "RIGHT": GEMMA},
}
HAND_TO_HEMISPHERE = {"RIGHT": "LEFT", "LEFT": "RIGHT"}

DT = 0.01
RUN_SECONDS = 120.0
BEAM_HALF = 1.0
CENTER_TOL = 0.15
JOULES_PER_TOKEN_EST = 0.5
PID_KP, PID_KI, PID_KD = 1.2, 0.1, 1.2
SPINE_TILT_CAP = 6.0
CATCH_TILT_CAP = 12.0
CATCH_WINDOW_S = 1.5
CATCH_DEADLINE_S = 2.5
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


# ------------------------------------------------------------ schedule --
def build_schedule(profile: dict, seed: int = SEED) -> dict:
    """One disturbance schedule from the forged environment profile,
    reused identically by every config (fairness)."""
    rng = random.Random(seed)
    classes = profile.get("event_classes", {})
    ps = classes.get("power_spike", {})
    accel = ps.get("gust_accel", 0.9)
    dur = ps.get("gust_duration_s", 3.0)
    gusts, t = [], 10.0 + rng.uniform(0.0, 5.0)
    while t < RUN_SECONDS - dur - 2.0:
        side = rng.choice([+1, -1])
        gusts.append({"onset": round(t, 2), "sign": side,
                      "accel": accel * side, "duration": dur})
        t += rng.uniform(12.0, 18.0)
    th = classes.get("thermal_excursion", {})
    n_thermal = int(th.get("events_per_120s", 1))
    thermal = []
    for _ in range(n_thermal):
        onset = round(rng.uniform(25.0, 85.0), 2)
        thermal.append({"onset": onset,
                        "duration": float(th.get("duration_s", 12.0))})
    cosmetics = [{"onset": round(rng.uniform(5.0, 115.0), 2),
                  "value": 165.0} for _ in range(6)]
    return {"gusts": gusts, "thermal": thermal, "cosmetics": cosmetics,
            "profile_sources": {k: v.get("source")
                                for k, v in classes.items()}}


# ----------------------------------------------------------------- llm --
def llm_call(server, prompt, n_predict, temperature, timeout=60):
    body = json.dumps({"prompt": prompt, "n_predict": n_predict,
                       "temperature": temperature,
                       "cache_prompt": False}).encode()
    req = urllib.request.Request(server.rstrip("/") + "/completion",
                                 data=body, headers={
                                     "Content-Type": "application/json"})
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
                                 capture_output=True, text=True,
                                 timeout=5)
        except Exception:
            continue
        if out.returncode == 0 and out.stdout.strip():
            return pattern
    return None


# ---------------------------------------------------------------- plant --
class Plant:
    def __init__(self, gusts):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.gusts = gusts
        self.t = 0.0
        self.x = 0.0
        self.v = 0.0
        self.theta = 0.0
        self.integral = 0.0
        self.falls = 0
        self.fall_times = []
        self.samples = 0
        self.in_center = 0
        self.catch_tilt = None
        self.catch_until = -1.0
        self.fired_gusts = set()
        self.on_gust_onset = None
        self.started_mono = None

    def gust_accel_at(self, t):
        for g in self.gusts:
            if g["onset"] <= t < g["onset"] + g["duration"]:
                return g["accel"]
        return 0.0

    def _step_locked(self):
        t = self.t
        for i, g in enumerate(self.gusts):
            if i not in self.fired_gusts and t >= g["onset"]:
                self.fired_gusts.add(i)
                if self.on_gust_onset is not None:
                    threading.Thread(target=self.on_gust_onset,
                                     args=(i, dict(g),
                                           time.perf_counter()),
                                     daemon=True).start()
        if t < self.catch_until and self.catch_tilt is not None:
            theta = self.catch_tilt
        else:
            err = -self.x
            self.integral += err * DT
            self.integral = max(-3.0, min(3.0, self.integral))
            theta = (PID_KP * err + PID_KI * self.integral
                     + PID_KD * (-self.v))
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
            self.x = 0.0
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
            delay = self.started_mono + t_now - time.monotonic()
            if delay > 0:
                time.sleep(min(delay, DT))
        self.stop_event.set()

    def snapshot(self):
        with self.lock:
            return {"t": self.t, "x": self.x, "v": self.v,
                    "theta": self.theta, "falls": self.falls}

    def apply_catch(self, tilt):
        with self.lock:
            self.catch_tilt = max(-CATCH_TILT_CAP,
                                  min(CATCH_TILT_CAP, float(tilt)))
            self.catch_until = self.t + CATCH_WINDOW_S

    def metrics(self):
        with self.lock:
            n = max(1, self.samples)
            return {"falls": self.falls, "fall_times": self.fall_times,
                    "time_in_center_pct": 100.0 * self.in_center / n,
                    "final_x": self.x}


def monitor_state(plant):
    s = plant.snapshot()
    return (f"Ball state (centered monitor): t={s['t']:.1f}s "
            f"x={s['x']:+.2f} (0=center, beam ends at +/-1.00), "
            f"velocity={s['v']:+.2f}, current tilt={s['theta']:+.1f} "
            f"deg, falls so far={s['falls']}. Target: keep ball at "
            f"x=0.")


def hand_local_state(plant, hand):
    """Transform the shared centered monitor into the catching
    hand's local coordinates.

    `distance_to_hand` is measured from the ball to that hand's end
    of the beam; `closing_speed` is the component of ball velocity
    toward that hand. Local tilt has one invariant meaning on both
    sides: positive pushes the ball away from the catching hand and
    back toward center; negative pulls it toward the hand. The
    wrapper converts local tilt back to the plant's global sign.
    """
    s = plant.snapshot()
    if hand == "RIGHT":
        distance = BEAM_HALF - s["x"]
        closing = max(0.0, s["v"])
        local_tilt = -s["theta"]
    else:
        distance = s["x"] + BEAM_HALF
        closing = max(0.0, -s["v"])
        local_tilt = s["theta"]
    return {"distance_to_hand": distance, "closing_speed": closing,
            "tilt_now": local_tilt, "snapshot": s}


def local_to_global_tilt(hand, local_tilt):
    return -float(local_tilt) if hand == "RIGHT" else float(local_tilt)


# ----------------------------------------------------------------- side --
class SideWorker:
    """Continuous short work tasks on one role's server. Pauses while
    the global thermal shed is active (the body sheds work)."""

    def __init__(self, role, server, plant, shed_event):
        self.role = role
        self.server = server
        self.plant = plant
        self.shed = shed_event
        self.completed = 0
        self.tokens = 0
        self.q_index = 0
        self.stop = threading.Event()

    def loop(self):
        while not self.stop.is_set() and not self.plant.stop_event.is_set():
            if self.shed.is_set():
                time.sleep(0.3)
                continue
            q = WORK_QUESTIONS[self.q_index % len(WORK_QUESTIONS)]
            self.q_index += 1
            text, tokens, lat, err = llm_call(self.server, q, 40, 0.5,
                                              timeout=60)
            if err is None and text:
                self.completed += 1
                self.tokens += tokens
            else:
                time.sleep(0.5)


# ----------------------------------------------------------------- run --
class StandingRunner:
    def __init__(self, config_name, servers, schedule):
        self.name = config_name
        self.servers = servers              # role -> server URL
        self.schedule = schedule
        self.plant = Plant(schedule["gusts"])
        self.shed = threading.Event()
        self.history = OrganHistory()
        self.ack = OracleAckV2(body=BodySpec(), history=self.history)
        self.ack.register("gust", "event", asset_risk=0.9,
                          body_asset=True, edge_level=0.1,
                          care_class="SELF")
        self.ack.register("thermal", "event", asset_risk=0.95,
                          body_asset=True, edge_level=0.5,
                          care_class="SELF")
        self.ack.register("display", "event", asset_risk=0.05,
                          edge_level=100.0, care_class="DISCRETIONARY")
        self.events = []
        self.elock = threading.Lock()
        self.tokens_by_server: dict[str, int] = {}
        self.workers = {role: SideWorker(role, srv, self.plant,
                                         self.shed)
                        for role, srv in servers.items()}
        self.abort_reason = None

    # -- ack feeding (2 Hz observation loop) -------------------------
    def ack_loop(self):
        fired_cos = set()
        while not self.plant.stop_event.is_set():
            snap = self.plant.snapshot()
            t = snap["t"]
            gust_val = self.plant.gust_accel_at(t)
            gi, gust = self.plant_active_gust(t)
            ctx = None
            if gust is not None:
                hand = "RIGHT" if gust["sign"] > 0 else "LEFT"
                ctx = {"ball": {"state": {"x": snap["x"],
                                          "v": snap["v"]},
                                "gust_accel": gust["accel"],
                                "hemisphere":
                                    HAND_TO_HEMISPHERE[hand]}}
            self.ack.process("gust", gust_val, ts=t, ctx=ctx)
            thermal_on = any(ev["onset"] <= t < ev["onset"]
                             + ev["duration"]
                             for ev in self.schedule["thermal"])
            if thermal_on:
                self.shed.set()
            else:
                self.shed.clear()
            self.ack.process("thermal", 1.0 if thermal_on else 0.0,
                             ts=t)
            disp = 0.0
            for i, c in enumerate(self.schedule["cosmetics"]):
                if c["onset"] <= t < c["onset"] + 1.0:
                    disp = c["value"]
            self.ack.process("display", disp, ts=t)
            time.sleep(0.5)

    def plant_active_gust(self, t):
        for i, g in enumerate(self.schedule["gusts"]):
            if g["onset"] <= t < g["onset"] + g["duration"]:
                return i, g
        return None, None

    # -- catch flow (reflex law, as v2) --------------------------------
    def handle_gust(self, gust_index, gust, wall_t0):
        hand = "RIGHT" if gust["sign"] > 0 else "LEFT"
        hemi = HAND_TO_HEMISPHERE[hand]
        server = self.servers[hemi]
        local = hand_local_state(self.plant, hand)
        prompt = (
            "Hand-local catch view: "
            f"distance_to_hand={local['distance_to_hand']:.2f}, "
            f"closing_speed={local['closing_speed']:.2f}, "
            f"tilt_now={local['tilt_now']:+.1f} deg. "
            "Use hand-local tilt: a positive number pushes the ball "
            "away from your hand and back toward center; a negative "
            "number pulls it toward your hand. Reply with ONE number "
            "only: the tilt that pushes the ball back toward center "
            "(between -12 and 12).")
        text, tokens, lat, err = llm_call(server, prompt, 16, 0.2,
                                          timeout=30)
        with self.elock:
            self.tokens_by_server[server] = \
                self.tokens_by_server.get(server, 0) + tokens
        value = parse_first_float(text) if text else None
        applied_tilt = (local_to_global_tilt(hand, value)
                        if value is not None else None)
        onset_latency = time.perf_counter() - wall_t0
        caught = False
        sign_error = False
        if value is not None and err is None:
            if onset_latency <= CATCH_DEADLINE_S:
                if value > 0:
                    self.plant.apply_catch(applied_tilt)
                    caught = True
                else:
                    sign_error = True
        self.history.add(hemi, onset_latency)
        with self.elock:
            self.events.append({
                "gust_index": gust_index, "onset": gust["onset"],
                "sign": gust["sign"], "falling_hand": hand,
                "hemisphere_role": hemi, "server": server,
                "reply": text, "parsed_tilt": value,
                "parsed_local_tilt": value,
                "applied_global_tilt": applied_tilt,
                "hand_local": {
                    "distance_to_hand":
                        round(local["distance_to_hand"], 3),
                    "closing_speed": round(local["closing_speed"], 3),
                    "tilt_now": round(local["tilt_now"], 3)},
                "latency_from_onset_s": round(onset_latency, 3),
                "call_latency_s": round(lat, 3), "tokens": tokens,
                "caught": caught, "sign_error": sign_error,
                "error": err})

    def run(self):
        self.plant.on_gust_onset = self.handle_gust
        threads = [threading.Thread(target=self.plant.physics_loop,
                                    daemon=True),
                   threading.Thread(target=self.ack_loop, daemon=True)]
        for w in self.workers.values():
            threads.append(threading.Thread(target=w.loop,
                                            daemon=True))
        fam_t = threading.Thread(target=self._family_monitor,
                                 daemon=True)
        threads.append(fam_t)
        for th in threads:
            th.start()
        self.plant.stop_event.wait(timeout=RUN_SECONDS + 60)
        for w in self.workers.values():
            w.stop.set()
        time.sleep(1.0)
        return self.result()

    def _family_monitor(self):
        while not self.plant.stop_event.is_set():
            hit = family_workload_present()
            if hit:
                self.abort_reason = f"family workload appeared: {hit}"
                self.plant.stop_event.set()
                return
            time.sleep(5.0)

    def result(self):
        pm = self.plant.metrics()
        by_role: dict[str, dict] = {}
        for role in ("LEFT", "RIGHT"):
            evs = [e for e in self.events
                   if e["hemisphere_role"] == role]
            lats = [e["latency_from_onset_s"] for e in evs]
            by_role[role] = {
                "server": self.servers[role],
                "events": len(evs),
                "catches": sum(1 for e in evs if e["caught"]),
                "sign_errors": sum(1 for e in evs if e["sign_error"]),
                "latency_mean": (statistics.fmean(lats) if lats
                                 else None),
                "latency_std": (statistics.pstdev(lats)
                                if len(lats) > 1 else 0.0),
                "work_completed": self.workers[role].completed,
                "work_tokens": self.workers[role].tokens,
            }
        by_hand: dict[str, dict] = {}
        for hand in ("LEFT", "RIGHT"):
            evs = [e for e in self.events
                   if e["falling_hand"] == hand]
            by_hand[hand] = {
                "events": len(evs),
                "catches": sum(1 for e in evs if e["caught"]),
                "sign_errors": sum(1 for e in evs if e["sign_error"]),
                "hemisphere_role": (evs[0]["hemisphere_role"]
                                    if evs else None),
                "server": (evs[0]["server"] if evs else None),
            }
        ack_counts: dict[str, int] = {}
        for rec in self.ack.records:
            d = rec.to_dict()
            key = f"{d.get('care_class')}/{d['disposition']}"
            ack_counts[key] = ack_counts.get(key, 0) + 1
        total_tokens = sum(self.tokens_by_server.values()) + sum(
            w.tokens for w in self.workers.values())
        return {
            "config": self.name,
            "servers": self.servers,
            "abort_reason": self.abort_reason,
            "plant": pm,
            "events": self.events,
            "by_role": by_role,
            "by_hand": by_hand,
            "ack_counts": ack_counts,
            "ack_mode_transitions": len(self.ack.mode_log),
            "tokens_total": total_tokens,
            "tokens_by_server": self.tokens_by_server,
            "est_joules": total_tokens * JOULES_PER_TOKEN_EST,
            "est_joules_basis": "tokens x 0.5 (EST)",
        }


def health_ok(server):
    try:
        with urllib.request.urlopen(server + "/health",
                                    timeout=5) as r:
            return json.loads(r.read()).get("status") == "ok"
    except Exception:
        return False


def main():
    profile = json.loads(Path(sys.argv[1]).read_text()) \
        if len(sys.argv) > 1 else {}
    out_path = sys.argv[2] if len(sys.argv) > 2 \
        else "standing_sim_results.json"
    schedule = build_schedule(profile)
    results = {"seed": SEED, "schedule_profile_sources":
               schedule["profile_sources"],
               "n_gusts": len(schedule["gusts"]),
               "n_thermal": len(schedule["thermal"]),
               "n_cosmetics": len(schedule["cosmetics"]),
               "configs": {}}
    for name, servers in CONFIGS.items():
        if not all(health_ok(s) for s in set(servers.values())):
            results["configs"][name] = {"skipped":
                                        "a required server is not "
                                        "healthy"}
            print(f"{name}: SKIPPED (health)", flush=True)
            continue
        print(f"{name}: running 120 s ...", flush=True)
        runner = StandingRunner(name, servers, schedule)
        results["configs"][name] = runner.run()
        c = results["configs"][name]
        print(f"{name}: falls={c['plant']['falls']} "
              f"in-center={c['plant']['time_in_center_pct']:.1f}% "
              f"work L/R={c['by_role']['LEFT']['work_completed']}/"
              f"{c['by_role']['RIGHT']['work_completed']} "
              f"acks={c['ack_counts']}", flush=True)
    Path(out_path).write_text(json.dumps(results, indent=1))
    print("wrote", out_path)


if __name__ == "__main__":
    main()
