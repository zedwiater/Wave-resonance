"""v12f: Compare viscosity modes in violent background.
- smoothstep (mine): thresholded, eps=0.1
- linear (Gemini): proportional, eps=1e-3
Both with W_floor. Violent: mass-15 sink + comet strike.
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


def run_branch(mode, eps, n_ticks=100, seed=11):
    np.random.seed(seed)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 30, gain_G=3.0)
    use_visc = (mode is not None)
    kw = {} if not use_visc else {
        "use_viscosity": True, "visc_nu0": 0.02,
        "visc_mode": mode, "visc_eps": eps,
        "visc_g_lo": 2.0, "visc_g_hi": 4.0,
    }
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.01, **kw)
    sys.bodies = [
        CO.Body("sink", [1.6, 1.2, 0.1], [0, 0.05, 0], mass=15.0),
        CO.Body("comet", [0.5, 3.5, 0.0], [0.15, -0.25, 0],
                mass=1.0, kappa=0.3),
    ]
    psi_inj, center = inject_vortex(sys.psi, ell=2, amp=0.3)
    sys.psi = psi_inj
    for t in range(n_ticks):
        sys.tick(dt_tick=4.0, use_bodies=True)
    ell_f, share_f = measure_ell_at(sys.psi, center)
    label = "OFF" if mode is None else "%s(eps=%g)" % (mode, eps)
    return {"mode": label, "ell_end": ell_f,
            "held": bool(ell_f == 2), "share": round(share_f, 3)}


def main():
    for mode, eps in [(None, 0), ("smoothstep", 0.1), ("linear", 1e-3),
                      ("linear", 0.1)]:
        r = run_branch(mode, eps)
        print(json.dumps(r), flush=True)
    print("V12F done", flush=True)


if __name__ == "__main__":
    main()
