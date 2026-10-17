"""SHARE handshake protocol — topological anchor pairing.

Two primitives:
  SEND: local wave propagation (fiber, light speed, distance matters)
  SHARE: topological mode-locking (anchors, distance irrelevant)

This implements the SHARE handshake:
1. Origin emits pilot tone (low-amplitude frequency sweep)
2. Target detects harmonic resonance at integer winding number
3. Both lock local oscillators to shared l mode
4. Coherence budget tracked (M_0 per coherence-second)
5. Tension cost tracked (K·sin(Δφ) per tick — the Alcubierre cost)
6. Re-pair when phase drift exceeds pi/4, else degrade gracefully to SEND

THE ALCUBIERRE REFRAMING:
  Alcubierre (1994): warp (x,y,z) coordinates to bring distant points together.
    Cost: exotic matter (negative energy density). Unphysical at scale.

  SHARE: match (ω,ℓ) to make distant points topologically adjacent.
    Cost: coupling energy (tension). Finite, measurable.

  Instead of bending spacetime, we bypass the distance metric entirely
  by working in frequency/mode space. The "warp bubble" is a phase-locked
  mode. The "exotic matter" is the tension holding the lock.

  Topological distance d_topo = f(Δω, Δφ, Δℓ, K) — not kilometers.

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
    Tracks tension cost (torque to maintain lock against drift).
    """

    def __init__(self, name, material="NV_diamond", base_nu=1.0,
                 coupling_K=1.0):
        self.name = name
        self.material = material
        self.base_nu = base_nu  # local oscillator base frequency
        self.coupling_K = coupling_K  # coupling strength (the "string tension")
        self.locked_ell = None  # shared winding number (None = unlocked)
        self.partner = None     # paired anchor name
        self.phase = 0.0        # local phase
        self.phase_drift = 0.0  # cumulative drift since lock
        self.coherence_budget = 0.0  # M_0 spent on maintenance
        self.tension_energy = 0.0  # cumulative ∫ K·sin(Δφ) dt — the Alcubierre cost
        self.tension_peak = 0.0  # max tension seen (for break-even analysis)
        self.lock_time = 0.0
        self.bits_shared = 0  # for per-bit cost calculation

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

    def tension(self):
        """Instantaneous tension: T = K·sin(Δφ).

        The restoring torque. Zero at Δφ=0 (locked) and Δφ=π (anti-locked).
        Maximum at Δφ=π/2. This is the "string tension" holding the
        topological link — the Alcubierre exotic-matter cost made finite.
        """
        if self.locked_ell is None:
            return 0.0
        return self.coupling_K * np.sin(self.phase_drift)

    def topological_distance(self, other):
        """Topological distance to another anchor.

        d_topo = f(Δω, Δφ, Δℓ, K)
        Not geographic — mode-space distance.
        Returns inf if ℓ modes differ (different topological sectors).
        """
        if self.locked_ell is None or other.locked_ell is None:
            return float('inf')
        if self.locked_ell != other.locked_ell:
            return float('inf')  # different sectors, no coupling possible
        d_omega = abs(self.base_nu - other.base_nu)
        d_phi = abs(self.phase_drift - other.phase_drift)
        K_eff = min(self.coupling_K, other.coupling_K)
        if K_eff <= 0:
            return float('inf')
        # Normalized detuning + phase separation, scaled by coupling
        return (d_omega + d_phi) / K_eff

    def tick(self, dt=1.0, thermal_noise=0.001, maintenance_pump=0.0001):
        """Advance one time step. Track phase drift, tension, and M_0 cost.

        Returns status: 'locked', 're-pairing', or 'degraded'.
        """
        if self.locked_ell is None:
            return "unlocked"

        self.lock_time += dt
        # Thermal noise causes phase drift (random walk)
        self.phase_drift += np.random.normal(0, thermal_noise * np.sqrt(dt))

        # TENSION COST: energy to hold lock against drift
        # E_tension = ∫ K·sin(Δφ) dt — this is the Alcubierre cost
        T = self.tension()
        self.tension_energy += abs(T) * dt
        self.tension_peak = max(self.tension_peak, abs(T))

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


