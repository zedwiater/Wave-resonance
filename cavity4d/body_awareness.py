"""
body_awareness.py — the body schema layer for the bilateral Dweller.

Zak's directive (2026-10-20 22:39 EDT): the next phase is not faster hands.
Hands are limited by physics. What the body needs is AWARENESS:

  - a canonical body spec (average size / speed / power) so the stack
    installs on any robot and reasons about the same body everywhere;
  - a finesse table from MATERIALS data + observation, not task training
    (a human does not grab a coffee cup at 20 mph — the material sets
    the speed);
  - reaction fixed by PRE-PROCESSING: one observation of an event plus
    the body spec -> trajectory arithmetic -> CATCH / LET_FALL triage,
    decided BEFORE acting, priced against history (past), state
    (present), and projection (future);
  - organ history built and adjusted continually from observation —
    the oracle trusts an organ exactly as much as its record says.

Pure python, no server calls. The plant constants below are the
ball_balance_v2 plant so the oracle can be validated by replaying that
test's event log (see run_replay at the bottom).
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------- plant ---
# ball_balance_v2 plant: a = 0.55*tilt - 0.12*v + gust ; fall at |x| > 1.0
PLANT_GAIN = 0.55          # accel per degree of tilt
DRAG = 0.12                # velocity damping coefficient
EDGE_X = 1.0               # |x| at which the ball is off the beam
POINT_OF_NO_RETURN = 0.85  # |x| beyond which a catch is not attempted

# Reference spine (wrapper PID from the v2 test design, gains logged in the
# results file): tilt = clamp(-(Kp*x + Kd*v), +/-6 deg authority).
# The Ki term is omitted from the oracle's instantaneous estimate — at the
# observation instant the integral term is small (verified: predicted tilt
# +1.40 vs logged +1.43 on a developed state). Stated, not hidden.
SPINE_KP = 1.2
SPINE_KD = 1.2
SPINE_CAP_DEG = 6.0

MARGIN_CATCH_S = 0.35      # margin above which a catch is committed


# ------------------------------------------------------------- body spec ---
@dataclass
class BodySpec:
    """Canonical average body. EVERY value is a labelled assumption —
    a starting body the stack can be dropped into, to be replaced by a
    real robot's measured spec sheet. Nothing here was measured on
    hardware; that is the point of labelling it."""
    height_m: float = 1.7            # assumption: average adult height
    arm_reach_m: float = 0.75        # assumption: average arm reach
    servo_tilt_rate_dps: float = 90.0  # assumption: modest servo slew rate
    servo_max_tilt_deg: float = 12.0   # assumption: matches v2 catch cap
    servo_max_torque_nm: float = 40.0  # assumption: mid-size actuator
    grip_force_max_n: float = 80.0     # assumption: firm human-class grip
    mass_kg: float = 70.0            # assumption: average adult mass
    power_budget_w: float = 150.0    # assumption: sustained body budget


# --------------------------------------------------------------- finesse ---
# Zak's rule, verbatim in spirit: a human does not grab a coffee cup at
# 20 miles an hour. The MATERIAL sets the approach speed and grip force —
# from materials data and observation, never from task training.
# material class -> (approach_speed_mps cap, grip_force_n cap)
FINESSE = {
    "glass":   (0.05, 8),    # fragile, smooth, low fracture threshold
    "ceramic": (0.08, 12),   # coffee-cup class: brittle, chip-prone
    "plastic": (0.25, 30),
    "wood":    (0.40, 50),
    "metal":   (0.60, 80),
    "unknown": (0.10, 15),   # conservative default: unclassified = gentle
}


def finesse_for(material: str) -> tuple[float, float]:
    """(speed_cap_mps, force_cap_n) for a material class; unknown
    materials get the conservative default, never the fastest row."""
    return FINESSE.get(str(material).lower(), FINESSE["unknown"])


def clamp_manipulation(material: str, desired_speed: float,
                       desired_force: float):
    """Clamp a desired manipulation to the material's finesse caps.
    Returns (speed, force, bound_by) where bound_by lists which caps
    bound ('speed' / 'force'), empty if the desire was already gentle."""
    s_cap, f_cap = finesse_for(material)
    bound = []
    speed = desired_speed
    force = desired_force
    if speed > s_cap:
        speed = s_cap
        bound.append("speed")
    if force > f_cap:
        force = f_cap
        bound.append("force")
    return speed, force, bound


# ---------------------------------------------------------- organ history --
class OrganHistory:
    """Per-hemisphere response-latency record, built purely from
    observations. History built and adjusted continually from
    observation: every timed response an organ gives becomes a sample,
    and the oracle's trust in that organ is just these percentiles."""

    def __init__(self):
        self._samples: dict[str, list[float]] = {}

    def add(self, hemisphere: str, latency_s: float) -> None:
        self._samples.setdefault(hemisphere, []).append(float(latency_s))

    def count(self, hemisphere: str) -> int:
        return len(self._samples.get(hemisphere, []))

    @staticmethod
    def _pct(sorted_vals: list[float], q: float) -> float:
        if not sorted_vals:
            return float("inf")
        if len(sorted_vals) == 1:
            return sorted_vals[0]
        # linear interpolation between closest ranks
        pos = q * (len(sorted_vals) - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, len(sorted_vals) - 1)
        frac = pos - lo
        return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac

    def p50(self, hemisphere: str) -> float:
        vals = sorted(self._samples.get(hemisphere, []))
        return self._pct(vals, 0.50)

    def p90(self, hemisphere: str) -> float:
        vals = sorted(self._samples.get(hemisphere, []))
        return self._pct(vals, 0.90)


