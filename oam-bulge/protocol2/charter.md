# OAM-Bulge PROTOCOL 2 — Charter (frozen before production)

Machine: Zak's PC (dezritawre-oma, Ryzen 9 5900XT, 32 threads).
Engine: `fs_engine.py` (byte-identical flow-split copy,
md5 8528e48448a709e8b9588a042d332541), implicit-midpoint GP,
Picard tol 1e-11, ≤16 sweeps, dt = 0.002, N = 128, g = 25.
Canonical `~/flow_split` and `~/oam_bulge/fs_engine.py` are
NOT modified; protocol-2 code lives in `~/oam_bulge/protocol2/`.

## Zak's doctrine (2026-11-07 10:51 ET, his words, tightened)

> A superfluid working system has only TWO variables — FLOW
> and PRECIPITATION FEEDBACK. The geometry of compression
> and tension in the TP backflow bulge must rectify at
> stable bulge maintenance and flow speed; too fast on
> either and you lose the quasi-frozen superfluid state.
> Any superfluid working system has to have those parts
> and the cadence sweet spot that locks the feed and
> backflow bulge in place. Tune filament backflow and
> filament flow speed TIMED TO the stable exchange back to
> the filament = TOROIDAL CURVE − POLOIDAL CURVE
> reintegration rate. For light, compression =
> electromagnetic confinement: magnetic OFFSET pressure on
> the filament creates backflow resembling second-sound
> bands; the confinement is a GRADIENT, so the filament
> carries quasi-frozen superfluid flow ratios.

Why this exists: runs 1–2 and the overnight sweet-spot hunt
all failed. Run 2's positive-only feed was a pump, not a
maintainer (ΣΔE_precip = +4569 = 121% of E0; abort t=2.6).
The hunt found β is the lethal axis, kP is inert (actuator
saturates before gain matters), and the 0.1-t.u. sense
cadence phase-matches the bulge's collapse/rebound. Zak's
ruling: the charter constraint itself was the error — this
protocol is LICENSED to amend, with every amendment
declared here before production.

## Amendments vs runs 1–2 (all declared, none silent)

A1. **Bilateral precipitation feed.** The feed corrects the
    bulge amplitude toward target for BOTH signs of the
    error e_k (precipitate in when e_k > 0, draw out when
    e_k < 0). Net and gross feed ledgers both reported.
A2. **Cadence derived from the system, not the wall clock.**
    Actuation interval Δt_cad = 1/|R|, R = Γ_tor − Γ_pol
    measured from the live velocity field (Phase 0),
    re-measured every ~1.0 t.u. from a trailing window and
    updated. The fixed 0.1-t.u. segment is abolished.
A3. **Graded EM-confinement analogue in the Hamiltonian.**
    V_conf(r,z) = κ_conf · s((r − r_c(z))/w) added to the
    GP Hamiltonian (see Constructions). κ_conf calibrated
    in Phase 0.
A4. **Temperature input removed.** Runs 1–2's pin-temp
    signal is superseded by the two-variable doctrine:
    FLOW (kz) × PRECIPITATION FEEDBACK (β). No sampler.
A5. **Twist stays bilateral, kP = 1.0 fixed, clip ±0.5.**
    kP was measured inert in the hunt; it is not swept.

## The two swept variables (Phase 1 screening)

- FLOW: kz ∈ {0.5, 1.0, 1.5} (construction C1 below).
- PRECIPITATION FEEDBACK: β ∈ {0.125, 0.25, 0.5}, the
  coefficient in β_k = β · e_k (signed, bilateral).
- T = 3 per point; T = 10 confirmation of the best point.

## Constructions (operationalizations, declared)

C1. **Flow-speed dial kz.** A uniform axial phase ramp
    e^{ikz·z} is single-valued on the periodic box (L = 2π)
    only for integer kz; non-integer mean gradients do not
    exist for a periodic field. The dial is therefore the
    AXIAL PHASE GRADIENT AT THE BULGE MIDPLANE, realized
    exactly as runs 1–2 realized their twist actuation:
    seed ← certified kz=1 Arm A state × exp(i·(kz−1)·sin Z),
    whose local gradient is 1 + (kz−1)·cos Z = kz at z = 0.
    kz = 1.0 reproduces the run 1/2 seeding. The realized
    midplane gradient of each seeded state is measured and
    reported. The global mean gradient stays at the
    quantized 1 — this is a construction choice forced by
    periodicity, stated here, not hidden.
