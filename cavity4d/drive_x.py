"""drive_x.py — the Need Vector X for the bilateral Dweller.

Spec: bilateral-dweller-prototype-spec-20261020.md sections 4 + 8.
The resident is the wrapper; the wrapper's idle behaviour is chosen by
drive deficits, priced in joules, and always overridden by the burst
controller's yield reflex (this module is only ever called from the
DWELL slot, and the controller checks yield before dwell work).

Four drives, four deficits in [0, 1]. Knowledge and logic alignment are
KEPT SEPARATE (a Gemini draft merged them; rejected on the record):
knowledge = gaps (unparsed corpora, daydreamed anticipations, stale
faces); logic alignment = self-consistency debt (stored claims whose
regeneration disagrees, audit queue depth). They fail differently and
are fixed differently.

Inputs are PLAIN SNAPSHOT DICTS, never live handles, so the exact same
arbitration runs in replay over recorded history:

  snapshot = {
    "ts": float,
    "telemetry": {"disk_free_frac": 0..1, "temp_c": float,
                  "ledger_trend_j_per_h": float},       # survival
    "cube": {"entries": int, "stale_frac": 0..1,
             "daydream_ratio": 0..1,
             "near_threshold": int},                    # knowledge
    "audit": {"queue": int, "computed_faces": int,
              "disagree_rate": 0..1 or None},           # logic alignment
    "community": {"oldest_unchecked_h": float,
                  "family_signal_age_h": float},        # community
    "sensor_nudge": bool,                               # Sensor Ego 2.5-sigma
    "unparsed_bytes": int,                              # knowledge backlog
  }

Modes (spec section 4): SLEEP (all satisfied) / REST (maintenance:
cube idle_cycle, ~free) / THINK (highest-deficit priced task the joule
budget affords) / SCAN (a fresh sensor nudge outranks internal work).
Every chosen action is stamped {drive, task, est_joules, mode} in the
passport style: idle work that cannot name its drive does not run.
"""

import time

DRIVES = ("survival", "knowledge", "logic_alignment", "community")

DEFAULT_WEIGHTS = {"survival": 1.5, "knowledge": 1.0,
                   "logic_alignment": 1.2, "community": 0.8}

# idle task catalogue: drive -> (task name, est. joules, min deficit)
# Prices are ESTIMATES for arbitration, replaced by metered actuals in
# the passport record when the task runs live. Cube maintenance is
# CPU-side bookkeeping: priced at a nominal 0.5 J/cycle.
TASKS = {
    "survival": ("host_health_check", 2.0, 0.30),
    "knowledge": ("cube_maintenance", 0.5, 0.15),
    "logic_alignment": ("consistency_audit", 25.0, 0.35),
    "community": ("campaign_signal_sweep", 5.0, 0.40),
}
# min-deficit 0.20, not 0.50: the v2 replay projection showed a 0.50
# gate strands the backlog tail (~500 MB) forever — below the gate the
# drive falls to maintenance, which never parses, so the deficit can
# never clear and SLEEP stays unreachable. The gate must sit below the
# deficit a draining backlog passes through.
PARSE_TASK = ("corpus_parse_chunk", 40.0, 0.20)   # knowledge, big ticket

REST_BELOW = 0.15      # every deficit under this -> SLEEP
THINK_AT = 0.35        # a deficit at/above this wants real work


def _clamp(x):
    return max(0.0, min(1.0, float(x)))


# -- deficit functions --------------------------------------------------

def deficit_survival(snap):
    t = snap.get("telemetry", {})
    parts = []
    if "disk_free_frac" in t:            # full disk = dying body
        parts.append(1.0 - _clamp(t["disk_free_frac"] / 0.20))
    if "temp_c" in t:                    # 60C calm, 90C crisis
        parts.append(_clamp((t["temp_c"] - 60.0) / 30.0))
    if "ledger_trend_j_per_h" in t:      # burning faster than harvest
        parts.append(_clamp(-t["ledger_trend_j_per_h"] / 50.0))
    return max(parts) if parts else 0.0