# ------------------------------------------------------------- the oracle --
def _spine_tilt_deg(x: float, v: float) -> float:
    """The spine's commanded tilt from this state (reference PID law,
    instantaneous terms only), capped at its +/-6 deg authority."""
    t = -(SPINE_KP * x + SPINE_KD * v)
    return max(-SPINE_CAP_DEG, min(SPINE_CAP_DEG, t))


def _time_to_edge(x: float, v: float, a_net: float) -> float:
    """Smallest t > 0 at which |x + v t + 0.5 a_net t^2| reaches EDGE_X,
    treating a_net as constant (the stated approximation — the real
    spine's counter-tilt grows as the state develops, so this oracle
    UNDERESTIMATES time-to-edge somewhat; see the replay caveats).
    Returns inf if the trajectory never reaches the edge."""
    if abs(x) >= EDGE_X:
        return 0.0
    best = float("inf")
    for target in (EDGE_X, -EDGE_X):
        c = x - target
        if abs(a_net) < 1e-12:
            if abs(v) < 1e-12:
                continue
            t = -c / v
            if t > 1e-9:
                best = min(best, t)
            continue
        disc = v * v - 2.0 * a_net * c
        if disc < 0:
            continue
        sq = math.sqrt(disc)
        for t in ((-v + sq) / a_net, (-v - sq) / a_net):
            if t > 1e-9:
                best = min(best, t)
    return best


