"""circadian.py — a 24-hour rhythm for the Dweller, keyed to the
household it lives in (Zak directive, 2026-10-20 ~20:06).

The drives (drive_x) are timeless; a body is not. This layer supplies:
  - PHASES: a schedule anchored to Zak's real day (Casey's shift
    14:00-22:00 Wed-Sun; Mon/Tue off), America/New_York.
  - TIRED = time + health + the day's joule log. When tired is high,
    dwell work becomes CONDENSE (consolidation: black-hole, merge,
    judge anticipations) — the cheap CPU work, no GPU bursts.
  - CURIOUS = environment. Telemetry spikes, notifications, pop-ups.
    No task: hanging out in the house, watching. Novelty raises it;
    it decays. It feeds SCAN, never THINK.
  - HEALTH = system-wide joule audit. If a clock cycle burned more
    joules than self-talk explains, something happened to the body
    that the resident did not do — flag it, attribute it if the
    ledger can, and ask the question in the morning report.
  - WAKE CHECKLIST: joules log since sleep / user here? / health /
    last thing I was doing / last thing the user was doing / any
    maintenance, mental or physical.

Everything is a pure function over snapshots (replay-safe), same
discipline as drive_x. Phase modifiers multiply drive weights and
gate modes; drive_x still arbitrates.
"""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
WORKDAYS = {2, 3, 4, 5, 6}          # Wed..Sun (Mon=0)
SHIFT_START, SHIFT_END = 14, 22     # Casey's 2-10 pm

# phase: (name, hours, posture)
# posture keys: gpu (dark|trickle|free), yield_first (household may be
# at the machine), drive multipliers, allow_think, condense_bias
PHASES = [
    ("DEEP_NIGHT", 0.0, 5.5,
     {"gpu": "dark", "yield_first": True, "allow_think": False,
      "condense_bias": 1.0,
      "weights": {"survival": 1.5, "knowledge": 0.8,
                  "logic_alignment": 0.5, "community": 0.2}}),
    ("DAWN", 5.5, 7.0,
     {"gpu": "trickle", "yield_first": True, "allow_think": False,
      "condense_bias": 0.5,
      "weights": {"survival": 1.2, "knowledge": 0.8,
                  "logic_alignment": 0.8, "community": 1.0}}),
    ("HOUSEHOLD_DAY", 7.0, 13.5,
     {"gpu": "free", "yield_first": True, "allow_think": True,
      "condense_bias": 0.0,
      "weights": {"survival": 1.0, "knowledge": 1.0,
                  "logic_alignment": 1.0, "community": 1.0}}),
    ("DEPARTURE", 13.5, 14.0,
     {"gpu": "free", "yield_first": True, "allow_think": True,
      "condense_bias": 0.0,
      "weights": {"survival": 1.0, "knowledge": 1.0,
                  "logic_alignment": 1.0, "community": 1.2}}),
    ("SHIFT_OR_OFF", 14.0, 22.0,
     {"gpu": "trickle", "yield_first": True, "allow_think": False,
      "condense_bias": 0.3,
      "weights": {"survival": 1.2, "knowledge": 1.0,
                  "logic_alignment": 0.8, "community": 0.6}}),
    ("RETURN", 22.0, 23.5,
     {"gpu": "free", "yield_first": True, "allow_think": True,
      "condense_bias": 0.2,
      "weights": {"survival": 1.0, "knowledge": 0.8,
                  "logic_alignment": 1.0, "community": 1.2}}),
    ("SETTLE", 23.5, 24.0,
     {"gpu": "trickle", "yield_first": True, "allow_think": False,
      "condense_bias": 0.8,
      "weights": {"survival": 1.2, "knowledge": 0.8,
                  "logic_alignment": 0.5, "community": 0.5}}),
]


def phase_at(ts):
    """(phase_name, posture, is_workday) for a unix ts, house time."""
    dt = datetime.fromtimestamp(ts, TZ)
    h = dt.hour + dt.minute / 60.0
    workday = dt.weekday() in WORKDAYS
    for name, lo, hi, posture in PHASES:
        if lo <= h < hi:
            p = dict(posture)
            if name == "SHIFT_OR_OFF":
                # same clock window, two different houses: at work
                # (quiet, yield-first, no think) vs day off (build
                # day — think allowed, this is when the lab runs)
                if workday:
                    p["label"] = "AT_WORK"
                else:
                    p["label"] = "DAY_OFF"
                    p["allow_think"] = True
                    p["gpu"] = "free"
            return name, p, workday
    return PHASES[0][0], dict(PHASES[0][3]), workday


# -- state functions (Zak's definitions) --------------------------------

