"""SHARE handshake protocol — topological anchor pairing.

Two primitives:
  SEND: local wave propagation (fiber, light speed, distance matters)
  SHARE: topological mode-locking (anchors, distance irrelevant)

This implements the SHARE handshake:
1. Origin emits pilot tone (low-amplitude frequency sweep)
2. Target detects harmonic resonance at integer winding number
3. Both lock local oscillators to shared l mode
4. Coherence budget tracked (M_0 per coherence-second)
5. Re-pair when phase drift exceeds pi/4, else degrade gracefully to SEND

Maps to:
  S2 (routing): mode overlap = topological distance
  B1 (Eddington): coherence maintenance as regulated pump
  H1/H3 (anchors): physical mode-locking via NV/erbium
"""
import json
import numpy as np


# --- CERN condensation frequency lookup (physics bridge) ---
# nu = m*c^2/h. Decay channels = sub-spectra loss coefficients.
CERN_TABLE = {
    "electron":  {"mass_MeV": 0.511,    "nu_Hz": 1.236e20,
                  "stable": True, "channels": {}},
    "pion":     {"mass_MeV": 139.57,   "nu_Hz": 3.375e22,
                  "stable": False, "channels": {"mu_nu": 0.9999}},
    "proton":   {"mass_MeV": 938.272,  "nu_Hz": 2.269e23,
                  "stable": True, "channels": {},
                  "note": "99% binding energy, topological soliton"},
    "neutron":  {"mass_MeV": 939.565,  "nu_Hz": 2.272e23,
                  "stable": False, "channels": {"p_e_nub": 1.0},
                  "lifetime_s": 880.2},
    "higgs":    {"mass_MeV": 125090.0, "nu_Hz": 3.024e25,
                  "stable": False,
                  "channels": {"bb": 0.582, "WW": 0.214, "gg": 0.082,
                               "tautau": 0.063, "cc": 0.029, "ZZ": 0.026,
                               "gammagamma": 0.0023},
                  "width_MeV": 4.1,
                  "note": "VEV 246 GeV = universal viscosity threshold"},
}

H_COHERENCE_THRESHOLD = np.pi / 4  # re-pair trigger


