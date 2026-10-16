"""v15: Transoceanic backbone — scaling the cavity to planetary internet.

Scale: 1 cavity unit = 3,704 km (2.7 units = 10,000 km max).
- MAREA (6,200 km) = 1.67 units.
- NY (1.0, 0) to London (1.0, pi): 2.0 units = 7,408 km (transatlantic).
- Tokyo (2.5, pi/2): outer node.

IXPs as condensation zones (mass=12, regional hubs).
EDFA repeaters: 4 small amplifiers (mass=2) along NY-London path,
spaced ~0.4 units (~1,480 km) apart — scaled from 50km real spacing.

Measures:
- M_0 ledger balance at backbone scale.
- Modal structure (does l=2 dominate the backbone waveguide?).
- Energy distribution (where's the power?).
- Hill spheres (device interaction ranges).

Note: solitons are memory (v14). This tests the BACKBONE (the universe),
not packet routing (which needs wave messengers, to be built).
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def main():
    np.random.seed(41)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 20, gain_G=3.0)
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.008,
                          use_viscosity=True, visc_nu0=0.02,
                          visc_mode="smoothstep", visc_eps=0.1,
                          visc_g_lo=2.0, visc_g_hi=4.0)
    # IXPs: NY, London, Tokyo (condensation zones)
    # EDFA repeaters along NY-London great circle
    sys.bodies = [
        CO.Body("sink", [1.0, 0.0, 0.0], [0, 0.03, 0],
                mass=12.0, sigma=0.7),      # NY IXP
        CO.Body("sink", [1.0, np.pi, 0.0], [0, 0.03, 0],
                mass=12.0, sigma=0.7),      # London IXP
        CO.Body("sink", [2.5, np.pi/2, 0.0], [0, 0.02, 0],
                mass=12.0, sigma=0.7),      # Tokyo IXP
        # EDFA repeaters (pump the backbone)
        CO.Body("amplifier", [1.0, 0.6, 0.0], [0, 0.03, 0],
                mass=2.0, sigma=0.4),
        CO.Body("amplifier", [1.0, 1.2, 0.0], [0, 0.03, 0],
                mass=2.0, sigma=0.4),
        CO.Body("amplifier", [1.0, 1.9, 0.0], [0, 0.03, 0],
                mass=2.0, sigma=0.4),
        CO.Body("amplifier", [1.0, 2.5, 0.0], [0, 0.03, 0],
                mass=2.0, sigma=0.4),
    ]

    # Settle for 50 ticks
    for t in range(50):
        sys.tick(dt_tick=4.0, use_bodies=True)

    # M_0 ledger
    ledger = sys.ledger
    # Modal structure at backbone (r=1.0, the NY-London ring)
    rho = np.linspace(0.3, 3.0, C.NR)
    ir = int(np.argmin(np.abs(rho - 1.0)))
    iz = C.NZ // 2
    vals = sys.psi[ir, :, iz]
    F = np.fft.fft(vals)
    idx = int(np.argmax(np.abs(F)))
    n = len(F)
    ell = idx if idx <= n // 2 else idx - n
    share = float(np.abs(F[idx]) / (np.abs(F).sum() + 1e-12))

    # Hill radii (device interaction ranges)
    hills = []
    for b in sys.bodies[:3]:  # IXPs only
        hills.append(round(float(getattr(b, 'hill_r', -1)), 3))

    # Energy distribution: field vs reservoir vs bodies
    E_field = float(C.energy(sys.psi))
    E_res = float(ledger.get("E_reservoir", 0))
    E_diss = float(ledger.get("dissipated", 0))

    print(json.dumps({
        "scale_km_per_unit": 3704,
        "ny_london_km": round(2.0 * 3704),
        "backbone_ell": ell,
        "backbone_share": round(share, 3),
        "E_field": round(E_field, 3),
        "E_reservoir": round(E_res, 3),
        "E_dissipated": round(E_diss, 3),
        "M0_balanced": bool(abs((E_field + E_res) - 7.0) < 2.0),
        "ixp_hill_r": hills,
        "device_range_units": [round(h * 0.01, 4) for h in hills],
    }), flush=True)
    print("V15 done", flush=True)


if __name__ == "__main__":
    main()