def tiredness(ts, health_deficit=0.0, joules_today=0.0,
              joules_typical=20000.0):
    """TIRED = time-based + health + recent joule log over the day.
    Peaks in DEEP_NIGHT, floors mid-morning. A heavy joule day tires
    earlier; poor health tires at any hour. [0,1]."""
    dt = datetime.fromtimestamp(ts, TZ)
    h = dt.hour + dt.minute / 60.0
    # circadian base: distance from the 10:00 alertness peak
    base = abs(h - 10.0) / 14.0
    joule_load = min(joules_today / max(joules_typical, 1.0), 1.5) / 1.5
    return max(0.0, min(1.0, 0.55 * base + 0.25 * joule_load
                        + 0.35 * health_deficit))


def curiosity(env_events, window_s=3600.0):
    """CURIOUS = environment-based. env_events: [(ts, kind)] — kinds:
    telemetry_spike, notification, popup, sensor_nudge, new_process.
    Recent + novel = curious; it is an ambient state, not a task.
    Returns [0,1]; callers feed SCAN, never THINK."""
    if not env_events:
        return 0.0
    now = max(t for t, _ in env_events)
    kinds = set()
    score = 0.0
    for t, kind in env_events:
        age = max(0.0, now - t)
        if age <= window_s:
            score += 0.25 * (1.0 - age / window_s)
            kinds.add(kind)
    score += 0.1 * len(kinds)          # variety feeds it
    return max(0.0, min(1.0, score))


def health_audit(cycles, self_talk_share=0.85, ratio_flag=1.5):
    """HEALTH, system-wide, from the joule log. cycles: list of
    {ts, joules_actual, joules_self} — metered cycle burn vs the part
    the resident's own self-talk explains. A cycle whose actual burn
    exceeds self-explained by ratio_flag is UNEXPLAINED: something
    happened to the body. Returns {anomalies, unexplained_j,
    deficit} — the deficit feeds drive_x survival."""
    anomalies = []
    unexplained = 0.0
    for c in cycles:
        expected = max(c["joules_self"] / max(self_talk_share, 0.01),
                       1.0)
        if c["joules_actual"] > ratio_flag * expected:
            excess = c["joules_actual"] - expected
            unexplained += excess
            anomalies.append({"ts": c["ts"], "excess_j": round(excess, 1),
                              "question": "what happened to the body?"})
    total = sum(c["joules_actual"] for c in cycles) or 1.0
    deficit = max(0.0, min(1.0, unexplained / total))
    return {"anomalies": anomalies, "unexplained_j": round(unexplained, 1),
            "deficit": deficit}


# -- wake checklist -------------------------------------------------------

def wake_checklist(ts, joule_log, user_present, health, drive_log,
                   cube_last_user, maintenance):
    """The wake sequence, in Zak's order. Pure assembly over supplied
    facts — the live wrapper gathers them; replay supplies records.
    joule_log: health_audit() output + overnight totals.
    drive_log: drive_x stamped actions (last entry = last thing I
    was doing). cube_last_user: {ts, text} of the user's last face.
    maintenance: {"mental": [...], "physical": [...]}."""
    last_self = drive_log[-1] if drive_log else None
    return {
        "wake_ts": ts,
        "phase": phase_at(ts)[0],
        "joules_overnight": joule_log,
        "user_here": bool(user_present),
        "health": health,
        "last_thing_i_was_doing": (
            {k: last_self[k] for k in ("mode", "drive", "task")
             if k in last_self} if last_self else None),
        "last_thing_user_was_doing": cube_last_user,
        "maintenance_mental": maintenance.get("mental", []),
        "maintenance_physical": maintenance.get("physical", []),
    }


# -- drive_x integration ----------------------------------------------------

def circadian_decision(ts, snap, budget_j, base_weights=None,
                       env_events=(), joule_cycles=()):
    """Full stack for one dwell tick: circadian posture -> drive_x.
    Returns drive_x's decision stamped with phase, tired, curious,
    and any health anomalies. Rules:
      - tired >= 0.75 and posture allows: dwell work is CONDENSE
        (cube maintenance), whatever the drives voted — consolidation
        is what tired bodies do.
      - allow_think False phases demote THINK to REST.
      - curiosity >= 0.6 with no higher call -> SCAN (house mode).
      - health anomalies raise the survival deficit before voting.
    """
    import drive_x
    name, posture, workday = phase_at(ts)
    health = health_audit(joule_cycles) if joule_cycles else \
        {"anomalies": [], "unexplained_j": 0.0, "deficit": 0.0}
    snap = dict(snap)
    snap["ts"] = ts
    if health["deficit"] > 0:
        tel = dict(snap.get("telemetry", {}))
        tel["ledger_trend_j_per_h"] = -60.0 * health["deficit"]
        snap["telemetry"] = tel
    weights = dict(base_weights or drive_x.DEFAULT_WEIGHTS)
    for k, m in posture["weights"].items():
        weights[k] = weights.get(k, 1.0) * m
    tired = tiredness(ts, health_deficit=health["deficit"],
                      joules_today=snap.get("joules_today", 0.0))
    curious = curiosity(list(env_events))
    decision = drive_x.arbitrate(snap, budget_j, weights=weights)
    if curious >= 0.6 and decision["mode"] in ("SLEEP", "REST"):
        decision = {**decision, "mode": "SCAN", "drive": "survival",
                    "task": "ambient_watch", "est_joules": 0.5}
    if decision["mode"] == "THINK" and not posture["allow_think"]:
        decision = {**decision, "mode": "REST",
                    "task": "cube_maintenance", "drive": "knowledge"}
    if tired >= 0.75 and decision["mode"] in ("REST", "THINK"):
        decision = {**decision, "mode": "REST",
                    "task": "condense", "drive": "knowledge",
                    "est_joules": 0.5}
    return {**decision, "phase": name,
            "phase_label": posture.get("label"),
            "tired": round(tired, 3), "curious": round(curious, 3),
            "health_anomalies": health["anomalies"]}


