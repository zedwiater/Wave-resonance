"""Entanglement emergence in EXPANDING wave cavity with transduction.

Zak's correction: the first version had fixed boundaries and no energy flow.
A real open resonator has:
  1. Expanding cavity (like cosmic expansion — the garden hose swells)
  2. Energy injection at boundaries (transduction IN from Planck scale)
  3. Energy dissipation (transduction OUT / excretion)
  4. Wave fronts bumping at energy extremes

This version includes all four. Tests whether non-local correlations
emerge in an open, expanding, driven-dissipative wave medium.
"""

import numpy as np
import json


class ExpandingCavity:
    """Wave cavity with expanding boundaries and energy throughput."""

    def __init__(self, nx=64, ny=64, seed=42):
        np.random.seed(seed)
        self.nx_base = nx
        self.ny_base = ny
        self.nx = nx
        self.ny = ny

        # Complex wave field
        self.psi = (np.random.randn(nx, ny) +
                    1j * np.random.randn(nx, ny)) * 0.1

        # Expansion rate (fractional growth per tick)
        # Analogous to Hubble parameter: H = (1/a)(da/dt)
        self.H = 0.002

        # Energy injection rate (transduction IN at boundaries)
        self.pump_rate = 0.02

        # Energy dissipation rate (transduction OUT / excretion)
        # Must exceed pump to prevent blowup (open system, net outflow)
        self.loss_rate = 0.05

        # Nonlinear saturation strength (prevents runaway)
        self.nl_strength = 0.1

        # SUBHARMONIC DRIVE (v3): global phase anchor
        # Periodic modulation at omega/2 spanning entire grid
        # Acts as collective mode clock — forces macroscopic phase lock
        self.subharmonic_on = False
        self.subharmonic_freq = 0.5  # omega/2
        self.subharmonic_amp = 0.03

        # KERR NONLINEARITY (v3): local amplitude modifies propagation velocity
        # n = n0 + n2*|psi|^2 — refractive index depends on energy density
        self.kerr_on = False
        self.kerr_coeff = 0.02

        # Partition for A/B regions (middle)
        self.px = nx // 2
        self.buffer = 4

        self.tick_count = 0
        self.energy_in_total = 0.0
        self.energy_out_total = 0.0

    def laplacian(self, f):
        lf = np.zeros_like(f)
        lf[1:-1, 1:-1] = (f[2:, 1:-1] + f[:-2, 1:-1] +
                          f[1:-1, 2:] + f[1:-1, :-2] -
                          4 * f[1:-1, 1:-1])
        return lf

    def expand_cavity(self):
        """Grow the cavity (garden hose swells but still flows).

        We don't actually resize the array (expensive). Instead, we
        scale the effective coordinates: the wave number k decreases
        as the cavity grows, mimicking cosmological redshift.
        """
        # Effective scale factor
        a = 1.0 + self.H * self.tick_count
        # Redshift the Laplacian (longer wavelengths as space expands)
        return 1.0 / (a ** 2)

    def tick(self, dt=0.05, shared_boundaries=True):
        """Evolve with expansion, pump, loss, subharmonic drive, and Kerr."""
        self.tick_count += 1
        t = self.tick_count * dt

        # Expansion factor (redshifts the wave operator)
        redshift = self.expand_cavity()

        # KERR: local propagation velocity depends on amplitude
        # Effective Laplacian scaled by (1 + kerr*|psi|^2)
        if self.kerr_on:
            kerr_factor = 1.0 + self.kerr_coeff * np.abs(self.psi)**2
            lap = self.laplacian(self.psi) * redshift * kerr_factor
        else:
            lap = self.laplacian(self.psi) * redshift

        # Nonlinear saturation
        nl = -self.nl_strength * np.abs(self.psi)**2 * self.psi

        # SUBHARMONIC DRIVE: global phase anchor at omega/2
        # Spans entire grid simultaneously — the collective clock
        sub = 0
        if self.subharmonic_on:
            sub_phase = self.subharmonic_freq * t
            sub = self.subharmonic_amp * np.exp(1j * sub_phase) * np.ones_like(self.psi)

        # ENERGY IN: pump at boundaries (Planck-scale transduction)
        # Inject coherent wavefronts at edges
        pump = np.zeros_like(self.psi)
        pump_phase = np.angle(np.mean(self.psi)) if shared_boundaries else 0
        pump[0, :] = self.pump_rate * np.exp(1j * pump_phase)
        pump[-1, :] = self.pump_rate * np.exp(1j * pump_phase)
        pump[:, 0] = self.pump_rate * np.exp(1j * pump_phase)
        pump[:, -1] = self.pump_rate * np.exp(1j * pump_phase)
        self.energy_in_total += np.sum(np.abs(pump)) * dt

        # ENERGY OUT: uniform dissipation (excretion)
        loss = -self.loss_rate * self.psi
        self.energy_out_total += np.sum(np.abs(loss)) * dt

        # Wave fronts bumping at energy extremes:
        # where |psi| is large, add extra nonlinear mixing
        # (simulates wave tails colliding at high-energy boundaries)
        intensity = np.abs(self.psi)**2
        imax = np.max(intensity)
        if imax > 0:
            extreme_mask = intensity > 0.8 * imax
            bump = -0.05j * extreme_mask * self.psi * intensity
        else:
            bump = 0

        # Evolve (now including subharmonic drive)
        self.psi += dt * (1j * lap + nl + pump + loss + bump + sub)

        # Boundary conditions
        if shared_boundaries:
            # Shared global phase (treatment)
            bp = np.angle(np.mean(self.psi))
            for edge in [0, -1]:
                amp = np.abs(self.psi[edge, :])
                self.psi[edge, :] = amp * np.exp(1j * bp)
                amp_c = np.abs(self.psi[:, edge])
                self.psi[:, edge] = amp_c * np.exp(1j * bp)
        # else: free boundaries (control) — no phase enforcement

    def phase_correlation_AB(self):
        """Non-local correlation between separated regions A and B."""
        int_A = np.zeros((self.nx, self.ny), dtype=bool)
        int_B = np.zeros((self.nx, self.ny), dtype=bool)
        int_A[:self.px - self.buffer, 2:-2] = True
        int_B[self.px + self.buffer:, 2:-2] = True

        psi_A = self.psi[int_A]
        psi_B = self.psi[int_B]
        if len(psi_A) == 0 or len(psi_B) == 0:
            return 0.0

        n = min(len(psi_A), len(psi_B))
        dphi = np.angle(psi_A[:n]) - np.angle(psi_B[:n])
        return float(np.abs(np.mean(np.exp(1j * dphi))))

    def energy_ledger(self):
        """M_0 ledger at cosmic scale: E_in - E_out = ΔE."""
        return {
            "E_in": float(self.energy_in_total),
            "E_out": float(self.energy_out_total),
            "balance": float(self.energy_in_total - self.energy_out_total),
            "field_energy": float(np.sum(np.abs(self.psi)**2)),
        }


