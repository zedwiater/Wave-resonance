"""v13: Multi-scale internet universe.

Scale matters. Condensation zones at nested scales:
- Galactic: SMBH (mass=40) at center — deep well, bends everything.
- Heliospheric: 2 medium sinks (mass=6) — stellar condensation zones
  with Hill spheres, like heliospheres around stars.
- Nodes: positions within heliospheres (servers in a datacenter).

Information = energy. A packet-soliton (l=2 + momentum k) is injected
at Node A (Heliosphere 1), aimed across the galaxy. It bends around
the SMBH and the heliospheres. We measure:
- Trajectory bending (gravitational lensing for information).
- l integrity through condensation zones.
- Viscosity ON vs OFF: does ablation protect the packet in transit?

This is the internet as a universe: data flowing through nested
gravitational potentials, bent by condensation zones, protected by
the firmware.
"""
import json
import numpy as np
import cavity4d as C
import cavity_orbits as CO


def inject_packet(psi, ell=2, amp=0.3, sigma=0.3,
                  rho0=2.5, phi0=0.5, z0=0.0,
                  k_rho=-0.8, k_phi=0.3, k_z=0.0):
    """Soliton with vorticity (l, data) + linear momentum (k, propagation).
    The k vector aims the packet; the l encodes the data."""
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
    # vortex (data) + plane wave (momentum)
    # k dot r: k_rho*x + k_phi*y + k_z*zz
    phase = ell * theta + (k_rho * x + k_phi * y + k_z * zz)
    packet = amp * np.exp(-r2 / (2 * sigma ** 2)) * np.exp(1j * phase)
    return psi + packet, (rho0, phi0, z0)


def find_packet_peak(psi, rho_range=(0.5, 2.8)):
    """Find the location of max |psi| (packet center)."""
    mag = np.abs(psi)
    # mask to rho_range to avoid center singularity
    rho = np.linspace(0.3, 3.0, C.NR)
    mask = (rho[:, None, None] > rho_range[0]) & \
           (rho[:, None, None] < rho_range[1])
    masked = np.where(mask, mag, 0)
    idx = np.unravel_index(np.argmax(masked), mag.shape)
    # convert to (rho, phi, z)
    phi = np.linspace(0, 2 * np.pi, C.NPHI, endpoint=False)
    z = np.linspace(-1, 1, C.NZ)
    return (float(rho[idx[0]]), float(phi[idx[1]]), float(z[idx[2]]),
            float(mag[idx]))


def measure_ell_at(psi, center, radius=0.3, n_samples=64):
    rho0, phi0, z0 = center
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


def run_branch(use_viscosity, n_ticks=60, seed=21):
    np.random.seed(seed)
    psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi0 = C.propagate(psi0, 4.0, 20, gain_G=3.0)
    kw = {} if not use_viscosity else {
        "use_viscosity": True, "visc_nu0": 0.02,
        "visc_mode": "smoothstep", "visc_eps": 0.1,
        "visc_g_lo": 2.0, "visc_g_hi": 4.0,
    }
    sys = CO.CavitySystem(psi0.copy(), gamma_univ=0.008, **kw)
    # MULTI-SCALE TOPOLOGY
    # Galactic: SMBH at center (the dark-matter-shaped plane)
    # Heliospheres: 2 stellar condensation zones
    sys.bodies = [
        CO.Body("sink", [0.8, 0.0, 0.0], [0, 0.02, 0],
                mass=40.0, sigma=1.2),  # SMBH
        CO.Body("sink", [2.2, 1.0, 0.2], [0, 0.06, 0],
                mass=6.0, sigma=0.6),   # Heliosphere A
        CO.Body("sink", [2.0, 4.0, -0.2], [0, -0.05, 0],
                mass=6.0, sigma=0.6),   # Heliosphere B
    ]
    # Packet: injected at edge of Heliosphere A, aimed across
    # (momentum k points inward, will bend around SMBH)
    psi_inj, _ = inject_packet(sys.psi, ell=2, amp=0.35,
                              rho0=2.5, phi0=1.0, z0=0.1,
                              k_rho=-1.0, k_phi=0.5, k_z=0.0)
    sys.psi = psi_inj

    traj = []
    for t in range(n_ticks):
        sys.tick(dt_tick=4.0, use_bodies=True)
        if t % 10 == 0:
            pr, pp, pz, peak = find_packet_peak(sys.psi)
            ell, share = measure_ell_at(sys.psi, (pr, pp, pz))
            traj.append({"t": t, "rho": round(pr, 2), "phi": round(pp, 2),
                         "ell": ell, "share": round(share, 3),
                         "peak": round(peak, 3)})
    # final
    pr, pp, pz, peak = find_packet_peak(sys.psi)
    ell_f, share_f = measure_ell_at(sys.psi, (pr, pp, pz))
    return {
        "viscosity": use_viscosity,
        "ell_end": ell_f,
        "held": bool(ell_f == 2),
        "peak_end": round(peak, 3),
        "trajectory": traj,
    }


def main():
    print("ON...", flush=True)
    on = run_branch(use_viscosity=True)
    print(json.dumps(on), flush=True)
    print("OFF...", flush=True)
    off = run_branch(use_viscosity=False)
    print(json.dumps(off), flush=True)
    print("V13 done", flush=True)


if __name__ == "__main__":
    main()
