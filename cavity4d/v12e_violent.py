"""v12e: Violent background — comet strike on ℓ=2 soliton.

The falsifier gate: OFF branch must DIE (ℓ collapses), ON must SURVIVE.
- Density-weighted viscosity (W_floor protects vortex eye).
- Comet aimed through soliton + massive sink nearby (tidal + shock).
- If OFF loses ℓ and ON holds ℓ=2, ablation shield is proven.

Physical picture (Zak): photon/electron as vortex in spacetime.
Tidal front compresses, trailing edge sheds. Topology rides through.
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def inject_vortex(psi, ell=2, amp=0.3, sigma=0.35,
                  rho0=1.8, phi0=1.0, z0=0.0):
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


def run_branch(use_viscosity, n_ticks=100, seed=11):
    np.random.seed(seed)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 30, gain_G=3.0)
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.01,
                          use_viscosity=use_viscosity,
                          visc_nu0=0.02, visc_g_lo=2.0, visc_g_hi=4.0)
    # VIOLENT: massive sink near soliton + comet on strike path
    # Soliton at (1.8, 1.0, 0.0). Sink at (1.6, 1.2, 0.1) mass 15.
    # Comet starts far, velocity aimed through soliton.
    sys.bodies = [
        CO.Body("sink", [1.6, 1.2, 0.1], [0, 0.05, 0], mass=15.0),
        CO.Body("comet", [0.5, 3.5, 0.0], [0.15, -0.25, 0],
                mass=1.0, kappa=0.3),
    ]
    psi_inj, center = inject_vortex(sys.psi, ell=2, amp=0.3)
    sys.psi = psi_inj

    ell_hist = []
    for t in range(n_ticks):
        out = sys.tick(dt_tick=4.0, use_bodies=True)
        if t % 10 == 0:
            ell, share = measure_ell_at(sys.psi, center)
            ell_hist.append({"t": t, "ell": ell,
                             "share": round(share, 3)})
    ell_f, share_f = measure_ell_at(sys.psi, center)
    return {
        "viscosity": use_viscosity,
        "ell_end": ell_f,
        "share_end": round(share_f, 3),
        "ell_held": bool(ell_f == 2),
        "history": ell_hist,
    }


def main():
    print("ON (density-weighted)...", flush=True)
    on = run_branch(use_viscosity=True)
    print(json.dumps(on), flush=True)
    print("OFF...", flush=True)
    off = run_branch(use_viscosity=False)
    print(json.dumps(off), flush=True)
    if on["ell_held"] and not off["ell_held"]:
        v = "PASS — ablation shield proven"
    elif not on["ell_held"] and not off["ell_held"]:
        v = "FAIL — both died (background too violent or soliton too weak)"
    elif on["ell_held"] and off["ell_held"]:
        v = "INCONCLUSIVE — background too gentle"
    else:
        v = "FAIL — viscosity hurt"
    print(json.dumps({"verdict": v}), flush=True)


if __name__ == "__main__":
    main()