def feasibility(state: dict, body: BodySpec, history: OrganHistory,
                hemisphere: str, gust_accel: float,
                extra_delay_s: float = 0.0) -> dict:
    """One-observation feasibility oracle.

    state: {'x': position, 'v': velocity} at observation time.
    gust_accel: the disturbance accel estimated from ONE observation
        (delta-v over a short window after onset — the caller measures
        the wind from the first tip, it does not get told the future).
    extra_delay_s: known fixed delay in the response path (e.g. a
        decider step) priced into t_respond.

    Returns an auditable verdict dict — every intermediate number is in
    it. The verdict is arithmetic, not a score:

      t_edge    — time for |x| to reach the edge under the net accel
                  (gust + spine's counter at its authority, spine is
                  already fighting) if nobody catches.
      t_respond — this organ's historical p50 latency + servo travel
                  time to the needed tilt (+ any known path delay).
      margin    — t_edge - t_respond.

      CATCH     margin > 0.35 s: the hand arrives with room to spare.
      LET_FALL  t_respond > t_edge (the hand cannot arrive — do not
                spend, do not interrupt the work), OR the tilt that
                would hold the ball exceeds the servo's max (physically
                cannot hold), OR the ball is already past the point of
                no return, OR the organ has no recorded history (the
                oracle does not promise on an unmeasured organ).
      MARGINAL  otherwise: physically possible, no room to spare —
                the caller prices it via decide()."""
    x = float(state["x"])
    v = float(state["v"])
    reasons: list[str] = []

    spine_tilt = _spine_tilt_deg(x, v)
    spine_accel = PLANT_GAIN * spine_tilt
    a_net = gust_accel + spine_accel - DRAG * v
    t_edge = _time_to_edge(x, v, a_net)

    # Tilt that zeroes the net accel (the catch tilt REPLACES the spine
    # tilt while applied, per the v2 design, so the spine term is not
    # in this equation): 0.55*T - DRAG*v + gust = 0
    needed_tilt = (DRAG * v - gust_accel) / PLANT_GAIN
    impossible_tilt = abs(needed_tilt) > body.servo_max_tilt_deg
    t_servo = abs(needed_tilt) / body.servo_tilt_rate_dps

    n_hist = history.count(hemisphere)
    organ_p50 = history.p50(hemisphere) if n_hist else float("inf")
    t_respond = organ_p50 + t_servo + extra_delay_s
    margin = t_edge - t_respond

    past_pnr = abs(x) >= POINT_OF_NO_RETURN
    if past_pnr:
        reasons.append(f"|x|={abs(x):.2f} already past point of no "
                       f"return {POINT_OF_NO_RETURN}")
    if impossible_tilt:
        reasons.append(f"needed tilt {needed_tilt:+.1f} deg exceeds "
                       f"servo max {body.servo_max_tilt_deg} deg — "
                       f"physically cannot hold")
    if n_hist == 0:
        reasons.append(f"no recorded history for organ {hemisphere} — "
                       f"oracle does not promise on an unmeasured organ")

    if past_pnr or impossible_tilt or n_hist == 0 or margin < 0:
        verdict = "LET_FALL"
        if margin < 0 and not (past_pnr or impossible_tilt or n_hist == 0):
            reasons.append(f"t_respond {t_respond:.2f}s > t_edge "
                           f"{t_edge:.2f}s — hand cannot arrive; do not "
                           f"spend, do not interrupt the work")
    elif margin > MARGIN_CATCH_S:
        verdict = "CATCH"
        reasons.append(f"margin {margin:+.2f}s > {MARGIN_CATCH_S}s — "
                       f"hand arrives with room to spare")
    else:
        verdict = "MARGINAL"
        reasons.append(f"margin {margin:+.2f}s within "
                       f"[0, {MARGIN_CATCH_S}]s — possible, no room; "
                       f"caller prices it")

    # Recommended catch tilt: the tilt that zeroes the accel, plus a
    # modest margin factor — finesse for control: never the max by
    # default, clamped to the servo's authority.
    rec_tilt = needed_tilt * 1.25
    rec_tilt = max(-body.servo_max_tilt_deg,
                   min(body.servo_max_tilt_deg, rec_tilt))

    return {
        "verdict": verdict,
        "hemisphere": hemisphere,
        "x": x, "v": v, "gust_accel": gust_accel,
        "spine_tilt_deg": spine_tilt,
        "a_net": a_net,
        "t_edge_s": t_edge,
        "needed_tilt_deg": needed_tilt,
        "recommended_tilt_deg": rec_tilt,
        "t_servo_s": t_servo,
        "organ_p50_s": organ_p50,
        "organ_history_n": n_hist,
        "extra_delay_s": extra_delay_s,
        "t_respond_s": t_respond,
        "margin_s": margin,
        "reasons": reasons,
    }