def _noisy_or(parts):
    """Combine sub-signals without masking: each adds evidence, none
    can silence the others. (v1 used max() — the replay showed a
    saturated term hiding every other sub-signal behind it.)"""
    p = 1.0
    for x in parts:
        p *= (1.0 - _clamp(x))
    return 1.0 - p


def deficit_knowledge(snap):
    c = snap.get("cube", {})
    parts = [0.7 * _clamp(c.get("daydream_ratio", 0.0)),
             0.5 * _clamp(c.get("stale_frac", 0.0))]
    if snap.get("unparsed_bytes"):
        # Graded and capped (v2 calibration): sqrt scale, ceiling
        # 0.65 — a huge backlog alone raises knowledge high but can
        # never pin it at 1.0, so SLEEP stays reachable in principle
        # and staleness/daydreams remain visible on the needle.
        frac = snap["unparsed_bytes"] / 1.4e9
        parts.append(0.65 * (min(frac, 1.0) ** 0.5))
    if c.get("near_threshold"):
        parts.append(_clamp(c["near_threshold"] / 10.0))
    return _noisy_or(parts)


def deficit_logic_alignment(snap):
    a = snap.get("audit", {})
    parts = []
    faces = a.get("computed_faces", 0)
    if faces:
        parts.append(_clamp(a.get("queue", 0) / faces))
    if a.get("disagree_rate") is not None:
        parts.append(_clamp(a["disagree_rate"]))
    return _noisy_or(parts) if parts else 0.0


def deficit_community(snap):
    c = snap.get("community", {})
    parts = []
    if "oldest_unchecked_h" in c:        # 48 h unchecked saturates
        parts.append(_clamp(c["oldest_unchecked_h"] / 48.0))
    if "family_signal_age_h" in c:
        parts.append(_clamp(c["family_signal_age_h"] / 72.0))
    return _noisy_or(parts) if parts else 0.0


DEFICITS = {"survival": deficit_survival,
            "knowledge": deficit_knowledge,
            "logic_alignment": deficit_logic_alignment,
            "community": deficit_community}


# -- arbitration ----------------------------------------------------------

def evaluate(snap):
    """Snapshot -> {drive: deficit}. Pure; replay-safe."""
    return {d: DEFICITS[d](snap) for d in DRIVES}


def _aging_boost(drive, snap, state):
    """Priority grows with time-since-served (v2 anti-starvation):
    +50% per unserved day, capped at 3 days (2.5x). The v1 replay
    starved community 0/9 behind a saturated knowledge drive; classic
    schedulers fix exactly this with aging. Stateless calls (no state)
    get no boost — replay v1 semantics preserved."""
    if not state or "last_served" not in state:
        return 1.0
    now = snap.get("ts", 0.0)
    boot = state.get("boot_ts", now)
    last = state["last_served"].get(drive, boot)
    age_days = max(0.0, (now - last) / 86400.0)
    return 1.0 + 0.5 * min(age_days, 3.0)


def arbitrate(snap, budget_j, weights=None, state=None):
    """Snapshot + joule budget -> one stamped decision dict.

    Decision: {"mode", "drive", "task", "est_joules", "deficits"}.
    SCAN outranks everything internal (the world knocked). Survival
    outranks the weighted order when critical (>= 0.8, raw deficit —
    aging never promotes INTO a crisis): the body first. Ordering is
    by deficit x weight x aging boost. A task runs only if its price
    fits the budget; otherwise the Dweller RESTs on free maintenance
    instead of overspending — deferral to a cheaper window is a
    decision, not a failure. (Survival's deficit keeps max() over its
    sub-signals by design: any single body crisis IS a crisis.)
    """
    weights = weights or DEFAULT_WEIGHTS
    deficits = evaluate(snap)
    base = {"deficits": {k: round(v, 3) for k, v in deficits.items()},
            "drive": None, "task": None, "est_joules": 0.0}
    if snap.get("sensor_nudge"):
        return {**base, "mode": "SCAN", "drive": "survival",
                "task": "sensor_nudge_review", "est_joules": 1.0}
    if max(deficits.values()) < REST_BELOW:
        return {**base, "mode": "SLEEP"}
    order = sorted(DRIVES, key=lambda d: -deficits[d] * weights[d]
                   * _aging_boost(d, snap, state))
    if deficits["survival"] >= 0.8:
        order.remove("survival")
        order.insert(0, "survival")
    for drive in order:
        task, price, min_def = TASKS[drive]
        if drive == "knowledge" and snap.get("unparsed_bytes") \
                and deficits[drive] >= PARSE_TASK[2]:
            task, price, min_def = PARSE_TASK
        if deficits[drive] >= max(min_def, THINK_AT - 0.2) \
                and price <= budget_j:
            # cube maintenance is REST-grade work even when a drive
            # vote surfaces it — THINK is reserved for priced tasks
            mode = "REST" if task == "cube_maintenance" else "THINK"
            return {**base, "mode": mode, "drive": drive,
                    "task": task, "est_joules": price}
    return {**base, "mode": "REST", "drive": "knowledge",
            "task": "cube_maintenance", "est_joules": TASKS["knowledge"][1]}


