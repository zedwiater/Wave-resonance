"""Generational frequency sweep: lepton family as toroidal harmonic ladder.

Tests whether electron/muon/tau mass ratios fit toroidal cavity mode
transitions, treating generations as higher-order (m,n) modes in the
same confinement topology.

Key insight (Koide): the ratio
    (m_e + m_mu + m_tau) / (sqrt(m_e) + sqrt(m_mu) + sqrt(m_tau))^2 = 2/3
is exact to measurement precision. In wave terms, this is a phase-locked
cavity mode: sqrt(m) ~ field amplitude, m ~ energy density.

We test:
1. Does the Koide ratio hold? (Sanity check on data)
2. Do generational mass ratios match toroidal harmonic ratios?
3. What (m,n) mode assignment gives the observed ladder?
4. What is the "generational frequency" — the harmonic step between generations?
"""

import numpy as np
import json

# Charged lepton masses in MeV/c^2 (PDG 2024)
LEPTONS = {
    "electron": 0.51099895000,
    "muon": 105.6583755,
    "tau": 1776.86,
}

# Also test quark families for comparison
QUARKS_LIGHT = {
    "up": 2.16,      # MSbar at 2 GeV
    "down": 4.67,
    "strange": 93.4,
}

H_EV_S = 4.135667696e-15


def koide_ratio(m1, m2, m3):
    """Compute Koide formula Q value."""
    numerator = m1 + m2 + m3
    denominator = (np.sqrt(m1) + np.sqrt(m2) + np.sqrt(m3)) ** 2
    return numerator / denominator


def toroidal_mode_freq(m, n, aspect_ratio):
    R = aspect_ratio
    return np.sqrt((m / R)**2 + n**2)


def generational_ladder_test(masses, family_name):
    """Test if mass ratios fit toroidal harmonic ladder."""
    names = list(masses.keys())
    values = np.array([masses[k] for k in names])

    # Mass ratios between generations
    ratios = values[1:] / values[:-1]

    # Koide Q
    q = koide_ratio(*values)

    # Try to fit as toroidal modes: find (m,n) for each generation
    # such that frequency ratios match mass ratios
    # Optimized: O(N^2) pair search instead of O(N^3) triple brute force
    best_fit = None
    best_err = float('inf')

    target_r12 = ratios[0]
    target_r23 = ratios[1]
    # Tolerance in log space for pair matching
    tol = 0.5

    for A in np.linspace(0.5, 10, 40):  # aspect ratio sweep
        # Generate modes
        modes = []
        for m in range(0, 15):
            for n in range(0, 15):
                if m == 0 and n == 0:
                    continue
                f = toroidal_mode_freq(m, n, A)
                modes.append(((m, n), f))
        modes.sort(key=lambda x: x[1])
        freqs = np.array([f for _, f in modes])

        # Find pairs matching r12: for each i, find j where f_j/f_i ≈ r12
        log_freqs = np.log(freqs)
        log_r12 = np.log(target_r12)
        log_r23 = np.log(target_r23)

        for i in range(len(modes)):
            # Find j: log(f_j) - log(f_i) ≈ log(r12)
            target_j = log_freqs[i] + log_r12
            # Binary search for closest
            j = np.searchsorted(log_freqs, target_j)
            for jj in [j-1, j, j+1]:
                if jj <= i or jj >= len(modes):
                    continue
                err12 = abs(log_freqs[jj] - log_freqs[i] - log_r12)
                if err12 > tol:
                    continue
                # Find k: log(f_k) - log(f_j) ≈ log(r23)
                target_k = log_freqs[jj] + log_r23
                k = np.searchsorted(log_freqs, target_k)
                for kk in [k-1, k, k+1]:
                    if kk <= jj or kk >= len(modes):
                        continue
                    err23 = abs(log_freqs[kk] - log_freqs[jj] - log_r23)
                    if err23 > tol:
                        continue
                    total_err = err12 + err23
                    if total_err < best_err:
                        best_err = total_err
                        best_fit = {
                            "aspect_ratio": round(A, 3),
                            "modes": [modes[i][0], modes[jj][0], modes[kk][0]],
                            "predicted_ratios": [
                                round(float(np.exp(log_freqs[jj] - log_freqs[i])), 4),
                                round(float(np.exp(log_freqs[kk] - log_freqs[jj])), 4),
                            ],
                            "observed_ratios": [round(target_r12, 4),
                                              round(target_r23, 4)],
                            "log_error": round(float(total_err), 4),
                        }

    return {
        "family": family_name,
        "masses_mev": {k: v for k, v in masses.items()},
        "mass_ratios": [round(r, 4) for r in ratios],
        "koide_Q": round(q, 6),
        "koide_target": 2/3,
        "koide_deviation_ppm": round(abs(q - 2/3) / (2/3) * 1e6, 2),
        "best_toroidal_fit": best_fit,
    }


