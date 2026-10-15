#!/usr/bin/env python3
"""
cavity4d v2 — smooth 4D cavity on a cylindrical grid (rho, phi, z).

v1 used a Cartesian grid whose 4-fold symmetry aliased Lz by multiples
of 4, corrupting the scattering measurement. v2 is cylindrical with a
spectral phi dimension: Lz is an EXACT conserved quantity of the discrete
system, and OAM projection is exact (no rings, no interpolation).

  1. Fill: cavity filled from captured expansion spectra
     (expand_capture.py .npz): 48 OAM amplitudes -> proper cylindrical
     modes (rho/w0)^|l| exp(-(rho/w0)^2) e^{ilφ}, Gaussian z envelope.
  2. Emerge: shared-reservoir saturable gain + aperture loss lets a
     SINGLE high-magnitude twist condense and persist (pump sustains it
     at finite energy against radiative loss).
  3. Scatter: a bit-encoded data packet propagates via the explicit
     split-step propagator through the twisted cavity. A pure twist is
     phi-symmetric (no Lz mixing by symmetry), so the scattering
     background is the twist + a counter-rotating seed: the azimuthal
     interference fringes scatter data across Lz. Output: S[in -> out].

"4D" = (rho, phi, z) + time through the propagator.

Usage:
  cavity4d.py --selfcheck
  cavity4d.py --emerge  --fill spectra/decay_bh_g001.npz --tick T
  cavity4d.py --scatter --fill spectra/decay_bh_g001.npz --tick T
"""
import argparse
import sys
import numpy as np

# --- cylindrical grid ----------------------------------------------------
NR, NPHI, NZ = 40, 64, 32
RMAX, LZ = 6.0, 16.0
DR = RMAX / NR
RHO = (np.arange(NR) + 0.5) * DR
DZ = LZ / NZ
Z = (np.arange(NZ) - NZ / 2) * DZ
KZ = 2 * np.pi * np.fft.fftfreq(NZ, DZ)
KZ2 = KZ ** 2 / 2.0
MODES = 48
ELLS = np.arange(MODES) - MODES // 2          # -24..23
LIDS = np.fft.fftfreq(NPHI, 1.0 / NPHI).astype(int)  # fft bin -> ell
BIN_OF = {int(l): int(bi) for bi, l in enumerate(LIDS)}
W0 = 1.5
OMEGA = 0.5
RHO3, Z3 = np.meshgrid(RHO, Z, indexing="ij")  # (NR, NZ)
V_TRAP = 0.5 * OMEGA ** 2 * (RHO3 ** 2 + Z3 ** 2)  # broadcast over phi


def _radial_eig(l):
    """Eigendecomposition of the radial Laplacian for angular mode l.

    Conservative finite-volume discretization (symmetric in the
    rho-weighted inner product), Dirichlet at RMAX, exact ghost-free
    origin (face area -> 0). Returns A, B, lam such that
    exp(-i dt M_l) v = A @ (exp(-i dt lam) * (B @ v)).
    """
    rho = RHO
    dr = DR
    n = NR
    face = np.arange(n + 1) * dr            # face radii; face[0] = 0
    # M[i,i+1] = face[i+1]/(rho[i] dr^2), M[i+1,i] = face[i+1]/(rho[i+1] dr^2)
    Ld = -(face[1:] + face[:-1]) / (rho * dr ** 2) - (l ** 2) / rho ** 2
    Lo = face[1:-1] / (rho[:-1] * dr ** 2)   # super-diagonal M[i,i+1]
    Lu = face[1:-1] / (rho[1:] * dr ** 2)    # sub-diagonal M[i+1,i]
    S = np.sqrt(rho)
    # Ms = S M S^-1 symmetric: Ms[i,i+1] = M[i,i+1] S[i]/S[i+1]
    Ms = np.diag(Ld) + np.diag(Lo * S[:-1] / S[1:], 1) \
        + np.diag(Lu * S[1:] / S[:-1], -1)
    lam, Q = np.linalg.eigh(Ms)
    # exp(M) = S^-1 Q exp(lam) Q^T S
    A = (Q / S[:, None])      # S^-1 Q
    B = (Q * S[:, None]).T    # Q^T S
    return A, B, lam


