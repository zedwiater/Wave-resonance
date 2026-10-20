"""burst_controller.py — micro-capacitor dwell/burst state machine.

Philosophy: trickle charge silently, dwell in default mode, burst rarely.
The edge node is mostly a cavity (CONTAIN), almost never an aperture
(PROJECT). One burst = one transform_scalars() packet (the black-hole
output), then straight back to sleep.

States:
  DWELL — default mode. Buffer trickle-charges from the ambient carrier;
          rate = harvest_coeff * carrier_power * impedance_efficiency.
  HOLD  — buffer full but phase-lock dirty: do NOT burst into noise.
          Waits for a clean lock (or buffer overflow decays).
  BURST — single event: emit the compressed packet, drain the buffer,
          return to DWELL.

Impedance hook: `impedance` (0..1) modulates trickle efficiency.
Set it via set_impedance() — the dynamic rho/sigma feedback loop
(wave-sunday item 1) will drive this slot when it exists. Until then it
defaults to 1.0.

No hardware dependencies. Deterministic. Testable.

v2 — the Dweller gets senses (Zak: "use system input telemetry for
sensing"):
  YieldSensor reads the machine's own telemetry — GPU busy percent
  and the process table — to feel a HUMAN arrive. While a human
  workload owns the machine, the controller yields: no harvest
  competition, no bursts, no dwell work. The machine belongs to
  whoever is sitting at it.
  dwell_work is the DWELL job slot: the KV cube's idle_cycle (and
  the anticipation falsifier) plug in here and think at trickle
  prices while the node sleeps.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

DWELL, HOLD, BURST = "DWELL", "HOLD", "BURST"
YIELD = "YIELD"

HUMAN_PATTERNS = ("TS4_x64", "AppId=", "waitforexitandrun", "Proton")


class YieldSensor:
    """Feel, from system input telemetry only."""

    def gpu_busy(self):
        vals = []
        for p in Path("/sys/class/drm").glob("card*/device/"
                                             "gpu_busy_percent"):
            try:
                vals.append(int(p.read_text().strip()))
            except (OSError, ValueError):
                pass
        return max(vals) if vals else None

    def human_workload(self):
        for pid in filter(str.isdigit, os.listdir("/proc")):
            try:
                cmd = Path(f"/proc/{pid}/cmdline").read_bytes()
                cmd = cmd.replace(b"\x00", b" ").decode("utf-8",
                                                         "replace")
            except OSError:
                continue
            if "llama-server" in cmd:
                continue
            if any(pat in cmd for pat in HUMAN_PATTERNS):
                return True
        return False

    def yielding(self):
        if self.human_workload():
            return True
        busy = self.gpu_busy()
        return busy is not None and busy >= 85


@dataclass
class BurstController:
    capacity: float = 1.0          # charge units; burst costs the full buffer
    harvest_coeff: float = 0.05    # trickle rate per unit carrier power per tick
    lock_threshold: float = 0.75   # phase-lock quality needed to burst
    decay: float = 0.0             # buffer leakage per tick in HOLD (0 = none)
    charge: float = 0.0
    impedance: float = 1.0         # slot for the MHD feedback loop (item 1)
    state: str = DWELL
    bursts: int = 0
    yield_check: object = None     # callable -> bool (YieldSensor.yielding)
    dwell_work: object = None      # callable(dt) — the DWELL job (cube)
    yielding: bool = False

    def set_impedance(self, z):
        """Dynamic rho/sigma hook. Clamped to [0, 1]."""
        self.impedance = max(0.0, min(1.0, float(z)))

    def step(self, dt, carrier_power, lock_quality):
        """One tick. carrier_power >= 0 (from transform_scalars),
        lock_quality in [0, 1] (1 = clean phase lock).
        Returns the burst packet event, or None."""
        carrier_power = max(0.0, float(carrier_power))
        lock_quality = max(0.0, min(1.0, float(lock_quality)))
        dt = max(0.0, float(dt))

        # the yield reflex comes before everything: a human on the
        # machine means no harvest, no burst, no dwell work
        if self.yield_check is not None and self.yield_check():
            self.yielding = True
            return None
        self.yielding = False

        # DWELL thinking: light work at trickle prices (cube cycles,
        # anticipation judgment) — only while truly dwelling
        if self.state == DWELL and self.dwell_work is not None:
            self.dwell_work(dt)

        # trickle: harvest only while dwelling
        if self.state in (DWELL, HOLD):
            self.charge += (self.harvest_coeff * carrier_power
                            * self.impedance * dt)

        if self.charge >= self.capacity:
            self.charge = self.capacity  # saturate, don't overflow
            if lock_quality >= self.lock_threshold:
                self.state = BURST
                self.bursts += 1
                self.charge = 0.0
                self.state = DWELL      # immediate return to sleep
                return {"event": "BURST", "packet": "transform_scalars",
                        "bursts_total": self.bursts}
            self.state = HOLD
        else:
            if self.state == HOLD and lock_quality >= self.lock_threshold:
                # lock cleaned up before full: still wait for capacity
                pass
            if self.charge < self.capacity and self.state == HOLD:
                if self.decay > 0:
                    self.charge = max(0.0, self.charge - self.decay * dt)
                    if self.charge < self.capacity:
                        self.state = DWELL
                # else: HOLD persists — buffer stays full, waiting for lock
        return None


# ---------------------------------------------------------------------------
def _selftest():
    print("burst controller self-test:")
    ok = True

    # 1. clean ambient: trickle -> burst -> dwell
    c = BurstController(capacity=1.0, harvest_coeff=0.5)
    ev = None
    for t in range(10):
        ev = c.step(1.0, carrier_power=0.5, lock_quality=0.9)
        if ev:
            break
    good = ev is not None and c.state == DWELL and c.charge == 0.0
    ok &= good
    print(f"  [{'OK ' if good else 'FAIL'}] clean lock: burst fired at tick {t}, "
          f"back to DWELL, buffer drained")

    # 2. dirty lock: buffer fills, NO burst, parks in HOLD
    c = BurstController(capacity=1.0, harvest_coeff=0.5)
    ev = None
    for _ in range(10):
        ev = c.step(1.0, carrier_power=0.5, lock_quality=0.2)
    good = ev is None and c.state == HOLD and c.charge == 1.0
    ok &= good
    print(f"  [{'OK ' if good else 'FAIL'}] dirty lock: no burst, state=HOLD, "
          f"buffer saturated (no overflow)")

    # 3. lock cleans up while holding: burst fires on next tick
    ev = c.step(1.0, carrier_power=0.5, lock_quality=0.95)
    good = ev is not None and ev["bursts_total"] == 1 and c.state == DWELL
    ok &= good
    print(f"  [{'OK ' if good else 'FAIL'}] lock cleaned: burst on next tick")

    # 4. impedance throttles harvest (the item-1 hook, exercised)
    c = BurstController(capacity=1.0, harvest_coeff=0.5)
    c.set_impedance(0.2)
    for _ in range(4):
        ev = c.step(1.0, carrier_power=0.5, lock_quality=0.9)
    good = ev is None and abs(c.charge - 0.2) < 1e-9
    ok &= good
    print(f"  [{'OK ' if good else 'FAIL'}] impedance 0.2: charge={c.charge:.2f} "
          f"after 4 ticks (expect 0.20)")

    # 5. zero ambient: nothing charges, no burst, stays asleep
    c = BurstController()
    evs = [c.step(1.0, carrier_power=0.0, lock_quality=1.0)
           for _ in range(20)]
    good = all(e is None for e in evs) and c.state == DWELL and c.charge == 0.0
    ok &= good
    print(f"  [{'OK ' if good else 'FAIL'}] dead ambient: 20 ticks, "
          f"no burst, deep sleep")

    # 6. yield reflex: human workload freezes everything
    c = BurstController(capacity=1.0, harvest_coeff=0.5,
                        yield_check=lambda: True)
    ev = c.step(1.0, carrier_power=5.0, lock_quality=1.0)
    good = ev is None and c.yielding and c.charge == 0.0 and c.bursts == 0
    ok &= good
    print(f"  [{'OK ' if good else 'FAIL'}] yield: no charge, no burst, "
          f"yielding flag set")

    # 7. dwell work runs in DWELL, stops under yield
    ticks = {"n": 0}
    flag = {"yield": False}
    c = BurstController(capacity=10.0, harvest_coeff=0.01,
                        dwell_work=lambda dt: ticks.__setitem__(
                            "n", ticks["n"] + 1),
                        yield_check=lambda: flag["yield"])
    for _ in range(3):
        c.step(1.0, carrier_power=0.1, lock_quality=0.0)
    flag["yield"] = True
    c.step(1.0, carrier_power=0.1, lock_quality=0.0)
    good = ticks["n"] == 3
    ok &= good
    print(f"  [{'OK ' if good else 'FAIL'}] dwell work: {ticks['n']} ticks "
          f"in DWELL, silent under yield")

    print("\nself-test:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    _selftest()
