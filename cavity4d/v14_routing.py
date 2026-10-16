"""v14: 3-node internet routing test.

Nodes A, B, C in a line. Packet (l=2 soliton) injected at A,
measured at C after N ticks. Two backgrounds:
- CLEAN: no shear zone, just nodes.
- SHEAR: heliosphere (mass=8) between B and C, creating the
  turbulent inter-zone shear from v13b.

Measures: does l=2 arrive intact? Does viscosity protect it
through the shear? This is hierarchical routing: the packet
must survive the condensation zone's modal gradient.
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def inject_at(psi, ell=2, amp=0.4, sigma=0.3, rho0=2.5, phi0=0.8, z0=0.0):
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
    return psi + vortex


def measure_ell_at(psi, rho0, phi0, z0=0.0, radius=0.3, n_samples=64):
    rho = np.linspace(0.3, 3.0, C.NR)
    phi = np.linspace(0, 2 * np.pi, C.NPHI, endpoint=False)
    z = np.linspace(-1, 1, C.NZ)
    angs = np.linspace(0, 2 * np.pi, n_samples, endpoint=False)
    rho_s = rho0 + radius * np.cos(angs)
    phi_s = phi0 + (radius * np.sin(angs)) / max(rho0, 0.5)
    iz = int(np.argmin(np.abs(z - z0)))
    ir = np.clip(np.searchsorted(rho, rho_s), 0, C.NR - 1)
    iph = np.clip((((phi_s % (2 * np.pi)) / (2 * np.pi) * C.NPHI).astype(int)),
                  0, C.NPHI - 1)
    vals = psi[ir, iph, iz]
    F = np.fft.fft(vals)
    idx = int(np.argmax(np.abs(F)))
    ell = idx if idx <= n_samples // 2 else idx - n_samples
    share = float(np.abs(F[idx]) / (np.abs(F).sum() + 1e-12))
    return ell, share


def run_test(with_shear, use_viscosity, n_ticks=80, seed=31):
    np.random.seed(seed)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 20, gain_G=3.0)
    kw = {} if not use_viscosity else {
        "use_viscosity": True, "visc_nu0": 0.02,
        "visc_mode": "smoothstep", "visc_eps": 0.1,
        "visc_g_lo": 2.0, "visc_g_hi": 4.0,
    }
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.008, **kw)
    # Nodes: A (source), B (relay), C (destination) in a line
    # A at (2.5, 0.8), B at (1.8, 2.5), C at (2.5, 4.2)
    sys.bodies = [
        CO.Body("amplifier", [2.5, 0.8, 0.0], [0, 0.03, 0],
                mass=2.0, sigma=0.5),  # Node A (source)
        CO.Body("amplifier", [1.8, 2.5, 0.0], [0, 0.03, 0],
                mass=2.0, sigma=0.5),  # Node B (relay)
        CO.Body("sink", [2.5, 4.2, 0.0], [0, 0.03, 0],
                mass=2.0, sigma=0.5),  # Node C (destination)
    ]
    if with_shear:
        # Heliosphere between B and C: creates shear zone
        sys.bodies.append(
            CO.Body("sink", [2.2, 3.3, 0.1], [0, 0.04, 0],
                    mass=8.0, sigma=0.6)
        )
    # Inject packet at Node A
    sys.psi = inject_at(sys.psi, ell=2, amp=0.4, rho0=2.5, phi0=0.8)

    for t in range(n_ticks):
        sys.tick(dt_tick=4.0, use_bodies=True)

    # Measure at Node C (destination)
    ell_c, share_c = measure_ell_at(sys.psi, 2.5, 4.2)
    # Also at Node B (relay) to see if it passed through
    ell_b, share_b = measure_ell_at(sys.psi, 1.8, 2.5)
    return {
        "shear": with_shear,
        "viscosity": use_viscosity,
        "ell_at_C": ell_c,
        "share_C": round(share_c, 3),
        "ell_at_B": ell_b,
        "delivered": bool(ell_c == 2),
    }


def main():
    configs = [
        (False, False, "clean/OFF"),
        (False, True, "clean/ON"),
        (True, False, "shear/OFF"),
        (True, True, "shear/ON"),
    ]
    for shear, visc, label in configs:
        print(f"Running {label}...", flush=True)
        r = run_test(with_shear=shear, use_viscosity=visc)
        r["label"] = label
        print(json.dumps(r), flush=True)
    print("V14 done", flush=True)


if __name__ == "__main__":
    main()