def decide(event_value_j: float, catch_cost_j: float, verdict) -> bool:
    """The rock rule: act only when the action is feasible AND its cost
    is acceptable against the goal value. A rock blocking the path is
    moved when the arm CAN move it (feasibility), the joules are
    acceptable (cost), and the goal beyond it is worth them (value).
      CATCH    -> act (feasibility already has room to spare).
      MARGINAL -> act only if value > cost.
      LET_FALL -> never act: either it cannot be done, or the attempt
                  itself is the waste."""
    v = verdict["verdict"] if isinstance(verdict, dict) else str(verdict)
    if v == "CATCH":
        return True
    if v == "MARGINAL":
        return event_value_j > catch_cost_j
    return False


# ------------------------------------------------------------ self-tests ---
def run_self_tests() -> list[str]:
    passed = []

    # 1. Coffee-cup clamp binds: glass, desired 8.9 m/s (~20 mph — the
    # speed Zak named) and a hard grip -> both caps bind.
    s, f, bound = clamp_manipulation("glass", 8.9, 40.0)
    assert s == 0.05 and f == 8 and "speed" in bound and "force" in bound, \
        (s, f, bound)
    # ceramic cup class, and unknown material -> conservative default
    assert finesse_for("ceramic") == (0.08, 12)
    assert finesse_for("unobtainium") == (0.10, 15)
    s2, f2, b2 = clamp_manipulation("metal", 0.3, 40.0)
    assert (s2, f2, b2) == (0.3, 40.0, [])  # already gentle: no clamp
    passed.append("finesse clamp: glass 8.9 m/s -> 0.05 (speed+force bind); "
                  "unknown material -> conservative default")

    body = BodySpec()

    # 2. Slow organ + fast gust -> LET_FALL.
    slow = OrganHistory()
    for lat in (3.0, 3.2, 2.9):
        slow.add("LEFT", lat)
    r = feasibility({"x": 0.03, "v": 0.22}, body, slow, "LEFT", 0.9)
    assert r["verdict"] == "LET_FALL", r
    passed.append(f"slow organ (p50 {r['organ_p50_s']:.2f}s) + gust 0.9 -> "
                  f"LET_FALL (t_edge {r['t_edge_s']:.2f}s < t_respond "
                  f"{r['t_respond_s']:.2f}s)")

    # 3. Fast organ + slow gust -> CATCH.
    fast = OrganHistory()
    for lat in (0.30, 0.35, 0.28):
        fast.add("RIGHT", lat)
    r = feasibility({"x": 0.0, "v": 0.0}, body, fast, "RIGHT", 0.2)
    assert r["verdict"] == "CATCH", r
    passed.append(f"fast organ (p50 {r['organ_p50_s']:.2f}s) + gust 0.2 -> "
                  f"CATCH (margin {r['margin_s']:+.2f}s)")

    # 4. Impossible tilt -> LET_FALL: gust so strong the holding tilt
    # exceeds the servo's max authority.
    r = feasibility({"x": 0.0, "v": 0.0}, body, fast, "RIGHT", 8.0)
    assert r["verdict"] == "LET_FALL" and abs(r["needed_tilt_deg"]) > 12, r
    passed.append(f"impossible tilt (needed {r['needed_tilt_deg']:+.1f} deg "
                  f"> 12 max) -> LET_FALL")

    # 5. Unmeasured organ -> LET_FALL (no promise on no record).
    r = feasibility({"x": 0.0, "v": 0.0}, body, OrganHistory(), "LEFT", 0.2)
    assert r["verdict"] == "LET_FALL", r
    passed.append("unmeasured organ (empty history) -> LET_FALL")

    # 6. Past point of no return -> LET_FALL even for a fast organ.
    r = feasibility({"x": 0.90, "v": 0.1}, body, fast, "RIGHT", 0.2)
    assert r["verdict"] == "LET_FALL", r
    passed.append("past point of no return (|x|=0.90) -> LET_FALL")

    # 7. decide() truth table — the rock rule.
    assert decide(1, 1000, "CATCH") is True        # feasible: act
    assert decide(100, 10, "MARGINAL") is True     # worth more than cost
    assert decide(5, 10, "MARGINAL") is False      # not worth the joules
    assert decide(10, 10, "MARGINAL") is False     # must EXCEED cost
    assert decide(10000, 1, "LET_FALL") is False   # hopeless: never spend
    passed.append("decide() truth table: CATCH acts; MARGINAL acts iff "
                  "value > cost; LET_FALL never acts")

    return passed


