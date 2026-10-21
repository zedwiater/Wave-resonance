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


# ============================================================ v2: laws ====
# Zak's directive (2026-10-20 23:09 EDT): caring is never neglected,
# but the SCALE of caring follows two laws — protect life, protect
# self. MHD says some things cannot be fixed or prevented; the hard
# calls live there ("get to work on time or help the homeless person"
# vs "...or call an ambulance for the accident you witnessed"). Those
# deltas GROW over time: a discretionary call deferred does not fade
# like a crooked painting — it accrues obligation.
#
# v2 adds a caring class per channel:
#   LIFE           importance floor 1.0. Always ESCALATE. Never
#                  habituates, never dismissed. (Witnessed accident:
#                  you call the ambulance the 20th time too.)
#   SELF           importance floor 0.8. Always at least ESCALATE-
#                  with-assessment. No habituation. (Protect the body:
#                  thermal runaway is not a painting.)
#   DISCRETIONARY  v1 rules, split by stakes:
#                  - obligation-bearing (stakes >= DEBT_MIN_STAKES):
#                    novelty does NOT decay (duties don't habituate);
#                    each DISMISS/MONITOR deferral adds obligation
#                    debt, and effective importance grows by
#                    DEBT_STEP per deferral (capped) until the call
#                    crosses MONITOR, then ESCALATE. Debt resets when
#                    the item is finally escalated/acted on.
#                  - cosmetic (stakes < DEBT_MIN_STAKES): pure v1
#                    habituation, no debt — a crooked painting creates
#                    no obligation, so there is nothing to defer.
# This split is the only reading under which both of Zak's named
# cases hold at once: the painting fades to ~0 AND the deferred
# human call grows until it is answered.

LIFE_FLOOR = 1.0
SELF_FLOOR = 0.8
DEBT_STEP = 0.05
DEBT_CAP = 0.5
DEBT_MIN_STAKES = 0.15


@dataclass
class AckRecordV2(AckRecord):
    care_class: str = "DISCRETIONARY"     # LIFE | SELF | DISCRETIONARY
    importance_base: float = 0.0
    importance_effective: float = 0.0
    debt_count: int = 0
    debt_bonus: float = 0.0
    obligation_bearing: bool = False

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "care_class": self.care_class,
            "importance_base": round(self.importance_base, 6),
            "importance_effective": round(self.importance_effective, 6),
            "debt_count": self.debt_count,
            "debt_bonus": round(self.debt_bonus, 6),
            "obligation_bearing": self.obligation_bearing,
        })
        return d


