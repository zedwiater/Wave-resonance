"""
env_forge.py — forge a simulated environment's physics out of the PC's
REAL telemetry errors (Zak's directive 2026-10-20 23:09 EDT).

Reads the dweller's tick log (dweller_log.jsonl), builds an anomaly
catalogue per channel that ACTUALLY exists in the log, classifies
outlier events, fits a simple event model (inter-arrival + magnitude)
per class, and writes env_profile.json that standing_sim.py samples
disturbances from.

Honesty rules (load-bearing):
- Only channels present in the log are measured. Missing channels
  (temperature, network, disk) are listed under "gaps" — never
  invented as data.
- A class with too few observed events falls back to the ball v2 gust
  parameters and is LABELLED fallback per class in the profile.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

MIN_EVENTS_MEASURED = 4        # below this a class is a fallback
V2_GUST_ACCEL = 0.9            # ball_balance_v2 GUST_ACCEL
V2_GUST_DURATION = 3.0


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def channel_series(records):
    """channel name -> list of (ts, value) for every numeric field."""
    series: dict[str, list] = {}
    for r in records:
        ts = _num(r.get("ts"))
        if ts is None:
            continue
        flat = {}
        for k, v in r.items():
            n = _num(v)
            if n is not None:
                flat[k] = n
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    n2 = _num(v2)
                    if n2 is not None:
                        flat[f"{k}.{k2}"] = n2
        for k, v in flat.items():
            series.setdefault(k, []).append((ts, v))
    for k in series:
        series[k].sort()
    return series


def stats_of(values):
    if not values:
        return None
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "p50": statistics.median(values),
    }


def detect_events(points, k_sigma=3.0):
    """Outlier events: value beyond mean + k*sigma (one-sided high) or
    mean - k*sigma (low). Returns list of {ts, value, z, direction}
    plus baseline stats. Consecutive outlier ticks collapse into one
    event (peak kept)."""
    values = [v for _, v in points]
    st = stats_of(values)
    if not st or st["std"] <= 1e-12:
        return st, []
    events = []
    in_event = False
    for ts, v in points:
        z = (v - st["mean"]) / st["std"]
        if abs(z) >= k_sigma:
            if not in_event or abs(z) > abs(events[-1]["z"]):
                ev = {"ts": ts, "value": v, "z": z,
                      "direction": "high" if z > 0 else "low"}
                if in_event:
                    events[-1] = ev
                else:
                    events.append(ev)
            in_event = True
        else:
            in_event = False
    return st, events


def event_model(events, span_s):
    if len(events) < 2:
        return None
    arrivals = [events[i + 1]["ts"] - events[i]["ts"]
                for i in range(len(events) - 1)]
    mags = [abs(e["z"]) for e in events]
    return {
        "n_events": len(events),
        "inter_arrival_mean_s": statistics.fmean(arrivals),
        "rate_per_min": 60.0 * len(events) / max(span_s, 1.0),
        "magnitude_z_mean": statistics.fmean(mags),
        "magnitude_z_max": max(mags),
    }


def forge(log_path: str) -> dict:
    records = []
    for line in Path(log_path).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    series = channel_series(records)
    span_s = 0.0
    if records:
        tss = [r["ts"] for r in records if _num(r.get("ts")) is not None]
        span_s = max(tss) - min(tss) if len(tss) > 1 else 0.0

    channels = {}
    class_events: dict[str, list] = {"power_spike": [], "load_surge": [],
                                     "thermal_excursion": [],
                                     "state_shift": []}
    # channel -> event class mapping (only for channels that exist)
    class_of = {
        "est_joules": "power_spike",
        "vram_used_frac": "load_surge",
        "tired": "state_shift",
        "curious": "state_shift",
    }
    for name, points in sorted(series.items()):
        st, events = detect_events(points)
        channels[name] = {"stats": st, "n_outlier_events": len(events),
                          "events": events[:20]}
        cls = class_of.get(name)
        if cls:
            class_events[cls].extend(
                [{**e, "channel": name} for e in events])

    def build_class(name, fallback_note, fallback_model):
        evs = sorted(class_events.get(name, []),
                     key=lambda e: e["ts"])
        model = event_model(evs, span_s)
        if model and len(evs) >= MIN_EVENTS_MEASURED:
            return {**model, "source": "measured", "fallback": None}
        return {**(model or {"n_events": len(evs)}),
                "source": "fallback",
                "fallback": fallback_note, **fallback_model}

    event_classes = {
        "power_spike": build_class(
            "power_spike",
            "too few est_joules outliers in a young log; using ball "
            "v2 gust parameters",
            {"gust_accel": V2_GUST_ACCEL, "gust_duration_s": V2_GUST_DURATION}),
        "load_surge": build_class(
            "load_surge",
            "too few vram_used_frac outliers; conservative synthetic "
            "rate (work-shed events are rare on this PC so far)",
            {"events_per_120s": 1}),
        "thermal_excursion": build_class(
            "thermal_excursion",
            "NO temperature channel exists in dweller telemetry — "
            "this class is wholly synthetic (assumed rate)",
            {"events_per_120s": 1, "duration_s": 12.0}),
        "state_shift": build_class(
            "state_shift",
            "too few tired/curious outliers; not sampled by the sim "
            "in v1 (informational class)",
            {}),
    }

    gaps = []
    if not any("temp" in c for c in channels):
        gaps.append("temperature: no thermal channel in dweller_log "
                    "(thermal_excursion class is synthetic)")
    gaps.append("network: no packet/drop channel in dweller_log — "
                "dropped-packet weather cannot be forged from this log")
    gaps.append("disk_io: no read/write channel in dweller_log")
    gaps.append("loadavg: no load channel in dweller_log (vram and "
                "est_joules are the only load-adjacent signals)")

    return {
        "source_log": str(log_path),
        "n_records": len(records),
        "span_s": span_s,
        "channels": channels,
        "event_classes": event_classes,
        "gaps": gaps,
        "quiet_fraction_note": (
            "records with empty health_anomalies: "
            f"{sum(1 for r in records if r.get('health_anomalies') == [])}"
            f"/{len(records)}"),
    }


def main():
    log = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dweller_log.jsonl"
    out = sys.argv[2] if len(sys.argv) > 2 else "env_profile.json"
    profile = forge(log)
    Path(out).write_text(json.dumps(profile, indent=1))
    print(f"records={profile['n_records']} span={profile['span_s']:.0f}s "
          f"channels={list(profile['channels'])}")
    for name, cls in profile["event_classes"].items():
        print(f"  {name}: source={cls['source']} "
              f"n={cls.get('n_events')}")
    for g in profile["gaps"]:
        print("  GAP:", g)
    print(profile["quiet_fraction_note"])


if __name__ == "__main__":
    main()