# ------------------------------------------------- replay vs the v2 log --
_STATE_RE = re.compile(r"x=([+-]?[0-9.]+).*?v=([+-]?[0-9.]+)", re.S)


def _parse_state(prompt: str):
    """Extract (x, v) from a logged centered-monitor prompt string.
    The results file logs prompts verbatim; onset x/v are NOT stored
    as separate fields — they are recovered from the prompt text."""
    m = _STATE_RE.search(prompt)
    return float(m.group(1)), float(m.group(2))


def _propagate(x: float, v: float, gust: float, seconds: float,
               dt: float = 0.01):
    """Mirror the v2 sim for `seconds`: spine PID tilt recomputed each
    step (instantaneous terms), x updated with the old v, then v —
    the sim's own integration order."""
    steps = int(round(seconds / dt))
    for _ in range(steps):
        tilt = _spine_tilt_deg(x, v)
        a = PLANT_GAIN * tilt - DRAG * v + gust
        x = x + v * dt
        v = v + a * dt
    return x, v


def _organ_latency(ev: dict) -> float:
    """The hemisphere's own response segment for one event. For Arm R
    that is latency_from_onset_s directly. For Arm D the logged
    latency_from_onset_s includes the decider's call, so the decider's
    own logged latency_s is subtracted — the organ's segment only."""
    lat = ev["catch"]["latency_from_onset_s"]
    if ev.get("decider"):
        lat -= ev["decider"]["latency_s"]
    return lat


def _build_histories(events_by_arm: dict, score_arm: str,
                     loo_index: int, hemisphere: str) -> OrganHistory:
    """History for scoring one event: all OTHER-arm organ latencies
    for this hemisphere + leave-one-out within the scored arm."""
    h = OrganHistory()
    for arm_name, events in events_by_arm.items():
        for j, ev in enumerate(events):
            if ev["assigned_hemisphere"] != hemisphere:
                continue
            if arm_name == score_arm and j == loo_index:
                continue
            h.add(hemisphere, _organ_latency(ev))
    return h


