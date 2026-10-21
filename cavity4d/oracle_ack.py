"""
oracle_ack.py — the acknowledge call: the preprocessing oracle as an
eye / intuition layer for the bilateral Dweller.

Zak's directive (2026-10-20 22:48 EDT): the preprocessing oracle is no
different from our eye or intuition. It does NOT poll the world and
compute everything. Sensors and organs notice a change; the noticing
fires an ACKNOWLEDGE call — an orienting interrupt — stamped with a
quick assessment made from preloaded world logic and laws (the
body_awareness feasibility arithmetic). The ack goes to the brain for
decision within its physical and mental abilities.

Between noticing and deciding sits the importance gate — "does brain
care?" A gust knocking the ball off: asset at risk, brain cares, mode
goes ACTIVE until the ball is safe. A crooked painting: noticed,
assessed (nothing at risk, no goal blocked), dismissed — and if it
keeps being noticed, habituation decays its importance so it stops
interrupting at all. Brains do not hold planning sessions about
crooked paintings.

Layer contract:
  observe -> (anomaly?) -> assess -> importance -> disposition
  DISMISS  log only. Never interrupts work.
  MONITOR  watch level up + re-check timer. Never interrupts work.
  ESCALATE to the brain, carrying observation + assessment. The ONLY
           disposition that interrupts work. Feasibility gates the
           ACTION inside the escalation, never the caring: an
           escalated ack whose feasibility says LET_FALL is recorded
           ESCALATE with action='none' — brain informed, body
           deliberately still.

Mode state machine: WATCH -> ACTIVE when an ESCALATE lands on a
body-asset channel; ACTIVE stands down to WATCH after the pinned
channel reads stable for `stand_down_dwell` consecutive calm
observations. MONITOR raises the watch level but never the mode.

Pure python, no server calls. The brain call itself is the caller's
job; this layer decides whether the brain gets called at all.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import body_awareness
from body_awareness import BodySpec, OrganHistory, decide, feasibility

Z_THRESHOLD = 2.5        # Sensor Ego's nudge threshold — same sigma line
DISMISS_BELOW = 0.25     # importance bands (transparent, printed in
MONITOR_UP_TO = 0.6      # every record's components)


# --------------------------------------------------------------- anomaly --
@dataclass
class Anomaly:
    channel: str
    kind: str                    # 'metric' | 'event'
    signature: str               # habituation key: same signature decays
    summary: str
    value: float
    z: float | None = None       # metric channels only


@dataclass
class AckRecord:
    ts: float
    channel: str
    anomaly_summary: str
    assessment: dict             # preloaded-law quick math / sketch
    importance: float
    importance_components: dict  # asset_risk, goal_relevance, novelty
    disposition: str             # DISMISS | MONITOR | ESCALATE
    action: str                  # none | act | brain
    habituated: bool
    mode_after: str

    def to_dict(self) -> dict:
        return {
            "ts": self.ts,
            "channel": self.channel,
            "anomaly_summary": self.anomaly_summary,
            "assessment": self.assessment,
            "importance": round(self.importance, 6),
            "importance_components": self.importance_components,
            "disposition": self.disposition,
            "action": self.action,
            "habituated": self.habituated,
            "mode_after": self.mode_after,
        }


# --------------------------------------------------------------- watcher --
class AnomalyWatcher:
    """Pre-attentive noticing. Two channel kinds:

    metric — z-score against a baseline. A provided baseline
        (mean, std) is authoritative; without one, a rolling Welford
        baseline is built from observations and detection starts only
        after `warmup_samples` (an eye that has never seen the room
        does not get to call things strange yet).
    event  — a step change: fires when |value| crosses the channel's
        edge_level upward (|prev| < level <= |value|). One ack per
        excursion; the return to baseline does not re-fire.
    """

    def __init__(self, z_threshold: float = Z_THRESHOLD,
                 warmup_samples: int = 30):
        self.z_threshold = z_threshold
        self.warmup_samples = warmup_samples
        self._cfg: dict[str, dict] = {}
        self._prev: dict[str, float] = {}
        self._stats: dict[str, list] = {}   # name -> [n, mean, M2]

    def register(self, name: str, kind: str, asset_risk: float = 0.0,
                 body_asset: bool = False, edge_level: float | None = None,
                 baseline: tuple[float, float] | None = None,
                 goal_relevance: float = 0.0) -> None:
        if kind not in ("metric", "event"):
            raise ValueError(f"unknown channel kind {kind!r}")
        if kind == "event" and edge_level is None:
            raise ValueError(f"event channel {name!r} needs edge_level")
        self._cfg[name] = {
            "kind": kind,
            "asset_risk": float(asset_risk),
            "body_asset": bool(body_asset),
            "edge_level": edge_level,
            "baseline": baseline,
            "goal_relevance": float(goal_relevance),
        }
        self._stats[name] = [0, 0.0, 0.0]

    def config(self, name: str) -> dict:
        return self._cfg[name]

    # -- baselines ------------------------------------------------------
    def _z(self, name: str, value: float) -> float | None:
        cfg = self._cfg[name]
        if cfg["baseline"] is not None:
            mean, std = cfg["baseline"]
            return (value - mean) / std if std > 0 else None
        n, mean, m2 = self._stats[name]
        if n < self.warmup_samples or n < 2:
            return None
        var = m2 / (n - 1)
        if var <= 1e-12:
            return None
        return (value - mean) / math.sqrt(var)

    def _absorb(self, name: str, value: float) -> None:
        st = self._stats[name]
        st[0] += 1
        delta = value - st[1]
        st[1] += delta / st[0]
        st[2] += delta * (value - st[1])

    def is_calm(self, name: str, value: float) -> bool:
        """Channel reads stable: an event channel is back below its
        edge level (the excursion is over — merely 'no NEW edge' while
        the gust is still blowing is NOT calm); a metric channel is
        back inside its z band."""
        cfg = self._cfg[name]
        if cfg["kind"] == "event":
            return abs(value) < cfg["edge_level"]
        z = self._z(name, value)
        return z is None or abs(z) < self.z_threshold

    # -- the noticing ----------------------------------------------------
    def observe(self, name: str, value: float) -> Anomaly | None:
        cfg = self._cfg[name]
        value = float(value)
        anomaly = None
        if cfg["kind"] == "event":
            prev = self._prev.get(name)
            level = cfg["edge_level"]
            if prev is not None and abs(prev) < level <= abs(value):
                direction = "+" if value > 0 else "-"
                anomaly = Anomaly(
                    channel=name, kind="event",
                    signature=f"{name}:{direction}",
                    summary=(f"{name}: step change {prev:+.3g} -> "
                             f"{value:+.3g} (edge level {level:g} "
                             f"crossed upward)"),
                    value=value)
        else:
            z = self._z(name, value)
            if z is not None and abs(z) >= self.z_threshold:
                direction = "high" if z > 0 else "low"
                anomaly = Anomaly(
                    channel=name, kind="metric",
                    signature=f"{name}:{direction}",
                    summary=(f"{name}: value {value:+.3g} is "
                             f"{z:+.1f} sigma from baseline"),
                    value=value, z=z)
        self._prev[name] = value
        self._absorb(name, value)
        return anomaly


# ----------------------------------------------------------------- layer --
class OracleAck:
    """The acknowledge layer: watcher + assessment + importance gate
    + dispositions + mode. Feed it EVERY observation (calm ones drive
    the stand-down); it returns an AckRecord only when something was
    noticed, else None."""

    def __init__(self, body: BodySpec | None = None,
                 history: OrganHistory | None = None,
                 stand_down_dwell: int = 3,
                 monitor_recheck_s: float = 30.0):
        self.watcher = AnomalyWatcher()
        self.body = body if body is not None else BodySpec()
        self.history = history if history is not None else OrganHistory()
        self.stand_down_dwell = stand_down_dwell
        self.monitor_recheck_s = monitor_recheck_s
        self.mode = "WATCH"                # WATCH | ACTIVE
        self.active_channel: str | None = None
        self.watch_level = "normal"        # normal | raised (MONITOR)
        self.monitor_until: float | None = None
        self._calm_streak = 0
        self._dismissals: dict[str, int] = {}   # signature -> DISMISS n
        self.records: list[AckRecord] = []
        self.mode_log: list[dict] = []
        self.counters = {"acks": 0, "dismissed": 0,
                         "monitored": 0, "escalated": 0}

    def register(self, *args, **kwargs) -> None:
        self.watcher.register(*args, **kwargs)

    # -- assessment ------------------------------------------------------
    def _assess(self, anomaly: Anomaly, cfg: dict,
                ctx: dict) -> tuple[dict, str]:
        """Quick math from preloaded laws. Returns (assessment,
        default_action). For a ball event with a state supplied, the
        §11 feasibility oracle IS the assessment — cause and effect
        anticipated before the brain is asked anything. Otherwise a
        generic consequence sketch: what is at risk, what is blocked."""
        ball = ctx.get("ball")
        if ball is not None:
            verdict = feasibility(ball["state"], self.body, self.history,
                                  ball["hemisphere"],
                                  ball["gust_accel"])
            # The rock rule prices the action inside the escalation.
            act = decide(ctx.get("event_value_j", 100.0),
                         ctx.get("catch_cost_j", 10.0), verdict)
            assessment = {
                "kind": "ball_feasibility",
                "asset_at_risk": True,
                "goal_blocked": bool(ctx.get("goal_blocked", False)),
                "hemisphere": ball["hemisphere"],
                "feasibility": verdict,
            }
            return assessment, ("act" if act else "none")
        assessment = {
            "kind": "generic",
            "asset_at_risk": cfg["asset_risk"] >= 0.5,
            "goal_blocked": bool(ctx.get("goal_blocked", False)),
            "note": ("no physical consequence model for this channel; "
                     "importance rests on asset risk and goal "
                     "relevance alone"),
        }
        return assessment, "brain"

    # -- mode ------------------------------------------------------------
    def _set_mode(self, mode: str, ts: float, channel: str | None,
                  reason: str) -> None:
        if mode == self.mode:
            return
        self.mode_log.append({"ts": ts, "from": self.mode, "to": mode,
                              "channel": channel, "reason": reason})
        self.mode = mode
        self.active_channel = channel if mode == "ACTIVE" else None
        self._calm_streak = 0

    # -- the acknowledge call ---------------------------------------------
    def process(self, channel: str, value: float, ts: float = 0.0,
                ctx: dict | None = None) -> AckRecord | None:
        ctx = ctx or {}
        cfg = self.watcher.config(channel)
        anomaly = self.watcher.observe(channel, value)

        if anomaly is None:
            # Calm reads on the pinned channel are the stand-down
            # clock; calm means the channel itself reads stable, not
            # merely that no new edge fired.
            if (self.mode == "ACTIVE" and channel == self.active_channel
                    and self.watcher.is_calm(channel, value)):
                self._calm_streak += 1
                if self._calm_streak >= self.stand_down_dwell:
                    self._set_mode("WATCH", ts, channel,
                                   "channel stable for "
                                   f"{self.stand_down_dwell} calm "
                                   "observations — standing down")
            return None

        if channel == self.active_channel:
            self._calm_streak = 0     # still disturbed; no stand-down

        # Importance gate: does brain care? Transparent arithmetic —
        # every component lands in the record.
        goal_relevance = float(ctx.get("goal_relevance",
                                       cfg["goal_relevance"]))
        prior_dismissals = self._dismissals.get(anomaly.signature, 0)
        novelty = 0.5 ** prior_dismissals     # habituation decay
        importance = max(cfg["asset_risk"], goal_relevance) * novelty
        components = {
            "asset_risk": cfg["asset_risk"],
            "goal_relevance": goal_relevance,
            "novelty_factor": novelty,
            "prior_dismissals": prior_dismissals,
            "signature": anomaly.signature,
        }

        assessment, gated_action = self._assess(anomaly, cfg, ctx)

        if importance < DISMISS_BELOW:
            disposition, action = "DISMISS", "none"
        elif importance <= MONITOR_UP_TO:
            disposition, action = "MONITOR", "none"
        else:
            disposition = "ESCALATE"
            # Feasibility gates the ACTION, never the caring: a
            # LET_FALL assessment still escalates, with action='none'
            # — brain informed, body deliberately still.
            action = gated_action

        record = AckRecord(
            ts=ts, channel=channel,
            anomaly_summary=anomaly.summary,
            assessment=assessment,
            importance=importance,
            importance_components=components,
            disposition=disposition, action=action,
            habituated=novelty < 1.0,
            mode_after=self.mode,   # provisional; mode update below
        )

        if disposition == "DISMISS":
            self._dismissals[anomaly.signature] = prior_dismissals + 1
            self.counters["dismissed"] += 1
        elif disposition == "MONITOR":
            self.counters["monitored"] += 1
            self.watch_level = "raised"
            self.monitor_until = ts + self.monitor_recheck_s
        else:
            self.counters["escalated"] += 1
            if cfg["body_asset"]:
                self._set_mode("ACTIVE", ts, channel,
                               f"ESCALATE on body-asset channel "
                               f"{channel} — make sure it does not "
                               f"fall; active until stable")
        self.counters["acks"] += 1
        record.mode_after = self.mode
        self.records.append(record)
        return record


# ------------------------------------------------------------ self-tests ---
def _event_layer(**kw) -> OracleAck:
    layer = OracleAck(**kw)
    layer.register("painting", "event", asset_risk=0.05,
                   edge_level=130.0)
    layer.register("gust", "event", asset_risk=0.9, body_asset=True,
                   edge_level=0.1)
    return layer


def _gust_ctx(x=0.0, v=0.0, gust=0.2, hemisphere="RIGHT",
              latencies=(0.30, 0.35, 0.28)) -> dict:
    hist = OrganHistory()
    for lat in latencies:
        hist.add(hemisphere, lat)
    return hist, {"ball": {"state": {"x": x, "v": v},
                           "gust_accel": gust,
                           "hemisphere": hemisphere}}


def run_self_tests() -> list[str]:
    passed = []

    # 1. Cosmetic anomaly -> DISMISS (the crooked painting).
    layer = _event_layer()
    layer.process("painting", 100.0, ts=0.0)
    rec = layer.process("painting", 165.0, ts=1.0)
    assert rec is not None and rec.disposition == "DISMISS", rec
    assert abs(rec.importance - 0.05) < 1e-9 and rec.action == "none"
    assert layer.mode == "WATCH"
    passed.append("cosmetic anomaly (asset risk 0.05) -> DISMISS, "
                  "importance 0.05, mode stays WATCH")

    # 2. Same cosmetic anomaly x4 -> importance decays, habituated.
    layer = _event_layer()
    imps, habs = [], []
    t = 0.0
    for _ in range(4):
        layer.process("painting", 100.0, ts=t)
        r = layer.process("painting", 165.0, ts=t + 0.5)
        imps.append(r.importance)
        habs.append(r.habituated)
        t += 1.0
    assert imps == [0.05, 0.025, 0.0125, 0.00625], imps
    assert habs == [False, True, True, True], habs
    assert all(r.disposition == "DISMISS" for r in layer.records)
    passed.append(f"cosmetic x4: importance decays {imps} (x0.5 per "
                  "dismissal), repeats flagged habituated")

    # 3. Gust-class anomaly -> ESCALATE + mode ACTIVE, feasible -> act.
    layer = _event_layer()
    hist, ctx = _gust_ctx()          # fast organ, gentle gust -> CATCH
    layer.history = hist
    layer.process("gust", 0.0, ts=0.0)
    rec = layer.process("gust", 0.2, ts=1.0, ctx=ctx)
    assert rec is not None and rec.disposition == "ESCALATE", rec
    assert rec.importance > 0.6 and layer.mode == "ACTIVE", rec
    assert rec.assessment["feasibility"]["verdict"] == "CATCH", rec
    assert rec.action == "act", rec
    passed.append("gust-class anomaly (asset risk 0.9) -> ESCALATE "
                  "importance 0.9, mode ACTIVE, feasibility CATCH -> "
                  "action 'act'")

    # 4. Calm observations stand ACTIVE down to WATCH (dwell = 3) —
    # and readings DURING the gust do not count as calm.
    layer.process("gust", 0.2, ts=1.5)     # gust still blowing: no edge,
    layer.process("gust", 0.2, ts=2.0)     # but NOT calm — no stand-down
    assert layer.mode == "ACTIVE"
    layer.process("gust", 0.0, ts=2.5)     # calm 1
    layer.process("gust", 0.0, ts=3.0)     # calm 2
    assert layer.mode == "ACTIVE"
    layer.process("gust", 0.0, ts=3.5)     # calm 3 -> stand down
    assert layer.mode == "WATCH", layer.mode_log
    passed.append("stand-down: gust-in-progress reads are not calm; "
                  "3 consecutive stable reads -> ACTIVE back to WATCH")

    # 5. MONITOR band: mid importance, watch level up, mode untouched.
    layer = OracleAck()
    layer.register("imu_bias", "metric", asset_risk=0.4,
                   baseline=(0.0, 1.0))
    rec = layer.process("imu_bias", 3.0, ts=0.0)
    assert rec is not None and rec.disposition == "MONITOR", rec
    assert abs(rec.importance - 0.4) < 1e-9, rec
    assert layer.mode == "WATCH" and layer.watch_level == "raised"
    assert layer.monitor_until == 30.0
    passed.append("metric anomaly at importance 0.4 -> MONITOR: watch "
                  "level raised + re-check timer set, mode stays WATCH")

    # 6. Feasibility LET_FALL inside an escalation -> action='none'.
    # Brain is informed; the body deliberately does nothing.
    layer = _event_layer()
    hist, ctx = _gust_ctx(gust=0.9, hemisphere="LEFT",
                          latencies=(3.0, 3.2, 2.9))   # slow organ
    layer.history = hist
    layer.process("gust", 0.0, ts=0.0)
    rec = layer.process("gust", 0.9, ts=1.0, ctx=ctx)
    assert rec is not None and rec.disposition == "ESCALATE", rec
    assert rec.assessment["feasibility"]["verdict"] == "LET_FALL", rec
    assert rec.action == "none", rec
    assert layer.mode == "ACTIVE"     # caring is not gated by feasibility
    passed.append("ESCALATE with feasibility LET_FALL -> action "
                  "'none': brain informed, body deliberately still, "
                  "mode still ACTIVE")

    return passed


if __name__ == "__main__":
    print("SELF-TESTS")
    for line in run_self_tests():
        print("  PASS:", line)