print("building radial eigenbases...", file=sys.stderr)
_RAD = [_radial_eig(int(l)) for l in LIDS]   # per fft-bin ell
print("done.", file=sys.stderr)


def _kinetic_half(psi_hat, dt):
    """Half kinetic step in (ell, rho, kz) spectral space.

    psi_hat: (NR, NPHI, NZ) after phi-FFT (axis=1), ell ordered by LIDS.
    """
    out = np.empty_like(psi_hat)
    fz = np.fft.fft(psi_hat, axis=2)
    for bi in range(NPHI):
        A, B, lam = _RAD[bi]
        W = B @ fz[:, bi, :]                       # (NR, NZ) eigenbasis
        W = W * np.exp(-0.5j * dt * (lam[:, None] + KZ2[None, :]))
        out[:, bi, :] = A @ W
    return np.fft.ifft(out, axis=2)


def propagate(psi, dt, steps, gain_G=0.0, gain_Esat=1.0, loss_0=0.0,
              aperture_a=0.0, v_extra=None, deformity=0.0, rho_planck=None,
              planck_V0=40.0, planck_W0=8.0):
    """Split-step: half kinetic -> potential+gain -> half kinetic.

    psi: (NR, NPHI, NZ) complex. Lz exactly conserved by the kinetic
    steps (phi is spectral). Gain: shared reservoir g = G/(1+E/Esat)
    - loss_0 - aperture(rho).

    Planck-scale deformity (D in [-1, 1], rho_planck ~ grid scale):
      D > 0 (isolated): repulsive core +D*V0*exp(-(rho/rho_P)^2) reflects
              waves at the Planck scale -> isolated expansion smooths
              into STANDING waves at the minimum scale (unitary).
      D < 0 (leak): absorptive core |D|*W0*exp(-(rho/rho_P)^2) drains
              the field -> higher energy LEAKS through the Planck scale.
      D = 0: no deformity.
    """
    ap = aperture_a * (RHO3 / (RMAX * 0.7)) ** 2  # (NR, NZ)
    V = V_TRAP[:, None, :] + (v_extra if v_extra is not None else 0.0)
    leak = 0.0
    if deformity != 0.0:
        rp = rho_planck if rho_planck else 2 * DR
        core = np.exp(-(RHO3 / rp) ** 2)[:, None, :]
        if deformity > 0:
            V = V + deformity * planck_V0 * core
        else:
            leak = -deformity * planck_W0 * core
    for _ in range(steps):
        ph = np.fft.fft(psi, axis=1)
        ph = _kinetic_half(ph, dt)
        psi = np.fft.ifft(ph, axis=1)
        E = float(np.sum(np.abs(psi) ** 2 * RHO[:, None, None])
                  * DR * (2 * np.pi / NPHI) * DZ)
        g = gain_G / (1 + E / gain_Esat) - loss_0 - ap[:, None, :]
        psi = (psi * np.exp(-1j * dt * V) * np.exp(dt * g)
               * np.exp(-dt * leak))
        ph = np.fft.fft(psi, axis=1)
        ph = _kinetic_half(ph, dt)
        psi = np.fft.ifft(ph, axis=1)
    return psi


def energy(psi):
    """Physical L^2 norm on the cylindrical domain: |psi|^2 rho dr dphi dz."""
    return float(np.sum(np.abs(psi) ** 2 * RHO[:, None, None])
                 * DR * (2 * np.pi / NPHI) * DZ)


def oam_mode(l, w0=W0):
    with np.errstate(over="ignore"):
        rad = (RHO / w0) ** abs(l) * np.exp(-(RHO / w0) ** 2)
    return rad