def coulomb_barrier_modes():
    """Calculate the (m,n) ordered pair for p-p fusion bias.

    The Coulomb barrier for p-p is ~1 MeV. We want the toroidal mode
    whose density antinode spacing matches the de Broglie wavelength
    at tunneling-relevant energies.

    Returns the mode numbers and corresponding RF frequencies for
    a given chamber geometry.
    """
    # p-p Coulomb barrier ~ 0.5-1 MeV
    # Tunneling significant at ~10 keV (thermal) due to Gamow peak
    # de Broglie wavelength at 10 keV for proton:
    # λ = h / sqrt(2*m*E)
    m_p_kg = 1.6726219e-27
    E_joules = 10e3 * 1.602176634e-19  # 10 keV
    h = 6.62607015e-34
    lambda_db = h / np.sqrt(2 * m_p_kg * E_joules)

    # For a chamber of radius r_chamber, the mode number n that gives
    # antinode spacing ~ λ_db:
    # Standing wave: antinode spacing = π * r / n (for poloidal modes)
    # Setting π*r/n = λ_db → n = π*r/λ_db

    results = {}
    for r_cm in [5, 10, 20]:  # chamber radii in cm
        r_m = r_cm / 100
        n_required = np.pi * r_m / lambda_db
        # Corresponding frequency for helicon wave (approximate)
        # f ~ v_A * k / (2π), v_A = Alfven speed
        # For B=500G, n=1e18 m^-3 hydrogen: v_A ~ 1e6 m/s
        v_alfven = 1e6  # m/s, order of magnitude
        k = 2 * np.pi / lambda_db
        f_rf = v_alfven * k / (2 * np.pi)
        results[f"chamber_r_{r_cm}cm"] = {
            "de_broglie_m_at_10keV": f"{lambda_db:.3e}",
            "poloidal_mode_n": int(round(n_required)),
            "rf_frequency_hz": f"{f_rf:.3e}",
            "note": (f"Mode n={int(round(n_required))} gives antinode spacing "
                     f"matching proton de Broglie wavelength at tunneling energy"),
        }

    return {
        "concept": ("Find (m,n) where density antinode spacing = proton "
                    "de Broglie wavelength at Gamow peak energy"),
        "gamow_peak_kev": 10,
        "chamber_scaling": results,
    }


def main():
    print("=== Generational Frequency Sweep ===", flush=True)
    print("Lepton family as toroidal harmonic ladder\n", flush=True)

    # Test lepton family
    lep = generational_ladder_test(LEPTONS, "charged_leptons")
    print(f"Family: {lep['family']}", flush=True)
    print(f"  Masses: {lep['masses_mev']}", flush=True)
    print(f"  Ratios (gen2/gen1, gen3/gen2): {lep['mass_ratios']}", flush=True)
    print(f"  Koide Q = {lep['koide_Q']:.6f}  (target 2/3 = 0.666667)", flush=True)
    print(f"  Deviation: {lep['koide_deviation_ppm']} ppm", flush=True)

    bf = lep["best_toroidal_fit"]
    if bf:
        print(f"\n  Best toroidal fit:", flush=True)
        print(f"    Aspect ratio R/r = {bf['aspect_ratio']}", flush=True)
        print(f"    Modes (e, μ, τ) = {bf['modes']}", flush=True)
        print(f"    Predicted ratios: {bf['predicted_ratios']}", flush=True)
        print(f"    Observed ratios:  {lep['mass_ratios']}", flush=True)
        print(f"    Log error: {bf['log_error']}", flush=True)

    # Test light quarks for comparison
    print(f"\n--- Light quarks (for comparison) ---", flush=True)
    qk = generational_ladder_test(QUARKS_LIGHT, "light_quarks")
    print(f"  Ratios: {qk['mass_ratios']}", flush=True)
    print(f"  Koide Q = {qk['koide_Q']:.6f}", flush=True)
    if qk["best_toroidal_fit"]:
        bfq = qk["best_toroidal_fit"]
        print(f"  Best modes: {bfq['modes']}, "
              f"aspect={bfq['aspect_ratio']}, err={bfq['log_error']}", flush=True)

    # Coulomb barrier ordered pair
    print(f"\n=== Coulomb Barrier Ordered Pair ===", flush=True)
    cb = coulomb_barrier_modes()
    print(f"Concept: {cb['concept']}", flush=True)
    for k, v in cb["chamber_scaling"].items():
        print(f"  {k}: n={v['poloidal_mode_n']}, "
              f"f_rf={v['rf_frequency_hz']} Hz", flush=True)
        print(f"    {v['note']}", flush=True)

    output = {
        "lepton_family": lep,
        "quark_family": qk,
        "coulomb_barrier": cb,
    }
    with open("/tmp/generational_sweep.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    print("\nDone", flush=True)


if __name__ == "__main__":
    main()
