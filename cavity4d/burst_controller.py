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
"""
from dataclasses import dataclass, field

DWELL, HOLD, BURST = "DWELL", "HOLD", "BURST"


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

    print("\nself-test:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    _selftest()