def fill_from_spectra(npz_path, tick=0):
    """Fill the cavity faithful to the captured spectrum.

    Each mode is divided by its radial-envelope norm so the filled
    Lz-powers equal the captured |a_l|^2 (the raw envelopes weight
    high-|l| by |l|!/2^|l|, which would drown the true spectrum).
    """
    d = np.load(npz_path)
    a = d["amps"][tick]
    zenv = np.exp(-(Z / 3.0) ** 2)
    psi = np.zeros((NR, NPHI, NZ), dtype=np.complex128)
    phis = np.linspace(0, 2 * np.pi, NPHI, endpoint=False)
    for amp, l in zip(a, ELLS):
        if abs(amp) > 0:
            rad = oam_mode(l)
            rn = float(np.sum(rad ** 2 * RHO * DR))
            if rn > 0:
                psi += (amp / np.sqrt(rn) * rad[:, None, None]
                        * np.exp(1j * l * phis)[None, :, None]
                        * zenv[None, None, :])
    e = energy(psi)
    return psi / np.sqrt(e) if e > 0 else psi


def oam_spectrum(psi):
    """Exact OAM powers: phi-FFT, sum |c_l|^2 over (rho, z)."""
    ph = np.fft.fft(psi, axis=1) / NPHI
    p = np.zeros(MODES)
    w = RHO * DR * DZ
    for i, l in enumerate(ELLS):
        bi = BIN_OF[int(l)]
        p[i] = float(np.sum(np.abs(ph[:, bi, :]) ** 2 * w[:, None]))
    s = p.sum()
    return p / (s + 1e-300)


def spectral_entropy(p):
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def emerge(npz_path, tick=0, steps=300, dt=0.02, gain_G=3.0, loss_0=0.8,
           e_sat=2.0, aperture_a=2.0):
    psi = fill_from_spectra(npz_path, tick)
    p0 = oam_spectrum(psi)
    psi = propagate(psi, dt, steps, gain_G=gain_G, gain_Esat=e_sat,
                    loss_0=loss_0, aperture_a=aperture_a)
    p1 = oam_spectrum(psi)
    return {"p_initial": p0, "p_final": p1,
            "dominant_ell": int(ELLS[int(np.argmax(p1))]),
            "share": float(p1.max()),
            "entropy_before": spectral_entropy(p0),
            "entropy_after": spectral_entropy(p1),
            "energy_end": energy(psi), "psi": psi}


def data_packet(bits, probe_ells, rho0=2.0, z0=0.0):
    env = np.exp(-((RHO3 - rho0) ** 2) / 0.5 - (Z3 - z0) ** 2 / 0.5)
    phis = np.linspace(0, 2 * np.pi, NPHI, endpoint=False)
    pkt = np.zeros((NR, NPHI, NZ), dtype=np.complex128)
    for b, l in zip(bits, probe_ells):
        if b:
            pkt += (env[:, None, :] * np.exp(1j * l * phis)[None, :, None])
    e = energy(pkt)
    return pkt / np.sqrt(e) if e > 0 else pkt