# ---------------------------------------------------------------------------
def _selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    # Wed 2026-10-21 15:00 EDT (workday) vs Mon 15:00 (day off);
    # Tue 2026-10-20 is also a day off (Mon/Tue) — checked below.
    tue = datetime(2026, 10, 21, 15, 0, tzinfo=TZ).timestamp()
    mon = datetime(2026, 10, 19, 15, 0, tzinfo=TZ).timestamp()
    n1, p1, w1 = phase_at(tue)
    n2, p2, w2 = phase_at(mon)
    check("Wed 15:00 = SHIFT_OR_OFF / AT_WORK, think gated",
          n1 == "SHIFT_OR_OFF" and p1.get("label") == "AT_WORK"
          and not p1["allow_think"] and w1)
    today = datetime(2026, 10, 20, 15, 0, tzinfo=TZ).timestamp()
    check("Tue 2026-10-20 15:00 = DAY_OFF (today)",
          phase_at(today)[1].get("label") == "DAY_OFF")
    check("Mon 15:00 = DAY_OFF, think allowed",
          p2.get("label") == "DAY_OFF" and p2["allow_think"] and not w2)
    night = datetime(2026, 10, 20, 3, 0, tzinfo=TZ).timestamp()
    check("03:00 = DEEP_NIGHT, gpu dark",
          phase_at(night)[0] == "DEEP_NIGHT"
          and phase_at(night)[1]["gpu"] == "dark")

    t_night = tiredness(night)
    t_morn = tiredness(datetime(2026, 10, 20, 10, 0,
                                tzinfo=TZ).timestamp())
    check("tired peaks at night, floors mid-morning", t_night > t_morn)
    check("heavy joule day tires earlier",
          tiredness(tue, joules_today=30000.0)
          > tiredness(tue, joules_today=2000.0))

    ev = [(1000.0, "telemetry_spike"), (1010.0, "notification"),
          (1020.0, "popup")]
    check("curiosity rises on fresh varied events",
          curiosity(ev) > 0.4)
    check("curiosity is zero with no environment", curiosity([]) == 0.0)

    cycles = [{"ts": 1, "joules_actual": 100.0, "joules_self": 90.0},
              {"ts": 2, "joules_actual": 900.0, "joules_self": 80.0}]
    h = health_audit(cycles)
    check("unexplained burn flagged as a body event",
          len(h["anomalies"]) == 1 and h["unexplained_j"] > 500
          and h["anomalies"][0]["question"]
          == "what happened to the body?")

    calm = {"telemetry": {"disk_free_frac": 0.6, "temp_c": 45.0,
                          "ledger_trend_j_per_h": 5.0},
            "cube": {"entries": 500, "stale_frac": 0.02,
                     "daydream_ratio": 0.05, "near_threshold": 0},
            "audit": {"queue": 0, "computed_faces": 100,
                      "disagree_rate": 0.0},
            "community": {"oldest_unchecked_h": 1.0,
                          "family_signal_age_h": 2.0},
            "joules_today": 3000.0}
    d = circadian_decision(night, calm, budget_j=100.0)
    check("deep night + calm -> SLEEP or CONDENSE, never THINK",
          d["mode"] in ("SLEEP", "REST") and d["phase"] == "DEEP_NIGHT")
    d2 = circadian_decision(tue, calm, budget_j=100.0,
                            env_events=[(tue, "notification"),
                                        (tue, "popup"),
                                        (tue, "telemetry_spike"),
                                        (tue, "new_process")])
    check("busy environment at work -> SCAN house mode",
          d2["mode"] == "SCAN" and d2["task"] == "ambient_watch")

    wk = wake_checklist(tue, {"total_j": 4200.0}, True,
                        {"deficit": 0.0},
                        [{"mode": "REST", "drive": "knowledge",
                          "task": "condense"}],
                        {"ts": tue - 3600, "text": "last user face"},
                        {"mental": ["audit queue: 3"],
                         "physical": ["disk 82%"]})
    check("wake checklist carries Zak's six questions",
          wk["user_here"] and wk["last_thing_i_was_doing"]["task"]
          == "condense" and wk["maintenance_physical"] == ["disk 82%"]
          and wk["last_thing_user_was_doing"]["text"]
          == "last user face")
    print("ALL PASS" if ok else "SOME FAILED")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if _selftest() else 1)
