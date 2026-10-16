"""v13b: Scale matters — modal structure of condensation zones.

Don't chase a moving packet. Instead: build the multi-scale topology
(SMBH + heliospheres) and measure the BACKGROUND field's modal content
as a function of scale. Does a condensation zone imprint its own
modal signature? Is information (phase structure) bent near masses?

- SMBH (mass=40) at center: galactic-scale condensation.
- 2 heliospheres (mass=6): stellar-scale condensation zones.
- Measure: dominant l vs radius. Phase gradient magnitude vs radius.
- Question: do condensation zones create distinct modal environments?
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def radial_modal_profile(psi, n_rings=8):
    """Dominant l in concentric rings around center."""
    rho = np.linspace(0.3, 3.0, C.NR)
    phi = np.linspace(0, 2 * np.pi, C.NPHI, endpoint=False)
    z = np.linspace(-1, 1, C.NZ)
    iz = C.NZ // 2
    out = []
    for i in range(n_rings):
        r_lo = 0.3 + i * (2.7 / n_rings)
        r_hi = 0.3 + (i + 1) * (2.7 / n_rings)
        r_mid = (r_lo + r_hi) / 2
        ir = int(np.argmin(np.abs(rho - r_mid)))
        # azimuthal FFT at this radius
        vals = psi[ir, :, iz]
        F = np.fft.fft(vals)
        # map to l using BIN_OF if available, else simple
        idx = int(np.argmax(np.abs(F)))
        n = len(F)
        ell = idx if idx <= n // 2 else idx - n
        share = float(np.abs(F[idx]) / (np.abs(F).sum() + 1e-12))
        # mean phase gradient magnitude (how "twisted" is this ring?)
        phase = np.angle(vals)
        dphase = np.abs(np.diff(np.unwrap(phase)))
        twist = float(dphase.mean())
        out.append({"r": round(r_mid, 2), "ell": ell,
                    "share": round(share, 3), "twist": round(twist, 3)})
    return out


def main():
    np.random.seed(21)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 20, gain_G=3.0)
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.008)
    # multi-scale: SMBH + 2 heliospheres
    sys.bodies = [
        CO.Body("sink", [0.8, 0.0, 0.0], [0, 0.02, 0],
                mass=40.0, sigma=1.2),
        CO.Body("sink", [2.2, 1.0, 0.2], [0, 0.06, 0],
                mass=6.0, sigma=0.6),
        CO.Body("sink", [2.0, 4.0, -0.2], [0, -0.05, 0],
                mass=6.0, sigma=0.6),
    ]
    # let it settle for 30 ticks
    for _ in range(30):
        sys.tick(dt_tick=4.0, use_bodies=True)

    profile = radial_modal_profile(sys.psi)
    print(json.dumps({"profile": profile}), flush=True)

    # Hill radii of the heliospheres (their "heliosphere" extent)
    for b in sys.bodies:
        print(json.dumps({
            "kind": b.kind, "mass": b.mass,
            "hill_r": round(float(getattr(b, 'hill_r', -1)), 3),
        }), flush=True)
    print("V13B done", flush=True)


if __name__ == "__main__":
    main()