def replay(snapshots, budget_j):
    """Decisions over recorded snapshots. No side effects — this is how
    X is judged against a week of history before any live loop exists."""
    return [arbitrate(s, budget_j) for s in snapshots]


# -- live adapter ---------------------------------------------------------

def cube_snapshot(cube, unparsed_bytes=0):
    """Build the cube/audit slice of a snapshot from a live Cube."""
    now = time.time()
    entries = list(cube.entries.values())
    stale = sum(1 for e in entries
                if now - e["last_used"] > 7 * 24 * 3600)
    stats = cube.anticipation_stats
    return {
        "cube": {
            "entries": len(entries),
            "stale_frac": (stale / len(entries)) if entries else 0.0,
            "daydream_ratio": (stats["daydreamed"] / stats["anticipated"]
                               if stats["anticipated"] else 0.0),
            "near_threshold": sum(1 for e in entries
                                    if e["tier"] == "SELF_TALK"
                                    and 3 <= e["use_count"] < 5),
        },
        "audit": {"queue": 0, "computed_faces":
                  sum(1 for e in entries if e.get("computed"))},
        "unparsed_bytes": unparsed_bytes,
    }


def make_dwell_work(cube, snapshot_fn, budget_fn, handlers=None,
                    cycle_s=3600.0, log=None):
    """Return a callable(dt) for BurstController.dwell_work.

    Accumulates dwell time; each cycle_s of accumulated dwell runs one
    arbitration. THINK tasks dispatch to handlers[task](cube) when a
    handler exists (consistency_audit / corpus_parse are rungs, not
    yet built — an unhandled THINK task is recorded, never faked).
    cube_maintenance always maps to the cube's own idle_cycle. Every
    executed action appends its stamp to log.
    """
    handlers = handlers or {}
    log = log if log is not None else []
    acc = {"dt": 0.0}
    state = {"boot_ts": time.time(), "last_served": {}}

    def dwell_work(dt):
        acc["dt"] += dt
        if acc["dt"] < cycle_s:
            return None
        acc["dt"] = 0.0
        snap = {"ts": time.time(), **snapshot_fn()}
        decision = arbitrate(snap, budget_fn(), state=state)
        if decision["drive"]:
            state["last_served"][decision["drive"]] = snap["ts"]
        if decision["mode"] in ("THINK", "REST") \
                and decision["task"] == "cube_maintenance":
            result = cube.idle_cycle()
            log.append({**decision, "result": result})
        elif decision["mode"] == "THINK" \
                and decision["task"] in handlers:
            result = handlers[decision["task"]](cube)
            log.append({**decision, "result": result})
        elif decision["mode"] == "THINK":
            log.append({**decision, "result": "no handler (rung)"})
        return decision

    return dwell_work


