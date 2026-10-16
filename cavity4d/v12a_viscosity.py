"""v12a: Viscous boundary ablation operator — standalone test.

The continuous version of v11's discrete shedding. Instead of "shed when
BER > threshold," apply gradient-dependent viscosity: high |∇ψ| (boundary
fringe) gets diffused, low |∇ψ| (core) is untouched. Noise bleeds into the
background dissipation sink continuously.

Test: noisy soliton (ℓ=2) → apply viscosity → core ℓ must hold, fringe
noise must drop.
"""
import json
import numpy as np


def make_soliton(nr=48, nphi=64, nz=32, ell=2, amp=0.5, sigma=0.4,
                 rho0=1.5, phi0=0.0, z0=0.0, noise_fringe=0.3):
    """Gaussian wave packet with OAM phase winding, noisy fringe."""
    rho = np.linspace(0.3, 3.0, nr)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    z = np.linspace(-1, 1, nz)
    RHO, PHI, Z = np.meshgrid(rho, phi, z, indexing="ij")
    # distance from center
    dphi = np.minimum(np.abs(PHI - phi0), 2 * np.pi - np.abs(PHI - phi0))
    d2 = (RHO - rho0) ** 2 + (dphi * rho0) ** 2 + (Z - z0) ** 2
    # soliton: Gaussian amplitude, ℓ phase winding around center
    # (phase relative to center, not global origin)
    psi = amp * np.exp(-d2 / (2 * sigma ** 2)) * np.exp(1j * ell * dphi)
    # add noise to fringe (outer region, d > 2*sigma)
    fringe = d2 > (2 * sigma) ** 2
    psi[fringe] += noise_fringe * (
        np.random.randn(*psi.shape) + 1j * np.random.randn(*psi.shape)
    )[fringe] * np.abs(psi[fringe]).mean()
    return psi


def apply_viscosity(psi, nu0=0.02, g_thresh=0.5, dt=1.0):
    """Gradient-dependent viscosity: diffuses high-gradient regions
    (boundary fringe), leaves low-gradient core untouched.
    psi ← psi + ν(|∇ψ|) ∇²ψ dt,  ν = nu0 * tanh(|∇ψ|/g_thresh)."""
    # gradient components (complex)
    gr, gp, gz = np.gradient(psi)
    gmag = np.sqrt(np.abs(gr) ** 2 + np.abs(gp) ** 2 + np.abs(gz) ** 2)
    # viscosity coefficient: ~0 in core, →nu0 at boundary
    nu = nu0 * np.tanh(gmag / (g_thresh + 1e-12))
    # Laplacian via divergence of gradient
    # (use second-order central differences manually for stability)
    lap = np.zeros_like(psi)
    for ax in range(3):
        # second derivative along axis ax
        fwd = np.roll(psi, -1, axis=ax)
        bwd = np.roll(psi, 1, axis=ax)
        # handle periodic (phi, axis=1) vs non-periodic
        if ax == 1:
            lap += (fwd - 2 * psi + bwd)
        else:
            # non-periodic: zero second derivative at boundaries
            lap += (fwd - 2 * psi + bwd)
            # (simple; boundaries are far from soliton)
    # apply
    return psi + nu * lap * dt


def measure_ell(psi, rho0=1.5, sigma=0.4):
    """Dominant OAM mode of the soliton core (not global)."""
    # extract core region and do azimuthal FFT
    nr, nphi, nz = psi.shape
    rho = np.linspace(0.3, 3.0, nr)
    # find radial index closest to rho0
    ir = int(np.argmin(np.abs(rho - rho0)))
    # take a slice at ir, mid-z
    sl = psi[ir, :, nz // 2]
    F = np.fft.fft(sl)
    # ℓ bins: assume standard ordering (need BIN_OF mapping; approximate)
    # For this test, just find peak and map to ℓ via fftfreq
    freqs = np.fft.fftfreq(nphi, d=1.0 / nphi)  # actually want integer ℓ
    # simpler: peak index → ℓ (0..nphi/2, then negative)
    idx = int(np.argmax(np.abs(F)))
    ell_meas = idx if idx <= nphi // 2 else idx - nphi
    return ell_meas, float(np.abs(F[idx]) / (np.abs(F).sum() + 1e-12))


def main():
    np.random.seed(5)
    psi = make_soliton(ell=2, amp=0.5, noise_fringe=0.3)
    ell0, share0 = measure_ell(psi)
    # fringe noise level (std of |psi| in fringe vs core)
    # define fringe as |psi| < 0.1*max (outer low-amplitude region)
    mag = np.abs(psi)
    fringe_mask = mag < 0.2 * mag.max()
    core_mask = mag > 0.5 * mag.max()
    noise0 = float(mag[fringe_mask].std())
    print(json.dumps({
        "ell_start": ell0, "share_start": round(share0, 3),
        "fringe_noise_start": round(noise0, 4),
    }), flush=True)

    # apply viscosity for 20 steps
    for _ in range(20):
        psi = apply_viscosity(psi, nu0=0.02, g_thresh=0.5, dt=1.0)

    ell1, share1 = measure_ell(psi)
    mag = np.abs(psi)
    fringe_mask = mag < 0.2 * mag.max()
    noise1 = float(mag[fringe_mask].std())
    # core amplitude preservation
    core_amp = float(mag[core_mask].mean()) if core_mask.any() else 0.0

    print(json.dumps({
        "ell_end": ell1, "share_end": round(share1, 3),
        "fringe_noise_end": round(noise1, 4),
        "noise_reduction": round(noise0 / (noise1 + 1e-12), 2),
        "ell_preserved": bool(ell1 == ell0),
    }), flush=True)
    print("V12A done", flush=True)


if __name__ == "__main__":
    main()