def scatter(npz_path, tick=0, steps=200, dt=0.02, g_nl=20.0):
    """Scattering matrix through the emerged twist + counter-rotating seed.

    A pure twist is phi-symmetric so it cannot mix Lz (exact symmetry).
    The physical scattering background is the twist with a counter-
    rotating component: azimuthal interference fringes at 2*l_t scatter
    data by +-2*l_t. Compares against the bare cavity.
    """
    em = emerge(npz_path, tick)
    tw, lt = em["psi"], em["dominant_ell"]
    # A pure twist is phi-symmetric and cannot mix Lz (exact symmetry), so
    # the physical scattering background is the twist dressed with a
    # companion twist: their azimuthal interference fringes scatter data
    # across Lz. Companion l=+2 at 15%: its radial profile overlaps the
    # l=0 twist, giving strong fringes (l=+5 lived at larger rho and
    # barely overlapped).
    phis = np.linspace(0, 2 * np.pi, NPHI, endpoint=False)
    zenv = np.exp(-(Z / 3.0) ** 2)
    seed = (oam_mode(2)[:, None, None] * np.exp(1j * 2 * phis)[None, :, None]
            * zenv[None, None, :])
    seed = seed / np.sqrt(energy(seed)) * np.sqrt(0.15 * em["energy_end"])
    bg = tw + seed
    v_twist = g_nl * np.abs(bg) ** 2
    probes = [2, 4, 6, 8, -3, -5, 10, -10]
    S_twist = np.zeros((8, MODES))
    S_bare = np.zeros((8, MODES))
    for i, l in enumerate(probes):
        bits = [1 if j == i else 0 for j in range(8)]
        pkt = data_packet(bits, probes) * 0.05
        S_twist[i] = oam_spectrum(propagate(pkt.copy(), dt, steps, v_extra=v_twist))
        S_bare[i] = oam_spectrum(propagate(pkt.copy(), dt, steps))
    return {"probes": probes, "S_twist": S_twist, "S_bare": S_bare,
            "twist_ell": lt}