def run_replay(results_path: str) -> dict:
    with open(results_path) as fh:
        data = json.load(fh)
    body = BodySpec()
    events_by_arm = {name: arm["events"] for name, arm in data["arms"].items()}
    DEADLINE_S = 2.5  # the v2 test's own catch deadline, from its design
    OBS_DELAY_S = 0.25

    def score_arm(arm_name: str, use_decider_state: bool,
                  extra_delay_from_decider: bool):
        rows = []
        for i, ev in enumerate(events_by_arm[arm_name]):
            hemi = ev["assigned_hemisphere"]
            gust = ev["gust_accel"]
            # State nearest onset: Arm R catch prompts were issued at
            # onset; Arm D onset states live in the DECIDER prompts
            # (its catch prompts show post-decider states).
            src = ev["decider"]["prompt"] if use_decider_state \
                else ev["catch"]["prompt"]
            x0, v0 = _parse_state(src)
            x_obs, v_obs = _propagate(x0, v0, gust, OBS_DELAY_S)
            hist = _build_histories(events_by_arm, arm_name, i, hemi)
            extra = ev["decider"]["latency_s"] \
                if (extra_delay_from_decider and ev.get("decider")) else 0.0
            r = feasibility({"x": x_obs, "v": v_obs}, body, hist, hemi,
                            gust, extra_delay_s=extra)
            lat = ev["catch"]["latency_from_onset_s"]
            actual = {
                "latency_s": lat,
                "in_time": lat <= DEADLINE_S,
                "caught": ev["caught"],
                "miss_reason": ev["miss_reason"],
                "fell": ev["fell"],
            }
            rows.append({
                "gust_index": ev["gust_index"],
                "hemisphere": hemi,
                "gust_accel": gust,
                "onset_state_from_prompt": {"x": x0, "v": v0},
                "observation_state_t+0.25s": {"x": round(x_obs, 4),
                                              "v": round(v_obs, 4)},
                "history_n": r["organ_history_n"],
                "organ_p50_s": round(r["organ_p50_s"], 3),
                "t_edge_s": round(r["t_edge_s"], 3),
                "t_respond_s": round(r["t_respond_s"], 3),
                "margin_s": round(r["margin_s"], 3),
                "oracle_verdict": r["verdict"],
                "actual": actual,
            })
        return rows

    def confusion(rows):
        c = {"catch_calls": 0, "catch_calls_in_time": 0,
             "marginal_calls": 0, "marginal_in_time": 0,
             "marginal_caught": 0,
             "letfall_calls": 0, "letfall_actually_late": 0,
             "letfall_actually_in_time": 0}
        for row in rows:
            v = row["oracle_verdict"]
            if v == "CATCH":
                c["catch_calls"] += 1
                c["catch_calls_in_time"] += bool(row["actual"]["in_time"])
            elif v == "MARGINAL":
                c["marginal_calls"] += 1
                c["marginal_in_time"] += bool(row["actual"]["in_time"])
                c["marginal_caught"] += bool(row["actual"]["caught"])
            else:
                c["letfall_calls"] += 1
                if row["actual"]["in_time"]:
                    c["letfall_actually_in_time"] += 1
                else:
                    c["letfall_actually_late"] += 1
        return c

    arm_r = score_arm("R", use_decider_state=False,
                      extra_delay_from_decider=False)
    arm_d = score_arm("D", use_decider_state=True,
                      extra_delay_from_decider=True)

    # --- Sensitivity diagnostic (POST-HOC, labelled as such): how much
    # of the oracle's pessimism is (a) cross-arm history pooling and
    # (b) the constant-accel t_edge? Recompute Arm R with within-arm
    # LOO-only histories and an EMPIRICAL t_edge: the OTHER arm's
    # logged fall time for the same gust (Arm D never landed a catch,
    # so its fall times are the spine-only counterfactual), measured
    # from the +0.25 s observation moment.
    d_falls = data["arms"]["D"]["fall_times"]
    sens_rows = []
    for i, ev in enumerate(events_by_arm["R"]):
        hemi = ev["assigned_hemisphere"]
        gust = ev["gust_accel"]
        hist = OrganHistory()
        for j, ev2 in enumerate(events_by_arm["R"]):
            if j != i and ev2["assigned_hemisphere"] == hemi:
                hist.add(hemi, _organ_latency(ev2))
        x0, v0 = _parse_state(ev["catch"]["prompt"])
        x_obs, v_obs = _propagate(x0, v0, gust, OBS_DELAY_S)
        r = feasibility({"x": x_obs, "v": v_obs}, body, hist, hemi, gust)
        t_edge_emp = (d_falls[ev["gust_index"]] - ev["onset_t"]
                      - OBS_DELAY_S)
        margin_emp = t_edge_emp - r["t_respond_s"]
        verdict_emp = ("CATCH" if margin_emp > MARGIN_CATCH_S
                       else "LET_FALL" if margin_emp < 0 else "MARGINAL")
        lat = ev["catch"]["latency_from_onset_s"]
        sens_rows.append({
            "gust_index": ev["gust_index"], "hemisphere": hemi,
            "loo_only_p50_s": round(r["organ_p50_s"], 3),
            "t_edge_empirical_s": round(t_edge_emp, 3),
            "margin_empirical_s": round(margin_emp, 3),
            "verdict_empirical": verdict_emp,
            "actual_latency_s": lat, "actual_in_time": lat <= DEADLINE_S,
            "actual_caught": ev["caught"],
            "actual_miss_reason": ev["miss_reason"],
        })
    sensitivity = {
        "label": "POST-HOC diagnostic — not the pre-registered method. "
                 "Isolates the two suspected pessimism sources.",
        "arm_R_events": sens_rows,
    }

    return {
        "method": {
            "data_source": os.path.basename(results_path),
            "state_extraction": "onset x/v are NOT logged as fields; "
                "recovered by regex from the verbatim logged prompt "
                "strings (Arm R: catch prompt, issued at onset; Arm D: "
                "decider prompt — its catch prompts are post-decider "
                "states and were not used as onset states).",
            "observation": "onset state propagated 0.25 s through the "
                "v2 plant (spine PID active, gust on) = the oracle's "
                "one-observation moment. Gust accel +/-0.9 taken from "
                "the logged design/schedule — in deployment it is "
                "estimated from delta-v over the window, per spec.",
            "history_method": "per scored event: OrganHistory = all "
                "other-arm organ latencies for the assigned hemisphere "
                "+ leave-one-out within the scored arm. Arm D organ "
                "latency = latency_from_onset_s - decider.latency_s "
                "(both logged). n=8 events/arm; indicative, not "
                "statistical.",
            "scoring_scope": "the oracle predicts TIMING feasibility "
                "only (arrival vs the v2 deadline of 2.5 s). Wrong-sign "
                "replies are a sign-discipline failure it cannot "
                "foresee and are not scored against it; they are listed "
                "per event.",
            "known_conservatism": "t_edge holds net accel constant at "
                "its observation value; the real spine's counter-tilt "
                "grows as the state develops (empirical time-to-fall "
                "was ~2.1 s/gust vs oracle t_edge ~1.6 s). History "
                "latencies are measured from gust onset while the "
                "oracle observes at +0.25 s — a further ~0.25 s of "
                "double-charged response time. Both biases push the "
                "oracle toward LET_FALL.",
        },
        "arm_R_reflex_law": {"events": arm_r, "confusion": confusion(arm_r)},
        "arm_D_decider_sanity": {"events": arm_d,
                                 "confusion": confusion(arm_d)},
        "sensitivity_diagnostic": sensitivity,
    }


if __name__ == "__main__":
    print("SELF-TESTS")
    for line in run_self_tests():
        print("  PASS:", line)
    here = os.path.dirname(os.path.abspath(__file__))
    out = run_replay(os.path.join(here, "ball_balance_v2_results.json"))
    out_path = os.path.join(here, "body_awareness_replay.json")
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\nREPLAY written to {out_path}")
    for key in ("arm_R_reflex_law", "arm_D_decider_sanity"):
        blk = out[key]
        print(f"\n== {key} ==")
        for row in blk["events"]:
            a = row["actual"]
            print(f"  g{row['gust_index']} {row['hemisphere']:5s} "
                  f"gust {row['gust_accel']:+.1f}  "
                  f"t_edge {row['t_edge_s']:.2f}  "
                  f"t_resp {row['t_respond_s']:.2f}  "
                  f"margin {row['margin_s']:+.2f}  -> "
                  f"{row['oracle_verdict']:8s} | actual lat "
                  f"{a['latency_s']:.2f}s caught={a['caught']} "
                  f"miss={a['miss_reason']}")
        print("  confusion:", json.dumps(blk["confusion"]))