class ShareAnchor:
    """Topological anchor node for SHARE primitive.

    Locks to a shared l mode via pilot-tone handshake.
    Tracks coherence budget (M_0 per coherence-second).
    """

    def __init__(self, name, material="NV_diamond", base_nu=1.0):
        self.name = name
        self.material = material
        self.base_nu = base_nu  # local oscillator base frequency
        self.locked_ell = None  # shared winding number (None = unlocked)
        self.partner = None     # paired anchor name
        self.phase = 0.0        # local phase
        self.phase_drift = 0.0  # cumulative drift since lock
        self.coherence_budget = 0.0  # M_0 spent on maintenance
        self.lock_time = 0.0

    def emit_pilot(self, ell_target=2, sweep_n=16, amp=0.01):
        """Origin: emit low-amplitude sweeping pilot tone.

        Returns pilot signature: (ell_target, sweep frequencies).
        In hardware: modulates local oscillator, broadcasts via
        classical channel (does not need to be fast — just needs
        to arrive before coherence window closes).
        """
        # Sweep around the target mode's expected frequency
        # In sim: just return the target; in hardware this is
        # a real frequency sweep detected by the partner's PLL
        return {"ell": ell_target, "amp": amp, "sweep_n": sweep_n,
                "from": self.name}

    def detect_pilot(self, pilot, noise_level=0.001):
        """Target: detect harmonic resonance in pilot tone.

        Returns True if local oscillator locks to pilot's ell.
        Simulates PLL capture: if pilot amp > noise threshold
        and ell is integer, lock succeeds.
        """
        ell = pilot["ell"]
        amp = pilot["amp"]
        # Integer winding number check (topological protection)
        if not isinstance(ell, int) or ell == 0:
            return False
        # Signal above noise floor
        if amp < noise_level:
            return False
        # LOCK: both anchors now share this ell mode
        self.locked_ell = ell
        self.partner = pilot["from"]
        self.phase = 0.0
        self.phase_drift = 0.0
        self.lock_time = 0.0
        return True

    def tick(self, dt=1.0, thermal_noise=0.001, maintenance_pump=0.0001):
        """Advance one time step. Track phase drift and M_0 cost.

        Returns status: 'locked', 're-pairing', or 'degraded'.
        """
        if self.locked_ell is None:
            return "unlocked"

        self.lock_time += dt
        # Thermal noise causes phase drift (random walk)
        self.phase_drift += np.random.normal(0, thermal_noise * np.sqrt(dt))
        # Maintenance pump corrects drift (costs M_0)
        correction = -np.sign(self.phase_drift) * min(
            abs(self.phase_drift), maintenance_pump * dt * 10)
        self.phase_drift += correction
        self.coherence_budget += maintenance_pump * dt

        # Check threshold
        if abs(self.phase_drift) > H_COHERENCE_THRESHOLD:
            # Decohered — need re-pairing
            old_ell = self.locked_ell
            self.locked_ell = None
            return f"re-pairing (was l={old_ell}, drift={self.phase_drift:.3f})"

        return "locked"

    def share_state(self, data):
        """Send data via SHARE primitive (topological, not propagating).

        In sim: returns (ell, data, phase) — the partner anchor
        reads this from the shared mode, not from a traveling wave.
        In hardware: modulates the shared l mode; partner's
        phase-locked detector reads the modulation.
        """
        if self.locked_ell is None:
            return None  # cannot SHARE without lock — fall back to SEND
        return {"ell": self.locked_ell, "data": data,
                "phase": self.phase, "from": self.name}


def demo_handshake():
    """Two anchors pair via pilot tone, exchange data, track budget."""
    np.random.seed(7)
    alice = ShareAnchor("NY", material="erbium")
    bob = ShareAnchor("London", material="erbium")

    # Step 1: Alice emits pilot
    pilot = alice.emit_pilot(ell_target=2)

    # Step 2: Bob detects and locks
    locked = bob.detect_pilot(pilot)
    # Alice also locks (she knows what she sent)
    alice.locked_ell = 2
    alice.partner = "London"

    # Step 3: Exchange via SHARE (no propagation delay)
    msg = alice.share_state({"key": "topological", "value": 42})

    # Step 4: Run for 100 ticks, track coherence
    statuses = []
    for t in range(100):
        sa = alice.tick(dt=1.0)
        sb = bob.tick(dt=1.0)
        statuses.append((sa, sb))
        if "re-pairing" in sa or "re-pairing" in sb:
            break

    n_ticks = len(statuses)
    total_budget = alice.coherence_budget + bob.coherence_budget

    return {
        "handshake": "pilot_tone",
        "locked": locked,
        "shared_ell": 2,
        "message_delivered": msg is not None,
        "ticks_before_repair": n_ticks,
        "total_M0_coherence": round(total_budget, 6),
        "M0_per_tick": round(total_budget / max(n_ticks, 1), 6),
        "final_status": statuses[-1] if statuses else None,
    }


def main():
    print("=== SHARE Handshake Demo ===", flush=True)
    result = demo_handshake()
    print(json.dumps(result, indent=2), flush=True)

    print("\n=== CERN Condensation Table ===", flush=True)
    for name, d in CERN_TABLE.items():
        print(f"{name}: {d['mass_MeV']:.3f} MeV = {d['nu_Hz']:.3e} Hz", flush=True)
        if not d["stable"] and d["channels"]:
            ch = ", ".join(f"{k} {v:.1%}" for k, v in d["channels"].items())
            print(f"  -> {ch}", flush=True)

    print("\nSHARE done", flush=True)


if __name__ == "__main__":
    main()
