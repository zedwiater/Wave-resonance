"""v15c: Speed hierarchy — measure orbital periods vs carrier wave speed.

Tests Gemini's speed hierarchy directly:
1. Fast carrier: measure phase velocity of background wave.
2. Slow orbits: measure orbital periods of IXPs, EDFAs, devices.
3. Ratio: carrier/orbital (Earth: 300,000/30 = 10,000x).

Method:
- Bodies: track phi(t), omega = dphi/dt, T_orb = 2pi/omega.
- Carrier: inject a phase pulse, track its radial propagation speed.
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def main():
    np.random.seed(43)
    # Cooler start: lower gain on initial propagate (mature, not Big Bang)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 10, gain_G=1.5)
    E0 = float(C.energy(psi0))

    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.008,
                          use_viscosity=True, visc_nu0=0.02,
                          visc_mode="smoothstep", visc_eps=0.1,
                          visc_g_lo=2.0, visc_g_hi=4.0)
    v_orb = 0.02
    sys.bodies = [
        CO.Body("sink", [1.0, 0.0, 0.0], [0, v_orb, 0],
                mass=2.5, sigma=0.5),
        CO.Body("sink", [1.0, np.pi, 0.0], [0, v_orb, 0],
                mass=2.5, sigma=0.5),
        CO.Body("amplifier", [1.0, 1.2, 0.0], [0, v_orb, 0],
                mass=0.5, sigma=0.3, kappa=0.05),
        CO.Body("sink", [0.8, 0.3, 0.0], [0, v_orb*1.2, 0],
                mass=0.1, sigma=0.15),
    ]
    names = ["ixp_ny", "ixp_london", "edfa", "device"]

    # Track phi over 60 ticks
    N = 60
    phi_track = np.zeros((len(sys.bodies), N+1))
    for i, b in enumerate(sys.bodies):
        phi_track[i, 0] = b.x[1]
    for t in range(N):
        sys.tick(dt_tick=4.0, use_bodies=True)
        for i, b in enumerate(sys.bodies):
            phi_track[i, t+1] = b.phi_unwrapped

    # Orbital periods: T = 2pi / omega, omega = dphi/dt
    # dt per tick = 4.0 (sim units)
    dt_total = N * 4.0
    results = {}
    for i, name in enumerate(names):
        dphi = phi_track[i, -1] - phi_track[i, 0]
        omega = dphi / dt_total  # rad per sim time unit
        T_orb = 2*np.pi / abs(omega) if abs(omega) > 1e-9 else float('inf')
        # Orbital speed: v = omega * rho (in grid units per time)
        rho = float(sys.bodies[i].x[0])
        v_orbital = abs(omega) * rho
        results[name] = {
            "omega": round(float(omega), 6),
            "T_orb": round(float(T_orb), 1),
            "v_orbital": round(float(v_orbital), 6),
            "rho": round(rho, 3),
        }

    # Carrier speed: measure from the wave equation parameters
    # In cavity4d, the propagate/tick uses a characteristic speed.
    # Estimate empirically: track a phase front.
    # Simpler: use the grid spacing and tick dt.
    # NR=48, rho 0.3-3.0 → dr = 2.7/48 = 0.056 units.
    # If the carrier crosses 1 radial cell per tick (dt=4.0):
    # v_carrier ≈ 0.056/4.0 = 0.014 units/time. But this is a guess.
    # Better: measure actual phase velocity from field evolution.
    # Take two snapshots, cross-correlate a radial slice.
    psi_a = sys.psi.copy()
    sys.tick(dt_tick=4.0, use_bodies=False)  # one tick, no bodies
    psi_b = sys.psi.copy()
    # Phase difference at backbone ring
    rho_arr = np.linspace(0.3, 3.0, C.NR)
    ir = int(np.argmin(np.abs(rho_arr - 1.0)))
    iz = C.NZ // 2
    # Use phase of the dominant mode to estimate propagation
    # Cross-correlate radial profiles to find shift
    prof_a = np.abs(psi_a[:, 0, iz])
    prof_b = np.abs(psi_b[:, 0, iz])
    # Find peak shift via cross-correlation
    corr = np.correlate(prof_b - prof_b.mean(), prof_a - prof_a.mean(), mode='full')
    shift_idx = int(np.argmax(corr)) - (len(prof_a) - 1)
    dr = 2.7 / C.NR
    # shift in units per tick (dt=4.0)
    v_carrier = abs(shift_idx) * dr / 4.0 if shift_idx != 0 else 0.0

    # Ratios
    ratios = {}
    for name in names:
        v_o = results[name]["v_orbital"]
        if v_o > 1e-9 and v_carrier > 1e-9:
            ratios[name] = round(v_carrier / v_o, 1)
        else:
            ratios[name] = None

    print(json.dumps({
        "E0": round(E0, 1),
        "v_carrier_units_per_time": round(float(v_carrier), 6),
        "v_carrier_km_s": round(float(v_carrier) * 3704 / 4.0, 1) if v_carrier>0 else 0,
        "orbits": results,
        "carrier_orbital_ratio": ratios,
        "earth_analog": 10000,
    }), flush=True)
    print("V15c done", flush=True)


if __name__ == "__main__":
    main()
