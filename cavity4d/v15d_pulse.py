"""v15d: Carrier speed via pulse tracking (Gemini's prescription).

Breaks the standing-wave problem:
- Open/absorbing boundaries (damping layer at outer edge).
- Clean l=2 Gaussian pulse injected at inner radius.
- Track peak radial position x_max(t) over ticks.
- v_carrier = slope of x_max vs t.

Also tests Zak's burn-vs-bury: the pulse is a wave-packet (data).
If it reaches the far end: available (geometry permits).
If absorbed: burned (energy to reservoir, wave destroyed).
"""
import json
import numpy as np
import cavity4d as C


def main():
    np.random.seed(44)
    NR, NPHI, NZ = C.NR, C.NPHI, C.NZ
    rho = np.linspace(0.3, 3.0, NR)
    phi = np.linspace(0, 2*np.pi, NPHI, endpoint=False)
    DR = rho[1] - rho[0]

    # Clean background: near-zero field (no standing waves to confuse)
    psi = np.zeros((NR, NPHI, NZ), dtype=complex)

    # Inject l=2 Gaussian pulse at rho=0.6
    r0 = 0.6
    sigma_r = 0.15
    amp = 1.0
    ell = 2
    iz = NZ // 2
    RHO3, PHI3, Z3 = np.meshgrid(rho, phi, [0], indexing='ij')
    RHO3 = RHO3[:, :, 0]
    PHI3 = PHI3[:, :, 0]
    pulse = amp * np.exp(-0.5*((RHO3 - r0)/sigma_r)**2) * np.exp(1j*ell*PHI3)
    # Localize in z as well (Gaussian around midplane)
    z = np.linspace(-1, 1, NZ)
    z_prof = np.exp(-0.5*(z/0.3)**2)
    for k in range(NZ):
        psi[:, :, k] = pulse * z_prof[k]

    # Absorbing boundary mask: 1.0 interior, smooth ramp to 0 at outer edge
    # Last 12 radial points are the damping layer
    absorb = np.ones(NR)
    n_damp = 12
    for i in range(n_damp):
        idx = NR - n_damp + i
        # Smooth cosine ramp: 1.0 -> 0.0
        absorb[idx] = 0.5 * (1 + np.cos(np.pi * (i+1) / (n_damp+1)))
    absorb_mask = absorb[:, None, None]

    # Track peak over 40 steps
    dt = 0.5
    N_steps = 40
    peaks = []
    energies = []
    for step in range(N_steps):
        # Single propagate step (no gain, no loss except absorbing boundary)
        psi = C.propagate(psi, dt, 1, gain_G=0.0)
        # Apply absorbing boundary
        psi = psi * absorb_mask
        # Find peak radial position (max |psi| at midplane, summed over phi)
        prof = np.abs(psi[:, :, iz]).mean(axis=1)  # radial profile
        # Only consider interior (before damping layer)
        prof_interior = prof[:NR-n_damp]
        i_peak = int(np.argmax(prof_interior))
        peaks.append(float(rho[i_peak]))
        energies.append(float(np.sum(np.abs(psi)**2)))

    peaks = np.array(peaks)
    times = np.arange(N_steps) * dt

    # Fit slope to the linear region (exclude early transient and late absorption)
    # Use middle 50% of steps
    i0, i1 = N_steps//4, 3*N_steps//4
    if i1 > i0 + 2:
        slope, intercept = np.polyfit(times[i0:i1], peaks[i0:i1], 1)
    else:
        slope = 0.0

    # Did the pulse survive? (burn vs bury)
    E_initial = energies[0]
    E_final = energies[-1]
    survival = E_final / E_initial if E_initial > 0 else 0

    print(json.dumps({
        "v_carrier_units_per_time": round(float(slope), 6),
        "v_carrier_km_s": round(float(slope) * 3704, 1),
        "peak_start": round(float(peaks[0]), 3),
        "peak_end": round(float(peaks[-1]), 3),
        "E_survival": round(float(survival), 4),
        "pulse_burned": bool(survival < 0.1),
        "n_steps": N_steps,
        "dt": dt,
    }), flush=True)
    print("V15d done", flush=True)


if __name__ == "__main__":
    main()