def planck_run(deformity=1.0, steps=400, dt=0.02, rho0=3.0):
    """Isolated expansion vs Planck leak: ring contraction experiment.

    A Gaussian ring at rho0 is pulled inward by the trap toward the
    Planck core (rho_P = 2*dr, the grid scale). NOTHING else acts
    (no gain, no aperture loss): a closed system except the leak.
      D > 0 (isolated): repulsive Planck core reflects the ring ->
              ingoing+outgoing interference = STANDING wave at the
              Planck scale; total energy conserved (unitary).
      D < 0 (leak): absorptive core drains the ring on arrival ->
              higher energy LEAKS through the Planck scale.
      D = 0: control (ring passes through / piles at origin).
    Measures per chunk: E_tot, E_core (rho < rho_P), E_shell
    (rho < 3*rho_P), and the standing metric (node-stability of the
    shell intensity; 1 = perfect standing wave).
    """
    rp = 2 * DR
    phis = np.linspace(0, 2 * np.pi, NPHI, endpoint=False)
    ring = (np.exp(-((RHO3 - rho0) ** 2) / 0.2)[:, None, :]
            * np.exp(-(Z3 / 2.0) ** 2)[:, None, :])
    psi = np.broadcast_to(ring, (NR, NPHI, NZ)).astype(np.complex128).copy()
    psi = psi / np.sqrt(energy(psi))
    core_m = np.broadcast_to((RHO3 < rp)[:, None, :], (NR, NPHI, NZ))
    shell_m = np.broadcast_to((RHO3 < 3 * rp)[:, None, :], (NR, NPHI, NZ))
    E_tot, E_core, E_shell = [], [], []
    n_chunks = 10
    for _ in range(n_chunks):
        psi = propagate(psi, dt, steps // n_chunks, deformity=deformity,
                        rho_planck=rp)
        E_tot.append(energy(psi))
        E_core.append(energy(psi * core_m))
        E_shell.append(energy(psi * shell_m))
    # standing-wave ratio in the Planck shell (rho_P < rho < 6*rho_P):
    # deep stationary nodes => standing wave; flat => traveling/drained
    prof = np.abs(psi[:, 0, NZ // 2]) ** 2
    sel = (RHO > rp) & (RHO < 6 * rp)
    swr = float(prof[sel].max() / (prof[sel].min() + 1e-30))
    return {"E_tot": E_tot, "E_core": E_core, "E_shell": E_shell,
            "swr": swr, "deformity": deformity}


def selfcheck():
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {info}")
        ok = ok and bool(cond)

    rng = np.random.default_rng(0)
    psi = (rng.standard_normal((NR, NPHI, NZ))
           + 1j * rng.standard_normal((NR, NPHI, NZ)))
    psi /= np.sqrt(energy(psi))
    e0 = energy(psi)
    # 1. unitary without gain/loss
    psi2 = propagate(psi.copy(), 0.02, 20)
    check("propagator conserves norm", abs(energy(psi2) - e0) < 1e-8,
          f"dE={energy(psi2)-e0:.2e}")
    # 2. Lz EXACTLY conserved (the v2 guarantee)
    pkt = data_packet([0, 1, 0, 0, 0, 0, 0, 0], [2, 4, 6, 8, -3, -5, 10, -10])
    out = propagate(pkt.copy(), 0.02, 100)
    p = oam_spectrum(out)
    check("Lz exactly conserved (no aliasing)",
          p[list(ELLS).index(4)] > 0.999,
          f"share(l=4)={p[list(ELLS).index(4)]:.6f}")
    # 3. OAM projection resolves a pure mode
    phis = np.linspace(0, 2 * np.pi, NPHI, endpoint=False)
    pure = (oam_mode(5)[:, None, None] * np.exp(1j * 5 * phis)[None, :, None]
            * np.exp(-(Z / 3.0) ** 2)[None, None, :])
    pp = oam_spectrum(pure)
    check("OAM projection exact", int(ELLS[int(np.argmax(pp))]) == 5
          and pp.max() > 0.999, f"share={pp.max():.6f}")
    # 4-6. reservoir emergence on 4 modes at EQUAL true power
    # (radial envelopes carry |l|!/2^|l| weight; correct for it)
    ls = (-6, -2, 3, 7)
    rn = {l: float(np.sum(oam_mode(l) ** 2 * RHO * DR)) for l in ls}
    b4 = sum(oam_mode(l)[:, None, None] / np.sqrt(rn[l])
             * np.exp(1j * l * phis)[None, :, None] for l in ls)
    b4 = b4 * np.exp(-(Z / 3.0) ** 2)[None, None, :]
    b4 /= np.sqrt(energy(b4))
    p_init = oam_spectrum(b4)
    pg_full = propagate(b4.copy(), 0.02, 300, gain_G=3.0, gain_Esat=2.0,
                        loss_0=0.8, aperture_a=2.0)
    pb_full = propagate(b4.copy(), 0.02, 300, loss_0=0.8, aperture_a=2.0)
    pg, pb = oam_spectrum(pg_full), oam_spectrum(pb_full)
    check("pump sustains the emerged twist",
          energy(pg_full) > 0.5 and energy(pb_full) < 0.05,
          f"E gain={energy(pg_full):.2f} bare={energy(pb_full):.4f}")
    check("selection condenses spectrum",
          spectral_entropy(pg) < spectral_entropy(p_init) - 0.3,
          f"{spectral_entropy(p_init):.2f}->{spectral_entropy(pg):.2f}")
    check("single twist dominates", pg.max() > 0.6,
          f"l={int(ELLS[int(np.argmax(pg))])} share={pg.max():.3f}")
    # 7. packet encodes bits
    pk = data_packet([1, 0, 1, 0, 0, 0, 0, 0], [2, 4, 6, 8, -3, -5, 10, -10])
    q = oam_spectrum(pk)
    on = [q[list(ELLS).index(l)] for l in (2, 6)]
    off = [q[list(ELLS).index(l)] for l in (4, 8)]
    check("packet encodes bits in OAM", min(on) > 5 * max(off) + 1e-9,
          f"on={np.mean(on):.3f} off={np.mean(off):.3f}")
    # 8. fill is faithful: filled Lz-powers match captured |a_l|^2
    # (canonical tick-4 is uniform; use max deviation, not correlation)
    have_spectra = True
    try:
        dd = np.load("spectra/canonical_s7_e42.npz")
        aa = dd["amps"][4]
        ref = np.abs(aa) ** 2
        ref = ref / ref.sum()
        pf = oam_spectrum(fill_from_spectra("spectra/canonical_s7_e42.npz",
                                            tick=4))
        dev = float(np.max(np.abs(ref - pf)))
        check("fill reproduces captured spectrum", dev < 1e-9,
              f"max|d|={dev:.2e}")
    except FileNotFoundError:
        have_spectra = False
    # 9-11. Planck deformity on the contracting ring
    if have_spectra:
        r_iso = planck_run(deformity=1.0, steps=300)
        r_leak = planck_run(deformity=-1.0, steps=300)
        check("isolated Planck wall conserves energy",
              abs(r_iso["E_tot"][-1] - r_iso["E_tot"][0]) < 1e-6,
              f"dE={r_iso['E_tot'][-1]-r_iso['E_tot'][0]:.2e}")
        check("Planck leak drains the ring",
              r_leak["E_tot"][-1] < 0.7 * r_leak["E_tot"][0],
              f"E {r_leak['E_tot'][0]:.3f}->{r_leak['E_tot'][-1]:.3f}")
        check("isolated wall excludes the core (reflects)",
              max(r_iso["E_core"]) < 0.05,
              f"max E_core={max(r_iso['E_core']):.4f}")
        check("isolated expansion stands at Planck scale (SWR)",
              r_iso["swr"] > 10.0 and r_leak["swr"] < 3.0,
              f"iso SWR={r_iso['swr']:.1f} leak SWR={r_leak['swr']:.1f}")
    ntests = 12 if have_spectra else 7
    print(f"RESULT: {'%d/%d' % (ntests, ntests) if ok else 'FAILED'} checks OK")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--emerge", action="store_true")
    ap.add_argument("--scatter", action="store_true")
    ap.add_argument("--planck", action="store_true")
    ap.add_argument("--fill", default="")
    ap.add_argument("--tick", type=int, default=0)
    args = ap.parse_args()
    if args.selfcheck:
        sys.exit(0 if selfcheck() else 1)
    fill = args.fill or "spectra/decay_bh_g001.npz"
    if args.planck:
        print("deformity | E_start -> E_end | max E_core | SWR")
        for D in (1.0, 0.0, -1.0):
            r = planck_run(deformity=D)
            tag = {1.0: "isolated", 0.0: "neutral ", -1.0: "leak    "}[D]
            print(f"  {tag}  | {r['E_tot'][0]:.3f}->{r['E_tot'][-1]:.3f} "
                  f"| {max(r['E_core']):.4f} | {r['swr']:.1f}")
    if args.emerge:
        r = emerge(fill, args.tick)
        print(f"emerged twist: l={r['dominant_ell']} share={r['share']:.3f} "
              f"E={r['energy_end']:.2f} "
              f"entropy {r['entropy_before']:.2f}->{r['entropy_after']:.2f}")
    if args.scatter:
        r = scatter(fill, args.tick)
        st, sb = r["S_twist"], r["S_bare"]
        np.savez("S_matrix.npz", S_twist=st, S_bare=sb,
                 probes=np.array(r["probes"]), twist_ell=r["twist_ell"])
        print("saved S_matrix.npz")
        idx = [list(ELLS).index(l) for l in r["probes"]]
        off_t = float(np.mean([st[i].sum() - st[i, idx[i]] for i in range(8)]))
        off_b = float(np.mean([sb[i].sum() - sb[i, idx[i]] for i in range(8)]))
        print(f"twist l={r['twist_ell']}: mean off-diagonal: "
              f"twist={off_t:.3f} bare={off_b:.3f}")
        print("S_twist rows (probe -> top-3 out modes):")
        for i, l in enumerate(r["probes"]):
            top = np.argsort(st[i])[::-1][:3]
            print(f"  in l={l:>3}: " + ", ".join(
                f"l={int(ELLS[j]):>3}:{st[i,j]:.2f}" for j in top))


if __name__ == "__main__":
    main()