C2. **Circulations.** From v = Im(ψ*∇ψ)/|ψ|² (spectral
    gradients; points with n < 5% of the loop-median n are
    excluded and the integral renormalized by covered arc):
    Γ_tor = ∮ v·dl on the circle r₀ = 1.0 at z = 0
    (azimuthal, about the filament axis);
    Γ_pol = ∮ v·dl on the circle ρ = 0.75 in the y = 0
    plane centred on the bulge centre (x,z) = (0,0)
    (poloidal, in the r–z plane about the bulge core).
    Companion loops (r ∈ {0.8, 1.2}; ρ ∈ {0.55, 0.95})
    reported in Phase 0 as robustness. Γ is sampled every
    10 steps wherever a run evolves.
    **R** = Γ_tor − Γ_pol (primary loops, time-averaged
    over the window). R is WELL-DEFINED in a window iff
    sign(R) is constant across the window's samples AND
    |mean R| ≥ 2·std(R). Δt_cad = 1/|mean R|, clipped to
    [0.04, 0.50] t.u. (declared bounds: ≥20 steps; ≤ half
    the bulge dynamical timescale class).
    **Fallback** (per window, if R not well-defined):
    Δt_cad = bulge rebound period measured from A(t) —
    mean interval between successive local maxima of A(t)
    after t = 0.3 (half-period from zero crossings if fewer
    than 2 maxima); Phase-0 value is the standing fallback
    if a production window cannot supply one.
    Angular-rate cross-checks Ω_tor = Γ_tor/(2π r₀²),
    Ω_pol = Γ_pol/(2π ρ²) are reported in phase0.md only;
    the controller uses the literal C2 construction.
C3. **Confinement.** V_conf(r,z) = κ_conf · s((r −
    r_c(z))/w), s = the engine's own smoothstep (0 → 1),
    w = 0.5, r_c(z) = 1.6 − 0.6·exp(−(z − δ)²/(2·0.75²)),
    δ = +0.5 (the pinch sits OFFSET from the bulge
    midplane z = 0 — the offset pressure). V enters the
    Hamiltonian through the same implicit-midpoint Picard
    solve as the interaction term: M = (g|mid|² + V)·mid.
    `fs_engine.py` is untouched; the stepping lives in
    protocol-2 code and is validated against the engine at
    V = 0 before any production (agreement < 1e-10 over 20
    steps from the seed). Energy books include the
    potential channel E_pot = dV·Σ V·n.
    **κ calibration (Phase 0):** for κ ∈ {0, 2, 4, 8, 16,
    32}, evolve the kz = 1 production seed (filament +
    bulge) UNCONTROLLED under the confined propagator to
    T = 0.5 and measure C(0.5) (frozen sense definition,
    C5). κ_conf = argmin |C(0.5) − 2.25| (2.25 = run 2's
    C(0) = 2.2499950693192123); ties → smaller κ. If κ = 0
    wins, that is a Phase-0 result and production still
    uses the chosen κ (= 0).
C4. **Bilateral feed.** At an actuation boundary:
    β_k = β · e_k (signed). ψ ← ψ·(1 + β_k·w(z)·W_bulge),
    w(z) = exp(−z²/2σ²), σ = 0.5, W_bulge the run-1/2
    bulge mask. Mass compensation on the outside region:
    ψ ← ψ·(1 + u·W_outside) with u found by bisection on
    [−0.95, 5] so total N returns to its pre-actuation
    value (N exact to bisection tolerance ≤1e-12 rel).
    Declared fallback (as run 2): if the bracket cannot
    reach the target, global renormalisation + shortfall
    flag. ΔE_precip (signed) booked per boundary; gross
    ledger Σ|ΔE_precip| accumulated; pumping flag iff
    gross > 25% of E0.
C5. **Sensing (frozen from runs 1–2).** A_k =
    prof(z0)/median(prof(|z|>2)) − 1; C_k =
    max_{|z|<1} prof(z)/median(prof(|z|>2)); prof = |ψ|²
    averaged over r < 0.8. Targets A_target = A(0),
    C_target = C(0) of the run's own seed. In-band iff
    C_k ∈ [0.8·C_target, 1.25·C_target]; maintenance =
    in-band fraction over actuation-boundary readings.
    Twist: Δg_k = clip(1.0·e_k, −0.5, +0.5), ψ ←
    ψ·exp(i·Δg_k·sin Z); ΔE_twist booked.
