"""v12c: Planetary trajectory — ℓ=2 soliton through sink turbulence.

Falsifier: inject weak vortex soliton (ℓ=2) into turbulent cavity with
active sinks. Run with viscosity ON vs OFF. If boundary ablation works:
- ℓ stays 2 (viscosity ON), even as sinks scatter the fringe.
- ℓ degrades or flips (viscosity OFF), noise penetrates the core.

The soliton is a planet; sinks are stars; viscosity is the atmosphere
ablating on re-entry.
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def inject_vortex(psi, ell=2, amp=0.15, sigma=0.35,
                  rho0=1.8, phi0=1.0, z0=0.0):
    """Add a weak vortex soliton to existing psi (does not replace)."""
    rho = np.linspace(0.3, 3.0, C.NR)
    phi = np.linspace(0, 2 * np.pi, C.NPHI, endpoint=False)
    z = np.linspace(-1, 1, C.NZ)
    RHO, PHI, Z = np.meshgrid(rho, phi, z, indexing="ij")
    dphi = (PHI - phi0 + np.pi) % (2 * np.pi) - np.pi
    x = RHO - rho0
    y = dphi * rho0
    zz = Z - z0
    r2 = x ** 2 + y ** 2 + zz ** 2
    theta = np.arctan2(y, x)
    vortex = amp * np.exp(-r2 / (2 * sigma ** 2)) * np.exp(1j * ell * theta)
    return psi + vortex, (rho0, phi0, z0)


def measure_ell_at(psi, center, radius=0.35, n_samples=64):
    """Dominant ℓ on a ring around center."""
    rho0, phi0, z0 = center
    rho = np.linspace(0.3, 3.0, C.NR)
    phi = np.linspace(0, 2 * np.pi, C.NPHI, endpoint=False)
    z = np.linspace(-1, 1, C.NZ)
    angs = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
    rho_s = rho0 + radius * np.cos(angs)
    phi_s = phi0 + (radius * np.sin(angs)) / rho0
    iz = int(np.argmin(np.abs(z - z0)))
    ir = np.clip(np.searchsorted(rho, rho_s), 0, C.NR - 1)
    iph = np.clip(((phi_s % (2 * np.pi)) / (2 * np.pi) * C.NPHI).astype(int),
                  0, C.NPHI - 1)
    vals = psi[ir, iph, iz]
    F = np.fft.fft(vals)
    idx = int(np.argmax(np.abs(F)))
    ell = idx if idx <= n_samples // 2 else idx - n_samples
    share = float(np.abs(F[idx]) / (np.abs(F).sum() + 1e-12))
    return ell, share


def run_branch(use_viscosity, n_ticks=80, seed=7):
    np.random.seed(seed)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 30, gain_G=3.0)  # warmup
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.01,
                          use_viscosity=use_viscosity,
                          visc_nu0=0.05, visc_g_lo=1.0, visc_g_hi=3.0)
    # turbulent background: 2 sinks + 1 amplifier
    sys.bodies = [
        CO.Body("sink", [1.2, 0.5, 0.0], [0, 0.08, 0], mass=3.0),
        CO.Body("sink", [2.2, 2.5, 0.3], [0, -0.06, 0], mass=2.0),
        CO.Body("amplifier", [1.0, 3.0, -0.2], [0, 0.05, 0], mass=1.5),
    ]
    # inject soliton away from sinks
    psi_inj, center = inject_vortex(sys.psi, ell=2, amp=0.15)
    sys.psi = psi_inj

    ell_hist = []
    for t in range(n_ticks):
        # tick handles body gravity + field update + viscosity
        out = sys.tick(dt_tick=4.0, use_bodies=True)
        if t % 10 == 0:
            ell, share = measure_ell_at(sys.psi, center)
            ell_hist.append({"t": t, "ell": ell,
                             "share": round(share, 3)})
    # final
    ell_f, share_f = measure_ell_at(sys.psi, center)
    return {
        "viscosity": use_viscosity,
        "ell_start": 2,
        "ell_end": ell_f,
        "share_end": round(share_f, 3),
        "ell_held": bool(ell_f == 2),
        "history": ell_hist,
    }


def main():
    print("Running viscosity ON...", flush=True)
    on = run_branch(use_viscosity=True)
    print(json.dumps(on), flush=True)
    print("Running viscosity OFF...", flush=True)
    off = run_branch(use_viscosity=False)
    print(json.dumps(off), flush=True)
    print(json.dumps({
        "verdict": "PASS" if (on["ell_held"] and not off["ell_held"])
        else ("PARTIAL" if on["ell_held"] else "FAIL"),
        "note": "viscosity protects ℓ" if on["ell_held"] else
                "ℓ lost even with viscosity",
    }), flush=True)


if __name__ == "__main__":
    main()
