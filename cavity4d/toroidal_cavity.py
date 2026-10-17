"""Toroidal wave cavity: periodic boundary wrapping (no edges).

Rewrites the wave software for toroidal topology per 2026-10-17 insight:
our 4D projection rides a toroidal host manifold. The simulation grid
should too.

Key changes from flat/lumped models:
- NO hard walls, NO edge damping hacks
- Periodic wrapping: psi[0,:] connects to psi[-1,:] seamlessly
- Laplacian uses np.roll (toroidal neighbors)
- Wave energy circulates continuously, no wall scattering
- Phase interference forms sustained standing-wave rings

This is the software mirror of the toroidal host geometry.
"""

import numpy as np
import json


class ToroidalCavity:
    """2D wave field on a toroidal grid (donut topology)."""

    def __init__(self, nx=64, ny=64, seed=42):
        np.random.seed(seed)
        self.nx = nx
        self.ny = ny
        self.psi = (np.random.randn(nx, ny) +
                    1j * np.random.randn(nx, ny)) * 0.1

        # Toroidal parameters
        self.H = 0.002          # expansion rate (Hubble analog)
        self.pump_rate = 0.02   # energy in
        self.loss_rate = 0.05   # energy out (net excreting)
        self.nl_strength = 0.1  # nonlinear saturation

        # Subharmonic + Kerr (from v3)
        self.subharmonic_on = True
        self.subharmonic_freq = 0.5
        self.subharmonic_amp = 0.03
        self.kerr_on = True
        self.kerr_coeff = 0.02

        self.tick_count = 0
        self.energy_in_total = 0.0
        self.energy_out_total = 0.0

    def laplacian_toroidal(self, f):
        """Discrete Laplacian with PERIODIC boundaries (torus).

        Uses np.roll for seamless wrapping. No edges exist.
        """
        return (np.roll(f, 1, axis=0) + np.roll(f, -1, axis=0) +
                np.roll(f, 1, axis=1) + np.roll(f, -1, axis=1) -
                4 * f)

    def tick(self, dt=0.05):
        """Evolve on toroidal grid."""
        self.tick_count += 1
        t = self.tick_count * dt

        # Cosmological redshift (expanding torus)
        a = 1.0 + self.H * self.tick_count
        redshift = 1.0 / (a ** 2)

        # Kerr-modified Laplacian
        if self.kerr_on:
            kerr_factor = 1.0 + self.kerr_coeff * np.abs(self.psi)**2
            lap = self.laplacian_toroidal(self.psi) * redshift * kerr_factor
        else:
            lap = self.laplacian_toroidal(self.psi) * redshift

        # Nonlinear saturation
        nl = -self.nl_strength * np.abs(self.psi)**2 * self.psi

        # Subharmonic global drive
        sub = 0
        if self.subharmonic_on:
            sub = self.subharmonic_amp * np.exp(1j * self.subharmonic_freq * t)

        # Energy throughput (distributed, not just at edges —
        # on a torus there ARE no edges, pump is volumetric)
        pump = self.pump_rate * np.exp(1j * np.angle(np.mean(self.psi)))
        pump_field = pump * np.ones_like(self.psi) * 0.1  # gentle volumetric
        self.energy_in_total += np.sum(np.abs(pump_field)) * dt

        # Dissipation
        loss = -self.loss_rate * self.psi
        self.energy_out_total += np.sum(np.abs(loss)) * dt

        # Wave front collisions at energy extremes
        intensity = np.abs(self.psi)**2
        imax = np.max(intensity)
        bump = 0
        if imax > 0:
            extreme = intensity > 0.8 * imax
            bump = -0.05j * extreme * self.psi * intensity

        # Evolve — NO boundary enforcement needed (torus has no boundary)
        self.psi += dt * (1j * lap + nl + pump_field + loss + bump + sub)

    def winding_number(self):
        """Measure dominant topological winding number.

        Computes phase winding around toroidal loops.
        Returns the ℓ mode with maximum spectral power.
        """
        # Phase gradient around x-loop (toroidal direction)
        phase = np.angle(self.psi)
        # Unwrap and compute net winding
        dphase_x = np.diff(phase, axis=0)
        # Wrap to [-pi, pi]
        dphase_x = (dphase_x + np.pi) % (2 * np.pi) - np.pi
        winding_x = np.sum(dphase_x, axis=0) / (2 * np.pi)

        # Dominant integer winding
        hist, bins = np.histogram(winding_x, bins=20, range=(-5, 5))
        peak_bin = np.argmax(hist)
        ell_est = int(round((bins[peak_bin] + bins[peak_bin+1]) / 2))
        return ell_est, float(np.max(hist) / np.sum(hist))

    def circulation_energy(self):
        """Energy in circulating modes vs total."""
        return float(np.sum(np.abs(self.psi)**2))

    def ledger(self):
        return {
            "E_in": float(self.energy_in_total),
            "E_out": float(self.energy_out_total),
            "balance": float(self.energy_in_total - self.energy_out_total),
            "field_energy": self.circulation_energy(),
            "ticks": self.tick_count,
        }


def run_toroidal(n_ticks=1000):
    """Run toroidal cavity, measure mode selection and ledger."""
    cav = ToroidalCavity(nx=64, ny=64, seed=42)

    ell_history = []
    for t in range(n_ticks):
        cav.tick()
        if t % 50 == 0:
            ell, conf = cav.winding_number()
            ell_history.append((t, ell, round(conf, 3)))

    final_ell, final_conf = cav.winding_number()
    ledger = cav.ledger()

    return {
        "topology": "toroidal (periodic boundaries, no edges)",
        "n_ticks": n_ticks,
        "final_dominant_ell": final_ell,
        "confidence": round(final_conf, 3),
        "ell_history": ell_history[-5:],
        "ledger": {k: round(v, 4) if isinstance(v, float) else v
                   for k, v in ledger.items()},
        "interpretation": (
            f"Toroidal cavity settles to |ℓ|={abs(final_ell)} "
            f"(confidence {final_conf:.1%}). "
            f"{'Matches predicted ℓ=2 quadrupole dominance. '
              'Toroidal host geometry confirmed in software.'
              if abs(final_ell) == 2 else
              'Mode differs from predicted ℓ=2 — investigate.'}"
        ),
    }


def main():
    print("=== Toroidal Wave Cavity ===", flush=True)
    print("Periodic boundaries. No edges. No walls.\n", flush=True)
    result = run_toroidal()
    print(json.dumps(result, indent=2), flush=True)
    print("\nDone", flush=True)


if __name__ == "__main__":
    main()
