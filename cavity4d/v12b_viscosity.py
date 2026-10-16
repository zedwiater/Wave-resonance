"""v12b: Viscous ablation, corrected.

Fixes from v12a:
- Soliton is a PROPER vortex: phase = ℓ·atan2(y,x) around its center
  (v12a used |phi-phi0|, which is not a winding).
- ℓ measured via azimuthal FFT on a ring around soliton center.
- Viscosity diagnostics: report gradient magnitudes to tune g_thresh.
"""
import json
import numpy as np


def make_vortex(nr=48, nphi=64, nz=32, ell=2, amp=0.5, sigma=0.35,
                rho0=1.5, phi0=0.0, z0=0.0, noise_amp=0.15, seed=5):
    rng = np.random.default_rng(seed)
    rho = np.linspace(0.3, 3.0, nr)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    z = np.linspace(-1, 1, nz)
    RHO, PHI, Z = np.meshgrid(rho, phi, z, indexing="ij")
    # local Cartesian around center
    dphi_wrapped = (PHI - phi0 + np.pi) % (2 * np.pi) - np.pi
    x = RHO - rho0
    y = dphi_wrapped * rho0
    zz = Z - z0
    r2 = x ** 2 + y ** 2 + zz ** 2
    theta = np.arctan2(y, x)
    psi = amp * np.exp(-r2 / (2 * sigma ** 2)) * np.exp(1j * ell * theta)
    # noise everywhere, stronger in fringe
    fringe = r2 > (1.5 * sigma) ** 2
    nse = (rng.standard_normal(psi.shape) + 1j * rng.standard_normal(psi.shape))
    psi = psi + noise_amp * nse * (0.3 + 0.7 * fringe)
    return psi, (rho0, phi0, z0)


def ring_ell(psi, center, radius=0.35, n_samples=128):
    """Sample psi on a ring around center (in x-y plane), FFT → dominant ℓ."""
    rho0, phi0, z0 = center
    nr, nphi, nz = psi.shape
    rho = np.linspace(0.3, 3.0, nr)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    z = np.linspace(-1, 1, nz)
    # ring in local x-y plane at z=z0
    angs = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
    # local x = r*cos(a), y = r*sin(a) → global rho, phi
    # x = rho - rho0 → rho = rho0 + r*cos(a)
    # y = dphi*rho0 → dphi = r*sin(a)/rho0 → phi = phi0 + that
    rr = radius
    rho_s = rho0 + rr * np.cos(angs)
    phi_s = phi0 + (rr * np.sin(angs)) / rho0
    # z index closest to z0
    iz = int(np.argmin(np.abs(z - z0)))
    # bilinear-ish: nearest neighbor for simplicity
    ir = np.clip(np.searchsorted(rho, rho_s) , 0, nr - 1)
    iph = np.clip(((phi_s % (2 * np.pi)) / (2 * np.pi) * nphi).astype(int),
                  0, nphi - 1)
    vals = psi[ir, iph, iz]
    F = np.fft.fft(vals)
    idx = int(np.argmax(np.abs(F)))
    ell_meas = idx if idx <= n_samples // 2 else idx - n_samples
    share = float(np.abs(F[idx]) / (np.abs(F).sum() + 1e-12))
    return ell_meas, share


def apply_viscosity(psi, nu0=0.05, g_lo=1.0, g_hi=3.0, dt=1.0,
                    verbose=False):
    """Relative-gradient viscosity: targets where |∇ψ|/|ψ| is high
    (noisy fringe, low amplitude + high variation), spares the core
    (high amplitude, smooth). Zero below g_lo, full above g_hi."""
    gr, gp, gz = np.gradient(psi)
    gmag = np.sqrt(np.abs(gr) ** 2 + np.abs(gp) ** 2 + np.abs(gz) ** 2)
    amp = np.abs(psi)
    # relative gradient: high where noise dominates over signal
    grel = gmag / (amp + 1e-6)
    # smoothstep: 0 for grel<g_lo, 1 for grel>g_hi
    t = np.clip((grel - g_lo) / (g_hi - g_lo + 1e-12), 0, 1)
    s = t * t * (3 - 2 * t)
    nu = nu0 * s
    if verbose:
        print(json.dumps({
            "gmag_mean": round(float(gmag.mean()), 4),
            "gmag_max": round(float(gmag.max()), 4),
            "nu_mean": round(float(nu.mean()), 5),
            "nu_max": round(float(nu.max()), 5),
        }), flush=True)
    lap = np.zeros_like(psi)
    for ax in range(3):
        lap += np.roll(psi, -1, axis=ax) - 2 * psi + np.roll(psi, 1, axis=ax)
    return psi + nu * lap * dt


def fringe_grad(psi, center, sigma=0.35):
    """Mean |∇ψ| in fringe (r > 2σ) — should DECREASE with viscosity."""
    rho0, phi0, z0 = center
    nr, nphi, nz = psi.shape
    rho = np.linspace(0.3, 3.0, nr)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    z = np.linspace(-1, 1, nz)
    RHO, PHI, Z = np.meshgrid(rho, phi, z, indexing="ij")
    dphi_wrapped = (PHI - phi0 + np.pi) % (2 * np.pi) - np.pi
    x = RHO - rho0
    y = dphi_wrapped * rho0
    zz = Z - z0
    r = np.sqrt(x ** 2 + y ** 2 + zz ** 2)
    gr, gp, gz = np.gradient(psi)
    gmag = np.sqrt(np.abs(gr)**2 + np.abs(gp)**2 + np.abs(gz)**2)
    return float(gmag[r > 2*sigma].mean())


def main():
    psi, center = make_vortex(ell=2, amp=0.5, noise_amp=0.15)
    ell0, share0 = ring_ell(psi, center)
    fg0 = fringe_grad(psi, center)
    # core amplitude
    rho0, phi0, z0 = center
    nr, nphi, nz = psi.shape
    rho = np.linspace(0.3, 3.0, nr)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    z = np.linspace(-1, 1, nz)
    RHO, PHI, Z = np.meshgrid(rho, phi, z, indexing="ij")
    dphi_wrapped = (PHI - phi0 + np.pi) % (2 * np.pi) - np.pi
    x = RHO - rho0; y = dphi_wrapped * rho0; zz = Z - z0
    r = np.sqrt(x**2 + y**2 + zz**2)
    core0 = float(np.abs(psi[r < 0.35]).mean())
    print(json.dumps({
        "ell_start": ell0, "share_start": round(share0, 3),
        "fringe_grad_start": round(fg0, 4),
        "core_amp_start": round(core0, 4),
    }), flush=True)

    for i in range(30):
        psi = apply_viscosity(psi, nu0=0.05, g_lo=1.0, g_hi=3.0, dt=1.0,
                              verbose=(i == 0))

    ell1, share1 = ring_ell(psi, center)
    fg1 = fringe_grad(psi, center)
    core1 = float(np.abs(psi[r < 0.35]).mean())
    print(json.dumps({
        "ell_end": ell1, "share_end": round(share1, 3),
        "fringe_grad_end": round(fg1, 4),
        "core_amp_end": round(core1, 4),
        "grad_reduction": round(fg0 / (fg1 + 1e-12), 2),
        "core_preserved": round(core1 / (core0 + 1e-12), 3),
        "ell_preserved": bool(ell1 == ell0 == 2),
    }), flush=True)
    print("V12B done", flush=True)


if __name__ == "__main__":
    main()
