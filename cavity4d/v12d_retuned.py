"""v12d: Retuned viscosity — wave software for this universe.

Fixes from v12c (where viscosity flipped ℓ 2→1):
- nu0: 0.05 → 0.02 (gentler).
- g_lo: 1.0 → 2.0 (fires only on extreme relative gradients).
- Amplitude floor: skip where |ψ| < 0.05 (never eat weak signals).
- Harsher background: 3× sink mass, closer encounters, 150 ticks.
  The OFF branch must actually fail for the test to mean anything.

Three definitions under test:
1. Discrete accumulation: bits → soliton (injection).
2. Macro stabilization: ℓ topology + viscosity ablation.
3. Decay: gamma_univ dissipation + sink scattering.
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def inject_vortex(psi, ell=5, amp=0.25, sigma=0.35,
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
    # also: peak amplitude near center (is soliton still there?)
    ir0 = int(np.argmin(np.abs(rho - rho0)))
    iph0 = int((phi0 % (2 * np.pi)) / (2 * np.pi) * C.NPHI)
    peak = float(np.abs(psi[ir0, iph0, iz]))
    return ell, share, peak


def run_branch(use_viscosity, n_ticks=150, seed=7):
    np.random.seed(seed)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 30, gain_G=3.0)
    # RETUNED viscosity: gentler, higher threshold, amplitude floor
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.01,
                          use_viscosity=use_viscosity,
                          visc_nu0=0.02, visc_g_lo=2.0, visc_g_hi=4.0)
    # HARSHER: massive sinks, close to soliton
    sys.bodies = [
        CO.Body("sink", [1.5, 0.8, 0.0], [0, 0.12, 0], mass=8.0),
        CO.Body("sink", [2.0, 1.8, 0.2], [0, -0.10, 0], mass=6.0),
        CO.Body("sink", [1.2, 2.2, -0.3], [0, 0.09, 0], mass=5.0),
    ]
    # stronger soliton (amp 0.25 vs 0.15) to survive the violence
    psi_inj, center = inject_vortex(sys.psi, ell=5, amp=0.25)
    sys.psi = psi_inj

    ell_hist = []
    for t in range(n_ticks):
        out = sys.tick(dt_tick=4.0, use_bodies=True)
        if t % 15 == 0:
            ell, share, peak = measure_ell_at(sys.psi, center)
            ell_hist.append({"t": t, "ell": ell,
                             "share": round(share, 3),
                             "peak": round(peak, 3)})
    ell_f, share_f, peak_f = measure_ell_at(sys.psi, center)
    return {
        "viscosity": use_viscosity,
        "ell_start": 5,
        "ell_end": ell_f,
        "share_end": round(share_f, 3),
        "peak_end": round(peak_f, 3),
        "ell_held": bool(ell_f == 5),
        "history": ell_hist,
    }


def main():
    print("Viscosity ON (retuned)...", flush=True)
    on = run_branch(use_viscosity=True)
    print(json.dumps(on), flush=True)
    print("Viscosity OFF...", flush=True)
    off = run_branch(use_viscosity=False)
    print(json.dumps(off), flush=True)
    # verdict: ON must hold ℓ where OFF fails
    if on["ell_held"] and not off["ell_held"]:
        v = "PASS"
    elif on["ell_held"] and off["ell_held"]:
        v = "INCONCLUSIVE (background too gentle)"
    elif not on["ell_held"] and not off["ell_held"]:
        v = "FAIL (both lost ℓ)"
    else:
        v = "FAIL (viscosity hurt)"
    print(json.dumps({"verdict": v}), flush=True)


if __name__ == "__main__":
    main()