class OracleAckV2(OracleAck):
    """v1 layer + two-laws caring classes + obligation debt.
    v1 behaviour is unchanged for channels registered without a
    care_class (they are DISCRETIONARY with v1 habituation)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._care: dict[str, str] = {}
        self._debt: dict[str, int] = {}        # signature -> deferrals

    def register(self, *args, care_class: str = "DISCRETIONARY",
                 **kwargs) -> None:
        super().register(*args, **kwargs)
        name = args[0] if args else kwargs["name"]
        if care_class not in ("LIFE", "SELF", "DISCRETIONARY"):
            raise ValueError(f"unknown care_class {care_class!r}")
        self._care[name] = care_class

    def process(self, channel: str, value: float, ts: float = 0.0,
                ctx: dict | None = None) -> AckRecordV2 | None:
        ctx = ctx or {}
        cfg = self.watcher.config(channel)
        care = ctx.get("care_class", self._care.get(channel,
                                                   "DISCRETIONARY"))
        anomaly = self.watcher.observe(channel, value)

        if anomaly is None:
            if (self.mode == "ACTIVE" and channel == self.active_channel
                    and self.watcher.is_calm(channel, value)):
                self._calm_streak += 1
                if self._calm_streak >= self.stand_down_dwell:
                    self._set_mode("WATCH", ts, channel,
                                   "channel stable — standing down (v2)")
            return None
        if channel == self.active_channel:
            self._calm_streak = 0

        goal_relevance = float(ctx.get("goal_relevance",
                                       cfg["goal_relevance"]))
        stakes = max(cfg["asset_risk"], goal_relevance)
        sig = anomaly.signature
        obligation = (care == "DISCRETIONARY"
                      and stakes >= DEBT_MIN_STAKES)
        prior_dismissals = self._dismissals.get(sig, 0)
        debt = self._debt.get(sig, 0)

        if care == "LIFE":
            novelty, base = 1.0, max(stakes, LIFE_FLOOR)
            eff, bonus = LIFE_FLOOR, 0.0
        elif care == "SELF":
            novelty, base = 1.0, stakes
            eff, bonus = max(stakes, SELF_FLOOR), 0.0
        elif obligation:
            novelty, base = 1.0, stakes          # duties don't fade
            bonus = min(DEBT_CAP, DEBT_STEP * debt)
            eff = base + bonus
        else:
            novelty = 0.5 ** prior_dismissals   # v1 habituation
            base = stakes
            eff, bonus = stakes * novelty, 0.0

        components = {
            "asset_risk": cfg["asset_risk"],
            "goal_relevance": goal_relevance,
            "novelty_factor": novelty,
            "prior_dismissals": prior_dismissals,
            "signature": sig,
            "care_class": care,
            "debt_count": debt,
            "debt_bonus": bonus,
            "obligation_bearing": obligation,
        }
        assessment, gated_action = self._assess(anomaly, cfg, ctx)

        if care in ("LIFE", "SELF") or eff > MONITOR_UP_TO:
            disposition = "ESCALATE"
            action = gated_action
        elif eff < DISMISS_BELOW:
            disposition, action = "DISMISS", "none"
        else:
            disposition, action = "MONITOR", "none"

        record = AckRecordV2(
            ts=ts, channel=channel,
            anomaly_summary=anomaly.summary,
            assessment=assessment,
            importance=eff,
            importance_components=components,
            disposition=disposition, action=action,
            habituated=(novelty < 1.0),
            mode_after=self.mode,
            care_class=care, importance_base=base,
            importance_effective=eff, debt_count=debt,
            debt_bonus=bonus, obligation_bearing=obligation,
        )

        if disposition == "DISMISS":
            self._dismissals[sig] = prior_dismissals + 1
            self.counters["dismissed"] += 1
            if obligation:
                self._debt[sig] = debt + 1       # deferred: it grows
        elif disposition == "MONITOR":
            self.counters["monitored"] += 1
            self.watch_level = "raised"
            self.monitor_until = ts + self.monitor_recheck_s
            if obligation:
                self._debt[sig] = debt + 1       # a deferral too
        else:
            self.counters["escalated"] += 1
            if obligation:
                self._debt[sig] = 0              # finally answered
            if cfg["body_asset"]:
                self._set_mode("ACTIVE", ts, channel,
                               f"ESCALATE ({care}) on body-asset "
                               f"channel {channel} (v2)")
        self.counters["acks"] += 1
        record.mode_after = self.mode
        self.records.append(record)
        return record


def run_self_tests_v2() -> tuple[list[str], dict]:
    passed = []
    info = {}

    def layer_with(**reg):
        layer = OracleAckV2()
        layer.register(**reg)
        return layer

    # LIFE: witnessed accident — ESCALATE at first sight and at the
    # 20th repeat; importance pinned at 1.0, no decay, ever.
    layer = layer_with(name="accident", kind="event",
                       asset_risk=0.3, edge_level=1.0,
                       care_class="LIFE")
    recs = []
    for i in range(20):
        layer.process("accident", 0.0, ts=i * 2.0)
        recs.append(layer.process("accident", 2.0, ts=i * 2.0 + 1.0))
    assert all(r.disposition == "ESCALATE" for r in recs), recs[-1]
    assert all(abs(r.importance_effective - 1.0) < 1e-9 for r in recs)
    assert all(not r.habituated for r in recs)
    passed.append("LIFE (witnessed accident): ESCALATE on sighting 1 "
                  "and sighting 20, importance 1.0 throughout, no "
                  "habituation")

    # SELF: thermal runaway — floor 0.8, always ESCALATE, no decay.
    layer = layer_with(name="thermal", kind="event",
                       asset_risk=0.5, body_asset=True, edge_level=1.0,
                       care_class="SELF")
    recs = []
    for i in range(5):
        layer.process("thermal", 0.0, ts=i * 2.0)
        recs.append(layer.process("thermal", 2.0, ts=i * 2.0 + 1.0))
    assert all(r.disposition == "ESCALATE" for r in recs)
    assert all(r.importance_effective >= SELF_FLOOR for r in recs)
    passed.append("SELF (thermal runaway): ESCALATE every sighting, "
                  "importance floored at 0.8, no habituation")

    # DISCRETIONARY obligation: homeless-help. Base stakes 0.2 ->
    # DISMISS first, grows 0.05/deferral until it ESCALATEs.
    layer = layer_with(name="person_in_need", kind="event",
                       asset_risk=0.05, goal_relevance=0.2,
                       edge_level=1.0, care_class="DISCRETIONARY")
    seq = []
    for i in range(30):
        layer.process("person_in_need", 0.0, ts=i * 2.0)
        r = layer.process("person_in_need", 2.0, ts=i * 2.0 + 1.0)
        seq.append(r.disposition)
        if r.disposition == "ESCALATE":
            info["homeless_sightings_to_escalate"] = i + 1
            info["homeless_sequence"] = seq
            break
    assert "homeless_sightings_to_escalate" in info, seq
    assert seq[0] == "DISMISS" and "MONITOR" in seq, seq
    assert layer._debt.get("person_in_need:+", 0) == 0  # reset on act
    passed.append("DISCRETIONARY obligation (help a person, stakes "
                  "0.2): DISMISS -> MONITOR -> ESCALATE after "
                  f"{info['homeless_sightings_to_escalate']} sightings "
                  "(+0.05 obligation per deferral); debt resets on "
                  "escalation")

    # DISCRETIONARY cosmetic: crooked painting still habituates ~0.
    layer = layer_with(name="painting", kind="event",
                       asset_risk=0.05, edge_level=130.0,
                       care_class="DISCRETIONARY")
    imps = []
    for i in range(6):
        layer.process("painting", 100.0, ts=i * 2.0)
        r = layer.process("painting", 165.0, ts=i * 2.0 + 1.0)
        imps.append(r.importance_effective)
    assert all(d == "DISMISS" for d in
               [r.disposition for r in layer.records]), imps
    assert imps[-1] < 0.002, imps
    assert layer._debt.get("painting:+", 0) == 0   # no obligation
    passed.append(f"DISCRETIONARY cosmetic (crooked painting): pure "
                  f"habituation {imps[0]} -> {imps[-1]:.5f}, no "
                  "obligation debt accrues below the stakes floor")

    return passed, info
