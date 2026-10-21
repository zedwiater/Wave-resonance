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
import ipaddress
import json
import math
import os
import re
import shutil
import subprocess
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
CROSSTALK_PATH = os.path.expanduser(
    "~/wave-sunday/harness/crosstalk.jsonl")
CORPUS_PATH = os.path.expanduser(
    "~/wave-sunday/harness/campaign_corpus.jsonl")
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


def read_temps():
    """All hwmon temperature channels: {max_c, channels{name: c}}.
    max_c is None when the body has no thermal sensors to feel."""
    channels = {}
    for p in sorted(glob.glob("/sys/class/hwmon/hwmon*/temp*_input")):
        try:
            val = int(open(p).read().strip()) / 1000.0
        except (OSError, ValueError):
            continue
        label_path = p.replace("_input", "_label")
        try:
            name = open(label_path).read().strip()
        except OSError:
            name = os.path.basename(os.path.dirname(p)) + "/" \
                + os.path.basename(p)
        channels[name] = val
    return {"max_c": max(channels.values()) if channels else None,
            "channels": channels}


def read_temp_c():
    t = read_temps()
    return t["max_c"] if t["max_c"] is not None else 50.0


def read_loadavg():
    try:
        return float(open("/proc/loadavg").read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _default_iface():
    """Default-route interface from /proc/net/route (no shell)."""
    try:
        for line in open("/proc/net/route").read().splitlines()[1:]:
            f = line.split()
            if len(f) >= 2 and f[1] == "00000000":
                return f[0]
    except OSError:
        pass
    return None


def _iface_ipv4(iface):
    """(ipv4, prefixlen) for an iface via `ip -o -4 addr`, or None."""
    if not iface:
        return None
    try:
        out = subprocess.run(["ip", "-o", "-4", "addr", "show", "dev",
                              iface], capture_output=True, text=True,
                             timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", out.stdout)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def _net_counters(iface):
    """Raw counters for one iface from /proc/net/dev, or None."""
    if not iface:
        return None
    try:
        lines = open("/proc/net/dev").read().splitlines()
    except OSError:
        return None
    for line in lines:
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        if name.strip() != iface:
            continue
        f = rest.split()
        if len(f) < 16:
            return None
        return {"rx_bytes": int(f[0]), "rx_packets": int(f[1]),
                "rx_errs": int(f[2]), "rx_drop": int(f[3]),
                "tx_bytes": int(f[8]), "tx_packets": int(f[9]),
                "tx_errs": int(f[10]), "tx_drop": int(f[11])}
    return None


def _disk_counters():
    """Raw counters for the root filesystem's device from
    /proc/diskstats. Candidate device ids, in order: the root
    mount's st_dev (ext4-style), then the rdev of the mount's
    source node from /proc/mounts — btrfs reports an ANONYMOUS
    st_dev (0:31 on Zak's PC) that appears in no diskstats line,
    while its source node /dev/mapper/root is dm-0 (253:0) and
    does. First candidate with a diskstats line wins."""
    wants = []
    try:
        dev = os.stat("/")
        wants.append((os.major(dev.st_dev), os.minor(dev.st_dev)))
    except OSError:
        pass
    try:
        for line in open("/proc/mounts"):
            f = line.split()
            if len(f) >= 2 and f[1] == "/":
                node = f[0].split("[")[0]
                try:
                    r = os.stat(node)
                    wants.append((os.major(r.st_rdev),
                                  os.minor(r.st_rdev)))
                except OSError:
                    pass
                break
    except OSError:
        pass
    try:
        lines = open("/proc/diskstats").read().splitlines()
    except OSError:
        return None
    for line in lines:
        f = line.split()
        if len(f) < 14 or (int(f[0]), int(f[1])) not in wants:
            continue
        return {"device": f[2],
                "read_bytes": int(f[5]) * 512,
                "write_bytes": int(f[9]) * 512,
                "reads": int(f[3]), "writes": int(f[7])}
    return None


_COUNTER_STATE = {"net": None, "disk": None}


def read_io_deltas():
    """Per-interval deltas for net + disk IO. First call after boot
    establishes the baseline (deltas 0, baseline=True) — a body
    cannot report flow it has not watched yet."""
    iface = _default_iface()
    out = {"iface": iface}
    currents = {"net": _net_counters(iface), "disk": _disk_counters()}
    for key in ("net", "disk"):
        cur = currents[key]
        prev = _COUNTER_STATE[key]
        _COUNTER_STATE[key] = cur
        if cur is None:
            out[key] = None
            continue
        if prev is None:
            out[key] = {**{k: 0 for k, v in cur.items()
                           if isinstance(v, int)},
                        "baseline": True}
            if "device" in cur:
                out[key]["device"] = cur["device"]
            continue
        d = {k: max(0, cur[k] - prev.get(k, cur[k]))
             for k, v in cur.items() if isinstance(v, int)}
        d["baseline"] = False
        if "device" in cur:
            d["device"] = cur["device"]
        out[key] = d
    return out


_PRESENCE_CACHE = {"ts": 0.0, "value": None}
PRESENCE_TTL_S = 1800.0        # at most one sweep per 30 ticks


def read_community_presence(now=None, force=False):
    """Who is around: a bounded, presence-only sweep.

    LAN: `nmap -sn` (ping scan — no ports, no external targets) on
    the default iface's subnet, rate-bounded by PRESENCE_TTL_S.
    Tailnet: `tailscale status --json` peers marked Online. If nmap
    is absent the LAN leg reports status "nmap_missing" (installing
    it is a sudo-trip item, never done from here) and the tailnet
    leg still answers.
    """
    now = now if now is not None else time.time()
    cached = _PRESENCE_CACHE["value"]
    if cached is not None and not force \
            and now - _PRESENCE_CACHE["ts"] < PRESENCE_TTL_S:
        return {**cached, "cached": True}
    iface = _default_iface()
    addr = _iface_ipv4(iface)
    subnet = None
    if addr:
        subnet = str(ipaddress.ip_network(
            f"{addr[0]}/{addr[1]}", strict=False))
    peers, ts_status = [], "missing"
    try:
        out = subprocess.run(["tailscale", "status", "--json"],
                             capture_output=True, text=True, timeout=8)
        data = json.loads(out.stdout)
        ts_status = "ok"
        for peer in (data.get("Peer") or {}).values():
            if peer.get("Online"):
                name = peer.get("HostName") or peer.get("DNSName") \
                    or "unknown"
                peers.append(name)
    except OSError:
        ts_status = "missing"      # CLI absent or not runnable
    except (ValueError, subprocess.SubprocessError):
        ts_status = "error"        # CLI answered, answer unusable
    nmap_path = shutil.which("nmap")
    if nmap_path is None or subnet is None:
        lan = {"status": "nmap_missing", "hosts_up": None}
    else:
        try:
            out = subprocess.run([nmap_path, "-sn", subnet],
                                 capture_output=True, text=True,
                                 timeout=60)
            hosts = len(re.findall(r"Nmap scan report for",
                                   out.stdout))
            lan = {"status": "ok", "hosts_up": hosts}
        except (OSError, subprocess.SubprocessError):
            lan = {"status": "error", "hosts_up": None}
    value = {"status": lan["status"], "hosts_up": lan["hosts_up"],
             "lan_subnet": subnet, "iface": iface,
             "known_peers_present": sorted(peers),
             "tailscale_status": ts_status, "swept_at": now,
             "cached": False}
    _PRESENCE_CACHE.update(ts=now, value=value)
    return value


def read_self_state(organs, channel_ok):
    """First-class self-knowledge for the tick record: is my
    identity intact, do I know my organs, how many of my body
    channels are answering. Failures feed the survival deficit —
    a body that cannot feel itself is a body in trouble."""
    intact = False
    try:
        core_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "identity_core.json")
        core = json.load(open(core_path))
        from identity import DEFAULT_CORE
        intact = core.get("name") == DEFAULT_CORE["name"]
    except Exception:
        intact = False
    organs_known = isinstance(organs, dict) \
        and {"gemma_8080", "second_8081"} <= set(organs) \
        and all(isinstance(organs[k], bool)
                for k in ("gemma_8080", "second_8081"))
    return {"identity_intact": intact, "organs_known": organs_known,
            "body_channels_ok": sum(1 for v in channel_ok.values()
                                    if v),
            "body_channels": channel_ok}


def compute_tp_flow(est_joules, elapsed_s, net_bytes_delta,
                    disk_bytes_delta, tokens=0):
    """tp_flow — normalized transduction throughput for one tick.

    Exact formula (dimensionless, 0..1):
      energy_rate_w   = est_joules / elapsed_s
      data_bytes      = net_bytes_delta + disk_bytes_delta
                        + 4 * tokens        (tokens priced at 4 B)
      data_rate_bps   = data_bytes / elapsed_s
      e_norm          = min(1, energy_rate_w / 100 W)
      d_norm          = min(1, log10(1 + data_rate_bps) / 7)
                        (saturates at 10 MB/s)
      tp_flow         = sqrt(e_norm * d_norm)   (geometric mean:
                        energy without data — or data without
                        energy — is not transduction)
    Returns (tp_flow, detail dict).
    """
    elapsed = max(float(elapsed_s), 1e-9)
    energy_rate = max(0.0, float(est_joules)) / elapsed
    data_bytes = max(0, net_bytes_delta) + max(0, disk_bytes_delta) \
        + 4 * max(0, tokens)
    data_rate = data_bytes / elapsed
    e_norm = min(1.0, energy_rate / 100.0)
    d_norm = min(1.0, math.log10(1.0 + data_rate) / 7.0)
    return math.sqrt(e_norm * d_norm), {
        "energy_rate_w": round(energy_rate, 3),
        "data_rate_bps": round(data_rate, 1),
        "e_norm": round(e_norm, 4), "d_norm": round(d_norm, 4)}



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
    temps = read_temps()
    organs = read_organs()
    io = read_io_deltas()
    load = read_loadavg()
    presence = read_community_presence()
    channel_ok = {
        "temps": temps["max_c"] is not None,
        "net": io.get("net") is not None,
        "disk_io": io.get("disk") is not None,
        "loadavg": load is not None,
        "community_presence": presence.get("tailscale_status") == "ok"
        or presence.get("status") == "ok",
    }
    return {"disk_free_frac": free / total,
            "temp_c": temps["max_c"] if temps["max_c"] is not None
            else 50.0,
            "temps": temps,
            "ledger_trend_j_per_h": 0.0,
            "vram_used_frac": read_vram_used_frac(),
            "organs": organs,
            "net": io.get("net"), "disk_io": io.get("disk"),
            "io_iface": io.get("iface"),
            "loadavg": load,
            "community_presence": presence,
            "self_state": read_self_state(organs, channel_ok)}


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
                 telemetry_fn=telemetry_snapshot, idle_w=45.0,
                 talk_path=None):
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
        # the callosum: two hemispheres, one voice (callosum.py).
        # Lazy import — a broken callosum disables the exchanges,
        # never the tick. talk_path None (dry-run) = no hemispheres.
        self.talk = None
        self.cycle_count = 0
        if talk_path:
            try:
                import callosum
                self._callosum = callosum
                self.talk = callosum.CrossTalk(talk_path)
            except Exception:
                self._callosum = None
                self.talk = None

    @staticmethod
    def _sense_fields(tel):
        """The first-class sense channels stamped on tick records."""
        return {"organs": tel.get("organs"),
                "vram_used_frac": tel.get("vram_used_frac"),
                "temps": tel.get("temps"), "net": tel.get("net"),
                "disk_io": tel.get("disk_io"),
                "loadavg": tel.get("loadavg"),
                "community_presence": tel.get("community_presence"),
                "self_state": tel.get("self_state")}

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
                   "temp_c": tel["temp_c"], **self._sense_fields(tel)}
            self.log_fn(rec)
            return rec
        if tel.get("disk_free_frac", 1.0) < DISK_FLOOR_FRAC:
            rec = {"ts": ts, "mode": "DISK_HOLD",
                   "disk_free_frac": tel["disk_free_frac"],
                   **self._sense_fields(tel)}
            self.log_fn(rec)
            return rec
        comm = community_snapshot(now=ts)
        pres = tel.get("community_presence") or {}
        if pres.get("swept_at"):
            # a stale presence sweep is a rising community deficit:
            # the body has not looked around in too long
            comm["presence_stale_h"] = max(
                0.0, (ts - pres["swept_at"]) / 3600.0)
        snap = {"telemetry": tel,
                "joules_today": self.joules_today,
                "community": comm,
                "self_state": tel.get("self_state"),
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
        # own VRAM, organs, and (2026-10-20 fix round) the new senses
        # as first-class channels — self and community included
        rec.update(self._sense_fields(tel))
        net_d = tel.get("net") or {}
        disk_d = tel.get("disk_io") or {}
        # read_io_deltas values ARE per-interval deltas (keys keep
        # the counter names: rx_bytes/tx_bytes/read_bytes/...)
        tp, tp_detail = compute_tp_flow(
            decision.get("est_joules", 0.0), TICK_S,
            net_d.get("rx_bytes", 0) + net_d.get("tx_bytes", 0),
            disk_d.get("read_bytes", 0) + disk_d.get("write_bytes", 0))
        rec["tp_flow"] = round(tp, 4)
        rec["tp_flow_detail"] = tp_detail
        if tel.get("disk_free_frac", 1.0) < DISK_WARN_FRAC:
            rec["disk_warn"] = True
        self.log_fn(rec)
        self._maybe_callosum(ts, snap, decision, tel)
        return rec

    # -- the callosum: symmetric exchange (ambidextrous, 2026-10-20
    #    fix round — either hemisphere may propose or dispose; the
    #    opener alternates by cycle parity inside callosum.py) ------
    def _orientation(self):
        """First line of the campaign corpus, trimmed — the mind's
        standing orientation, read by both hemispheres each cycle."""
        try:
            first = open(CORPUS_PATH).readline()
            d = json.loads(first)
            text = (f"Campaign: {d.get('campaign', '')} "
                    f"Rule: {d.get('rule', '')}")
            return text[:400]
        except (OSError, ValueError):
            return ""

    def _maybe_callosum(self, ts, snap, decision, tel):
        """Run one bilateral exchange on a slow cadence (tick 2 after
        boot, then every 30 ticks), never in DEEP_NIGHT, never while
        Zak is at work. Wrapped end-to-end: the callosum failing can
        never break a tick. The exchange TEXT lives in
        crosstalk.jsonl; the dweller log gets a CALLOSUM marker plus
        any right-side proposal (Zak's visibility window — a log,
        not an output channel)."""
        if self.talk is None:
            return
        if os.environ.get("HARNESS_CALLOSUM", "1") == "0":
            return
        if not (self.ticks == 2 or self.ticks % 30 == 0):
            return
        if decision.get("phase") == "DEEP_NIGHT":
            return
        if decision.get("phase_label") == "AT_WORK":
            return
        try:
            summary = (
                f"Phase {decision.get('phase')} "
                f"({decision.get('phase_label')}), "
                f"tired {decision.get('tired')}, "
                f"deficits {decision.get('deficits')}, "
                f"organs {tel.get('organs')}, "
                f"VRAM used frac {tel.get('vram_used_frac')}, "
                f"cube entries {len(self.cube.entries)}, "
                f"last decision {decision.get('mode')}/"
                f"{decision.get('drive')}/{decision.get('task')}.")
            orient = self._orientation()
            if orient:
                summary = orient + "\n" + summary
            entries = self._callosum.run_exchange(
                summary, self.talk, cycle=self.cycle_count + 1)
            self.cycle_count += 1
            rec = {"ts": ts, "mode": "CALLOSUM",
                   "entries": len(entries),
                   "cycle": self.cycle_count}
            for e in entries:
                if e.get("kind") == "proposal":
                    rec["proposal"] = e["text"]
                    rec["proposal_side"] = e.get("side")
                    if e.get("side") == "right":
                        # legacy field, kept for log continuity
                        rec["right_proposal"] = e["text"]
            self.log_fn(rec)
        except Exception:
            pass


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
    d = Dweller(cube, log, meter_fn=_meter_factory(),
                talk_path=CROSSTALK_PATH)
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
                # disk check WITHOUT a full telemetry snapshot:
                # a snapshot call would consume the IO-delta
                # baselines that belong to the tick's own record
                if shutil.disk_usage("/").free \
                        / shutil.disk_usage("/").total \
                        >= DISK_FLOOR_FRAC:
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
