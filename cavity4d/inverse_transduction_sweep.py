"""Inverse transduction spectrum sweep: CERN particle masses vs toroidal harmonics.

NOTE (2026-10-17): This script tests the STATIC hypothesis — particle masses
as toroidal eigenvalues. Result was null (p=0.62). The framework has pivoted
to DYNAMIC wave spectrum analysis; see dynamic_spectrum_thesis.md.
This script is retained as an honest null, not deleted.

Hypothesis: if particles are transduced modes of a toroidal host geometry,
their masses should follow toroidal cavity eigenmode relationships,
not random values.

Toroidal eigenmodes: f(m,n) ~ sqrt( (m/R)^2 + (n/r)^2 )
where m = toroidal mode number, n = poloidal mode number,
R = major radius, r = minor radius.

We fit the aspect ratio A = R/r to best explain observed mass ratios
as harmonic relationships, then test against random null hypothesis.

Data: PDG particle masses (MeV/c^2).
"""

import numpy as np
import json

# PDG particle masses in MeV/c^2 (well-established values)
PARTICLES = {
    "electron": 0.51099895,
    "muon": 105.6583755,
    "pion_charged": 139.57039,
    "kaon_charged": 493.677,
    "proton": 938.27208816,
    "neutron": 939.56542052,
    "lambda": 1115.683,
    "j_psi": 3096.900,
    "upsilon": 9460.40,
    "w_boson": 80379,
    "z_boson": 91187.6,
    "higgs": 125100,
}

# Compton frequency in Hz: f = mc^2 / h
# h = 4.135667696e-15 eV·s
H_EV_S = 4.135667696e-15

def compton_freq_hz(mass_mev):
    mass_ev = mass_mev * 1e6
    return mass_ev / H_EV_S


def toroidal_mode_freq(m, n, aspect_ratio):
    """Normalized eigenfrequency for toroidal mode (m,n).

    f ~ sqrt( (m/R)^2 + (n/r)^2 ), normalized to r=1, R=aspect_ratio.
    """
    R = aspect_ratio
    r = 1.0
    return np.sqrt((m / R)**2 + (n / r)**2)


def find_best_mode_assignment(masses, aspect_ratio, max_m=10, max_n=10):
    """Assign each particle mass to the nearest toroidal harmonic.

    Returns total log-error and assignments.
    """
    # Normalize masses to electron mass
    m_e = masses["electron"]
    norm_masses = {k: v / m_e for k, v in masses.items()}

    # Generate all toroidal modes up to max_m, max_n
    modes = []
    for m in range(0, max_m + 1):
        for n in range(0, max_n + 1):
            if m == 0 and n == 0:
                continue
            f = toroidal_mode_freq(m, n, aspect_ratio)
            modes.append((m, n, f))

    # Normalize modes to lowest mode frequency
    modes.sort(key=lambda x: x[2])
    f0 = modes[0][2]
    modes = [(m, n, f / f0) for m, n, f in modes]

    assignments = {}
    total_log_err = 0.0
    for name, mass_ratio in norm_masses.items():
        # Find nearest mode
        best = min(modes, key=lambda x: abs(np.log(x[2]) - np.log(mass_ratio)))
        m, n, f_mode = best
        log_err = abs(np.log(f_mode) - np.log(mass_ratio))
        total_log_err += log_err
        assignments[name] = {
            "mode": (m, n),
            "predicted_ratio": round(f_mode, 4),
            "observed_ratio": round(mass_ratio, 4),
            "log_error": round(log_err, 4),
        }

    return total_log_err, assignments


def sweep_aspect_ratio(masses, a_min=0.5, a_max=10.0, n_steps=50):
    """Sweep toroidal aspect ratio, find best fit."""
    results = []
    for a in np.linspace(a_min, a_max, n_steps):
        err, _ = find_best_mode_assignment(masses, a)
        results.append((a, err))
    results.sort(key=lambda x: x[1])
    return results


def null_test(masses, n_trials=100, seed=42):
    """Random null: shuffle mass values, see if random data fits as well."""
    np.random.seed(seed)
    names = list(masses.keys())
    values = list(masses.values())

    real_err, _ = find_best_mode_assignment(masses, 2.0)  # placeholder

    # Find best aspect ratio for real data first
    sweep = sweep_aspect_ratio(masses)
    best_a_real = sweep[0][0]
    real_err = sweep[0][1]

    null_errors = []
    for _ in range(n_trials):
        shuffled = dict(zip(names, np.random.permutation(values)))
        s = sweep_aspect_ratio(shuffled, n_steps=20)
        null_errors.append(s[0][1])

    null_errors = np.array(null_errors)
    p_value = np.mean(null_errors <= real_err)

    return {
        "real_best_aspect": round(best_a_real, 3),
        "real_error": round(real_err, 4),
        "null_mean_error": round(np.mean(null_errors), 4),
        "null_std_error": round(np.std(null_errors), 4),
        "p_value": round(p_value, 4),
        "n_trials": n_trials,
    }


def main():
    print("=== Inverse Transduction Spectrum Sweep ===", flush=True)
    print("CERN particle masses vs toroidal cavity harmonics\n", flush=True)

    # Show Compton frequencies
    print("Particle Compton frequencies:", flush=True)
    for name, mass in PARTICLES.items():
        f = compton_freq_hz(mass)
        print(f"  {name:15s} {mass:12.3f} MeV  →  {f:.3e} Hz", flush=True)

    print("\nSweeping toroidal aspect ratio R/r...", flush=True)
    sweep = sweep_aspect_ratio(PARTICLES)
    print(f"\nTop 5 aspect ratios:", flush=True)
    for a, err in sweep[:5]:
        print(f"  R/r = {a:.3f}  →  total log-error = {err:.4f}", flush=True)

    best_a = sweep[0][0]
    print(f"\nBest aspect ratio: R/r = {best_a:.3f}", flush=True)

    err, assignments = find_best_mode_assignment(PARTICLES, best_a)
    print("\nMode assignments at best fit:", flush=True)
    for name, info in assignments.items():
        m, n = info["mode"]
        print(f"  {name:15s} → mode ({m},{n})  "
              f"pred={info['predicted_ratio']:.2f}  "
              f"obs={info['observed_ratio']:.2f}  "
              f"err={info['log_error']:.4f}", flush=True)

    print("\nRunning null hypothesis test (100 trials)...", flush=True)
    null_result = null_test(PARTICLES)
    print(json.dumps(null_result, indent=2), flush=True)

    # Interpretation
    p = null_result["p_value"]
    if p < 0.05:
        interp = (f"p={p}: particle masses fit toroidal harmonics significantly "
                  f"better than random. Inverse transduction SURVIVES this test.")
    else:
        interp = (f"p={p}: no significant harmonic structure vs random. "
                  f"Inverse transduction FAILS this test at particle scale.")

    print(f"\n=== VERDICT ===\n{interp}", flush=True)

    output = {
        "hypothesis": "particle masses are toroidal transduction modes",
        "best_aspect_ratio": round(best_a, 3),
        "mode_assignments": assignments,
        "null_test": null_result,
        "verdict": interp,
    }
    print("\n" + json.dumps(output, indent=2)[:2000], flush=True)
    print("\nDone", flush=True)


if __name__ == "__main__":
    main()