def share_vs_send_breakeven(distance_km, data_bits, tension_per_tick,
                          ticks_needed, send_joules_per_km_per_bit=1e-9):
    """Break-even analysis: when does SHARE cost exceed SEND cost?

    E_share = tension_per_tick × ticks_needed (topological, distance-independent)
    E_send  = distance_km × data_bits × J/km/bit (propagation, distance-dependent)

    SHARE wins when E_share < E_send.
    The crossover distance is where they equal.

    This is the Alcubierre reframing: instead of warping (x,y,z) to bring
    distant points together (requiring exotic matter), we match (ω,ℓ) to make
    distant points topologically adjacent (requiring coupling energy).

    The "exotic matter" cost becomes a finite, measurable tension cost.
    """
    E_share = tension_per_tick * ticks_needed
    E_send = distance_km * data_bits * send_joules_per_km_per_bit

    if E_share <= 0:
        return {"winner": "SHARE", "reason": "zero tension cost",
                "E_share": 0, "E_send": E_send}

    # Crossover: distance where E_send = E_share
    if data_bits * send_joules_per_km_per_bit > 0:
        crossover_km = E_share / (data_bits * send_joules_per_km_per_bit)
    else:
        crossover_km = float('inf')

    winner = "SHARE" if E_share < E_send else "SEND"
    return {
        "winner": winner,
        "E_share_J": round(E_share, 9),
        "E_send_J": round(E_send, 9),
        "crossover_km": round(crossover_km, 1),
        "ratio": round(E_send / max(E_share, 1e-18), 2),
        "interpretation": (
            f"SHARE wins beyond {crossover_km:.1f} km for this data volume. "
            f"Below that, just send it through fiber."
        ),
    }


def demo_handshake():
    """Two anchors pair via pilot tone, exchange data, track budget."""
    np.random.seed(7)
    alice = ShareAnchor("NY", material="erbium", coupling_K=1.0)
    bob = ShareAnchor("London", material="erbium", coupling_K=1.0)

    # Step 1: Alice emits pilot
    pilot = alice.emit_pilot(ell_target=2)

    # Step 2: Bob detects and locks
    locked = bob.detect_pilot(pilot)
    # Alice also locks (she knows what she sent)
    alice.locked_ell = 2
    alice.partner = "London"

    # Step 3: Exchange via SHARE (no propagation delay)
    msg = alice.share_state({"key": "topological", "value": 42})
    alice.bits_shared += 1024  # simulated payload
    bob.bits_shared += 1024

    # Step 4: Run for 100 ticks, track coherence AND tension
    statuses = []
    for t in range(100):
        sa = alice.tick(dt=1.0)
        sb = bob.tick(dt=1.0)
        statuses.append((sa, sb))
        if "re-pairing" in sa or "re-pairing" in sb:
            break

    n_ticks = len(statuses)
    total_budget = alice.coherence_budget + bob.coherence_budget
    total_tension = alice.tension_energy + bob.tension_energy
    peak_tension = max(alice.tension_peak, bob.tension_peak)
    topo_dist = alice.topological_distance(bob)

    # Break-even: NY-London is ~5,570 km
    breakeven = share_vs_send_breakeven(
        distance_km=5570,
        data_bits=1024,
        tension_per_tick=total_tension / max(n_ticks, 1),
        ticks_needed=n_ticks,
    )

    return {
        "handshake": "pilot_tone",
        "locked": locked,
        "shared_ell": 2,
        "message_delivered": msg is not None,
        "ticks_before_repair": n_ticks,
        "total_M0_coherence": round(total_budget, 6),
        "M0_per_tick": round(total_budget / max(n_ticks, 1), 6),
        "total_tension_energy": round(total_tension, 6),
        "tension_per_tick": round(total_tension / max(n_ticks, 1), 6),
        "peak_tension": round(peak_tension, 6),
        "topological_distance": round(topo_dist, 6) if topo_dist != float('inf') else "inf",
        "breakeven_5570km": breakeven,
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
