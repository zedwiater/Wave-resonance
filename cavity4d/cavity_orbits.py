"""v4: wave-dynamic Newtonian mechanics for the cavity.

Bodies (sinks, amplifiers, comets) are Newtonian particles in the mass
potential:  v += (-grad(Phi) - gamma_drag * v) * dt.  The field's Phi moves
them; their mass deepens Phi (two-way coupling).  Each body leaves a
trailing spectra tail (deposit + decay); tails bend around sinks because
the bodies do, and stretch near amplifiers/stars.

Scales in one frame: universal mass (steady dissipation, no resets) ->
stable orbits (data/amplifiers; RAM bit cycle logged as precession) ->
comets (transient true-interaction events) -> wave modulation -> radiation.

Falsifiers: orbits must close (not spiral/decay); trails must bend
measurably near sinks; comet passage must change share/entropy vs control;
precession period must be stable when the system is stabilized.
"""
import numpy as np

import cavity4d as C
import cavity_cage as CG


# ---------------------------------------------------------------- field helpers
def grad_phi(Phi):
    """grad(Phi) in physical units. phi-component carries the 1/rho."""
    dPdr, dPdp, dPdz = np.gradient(Phi, C.DR, 2 * np.pi / C.NPHI, C.DZ)
    return dPdr, dPdp / C.RHO[:, None, None], dPdz


def _wrap_phi(x):
    """Wrap the angle coordinate into [0, 2pi). Bodies can wind up
    enormous phi_unwrapped (1e5+ rad) via Coriolis spin-up on close
    passages; the periodic coordinates must not see the winding number."""
    x = np.array(x, dtype=float, copy=True)
    x[1] = x[1] % (2 * np.pi)
    return x


def hill_radius(body, grads, G_const):
    """Lagrangian interaction boundary: the Hill sphere where the body's
    gravity balances the central tidal field. Inside this radius the
    planet's local frame dominates and its data is PROTECTED —
    external trajectories cannot perturb it unless they TARGET it
    (enter the sphere). r_H = (G*m / (3*tidal))^(1/3)."""
    g = -np.array([_trilerp(gp, body.x) for gp in grads])
    r = max(body.x[0], 0.5)
    tidal = abs(g[0]) / r + 1e-12
    return float((G_const * body.mass / (3 * tidal)) ** (1 / 3))


def modal_pump(psi, ell_target, dE):
    """Data manipulation: inject dE directly into OAM mode ell_target.

    This is the v5 modal amplifier — it acts in spectral space (the
    trailing spectra tail / mode content), not in physical space.
    Unlike spatial amplifiers (which never moved share in v1-v4), this
    directly reshapes the modal distribution = information shift.
    Returns (psi_new, dE_injected)."""
    if dE <= 1e-12:
        return psi, 0.0
    F = np.fft.fft(psi, axis=1) / C.NPHI  # match oam_spectrum normalization
    bi = C.BIN_OF[int(ell_target)]
    w = C.RHO * C.DR * C.DZ
    # Physical energy in the mode (C.energy units): oam_spectrum's
    # sum|ph|^2*w misses a 2pi vs C.energy (Parseval: sum_modes =
    # E_total/2pi). Corrected here so dE is in true energy units.
    E_mode = float(np.sum(np.abs(F[:, bi, :]) ** 2 * w[:, None])) * 2 * np.pi
    if E_mode < 1e-300:
        return psi, 0.0  # nothing to amplify — can't create a mode ex nihilo
    scale = np.sqrt((E_mode + dE) / E_mode)
    F[:, bi, :] *= scale
    return np.fft.ifft(F * C.NPHI, axis=1), dE