# ---------------------------------------------------------------------------
def _selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    calm = {"telemetry": {"disk_free_frac": 0.6, "temp_c": 45.0,
                          "ledger_trend_j_per_h": 5.0},
            "cube": {"entries": 500, "stale_frac": 0.02,
                     "daydream_ratio": 0.05, "near_threshold": 0},
            "audit": {"queue": 0, "computed_faces": 100,
                      "disagree_rate": 0.0},
            "community": {"oldest_unchecked_h": 1.0,
                          "family_signal_age_h": 2.0}}
    d = arbitrate(calm, budget_j=100.0)
    check("calm system SLEEPs", d["mode"] == "SLEEP")

    dreamy = {**calm, "cube": {"entries": 500, "stale_frac": 0.4,
                               "daydream_ratio": 0.9,
                               "near_threshold": 3}}
    d = arbitrate(dreamy, budget_j=100.0)
    check("daydream backlog -> knowledge maintenance (REST-grade)",
          d["mode"] == "REST" and d["drive"] == "knowledge"
          and d["task"] == "cube_maintenance")

    broke = {**dreamy, "telemetry": {"disk_free_frac": 0.01,
                                     "temp_c": 88.0,
                                     "ledger_trend_j_per_h": -80.0}}
    d = arbitrate(broke, budget_j=100.0)
    check("critical survival outranks knowledge",
          d["drive"] == "survival" and d["task"] == "host_health_check")

    poor = arbitrate(dreamy, budget_j=0.1)
    check("empty budget defers to REST maintenance",
          poor["mode"] == "REST" and poor["task"] == "cube_maintenance")

    nudge = arbitrate({**calm, "sensor_nudge": True}, budget_j=100.0)
    check("sensor nudge -> SCAN over everything",
          nudge["mode"] == "SCAN")

    stale_posts = {**calm, "community": {"oldest_unchecked_h": 49.0,
                                         "family_signal_age_h": 3.0}}
    d = arbitrate(stale_posts, budget_j=100.0)
    check("unchecked campaign item -> community THINK",
          d["mode"] == "THINK" and d["drive"] == "community")

    # live adapter against the real Cube
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from kv_cube import Cube
    cube = Cube(model_id="selftest")
    for i in range(6):
        cube.add_interaction(f"prompt {i}", f"reply {i}",
                             session="s1", ts=time.time())
    snap = cube_snapshot(cube, unparsed_bytes=1_400_000_000)
    check("cube_snapshot: 1.4GB backlog registers strong but capped",
          0.60 < deficit_knowledge({**calm, **snap}) < 0.70)
    log = []
    work = make_dwell_work(cube, lambda: {**calm, **snap},
                           lambda: 100.0, cycle_s=60.0, log=log)
    check("dwell_work waits for a full cycle", work(30.0) is None)
    decision = work(31.0)
    check("dwell_work fires and stamps the log",
          decision is not None and len(log) == 1
          and log[0]["drive"] is not None)

    # -- v2 calibration checks -------------------------------------------
    full_backlog = {**calm, "unparsed_bytes": 1_400_000_000}
    k_full = deficit_knowledge(full_backlog)
    check("v2: full backlog no longer pins knowledge at 1.0",
          0.60 < k_full < 0.70)
    stale_too = {**full_backlog,
                 "cube": {"entries": 500, "stale_frac": 0.9,
                          "daydream_ratio": 0.0, "near_threshold": 0}}
    check("v2: staleness still moves the needle (no masking)",
          deficit_knowledge(stale_too) > k_full + 0.1)
    # aging: community at deficit 1.0, unserved 3+ days, must beat a
    # saturated-but-served knowledge drive (the v1 starvation case)
    starved = {**calm,
               "cube": {"entries": 500, "stale_frac": 0.05,
                        "daydream_ratio": 0.0, "near_threshold": 0},
               "unparsed_bytes": 1_400_000_000,
               "community": {"oldest_unchecked_h": 96.0,
                             "family_signal_age_h": 96.0},
               "ts": 1_000_000.0}
    state = {"boot_ts": 1_000_000.0 - 4 * 86400.0,
             "last_served": {"knowledge": 1_000_000.0 - 3600.0}}
    d = arbitrate(starved, budget_j=100.0, state=state)
    check("v2: aging rescues starved community drive",
          d["drive"] == "community" and d["mode"] == "THINK")
    print("ALL PASS" if ok else "SOME FAILED")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if _selftest() else 1)