def run_experiment(n_ticks=800, subharmonic=False, kerr=False):
    """Run with optional subharmonic drive and Kerr nonlinearity (v3)."""
    # Treatment: expanding + shared boundaries + optional subharmonic/Kerr
    cav_s = ExpandingCavity(seed=42)
    cav_s.subharmonic_on = subharmonic
    cav_s.kerr_on = kerr
    Cs, Es = [], []
    for t in range(n_ticks):
        cav_s.tick(shared_boundaries=True)
        if t % 20 == 0:
            Cs.append(cav_s.phase_correlation_AB())
            Es.append(cav_s.energy_ledger())

    # Control: expanding + free boundaries + same drive settings
    cav_f = ExpandingCavity(seed=42)
    cav_f.subharmonic_on = subharmonic
    cav_f.kerr_on = kerr
    Cf, Ef = [], []
    for t in range(n_ticks):
        cav_f.tick(shared_boundaries=False)
        if t % 20 == 0:
            Cf.append(cav_f.phase_correlation_AB())
            Ef.append(cav_f.energy_ledger())

    n_avg = len(Cs) // 4
    Cs_f = float(np.mean(Cs[-n_avg:]))
    Cf_f = float(np.mean(Cf[-n_avg:]))

    ledger_s = Es[-1]
    ledger_f = Ef[-1]

    emergence = Cs_f - Cf_f

    return {
        "n_ticks": n_ticks,
        "model": "expanding cavity + transduction (pump + loss)",
        "subharmonic": subharmonic,
        "kerr": kerr,
        "C_shared_expanding": round(Cs_f, 4),
        "C_free_expanding": round(Cf_f, 4),
        "emergence_delta": round(float(emergence), 4),
        "ledger_shared": {k: round(v, 4) for k, v in ledger_s.items()},
        "ledger_free": {k: round(v, 4) for k, v in ledger_f.items()},
        "verdict": (
            "EMERGENCE DETECTED" if emergence > 0.2 else
            "WEAK SIGNAL" if emergence > 0.05 else
            "NO EMERGENCE"
        ),
    }


def main():
    print("=== Entanglement Emergence v3: Subharmonic + Kerr ===", flush=True)

    configs = [
        (False, False, "baseline (no subharmonic, no Kerr)"),
        (True, False, "subharmonic drive only"),
        (False, True, "Kerr nonlinearity only"),
        (True, True, "subharmonic + Kerr (full)"),
    ]

    results = []
    for sub, kerr, label in configs:
        print(f"\n--- {label} ---", flush=True)
        r = run_experiment(n_ticks=800, subharmonic=sub, kerr=kerr)
        r["config"] = label
        results.append(r)
        print(f"  C_shared={r['C_shared_expanding']}, "
              f"C_free={r['C_free_expanding']}, "
              f"delta={r['emergence_delta']}, "
              f"verdict={r['verdict']}", flush=True)

    print("\n=== Summary ===", flush=True)
    print(json.dumps(results, indent=2), flush=True)
    print("\nDone", flush=True)


if __name__ == "__main__":
    main()