def _trilerp(F, x):
    """Trilinear interpolation of grid field F at physical x=[rho,phi,z].
    phi is periodic; rho/z clamp."""
    x = _wrap_phi(x)
    fr = x[0] / C.DR - 0.5
    fp = (x[1] % (2 * np.pi)) / (2 * np.pi) * C.NPHI
    fz = (x[2] + C.LZ / 2) / C.DZ
    i0 = int(np.floor(fr))
    j0 = int(np.floor(fp))
    k0 = int(np.floor(fz))
    di, dj, dk = fr - i0, fp - j0, fz - k0
    # defensive clamp: bodies can overshoot the grid during substeps
    # (fast comets, slingshots) before the soft containment catches them.
    # _trilerp must never crash on out-of-bounds input.
    i0 = max(min(i0, C.NR - 1), 0)
    i1 = max(min(i0 + 1, C.NR - 1), 0)
    k0 = max(min(k0, C.NZ - 1), 0)
    k1 = max(min(k0 + 1, C.NZ - 1), 0)
    j0w, j1w = j0 % C.NPHI, (j0 + 1) % C.NPHI
    c000 = F[i0, j0w, k0]
    c100 = F[i1, j0w, k0]
    c010 = F[i0, j1w, k0]
    c110 = F[i1, j1w, k0]
    c001 = F[i0, j0w, k1]
    c101 = F[i1, j0w, k1]
    c011 = F[i0, j1w, k1]
    c111 = F[i1, j1w, k1]
    c00 = c000 * (1 - di) + c100 * di
    c10 = c010 * (1 - di) + c110 * di
    c01 = c001 * (1 - di) + c101 * di
    c11 = c011 * (1 - di) + c111 * di
    c0 = c00 * (1 - dj) + c10 * dj
    c1 = c01 * (1 - dj) + c11 * dj
    return c0 * (1 - dk) + c1 * dk


def _deposit_kernel(x, sigma=0.75):
    """Gaussian deposit kernel around physical position x -> (NR,NPHI,NZ)."""
    if not np.all(np.isfinite(x)):
        return np.zeros((C.NR, C.NPHI, C.NZ))
    x = _wrap_phi(x)
    ph = (np.arange(C.NPHI) / C.NPHI) * 2 * np.pi
    dphi = np.minimum(np.abs(ph - x[1]), 2 * np.pi - np.abs(ph - x[1]))
    d2 = ((C.RHO[:, None, None] - x[0]) ** 2
          + (dphi[None, :, None] * x[0]) ** 2
          + (C.Z[None, None, :] - x[2]) ** 2)
    K = np.exp(-d2 / (2 * sigma ** 2))
    return K / K.sum()