C6. **Cadence bookkeeping.** Actuation intervals are
    variable-length (steps = round(Δt_cad/dt), ≥ 20).
    Books are kept per actuation interval (the successor
    of run 2's per-segment books). Snapshots every 10
    steps regardless (spectrum readout unchanged from
    runs 1–2: same masks, shell spectra, centroids, band
    edges K² ∈ {25, 169, 1600}, spectrum gradient =
    centroid_bulge − centroid_floor).

## Frozen grading (same bars as runs 1–2 / the hunt)

- **HOLDS** iff A(T)/A(0) ≥ 0.80 AND maintenance ≥ 0.80.
  PARTIAL iff exactly one. FAIL otherwise.
- Books: cumulative relative N drift < 1e-7; within-
  interval relative E drift < 1e-3 (actuation-free
  stretches only; boundary ΔE ledgers separate). Picard
  tol 1e-11, ≤16 sweeps (engine). Violations are results,
  flagged, never silently re-run. Aborts are atomic:
  ABORT record + last state preserved.
- Phase 2 confirmation: best screening point by highest
  min(A ratio, maintenance), tie → lowest gross feed;
  T = 10, full readout + delta-stream statistics (hunt
  Phase-3 method). If no point holds at T = 3, the
  least-bad point is confirmed and the two-variable map
  is the result.

## Phase 0 (before any control; results to disk first)

P0a. kz = 1 seed (identical to run 1), NO confinement,
     NO control, T = 2: Γ_tor(t), Γ_pol(t) every 10 steps;
     R statistics; Δt_cad or fallback rebound period.
P0b. κ scan per C3 → κ_conf.
phase0.md records both, with uncertainties (window std),
before Phase 1 launches. Per-config pre-passes (Phase 1)
repeat P0a at T = 1 with confinement ON and the config's
own seed, giving each config its own starting cadence
and fallback.

---

## FINAL AMENDMENTS (Zak's go, 2026-11-07 11:37 ET)

These supersede the sections above where they conflict
(notably: the C1 kz sweep, the density-swell bulge, the
cadence-metronome controller, and the HOLDS bars). Source:
Zak's orders + the model paper
(files/tp-filament-light-model-paper-20261107.md §§1/5/9).

### Phase 0 outcomes (measured, from phase0.md)

- Γ_tor = 6.28284 ± 0.00070 (the 2π unit-winding quantum);
  Γ_pol = 0.0641 ± 0.2577; **R = Γ_T − Γ_P = 6.2188 ±
  0.2578, well-defined in the full window and both halves**
  (paper §8.1: the closure equation is computable).
- τ_circ := 1/|R̄| = **0.1608 t.u.** (the Phase-0
  circulation time; rebound fallback = 0.11).
- κ_conf = **32** by the C3 rule (C(0.5) = 0.9918, closest
  to 2.25). Caveat on record: no scanned κ held the
  compression class (best is at the scan edge); the
  calibration was made on the density-swell seed and is
  carried as FIXED BACKGROUND under FA4, not re-derived.

### FA1 — Bulge = phase-split wall pair (replaces density swell)

Seed: certified kz=+1 filament × exp(i·φ_off(z)),
φ_off(z) = (Δφ₀/2)·W(z)·tanh(z/λ_w), Δφ₀ = π, λ_w = 0.15,
W(z) = 1 − smoothstep((|z| − 0.75)/0.5) (1 inside |z| ≤ 0.75,
0 outside |z| ≥ 1.25; widened from the (0.5, 1.0) draft before
production so the realized split lands at Δφ ≈ π rather than
being diluted by the window ramp — construction declared
here, realized Δφ still measured, per FA1). NO amplitude swell: density is
continuous through the split. Renormalised to the
certified norm (guard; the factor is unitary).
**Δφ instrument:** unwound field χ = ψ·e^{−i(θ+Z)}; wall
phases φ± = arg(Σ χ·W±) with W± the core weights (r < 0.8,
0 < ±z < 1, smooth edges as the masks); Δφ =
wrap(φ₊ − φ₋) ∈ [0, 2π). Coherence coh± = |Σ χ·W±| /
Σ|χ|·W±; walls IDENTIFIABLE iff coh₊ ≥ 0.5 AND coh₋ ≥ 0.5
(declared threshold). Δφ_target := realized Δφ(0),
measured per config and recorded. Wall separation
(z̄₊ − z̄₋ of |χ|·W±) recorded as the geometric shadow.

### FA2 — Maintained variable and grading (replaces HOLDS)

HOLDS iff **Δφ in-band at ≥ 80% of return passes** AND
**wall-pair survival at T** (both walls identifiable).
Band = [0.8, 1.25] × Δφ_target. PARTIAL iff exactly one
holds; FAIL otherwise. Density A and compression C are
recorded every 10 steps for continuity with runs 1–2 but
are NOT graded here (paper §8.3's A-based bars are
superseded by Zak's A2 wording for this protocol).

### FA3 — Phase-gated bilateral return (replaces the metronome)

Attempts at t_k = k·τ_ex (k = 1, 2, …). At each attempt:
φ_ret = arg(Σ χ·W_ret), W_ret = backflow annulus
(1.0 < r < 1.6, |z| < 1 window); φ_bul = arg(Σ χ·W_core),
W_core = r < 0.8, |z| < 1. Mismatch m = wrap(φ_ret −
φ_bul) ∈ (−π, π]. **LAND iff |m| ≤ tol**; otherwise
DEFER — no actuation, a circulation miss is logged.
On landing, BOTH corrections apply:
- Phase: inter-wall correction Δφ_corr = clip(1.0 ·
  e_φ, −0.5, +0.5), e_φ = wrap(Δφ_target − Δφ_meas);
  applied as ψ ← ψ·exp(i·(Δφ_corr/2)·W(z)·tanh(z/λ_w))
  (the FA1 profile). Booked as ΔE_twist. (Successor of
  run 2's twist in the phase-split basis; same gain/clip.)
- Precipitation: e_A = A_target − A_k, A_target = A(0)
  of this seed (≈ 0 for the phase-split seed — the feed
  maintains the filament's density profile), β_k =
  0.25 · e_A (β = 0.25 fixed background, the hunt's
  least-bad completing value), bilateral C4 construction,
  N exact by construction. Booked as ΔE_precip.
Every attempt is logged (t, Δφ, in-band, φ_ret, φ_bul, m,
landed/deferred, Δφ_corr, β_k, u, shortfall, ΔE_twist,
ΔE_precip, N before/after). Acceptance fraction and the
realized landing intervals are primary data (the emergent
cadence). Books per actuation interval as before.

### FA4 — The moved knobs (sweep ONLY these)

τ_ex ∈ {0.5×, 1×, 2×} τ_circ = {0.0804, 0.1608, 0.3216}
t.u. × tol ∈ {π/8, π/4, π/2}. Fixed background: χ = 1.00,
kz = +1, κ_conf = 32 (C3 form in the Hamiltonian),
β = 0.25, phase gain 1.0 clip ±0.5. Screening T = 3.
Confirmation: best point by highest min(Δφ-in-band
fraction, survival ∈ {0,1}); tie → lowest gross |ΔE|
= Σ(|ΔE_twist| + |ΔE_precip|) over landed attempts;
T = 10, full readout + delta-stream statistics over
attempt boundaries (hunt Phase-3 method).

### FA5 — Qubit-plate arm (at the confirmed best config)

Plate state: the confirmation run's final ψ if wall
survival held there, else the best config's t = 0 seed
(the choice made is recorded). 24 replicas: ψ ←
ψ·exp(i·a·exp(−d²/2σ_p²)), σ_p = 0.35, a ~ U[0, 2π),
centre uniform in the bulge (r < 1.2 with sqrt-radius
draw, angle uniform, z uniform in |z| < 0.8); RNG =
numpy default_rng(20261107 + replica), drawing a first,
then centre. Controller OFF, confinement ON, evolve
1.0 t.u. One no-packet control run in lockstep
(checkpointed every 10 steps) supplies δψ = ψ_rep −
ψ_ctrl. Packet energy E_pkt = dV·Σ|δψ|² by region.
**Escape** iff outside-region share of E_pkt at t = 1.0
≥ 0.50. **Settle** iff not escaped AND the bulge core
window's density-weighted circular variance of the
unwound phase at t = 1.0 ≤ 1.25 × control's. Else
"persist". Match(a) iff min circular distance from a to
{φ₊, φ₋} (plate-state wall phases) ≤ tol_best; baseline
share = min(1, 2·tol_best/π). **§9 PASS** iff (escapes
in match window)/(all escapes) ≥ 3 × baseline share AND
≥ 80% of mismatched packets settle. Escape fraction vs
error phase (8 bins of π/4) tabulated — the curve is
the deliverable.

---

## ITERATION AMENDMENTS (Zak's dial authority, 2026-11-07 ~12:21 ET)

Authority: "make it work this time; the dials and data are
yours." Each amendment states its data reason BEFORE use.
Deliverable order is hard: a confirmed A2 HOLD at T=10
first; FA5 injections only after a hold exists.

### FA6 — Settled seed, settled target (equilibrium-first)

DATA REASON: batch-1 point (tau 0.5x, tol pi/4) landed
34/37 attempts with the phase correction SATURATED at the
+0.5 clip on 34/34 landings, pumped sum dE_twist = +429,
and still scored dphi in-band 0.0/37: the seeded split
Delta phi_0 = 2.737 is not a maintainable state — the
system relaxes Delta phi to ~0.5 within ~0.3 t.u. and the
saturated controller can only hold it there. Fighting the
relaxation to a foreign target is the run-2 pump in the
phase channel. CONSTRUCTION: the production seed becomes
the FA1 wall-pair seed evolved UNCONTROLLED (confinement
on, no attempts) to t_settle = 1.0; Delta phi_target :=
the settled Delta phi(1.0), A_target := A(1.0), recorded
in wp_seed_settled.json. The A2 band brackets the system's
own attractor; the controller trims fluctuations. The
batch-1 grid stands as the map of the un-settled target.
NAMED CAVEAT: the settled Delta phi* (~0.5) is NOT the
paper section 9 anti-phase value pi; a hold at Delta phi*
is a container at the phase the system chooses, reported
as exactly that.

### FA7 — TP-cell seed: poloidal vortex ring at the bulge

DATA REASON: Phase 0 measured Gamma_pol ~= 0.06 +/- 0.26
— the current seed has toroidal flow but NO poloidal
circulation; there is no backflow structure to hold the
walls apart in phase (the doctrine's TP cell is missing
its P). CONSTRUCTION: multiply the FA1 seed by a vortex
ring at the bulge: phase factor exp(i*m*alpha),
alpha = atan2(z, r - R_ring), R_ring = 1.1, m = +1;
amplitude carve sqrt(d^2/(d^2 + a_c^2)), a_c = 0.25,
d = sqrt((r - R_ring)^2 + z^2) (minimum-image in z);
renormalised to the filament norm. Measurement adds a
poloidal loop rho = 1.30 (encloses the ring core);
primary Gamma_pol (rho = 0.75) unchanged for
comparability. VALIDATION before any controlled run:
uncontrolled T = 1.5 — ring persistence (core density
minimum + Gamma_pol(rho=1.3) sign/magnitude), Delta phi
trajectory, coherences, books. If the ring holds the
split nearer pi uncontrolled, the TP seed supersedes
FA6's settled seed as the container candidate (target =
its realized settled Delta phi, same equilibrium-first
rule).

### FA7.1 — Measurement correction (same day, before TP grading)

The rho = 1.30 poloidal loop reads ~0 BY SYMMETRY for any
axisymmetric ring (the ring pierces the y=0 plane at two
cores of opposite in-plane winding; a loop enclosing both
nets zero). Measured at the TP seed: Gpol_13 = 4.1e-05.
The ring's circulation is therefore measured on a small
loop around ONE core: Gamma_ring = circulation on the
circle centre (x, z) = (R_ring, 0), radius 0.45, in the
y = 0 plane. Ring persistence is graded on Gamma_ring
plus the carved core's density (mean n within d < 0.15
of the core circle) vs its t = 0 value. Gpol (rho = 0.75)
remains the comparability channel. Also recorded: the
ring imprint re-phases the wall windows (realized TP
dphi0 = 1.306, not 2.737) — the ring phase threads the
bulge interior; the TP target is its settled value under
the same equilibrium-first rule as FA6.

## Amendment A6 — Plasmoid-first (inverse) seeding arm (Zak, 2026-11-07 ~13:23)

INVERTED vs FA1: no pre-split walls. Seed = plain
certified filament (no phase split) x a central PLASMOID:
a localized phase-twist packet at the bulge centre,
psi <- psi * exp(i * Phi_p * exp(-d^2 / (2 sigma_p^2))),
Phi_p = pi, sigma_p = 0.5, d = minimum-image distance to
the origin (declared construction). The construction
self-organizes under the same confinement + FA3
phase-gated return machinery; controller targets for this
arm: Delta phi_target := pi (the paper's anti-phase
value — a controller target only, NOT seeded into the
field), A_target := A(0) of the plasmoid seed. Grading:
A2 as written, with Delta phi EMERGENT (band
[0.8, 1.25] x pi). Readouts unique to this arm:
(1) plasmoid centroid migration — packet disturbance
energy (|dpsi|^2 vs a no-packet control in lockstep):
circular centroid per axis, radial distance from the
filament axis, and packet-energy fraction inside the
wall region (r < 0.8, 0.3 < |z| < 1.0) vs time;
(2) Delta phi onset — first sustained identifiable time
(coh >= 0.5 at 3 consecutive snapshots) and closest
approach of Delta phi to pi in the late window;
(3) second-sound band annealing — bulge spectral entropy
over the 112-shell distribution and SS-band fraction
(declared: bulge power share in the engine's band index
1, K^2 in [25, 169)) vs time; prediction on record:
early broad/modulated spectrum -> late band fraction
rising, entropy falling. Config: the A1 arm's best
completed screening point (FA4 rule) for comparability.
T = 3 screening; T = 10 confirmation if it grades. This
arm does not displace A1; imposed-vs-emergent Delta phi
is itself the result. Priority unchanged: a confirmed
hold from EITHER arm before FA5 injections.

### A6 readout (4) — cavity volume vs band alignment (Zak, 2026-11-07 ~13:37)

In the plasmoid arm, track CAVITY VOLUME against
BAND-ALIGNMENT FRACTION over time. Declared proxies:
cavity volume = wall separation (snapshot field wall_sep;
the bulge window's cross-section is fixed by the mask,
so separation is the cavity's 1-D size — volume proxy =
wall_sep x window cross-section, monotone in wall_sep);
band-alignment fraction = ss_band_frac (bulge power
share in band index 1, K^2 in [25, 169)). His claim on
record: expansion is rented from the anti-alignment —
as bands align (annealing completes) the cavity should
CONTRACT. Report the alignment-vs-volume trajectory
(correlation + quartile means); rising alignment with
flat/expanding volume contradicts the miniature and is
a reportable result either way.

## FA8 — CONSTRAINED-STATIONARY WALL-PAIR PREP (dial/construction authority; recorded before use)

Reasoning (from the data): every seed so far — density bulge, FA1 wall pair,
FA7 TP ring — was a raw imprint, NOT a stationary state, and its measured
behaviour is dominated by relaxation: the FA1 pair's Δφ winds and decays
within ~0.1–0.3 t.u.; the settled state (FA6) continues decaying toward
Δφ ≈ 0 over 3 t.u. (st_t1.0_tolpi4 attempt series lives at |signed Δφ| ≲ 0.6);
the FA7 ring's carved core fills in (core density 0.18 → 2.7) and Γ_ring
collapses (2π → 0.19) by t = 0.5. The wall pair's Δφ is, as imprinted, an
unprotected soft mode. Before concluding the container does not exist in
this system, prepare the split state the way stationary states are always
prepared: imaginary-time relaxation with the wall-pair PHASE PROFILE PINNED
(the FA1 profile exp(i·(π/2)·W(z)) re-imposed at every imaginary step),
density free, under the same confinement. The result is a constrained
stationary state carrying the split; on release the only question that
matters is measured: uncontrolled evolution T = 1 — does Δφ persist
(drift small) where the raw imprint wound away? If yes, FA8 seed replaces
FA1/FA6 seeds (targets from its realized Δφ(0) per FA1/FA2, screening as
before). If the pinned prep fails to converge or the released state still
decays in ≲0.3 t.u., the wall-pair container is not preparable in this
scalar GP system by phase construction — a strong, reportable negative.

## FA9 — CADENCE-EDGE PROBE (dial authority; recorded before use)

The settled-arm data show the phase gate nearly always open (max |mismatch|
0.323 rad at tol π/4) and the controller's corrections decaying between
attempts: Δφ relaxes ~1.5 rad per 0.1 t.u. early (pinned settle) against a
±0.5 clip. The one axis of the A4 grid not yet probed at its edge is attempt
DENSITY: τ_ex = 0.25×τ_circ ≈ 0.040 t.u. (≈ every 20 steps), settled seed,
tol π/4. Per-interval free decay (~0.6 rad) vs clip (0.5) makes this the
marginal point of the cadence axis; if in-band fraction does not rise
materially here, the cadence axis is exhausted for this controller family
and the negative is structural, not a scheduling miss. One run, T = 3.
