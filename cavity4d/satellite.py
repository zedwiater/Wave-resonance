"""v5: Virtual Satellite Array — non-invasive telemetry for the cavity.

The satellite analogy: you cannot understand a macro-system with local
work (chopping wood) alongside galactic-scale sinks by staring at a
single coordinate grid. A satellite array orbiting above the cavity logs
the aggregate state without collapsing the wavefunctions it measures.

Probes are READ-ONLY. They never modify psi, the ledger, or bodies.
The telemetry stream IS the system hum — the background carrier that
exposes RAM bit cycles as steady precession, well-depth sums, and the
M_0 global budget.

M_0 (Weight of the Universe):
    M_0(t) = E_field(t) + M_condensed(t) + E_trail(t)
Sinks and amplifiers are TRANSFERS within M_0 (field<->condensed), not
sources. The propagator pump adds energy; gamma_univ + trail decay
remove it (deterioration). The satellite verifies M_0 stays bounded and
that transfers balance: every unit the amplifiers inject must have been
condensed by a sink first.
"""
import json
import numpy as np

import cavity4d as C


class SatelliteArray:
    """A constellation of non-invasive probes. sample() reads the system;
    it must never mutate it."""

    def __init__(self, n_probes=6):
        # probe points: fixed phase-space positions (rho, phi, z)
        rng = np.random.default_rng(7)
        self.probes = [(float(rng.uniform(0.5, 4.0)),
                        float(rng.uniform(0, 2 * np.pi)),
                        float(rng.uniform(-4.0, 4.0)))
                       for _ in range(n_probes)]
        self.stream = []
        self.M0_0 = None

    def _probe_field(self, psi, x):
        # nearest-grid sample (non-invasive read)
        ir = int(np.clip(round(x[0] / C.DR - 0.5), 0, C.NR - 1))
        ip = int((x[1] % (2 * np.pi)) / (2 * np.pi) * C.NPHI) % C.NPHI
        iz = int(np.clip(round((x[2] + C.LZ / 2) / C.DZ), 0, C.NZ - 1))
        v = psi[ir, ip, iz]
        return {"amp": float(abs(v)), "phase": float(np.angle(v))}

    def sample(self, tick, system):
        """Read-only snapshot of the aggregate state."""
        psi = system.psi
        E_field = float(C.energy(psi))
        M_cond = float(system.ledger["condensed_mass"])
        # v8 M_0 = field + condensed + reservoir. EXACTLY conserved:
        # pump draws from reservoir, dissipation credits it,
        # sinks/stars/hawking move field↔condensed (neutral).
        # The trail is information, not energy (excluded).
        E_res = float(system.ledger.get("E_reservoir", 0.0))
        M_0 = E_field + M_cond + E_res
        E_trail = float(system.trails.mass())  # diagnostic only
        if self.M0_0 is None:
            self.M0_0 = M_0

        s = C.oam_spectrum(psi)
        # phase coherence: |<exp(i*arg psi)>| weighted by |psi| — the hum's
        # coherence. 1 = perfectly coherent, 0 = random phases.
        mag = np.abs(psi)
        coh = float(abs(np.sum(mag * np.exp(1j * np.angle(psi)))
                        / (np.sum(mag) + 1e-300)))

        Phi = system.total_phi()
        rec = {
            "tick": tick,
            "E_field": round(E_field, 4),
            "M_condensed": round(M_cond, 4),
            "E_trail": round(E_trail, 4),
            "M_0": round(M_0, 4),
            "M_0_drift": round(M_0 - self.M0_0, 4),
            "well_min": round(float(Phi.min()), 5),
            "well_sum": round(float(Phi[Phi < 0].sum()), 4),
            "dominant_ell": int(C.ELLS[int(np.argmax(s))]),
            "share": round(float(s.max()), 4),
            "entropy": round(float(C.spectral_entropy(s)), 4),
            "coherence": round(coh, 4),
            "carrier_drift": round(float(system.carrier.drift()), 6),
            "gain_G": round(float(system.gain_G), 3),
            "dissipated": round(float(system.ledger["dissipated"]), 4),
            "pump_recycled": round(float(system.ledger["pump_in"]), 4),
            "cost_ledger": {k: round(float(v), 4)
                            for k, v in system.cost_ledger.items()},
            "bodies": [{"kind": b.kind, "rho": round(float(b.x[0]), 3),
                        "phi": round(float(b.x[1] % (2 * np.pi)), 3),
                        "mass": round(float(b.mass), 3),
                        "cycles": b.cycles,
                        "hill_r": round(float(getattr(b, "hill_r", 0.0)), 3),
                        "tell": (int(b.target_ell)
                                 if b.target_ell is not None else None)}
                       for b in system.bodies],
            "targeting_events": [list(e) for e in system.targeting_events],
            "proper_time_divergence": (
                max([b.cycles for b in system.bodies] or [0])
                - min([b.cycles for b in system.bodies] or [0])),
            "probes": [self._probe_field(psi, x) for x in self.probes],
        }
        self.stream.append(rec)
        return rec

    def dump_jsonl(self, path):
        with open(path, "w") as f:
            for rec in self.stream:
                f.write(json.dumps(rec) + "\n")

    def M0_report(self):
        """Is the Weight of the Universe bounded?"""
        M0s = np.array([r["M_0"] for r in self.stream])
        return {
            "M0_start": round(float(M0s[0]), 4),
            "M0_end": round(float(M0s[-1]), 4),
            "M0_range": round(float(M0s.max() - M0s.min()), 4),
            "M0_mean": round(float(M0s.mean()), 4),
            "bounded": bool((M0s.max() - M0s.min()) < 0.2 * M0s.mean()),
        }

    def transfer_report(self):
        """Did amplifiers only spend what sinks condensed?"""
        if not self.stream:
            return {}
        last = self.stream[-1]
        return {
            "condensed_total": last["M_condensed"],
            "recycled_total": last["pump_recycled"],
            "pool_remaining": round(last["M_condensed"]
                                    - last["pump_recycled"], 4),
            "recycling_closed": bool(last["pump_recycled"]
                                     <= last["M_condensed"] + 1e-9),
        }