# ---------------------------------------------------------------- bodies
class Body:
    """A Newtonian body in the cavity: sink, amplifier (star), or comet.

    kind='sink': condenses matter (v3 loop), carries condensed mass.
    kind='amplifier': star — massive, injects pump energy as structure.
    kind='comet': transient — no condensation, strong trail; the
        true-interaction event. Leaves; does not stay.
    """

    def __init__(self, kind, x, v, mass=1.0, kappa=0.15, sigma=0.75,
                 trail_strength=1.0, target_ell=None):
        assert kind in ("sink", "amplifier", "comet")
        self.kind = kind
        self.x = np.array(x, dtype=float)    # [rho, phi, z]
        self.v = np.array(v, dtype=float)    # [vrho, vphi, vz]
        self.mass = mass
        self.kappa = kappa
        self.sigma = sigma
        self.trail_strength = trail_strength
        # v5: amplifiers are MODAL (data manipulation) — each carries a
        # target OAM mode it pumps. None = spatial fallback (control).
        self.target_ell = target_ell
        # v6: Lagrangian interaction boundary (Hill sphere). Computed per
        # tick from the tidal field; the planet's sovereign local frame.
        self.hill_r = 0.0
        # v6b: fixed planets (for controlled protection tests). When True,
        # gravity_step is skipped — the planet is a stationary star.
        # (Orbit stability is v4's open problem; protection logic is v6's.)
        self.fixed = False
        self.phi_unwrapped = x[1]
        self.cycles = 0                      # RAM bit cycles (2π crossings)
        self.path = [self.x.copy()]

    def gravity_step(self, grads, dt, gamma_drag, substeps=20):
        # Cylindrical-coordinate Newtonian dynamics. The fictitious
        # forces are NOT optional: without the centrifugal term
        # rho*vphi^2, every "orbit" is really infall (found 2026-10-15 —
        # bodies spiraled in even with exact v_circ and zero drag).
        #   d(v_rho)/dt = g_rho + rho*vphi^2          (centrifugal)
        #   d(vphi)/dt  = g_phi/rho - 2*v_rho*vphi/rho (Coriolis)
        #   d(v_z)/dt   = g_z
        h = dt / substeps
        for _ in range(substeps):
            g = -np.array([_trilerp(gp, self.x) for gp in grads])
            rho = max(self.x[0], 1e-6)
            a_rho = g[0] + rho * self.v[1] ** 2
            a_phi = g[1] / rho - 2 * self.v[0] * self.v[1] / rho
            a_z = g[2]
            self.v += (np.array([a_rho, a_phi, a_z])
                       - gamma_drag * self.v) * h
            # in-loop speed cap: explicit Euler + quadratic centrifugal
            # feedback can blow up to inf (then inf-inf=NaN) on close
            # encounters *within* the substep loop — a post-loop cap is
            # too late. 3.0 is ~10x orbital velocity (numerical guard).
            vphys = np.sqrt(self.v[0] ** 2 + (rho * self.v[1]) ** 2
                            + self.v[2] ** 2)
            if not np.isfinite(vphys):
                self.v[:] = 0.0  # freeze, don't poison the run
                break
            if vphys > 3.0:
                self.v *= 3.0 / vphys
            # angular-velocity cap: near the center, Coriolis spin-up can
            # wind phi_unwrapped to 1e5+ rad (physical speed stays capped
            # because rho is small, but the angle accumulator explodes).
            # 10 rad/time is ~60x orbital — a numerical guard, not physics.
            if abs(self.v[1]) > 10.0:
                self.v[1] = np.sign(self.v[1]) * 10.0
            self.x += self.v * h
            if not np.all(np.isfinite(self.x)):
                break
        # soft containment
        if self.x[0] > C.RMAX - 0.3:
            self.x[0] = C.RMAX - 0.3
            self.v[0] = -abs(self.v[0]) * 0.5
        if self.x[0] < 0.3:
            self.x[0] = 0.3
            self.v[0] = abs(self.v[0]) * 0.5
        if abs(self.x[2]) > C.LZ / 2 - 0.5:
            self.x[2] = np.sign(self.x[2]) * (C.LZ / 2 - 0.5)
            self.v[2] *= -0.5
        # precession / bit-cycle log
        prev = self.phi_unwrapped
        self.phi_unwrapped += self.v[1] * dt
        if int(self.phi_unwrapped // (2 * np.pi)) != int(prev // (2 * np.pi)):
            self.cycles += 1
        self.path.append(self.x.copy())

    def orbit_closed(self, tol=0.5):
        """Has the body returned near its start (stable orbit)?"""
        if len(self.path) < 4:
            return False
        d = np.linalg.norm(self.path[-1] - self.path[0])
        return bool(d < tol)


def body_potential(bodies, G_const=0.005, sigma_soft=0.5):
    """Analytic softened point-mass potential of the bodies on the grid.
    Two-way coupling: bodies' mass deepens Phi (they are mass)."""
    ph = (np.arange(C.NPHI) / C.NPHI) * 2 * np.pi
    Phi_b = np.zeros((C.NR, C.NPHI, C.NZ))
    for b in bodies:
        bx = _wrap_phi(b.x)
        dphi = np.minimum(np.abs(ph - bx[1]), 2 * np.pi - np.abs(ph - bx[1]))
        d2 = ((C.RHO[:, None, None] - bx[0]) ** 2
              + (dphi[None, :, None] * bx[0]) ** 2
              + (C.Z[None, None, :] - bx[2]) ** 2)
        Phi_b -= G_const * b.mass / np.sqrt(d2 + sigma_soft ** 2)
    return Phi_b


# ---------------------------------------------------------------- trails
class TrailField:
    """Trailing spectra tails: deposit at body positions, exponential decay.
    Tails bend around sinks because the bodies' paths do."""

    def __init__(self, tau_trail=20.0, dt_tick=4.0):
        self.T = np.zeros((C.NR, C.NPHI, C.NZ))
        self.decay = np.exp(-dt_tick / tau_trail)

    def tick(self, bodies):
        self.T *= self.decay
        for b in bodies:
            self.T += b.trail_strength * _deposit_kernel(b.x, b.sigma)
        return self.T

    def mass(self):
        return float(self.T.sum())

    def bend_metric(self, bodies):
        """Fraction of trail mass within 1.5 units of any sink —
        measures whether tails bend toward / wrap around sinks."""
        sinks = [b for b in bodies if b.kind == "sink"]
        if not sinks:
            return 0.0
        ph = (np.arange(C.NPHI) / C.NPHI) * 2 * np.pi
        near = np.zeros_like(self.T, dtype=bool)
        for s in sinks:
            dphi = np.minimum(np.abs(ph - s.x[1]), 2 * np.pi - np.abs(ph - s.x[1]))
            d2 = ((C.RHO[:, None, None] - s.x[0]) ** 2
                  + (dphi[None, :, None] * s.x[0]) ** 2
                  + (C.Z[None, None, :] - s.x[2]) ** 2)
            near |= d2 < 1.5 ** 2
        return float(self.T[near].sum() / max(self.T.sum(), 1e-12))


# ---------------------------------------------------------------- system
class CavitySystem:
    """The full v4 system: field + hum carrier + bodies + trails.

    Dissipation: universal steady drain gamma_univ on the field every tick
    (the mass deteriorates at a steady rate; the pump replenishes).
    Condensation: GLOBAL condition — sink runaway (kappa boost) only when
    system-wide min(Phi) < Phi_crit.
    """

    def __init__(self, psi, gamma_univ=0.01, gamma_drag=0.02,
                 Phi_crit=-0.20, G_const=0.001, kappa_base=0.15,
                 comet_epsilon=0.1, stellar_sigma=0.5, hawking_coeff=1e-4,
                 c_speed=float('inf'), use_viscosity=False,
                 visc_nu0=0.05, visc_g_lo=1.0, visc_g_hi=3.0,
                 visc_mode='smoothstep', visc_eps=0.1):
        self.psi = psi
        self.carrier = CG.HumCarrier(psi)
        self.ledger = CG.new_ledger()
        self.trails = TrailField()
        self.bodies = []
        self.gamma_univ = gamma_univ
        self.gamma_drag = gamma_drag
        self.Phi_crit = Phi_crit
        self.G_const = G_const
        self.kappa_base = kappa_base
        self.comet_epsilon = comet_epsilon
        self.gain_G = 3.0
        self.E_hist = []
        self.stable_ticks = 0
        # v12: viscous boundary ablation — gradient-selective diffusion
        # that sheds fringe noise while preserving core topology.
        # Continuous, not threshold-triggered. Off by default.
        self.use_viscosity = use_viscosity
        self.visc_nu0 = visc_nu0
        self.visc_g_lo = visc_g_lo
        self.visc_g_hi = visc_g_hi
        self.visc_mode = visc_mode
        self.visc_eps = visc_eps
        # v6: log of (planet_kind, distance) when a comet's trajectory
        # enters a planet's Hill sphere = a TARGETING event (protection
        # breached by intent/trajectory, not by proximity alone).
        self.targeting_events = []
        # v7: cost ledger — every operation metered, proportional to its
        # geometric boundary (Hill sphere). This closes the M_0 budget:
        # internal transfers are costed, not free.
        # Keys: energy moved BY each mechanism (positive = into field).
        self.cost_ledger = {
            "star_radiation": 0.0,   # amplifiers: L ∝ r_H² (photosphere)
            "sink_accretion": 0.0,   # sinks: dE ∝ r_H³ (volume swept)
            "hawking": 0.0,          # sinks: thermal ∝ 1/M² (horizon glow)
            "comet_kicks": 0.0,      # comets: phase kicks (work done)
        }
        # v7: stellar/black-hole coefficients (tunable; universal physics)
        self.stellar_sigma = stellar_sigma
        self.hawking_coeff = hawking_coeff
        # v8: pump reservoir. The propagator pump draws from this, not
        # from nothing. Dissipation credits it (waste heat). If empty,
        # the pump stalls. M_0 = E_field + M_condensed + E_reservoir
        # is then EXACTLY conserved (flat).
        E0 = C.energy(psi)
        self.ledger["E_reservoir"] = 2.0 * E0
        self.ledger["pump_metered"] = 0.0
        # v8 c-cone: finite influence speed. Pulses emitted by comets
        # expand at c_speed; planets are affected only when the front
        # reaches them. inf = instantaneous (Hill only, baseline).
        self.c_speed = c_speed
        self.pulses = []  # (x_emit, t_emit) for active pulse fronts
        self.tick_count = 0

    def _body_distance(self, a, b):
        """Physical distance between two bodies (phi-aware)."""
        xa, xb = _wrap_phi(a.x), _wrap_phi(b.x)
        dphi = abs(xa[1] - xb[1])
        dphi = min(dphi, 2 * np.pi - dphi)
        return float(np.sqrt((xa[0] - xb[0]) ** 2
                             + (dphi * xa[0]) ** 2 + (xa[2] - xb[2]) ** 2))

    def _hill_mask(self, planet):
        """Boolean mask of the grid inside the planet's Hill sphere."""
        x = _wrap_phi(planet.x)
        ph = (np.arange(C.NPHI) / C.NPHI) * 2 * np.pi
        dphi = np.minimum(np.abs(ph - x[1]), 2 * np.pi - np.abs(ph - x[1]))
        d2 = ((C.RHO[:, None, None] - x[0]) ** 2
              + (dphi[None, :, None] * x[0]) ** 2
              + (C.Z[None, None, :] - x[2]) ** 2)
        return d2 < planet.hill_r ** 2

    def total_phi(self):
        Phi_f = CG.mass_potential(CG.mass_density(self.psi), sigma=1.0,
                                  condensed=self.ledger["condensed_field"],
                                  beta=1.0)
        return Phi_f + body_potential(self.bodies, self.G_const)

    def apply_viscosity(self):
        """v12f: Density-weighted viscous ablation, two modes.
        Mode 'smoothstep' (default): nu = nu0 * smoothstep(grel) * W_floor.
          Selective, thresholded. Safe.
        Mode 'linear' (Gemini v12.1): nu = nu0 * W_floor * grel (clipped).
          Proportional, no threshold. More aggressive fringe ablation.
        W_floor = |ψ|²/(|ψ|²+ε²) in both: protects vortex eye.
        Shed entropy → background → gamma_univ → M_0 as heat."""
        gr, gp, gz = np.gradient(self.psi)
        gmag = np.sqrt(np.abs(gr)**2 + np.abs(gp)**2 + np.abs(gz)**2)
        amp = np.abs(self.psi)
        grel = gmag / (amp + 1e-6)
        # density weight: zero at vortex eye, unity in bulk
        eps = getattr(self, 'visc_eps', 0.1)
        W_floor = (amp ** 2) / (amp ** 2 + eps ** 2)
        mode = getattr(self, 'visc_mode', 'smoothstep')
        if mode == 'linear':
            # Gemini v12.1: proportional to relative fluctuation,
            # no threshold — even mild noise gets some viscosity.
            # Clip grel to avoid blowup (grel can be large).
            nu = self.visc_nu0 * W_floor * np.clip(grel, 0, 5.0)
        else:
            # smoothstep: 0 below g_lo, 1 above g_hi
            t = np.clip((grel - self.visc_g_lo) /
                        (self.visc_g_hi - self.visc_g_lo + 1e-12), 0, 1)
            s = t * t * (3 - 2 * t)
            nu = self.visc_nu0 * s * W_floor
        lap = np.zeros_like(self.psi)
        for ax in range(3):
            lap += (np.roll(self.psi, -1, axis=ax) - 2 * self.psi
                    + np.roll(self.psi, 1, axis=ax))
        E_pre = C.energy(self.psi)
        self.psi = self.psi + nu * lap * 1.0  # dt=1 for stability
        # the diffused energy is thermal waste: debit to reservoir
        # (M_0 neutral: field → reservoir as heat)
        diss = E_pre - C.energy(self.psi)
        if diss > 0:
            self.ledger["dissipated"] += diss
            self.ledger["E_reservoir"] += diss

    def tick(self, dt_tick=4.0, use_bodies=True):
        # field propagation is done outside (chunked); here: system update
        # v6: targeting events are per-tick (the satellite timestamps them)
        self.targeting_events = []
        self.tick_count += 1
        # 1. universal steady dissipation (the Weight of the Universe:
        #    mass deteriorates at a steady rate; the pump replenishes)
        # v8: dissipated energy credits the reservoir as waste heat
        # (M_0 neutral: E_field → E_reservoir).
        E_pre_diss = C.energy(self.psi)
        self.psi *= np.exp(-self.gamma_univ * dt_tick)
        diss = E_pre_diss - C.energy(self.psi)
        self.ledger["dissipated"] += diss
        self.ledger["E_reservoir"] += diss
        # 2. hum controller vs assumed carrier
        E = C.energy(self.psi)
        hum_E = self.carrier.hum_energy()
        if E > 1.25 * hum_E:
            self.gain_G *= 0.95
        elif E < 0.75 * hum_E:
            self.gain_G *= 1.05
        self.carrier.tick(self.psi)
        # 3. potential + bodies
        Phi = self.total_phi()
        min_phi = float(Phi.min())
        # Global condensation condition: sink runaway ONLY when the system
        # says so (min Phi < Phi_crit). Amplifiers do NOT get the boost —
        # a 3x multiplicative pump (1.45x/tick) blows the field to inf
        # (found 2026-10-15: both branches NaN'd). Sinks are damping
        # (1-0.45K), safe to boost; amplifiers stay at kappa_base.
        kappa_sink = self.kappa_base * (3.0 if min_phi < self.Phi_crit else 1.0)
        if use_bodies and self.bodies:
            grads = grad_phi(Phi)
            # v6: Lagrangian interaction boundaries. Each data-planet's
            # Hill sphere is its sovereign local frame — computed from
            # the tidal field every tick (relativity expressed in locality:
            # the boundary moves with the planet and the local curvature).
            for b in self.bodies:
                if b.kind in ("sink", "amplifier"):
                    b.hill_r = hill_radius(b, grads, self.G_const)
            for b in self.bodies:
                if not b.fixed:
                    b.gravity_step(grads, dt_tick, self.gamma_drag)
                if b.kind == "comet":
                    # true interaction: the comet's passage is wave
                    # modulation — a phase kick along its path.
                    # v6 PROTECTION: the kick is masked OUT of every
                    # non-targeted planet's Hill sphere. A planet is
                    # TARGETED iff the comet's trajectory enters its
                    # sphere; otherwise its local data is invariant.
                    # (The planet's own intentional radiation is never
                    # gated — shouting is allowed, breaking in isn't.)
                    # v8 c-cone: if c_speed finite, the kick propagates as
                    # expanding rings (finite influence speed), not an
                    # instantaneous blob. Hill protection applies in both.
                    if self.c_speed < float('inf'):
                        # emit pulse; compute rings from active pulses
                        self.pulses.append((b.x.copy(), self.tick_count))
                        K = np.zeros((C.NR, C.NPHI, C.NZ))
                        max_d = 8.0  # prune beyond this
                        alive = []
                        for (x_e, t_e) in self.pulses:
                            r = self.c_speed * (self.tick_count - t_e)
                            if r > max_d:
                                continue
                            alive.append((x_e, t_e))
                            # ring at radius r, width sigma
                            xe = _wrap_phi(np.array(x_e, dtype=float))
                            ph = (np.arange(C.NPHI) / C.NPHI) * 2 * np.pi
                            dphi = np.minimum(np.abs(ph - xe[1]),
                                              2 * np.pi - np.abs(ph - xe[1]))
                            d = np.sqrt(
                                (C.RHO[:, None, None] - xe[0]) ** 2
                                + (dphi[None, :, None] * xe[0]) ** 2
                                + (C.Z[None, None, :] - xe[2]) ** 2)
                            ring = np.exp(-((d - r) / b.sigma) ** 2)
                            # amplitude decays with radius (energy spreads)
                            ring = ring / (1.0 + r)
                            K = K + ring
                        self.pulses = alive
                        if K.max() > 0:
                            K = K / K.max()
                    else:
                        # Hill-only (baseline): instantaneous Gaussian
                        K = _deposit_kernel(b.x, b.sigma)
                        K = K / K.max()
                    for p in self.bodies:
                        if p.kind not in ("sink", "amplifier"):
                            continue
                        d = self._body_distance(b, p)
                        if d < p.hill_r * 2.0:
                            # TARGETED: trajectory enters the Hill sphere —
                            # full interaction (protection breached by
                            # intent/trajectory).
                            self.targeting_events.append(
                                (p.kind, round(float(d), 3)))
                        else:
                            # not targeted: shield the Hill sphere.
                            # Protection is the DEFAULT; targeting is the
                            # exception. (The planet's own intentional
                            # radiation is never gated — shouting is
                            # allowed, breaking in isn't.)
                            K = K * (1 - self._hill_mask(p))
                    self.psi = self.psi * np.exp(1j * self.comet_epsilon * K)
                elif b.kind == "sink":
                    # v7 BLACK HOLE: horizon → Hawking radiation.
                    # Accretion sweeps the Hill volume (cost ∝ r_H³);
                    # the horizon glows faintly thermal: F ∝ 1/M².
                    # (Universal: stars radiate from photosphere ∝ r²,
                    #  black holes from horizon ∝ 1/M².)
                    K = _deposit_kernel(b.x, b.sigma)
                    K = K / K.max()  # peak-1 like Condensate.K
                    m_before = np.abs(self.psi) ** 2
                    E_pre = C.energy(self.psi)
                    self.psi = self.psi * (1 - kappa_sink * K)
                    dE = E_pre - C.energy(self.psi)
                    self.ledger["condensed_mass"] += dE
                    self.ledger["condensed_field"] += m_before - np.abs(self.psi) ** 2
                    b.mass += dE  # the body carries what it condenses
                    self.cost_ledger["sink_accretion"] += dE
                    # Hawking: thermal glow from the horizon, paid for by
                    # the hole's mass (M_0 neutral: mass → field).
                    # Broadband/incoherent — a tiny uniform lift, not modal.
                    hawking_dE = self.hawking_coeff / (b.mass**2 + 1e-6) * dt_tick
                    hawking_dE = min(hawking_dE, b.mass * 0.01)  # don't evaporate
                    if hawking_dE > 1e-12:
                        hill = self._hill_mask(b)
                        n_hill = hill.sum()
                        if n_hill > 0:
                            # uniform energy density added in Hill sphere
                            self.psi[hill] *= np.sqrt(
                                1 + hawking_dE / (C.energy(self.psi[hill]) + 1e-300))
                            b.mass -= hawking_dE
                            self.ledger["condensed_mass"] -= hawking_dE
                            self.cost_ledger["hawking"] += hawking_dE
                elif b.kind == "amplifier":
                    # v7 STAR: core → photosphere. Luminosity follows
                    # Stefan-Boltzmann: L = sigma * r_H² (the photosphere
                    # IS the Hill sphere — energy percolates through the
                    # 4D medium and releases at the boundary). Cost ∝
                    # geometric boundary (v7 metering). Draws from the
                    # condensed pool (stellar fuel); never ex nihilo.
                    pool = self.ledger["condensed_mass"]
                    if b.target_ell is not None:
                        # modal: inject into target OAM mode (information shift)
                        L_star = self.stellar_sigma * b.hill_r**2
                        dE_want = L_star * dt_tick
                        dE = min(dE_want, pool)
                        self.psi, dE_in = modal_pump(self.psi, b.target_ell, dE)
                        self.ledger["condensed_mass"] -= dE_in
                        self.ledger["pump_in"] += dE_in  # recycled, not created
                        self.cost_ledger["star_radiation"] += dE_in
                    else:
                        # spatial fallback (control): local multiplicative,
                        # but pool-capped — still M_0 neutral.
                        K = _deposit_kernel(b.x, b.sigma)
                        K = K / K.max()
                        E_pre = C.energy(self.psi)
                        psi_try = self.psi * (1 + self.kappa_base * K)
                        dE_want = C.energy(psi_try) - E_pre
                        dE = min(max(dE_want, 0.0), pool)
                        if dE_want > 1e-12:
                            self.psi = self.psi * (1 + self.kappa_base * K
                                                   * (dE / dE_want))
                            self.ledger["condensed_mass"] -= dE
                            self.ledger["pump_in"] += dE
                            self.cost_ledger["star_radiation"] += dE
            self.trails.tick(self.bodies)
        # v12: viscous boundary ablation (optional, off by default).
        # Sheds fringe entropy continuously; core topology untouched.
        if self.use_viscosity:
            self.apply_viscosity()
        # field sanity: catch blowup at the source, not as NaNs at the end
        if not np.all(np.isfinite(self.psi)):
            raise FloatingPointError("field went non-finite in CavitySystem.tick")
        # 4. stability bookkeeping
        self.E_hist.append(C.energy(self.psi))
        if len(self.E_hist) > 5:
            recent = np.array(self.E_hist[-5:])
            if np.max(np.abs(np.diff(recent)) / recent[:-1]) < 0.02 \
                    and min_phi > self.Phi_crit:
                self.stable_ticks += 1
        return {"E": float(C.energy(self.psi)), "min_phi": min_phi,
                "kappa_sink": kappa_sink, "gain_G": self.gain_G}


def circular_velocity(rho0, Phi):
    """Estimate circular orbit velocity at rho0 from dPhi/drho (z=0, phi=0)."""
    ir = int(np.argmin(np.abs(C.RHO - rho0)))
    iz = C.NZ // 2
    dPdr = (Phi[min(ir + 1, C.NR - 1), 0, iz] - Phi[max(ir - 1, 0), 0, iz]) \
        / (2 * C.DR)
    # centripetal: v^2/r = |dPhi/dr| (well => Phi rises outward => inward pull)
    return float(np.sqrt(max(rho0 * abs(dPdr), 1e-6)))
