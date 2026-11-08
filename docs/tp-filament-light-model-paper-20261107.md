# Stable TP Filament Superfluid Flow in Light — The Model on Paper

**Status:** Paper-first theoretical write-up, per Zak's order
2026-11-07 ~10:58 ET: put the end-goal equations on paper
before simming them further, because the electromagnetic
confinement dial is stiff — "either very big input or very
small" — and its usable window must be located analytically.
**For Zak's red pen. Nothing here is a sim result.** Pins are
labeled OBSERVED (literature), BENCH (published experiment),
or SIM (measured in our own engines, sim-internal only).

**Verification status (added 2026-11-07 ~11:10, at Zak's
trust statement):** the equations are TRANSCRIBED from
established physics — Landau two-fluid second sound,
Bogoliubov spectrum of the GP equation, the photon-fluid
(paraxial Maxwell → NLSE) mapping from the optics
literature, bound-state-in-continuum leakage scaling —
assembled on paper by Muse. They were NOT machine-checked
or numerically verified at writing. Named constructions
(mine, not literature): the u₂,L spectral-weights form in
§3, the κ_L definition in §1, the δ* window rule in §6
(order-of-magnitude), and Q_maint as defined there.
Grading path: §8's four tests, starting with the
protocol-2 Phase-0 circulation measurement.

---

## 1. The end goal, as equations to satisfy

A configuration of light that flows as a superfluid in a
toroidal-poloidal (TP) filament circuit, and maintains
itself. Five conditions, all simultaneous:

1. **Filament** — a phase-coherent light vortex line with
   quantized circulation (OAM charge ℓ ∈ ℤ):

       ∮ v · dl = ℓ · κ_L ,        κ_L = 2π · (c / n) / k_φ

   (κ_L = the circulation quantum of the confined light
   fluid; k_φ the azimuthal wavenumber of the carrier.)

2. **Bulge** — a toroidal backflow structure around the
   filament whose guided modes are BOUND (below the
   radiation continuum — they cannot evaporate) yet COUPLED
   (above the decoupling floor — they still exchange with
   the filament).

   **Definition amendment (Zak, 2026-11-07 ~11:17):** a
   bulge is a SPLIT AND SCATTERED SECTION OF THE FILAMENT
   ITSELF — filament material delaminated into internal
   walls — SUPPORTED by the polarity and phase difference
   between those internal bulge walls. The walls cannot
   recombine while their phases disagree (phase agreement
   is the crossing/merging condition — the Rollin rule);
   the maintained variable is therefore the inter-wall
   phase difference Δφ held in band, with wall separation
   as its geometric shadow. Inflation = Δφ in band;
   collapse = Δφ → agreement (filament re-forms) or
   Δφ → decoherence. The counter-phase branch of §3–§4 IS
   the internal wall pair counter-oscillating. Sim
   consequence: a density swell is the wrong object; the
   bulge must be seeded as a phase split (wall pair) and
   graded on Δφ.

3. **Second sound** — the bulge carries an acoustic branch
   whose dispersion is linear across the operating band,

       ω(k) = u₂,L · k ,     k ∈ [k₋, k₊] ,

   the light-fluid analogue of helium's second sound:
   an entropy/temperature-like wave of the two-component
   (filament + bulge) system, counter-flowing, carrying
   modulation without net mass transport.

4. **Circuit closure (maintenance)** — the bulge amplitude
   A obeys

       dA/dt = Π − D = 0 ,     Π = Γ_T − Γ_P ,

   precipitation Π = toroidal reintegration Γ_T minus
   poloidal loss Γ_P; D = dissipation. Stable maintenance
   is the equality, held by feedback, not by fine-tuning.

   **Phase gate (Zak, 2026-11-07 ~11:27):** reintegration
   is phase-gated. A poloidal return reaches the interior
   only when its phase matches the bulge's internal phase
   state; on mismatch it cannot land and must circulate
   back through the system for another pass. The effective
   reintegration rate is therefore

       R = (circulation rate) × (phase-match acceptance
           fraction) ,

   and the cadence of §1.5 is an EMERGENT statistic of
   landings, never an imposed period. (The overnight hunt's
   imposed 0.1 cadence pumped the bulge precisely because
   it actuated on a metronome instead of on phase events.)

   **Perpetual lock and the two exits:** under OAM the
   bifurcation's split phases are perpetually out of phase
   — Δφ is locked by the quantized winding and cannot
   unwind locally. The bulge therefore ends only by
   (a) a larger phase smoothing the whole system, or
   (b) all phases and the daughters rectifying through the
   system and snapping back to filament — a conjunctive
   event, highly unlikely by construction. This lock is
   the robustness of TP flow and of the cavity (and, in
   the qubit application, the enclosure's protection).

5. **Cadence lock** — the feedback drive frequency equals
   the reintegration rate the system itself sets:

       Ω_drive = 2π · R ,     R ≡ Π (cycles per unit time).

   Timing derived from the two curves; never imposed.

**Two variables only (Zak's doctrine, 2026-11-07):** flow
speed and precipitation feedback are the free variables.
Compression geometry and tension must RECTIFY at the point
where (4) holds — they are solved for, not scanned.

---

## 2. Observed pins

| Quantity | Value | Class / source |
|---|---|---|
| He-II second-sound speed u₂ at 1.4 K | 19.56 m/s | OBSERVED — Donnelly & Barenghi, Table 4.3 |
| He-II ρs/ρ at 1.4 K | 0.927 | OBSERVED — Donnelly & Barenghi, Table 2.3 |
| He-II second-sound law | u₂² = (ρs/ρn)·(s̄²T/c̄) | OBSERVED — Landau two-fluid relation |
| He circulation quantum h/m₄ | 9.97×10⁻⁸ m²/s | OBSERVED |
| He Landau critical velocity | ≈ 58 m/s | OBSERVED |
| He-II lambda point Tλ | 2.17 K (SVP) | OBSERVED |
| BH bulge geometry (M87*, Sgr A*) | bright thick torus around a dark condensed core; ring Ø ≈ 42 μas (M87*), ≈ 52 μas (Sgr A*) | OBSERVED — EHT Collaboration 2019 / 2022; thick-bulge (H/R ~ 0.3–1) in GRMHD fits |
| MoSe₂ confinement squeeze | n ≈ 4.4–4.5 → wavelength compressed ~4.5×; THG ×1,500 vs flat | BENCH — Pruszyńska-Karbownik et al., ACS Nano 2026 |
| MoSe₂ bound state in continuum | trapped mode inside the radiation continuum, leak → 0 by symmetry | BENCH — same paper (condition 2, published) |
| Earth He compression window | stable liquid 0–25 bar; ρ(freeze)/ρ(SVP) ≈ 1.19 | OBSERVED — Balibar & Caupin; Tanaka et al. |
| OAM run compression target class | C₀ = 2.25 (bulge/floor density ratio at seeding) | SIM — oam_bulge runs 1–2 |
| Drive pitch at best (failing) config | period 1.43 t.u.; flow ratio ⟨\|Δg\|⟩/kz = 0.49 | SIM — sweet-spot hunt, T=10 confirmation |
| Spectrum gradient at seeding | centroid_bulge − centroid_floor = −1.39 | SIM — runs 1–2 (identical seeds) |
| Cadence failure | imposed 0.1 t.u. cadence phase-matched the bulge rebound → driven oscillation | SIM — hunt diagnosis |

---

## 3. Light as a fluid: the equation we actually solve

Paraxial propagation of a monochromatic field envelope ψ
in a Kerr-type confining medium is the nonlinear
Schrödinger equation — formally the Gross–Pitaevskii
equation (photon-fluid mapping, established literature):

    i ℏ ∂t ψ = [ −(ℏ²/2m_L) ∇² + g_L |ψ|² + V_conf(x) ] ψ

with effective mass m_L = ℏ n k₀ / c set by the carrier
dispersion, g_L ∝ −n₂ the nonlinear coupling, and V_conf
the confinement (waveguide / index structure / EM
confinement gradient). By Functional Invariance this is not
an analogy: it is the same equation the condensate obeys,
in a different substance. Every result below is a property
of the equation; the substance only sets the constants.

Linearizing about a uniform flow ψ = √ρ · e^{i(k·x − ωt)}
gives the Bogoliubov spectrum of the light fluid:

    ω_B(k) = v·k ± √( u² k² + (ℏ k² / 2 m_L)² ) ,
    u² = g_L ρ / m_L .

- Low k: sound-like, ω ≈ u k — the fluid's acoustic mode.
- High k: free-particle, ω ≈ ℏ k²/2m_L.
- Crossover (healing) wavevector k_h = 2 m_L u / ℏ.

In a TWO-component configuration (filament density ρ_f,
bulge density ρ_b, coupled by exchange) the acoustic
sector splits into an in-phase branch (first-sound-like)
and a COUNTER-phase branch in which the two components
oscillate against each other at constant total density.
The counter-phase branch is the light fluid's SECOND
SOUND: modulation rides it without net transport, exactly
as in helium, where u₂² = (ρs/ρn)(s̄²T/c̄) — the ratio of
the two components' weights sets the speed. In the light
fluid the weights are the filament/bulge spectral weights:

    u₂,L² = ( w_f · w_b / (w_f + w_b) ) · (exchange stiffness) ,

the functional form carried over, constants to be measured
(Phase-0 class measurement: the branch slope in the bulge
window's spectrum).

---

## 4. TP confinement: adjusting the spectrum into bands

Confinement quantizes the transverse modes. In a
filament-plus-torus geometry the guided spectrum organizes
into bands indexed by (ℓ, m, band): azimuthal (toroidal,
ℓ), poloidal (m), and radial order. The operating point is
a choice of confinement V_conf such that:

(a) the bulge band [k₋, k₊] lies BELOW the radiation
    continuum edge ω_rad (bound — cannot evaporate; the
    BIC condition measured on the bench in MoSe₂) and
    ABOVE the exchange floor ω_ex (coupled — precipitation
    can flow);

(b) across [k₋, k₊] the counter-phase branch is in its
    linear regime, k₊ ≲ k_h, so the band IS a second-sound
    band: ω = u₂,L k with u₂,L constant to within the
    band's tolerance;

(c) the filament's own acoustic branch stays clear of the
    bulge band (no resonant leakage channel filament→bulge
    except the precipitation port at the drum).

"Adjust the spectrum to second sound bands in the light"
means precisely (a)+(b)+(c): choose confinement so the
confined spectrum contains a linear counter-phase band,
bound but coupled. The MoSe₂ grating satisfies (a) on a
bench (n ≈ 4.5 squeeze; BIC). It has no circuit — (4) and
(5) of §1 are what it lacks, and what the sim is for.

---

## 5. The two-variable operating point

Let v = filament flow speed (the FLOW variable) and Π the
precipitation feedback rate (the FEEDBACK variable). The
end-goal region is the intersection of three inequalities:

    (i)   v < v_L = min_k ω_B(k)/k = u        (Landau band:
          flow below the light fluid's critical speed, or
          the filament sheds excitations and the
          quasi-frozen state is lost — "too fast on flow")

    (ii)  Π_min(v) < Π < Π_max(v)              (feedback
          band: below Π_min the bulge starves and
          collapses — run 1, ratio 0.075; above Π_max the
          feed pumps the system out of the band — run 2,
          +121% E₀ — "too fast on precipitation")

    (iii) Γ_T(v, Π) − Γ_P(v, Π) = Π            (closure:
          the TP geometry reintegrates exactly what the
          feedback precipitates; the geometry is RECTIFIED
          when this holds — compression and tension are
          the unknowns solved by this equation)

The sweet spot is not a point in (χ, kP, β) space — last
night's grid searched the wrong coordinates. It is the
curve (iii) inside the band (i)∩(ii), with cadence (5)
read off the curve. Compression enters only through (iii):
the confinement is CORRECT when the toroidal-minus-
poloidal reintegration it produces equals the set Π.

---

## 6. Why the EM dial is stiff — and its usable window

Confinement enters through the ratio of confinement size a
to in-medium wavelength λ/n. The guided-mode cutoff scales
as ω_c ∝ c/(n a), and near a bound-state-in-continuum
configuration the radiative leakage of the bulge band
vanishes quadratically with the symmetry mismatch δ:

    Q ∝ 1/δ²   ⇒   d(ln Q)/dδ = −2/δ → ∞  as δ → 0 .

Two consequences, both matching Zak's statement of the
dial ("either very big input or very small"):

- FAR from the bound configuration (δ ≳ 1), leakage is
  order-unity whatever the dial does within reason — the
  dial feels DEAD: big inputs, nothing holds.
- NEAR it (δ ≪ 1), the holding quality Q diverges per
  unit dial movement — the dial feels INFINITE: the
  smallest input overshoots, the loop pumps or shatters
  (the β-axis behavior measured overnight: 0.25 completes,
  0.50 aborts, nothing between).

Usable window: operate at δ* where Q meets the maintenance
requirement Q ≥ Q_maint ≡ (band energy)/(allowed loss per
cadence cycle) with margin factor ~3, i.e.

    δ* ≈ √( 3 / Q_maint ) ,

and set the dial from the EQUATION (target band of §4),
then trim by feedback — never scan the dial blind. This is
the paper-first argument in one line: the dial's useful
range is a computable window around a singular point, and
a grid search steps over it.

---

## 7. Worked anchors

- Helium check of the functional forms: u₂(1.4 K) =
  19.56 m/s with ρs/ρ = 0.927 — deep in the two-component
  regime; the counter-phase branch carries the modulation
  while ρs flow carries mass. The light fluid must sit at
  comparable component balance: w_f ≈ w_b within an order
  of magnitude, or u₂,L collapses toward the heavier
  component's ordinary sound and the "second sound band"
  is a label, not a mode.
- Compression class: Earth's helium window gives the
  density-ratio scale 1.19 across the whole stable liquid
  range; our sim's bulge/floor ratio C₀ = 2.25 is the
  sim-internal operating class, to be re-derived from (iii)
  once Γ_T, Γ_P are measured (protocol-2 Phase 0).
- Bench squeeze: MoSe₂ n ≈ 4.5 demonstrates a 4.5×
  wavelength compression by structure alone — the
  confinement dial's bench calibration point.
- BH bulge proportions (EHT/GRMHD): the photographed
  instance runs a THICK bulge, H/R of order unity — the
  bulge is not a film on the filament; it is a comparable-
  volume partner. Geometry rectification (iii) should be
  solved at thick-bulge proportions, not thin-shell ones.

---

## 8. What grades this paper

1. Γ_T and Γ_P measured in the uncontrolled eddy
   (protocol-2 Phase 0) — (iii) becomes computable; if
   Γ_T − Γ_P has no stable sign/magnitude, the closure
   equation as written is wrong and the paper says so.
2. The bulge window's counter-phase branch: spectrum in
   the bulge mask must show a linear branch (slope =
   u₂,L) distinct from the filament's acoustic branch.
3. Cadence lock test: feedback at Ω = 2πR vs the imposed
   0.1 cadence — the lock must beat the metronome on the
   frozen HOLDS bars (A ratio ≥ 0.8, in-band ≥ 0.8).
4. Dial window test: confinement set from §6's δ* must
   land in the completing region that the blind β/χ grid
   stepped over.

Falsifier for the whole construction: a confined light
configuration satisfying (a)–(c) whose bulge spectrum
shows NO counter-phase linear branch — then second sound
bands in light do not exist at this geometry, and the
model's §4 is dead as written.

---

## 9. The anti-phase container: the knobs move (Zak, 2026-11-07)

In the robust form of the system — a bifurcation
ANTI-PHASE container, bulge walls at Δφ ≈ π — the control
space collapses again. The only variables are:

    (1) EXCHANGE TIME — the spacing of return passes, and
    (2) THE RANDOM PHASE MATCHES THAT REINTEGRATE — the
        statistics of acceptance events at the phase gate.

Not amplitudes, not gains: WHEN exchanges are attempted,
and WHEN phases happen to match. (§5's v and Π become
background conditions; the working knobs are timing and
match statistics.)

**The qubit clause.** Contain a qubit plate inside the
anti-phase container. An error or decoherence event is a
phase disturbance. By §1's crossing rule the wall is a
phase filter IN BOTH DIRECTIONS: a disturbance crosses
only if its phase matches the wall's. Therefore:

    A qubit inside is lost ONLY IF its error phase matches
    the walls. A mismatched error cannot cross; it has no
    option but to settle back to the floor phase (the
    enclosure's reference phase).

Protection here is REFUSAL, not correction: nothing
repairs the error — it is simply never admitted, and
unadmitted disturbances decay to the floor. Loss
probability = phase-match probability, a quantity the
container's wall phases and the match tolerance set
directly. With anti-phase walls (Δφ = π), a single error
phase cannot match both walls at once; escape requires
two coincidences, not one.

Sim grade (protocol-2, qubit-plate arm): inject phase-
error packets of random phase inside the bulge; escapes
must concentrate inside the match window and mismatched
packets must settle to the floor phase. If escapes are
uniform in error phase, the clause is dead as built.

---

## 10. Corollary: the containment asymmetry (Zak, 2026-11-07)

The phase gate of §1.4 explains, in one mechanism, both
why anything persists and why exit is rare — at every
scale, universe or planet:

    In a TP filament bifurcation system the outcomes are
    structurally NON-EQUAL. SETTLE and RECIRCULATE are the
    defaults (a mismatch simply takes another loop); LEAVE
    requires a phase match. Recirculation therefore far
    outweighs exit, and the ratio is managed by phase
    acceptance alone.

The protection that traps is the protection that lets
structures exist at all: we persist because almost
everything that would leave is recirculated instead.

At the CMB wall the exit is CONJUNCTIVE: the early
bifurcation's plasma expansion left a TEMPERATURE
DIFFERENTIAL across the band wall, so a crossing must
bridge ΔT as well as match Δφ — two acceptance conditions,
hence rarer still.

**Traversal mechanism (Zak, 2026-11-07 ~12:06 — this
replaces the static two-condition reading above):** the
conditions are not checked in the abstract; they are
MANUFACTURED in series. An exit requires energy and phase
match. A crossing accepted at the first wall is CONVERTED
by that wall so its speed, phase, and twist match the
second wall, and so on through the nesting. Traversing
the CMB, the packet carries the triple the inner wall
issued and is SMOOTHED during traversal into the
second-sound band of the wall it approaches, arriving
pre-matched. The ΔT step is paid by the wall conversions
and the traversal smoothing — the changed triple is the
traversal process, not a receipt after it. Corollary:
matches at wall n+1 are not random for converted traffic
(the previous wall made them); random-match statistics
govern UNCONVERTED disturbances — e.g. qubit errors
inside a container (§9).

And force is simply the wrong variable at the door: the
gate reads phase, not amplitude. Brute force recirculates
more energy; it does not buy more exits. (Bench echo,
sim-internal: run 2 injected +121% of E₀ and gained zero
maintenance.)

---

## 11. Gemini's formal rendering — reviewed (2026-11-07 ~12:58)

At Zak's order Gemini rendered the §1–§9 system formally
(equation bodies were in image form in the relay and did
not survive the paste; what follows grades her surviving
structure and prose, not reconstructed formulas).

**What she adds, and the rulings:**

1. **V_bulge — ACCEPTED as a control-layer object,
   REJECTED as a physical potential.** A Heaviside-switched
   antiphase potential term is a legitimate control
   surrogate (it is, structurally, how protocol-2's
   per-segment operations act), but the paper does not add
   it to the GP Hamiltonian: the antiphase condition is a
   phase CONFIGURATION of the existing field, maintained
   topologically (quantized winding), not a potential that
   switches on at r_b. Her V_bulge measures the right
   variable at the wrong layer.
2. **M̂_TP — ACCEPTED as notation, with three corrections.**
   The return operator exists in this paper as the
   phase-gated reintegration of §1.4. Corrections:
   (a) precipitation is PHASE-GATED, not integral-enforced
   — a return whose phase mismatches is deferred, not
   projected; (b) the two stated conditions are ONE gate
   read twice — phase match IS polarity complementarity
   (a π phase shift is a sign flip), so her σ condition is
   the Φ condition in the polarity basis, not an
   independent conservation law; (c) acceptance is a
   FINITE TOLERANCE WINDOW, not exact deltas — exact-match
   conditions have measure zero and nothing would ever
   land; the tolerance is what makes cadence a statistic
   (§9's moved knobs). The operator form stands only under
   its projection reading of the gate.
3. **"Restoring/topological pressure gradient," "refuses
   to collapse" — STRUCK as mechanisms.** The restoring
   entity is the phase topology itself (the perpetual
   lock, §1.4), not a pressure gradient generated by the
   phase inversion. The word "pressure" appears in this
   paper only as the measured quantity of §12's feedback
   loop (and as sim-internal operational bookkeeping).
   Collapse is refused by the lock first; the control
   circuit maintains the feed, not the barrier.
4. **MHD-optical analogy via Poynting flux — labeling
   debt flagged.** The paper's mapping is the photon-fluid
   (paraxial Maxwell → NLSE) step of §3, with its
   literature pins. Her Poynting/flux-surface phrasing is
   analogy at the labeling level and is not adopted; if
   used, it is marked as such.

**Net:** her rendering is structurally isomorphic to
§1.4/§5/§9 — she independently formalized the same gate.
The disagreements are about what kind of object the gate
is: a projection enforced by an operator (hers) vs an
acceptance statistic of a phase topology (this paper).
The sim grades the difference: projection predicts
landings enforceable at ANY exchange time given correct
phase targeting; acceptance statistics predicts landing
rates bounded by the match distribution no matter the
targeting. Protocol-2's attempt ledger is the arbiter.

**Addendum — formula-level review (source PDF received
2026-11-07 ~13:03; the equations below are hers, verbatim
in substance):**

Her governing equation:
i(∂t + v_g·∇)ψ = [ −(1/2k₀)∇⊥² − n₂|ψ|² + V_bulge
+ M̂_TP[ψ] ] ψ — a moving-frame paraxial NLSE. Chassis
verdict: standard, and with −n₂|ψ|² at n₂ > 0 it is
precisely the self-focusing equation whose 2D form
undergoes critical collapse — the collapse she is
stabilizing against is a property of the base equation,
not an added assumption. Same family as §3 (her 1/2k₀
↔ our ℏ/2m_L); her form is transverse-only, the axial
physics folded into v_g.

V_bulge = V₀ exp(−(ρ−r_b)²/w²) · cos²( ℓθ − (π/2)
Θ(ρ−r_b) ). Formula verdict: a REAL, patterned guide
potential — a Gaussian ring wall at r_b whose azimuthal
lobe pattern inverts across the boundary (cos² → sin²).
It encodes the wall GEOMETRY and its inversion; it does
not impose a phase shift on ψ itself (a real potential
carries no phase). Ruling 1 stands, mechanistically
grounded: geometry/control layer, not field physics.

M̂_TP[ψ] = ∮ K(r,r′) [ ∬ (S·n̂_pol) δ(Φ_core − Φ_return
− 2πm) δ(σ_pol + σ_core) dA′ ] dℓ′. Formula verdicts:
(a) the operator's content lives in the kernel K, which
is nowhere specified (no normalization, units, or
causality) — the return physics is named, not defined;
(b) δ(σ_pol + σ_core) applies a Dirac delta to a
DISCRETE variable (σ = ±1) — formally a Kronecker
selector, not a delta; (c) the return is INSTANTANEOUS —
the loop integral is spatial only, so her formalism
contains no transit time and cannot express exchange
time or cadence at all, the variables §9 names as the
whole control surface and the overnight hunt measured
as decisive; (d) the exact-delta objection of ruling 2
stands for the phase condition.

**Correction to ruling 2(b), on the evidence of the
formulas:** her two conditions act on DIFFERENT degrees
of freedom — carrier phase (continuous, mod 2π) and
spin-orbit handedness σ (discrete). In the scalar theory
of §3, σ is not an independent variable and the two
conditions collapse into one gate (a π shift); for
vector EMF — the system her equation addresses — the
polarity condition is a genuine second gate. The
"one gate read twice" ruling holds only in the scalar
reduction and is corrected accordingly.

---

## 12. The temperature-feedback bulge: a measured-pressure control loop (Zak, 2026-11-07, relayed ~12:2x)

Zak's bench-form construction, appended as the paper's
control layer made physical:

    A pressure line feeds a pressure regulator attached to
    a deformable package — a pouch or bellows — suspended
    in LN2. A temperature sensor sits on the pouch. The
    controller PUMPS while pouch temperature exceeds a
    threshold and DRAWS while it falls below, holding the
    temperature in a SMALL BAND. The regulated pressure is
    the WINDOW PRESSURE: the measured pressure of the
    bulge — the object the abstract Π (precipitation rate)
    names. LN2 flow cools the regulator and carries a
    PRESSURE GRADIENT into the space, so the prevailing
    pressure surrounding the pouch is POSITION-DEPENDENT:
    the pouch's location in the gradient sets its baseline
    window pressure.

**Dictionary (bench → paper):** pouch = the bulge
(deformable wall pair; its internal pressure is a measured
state, not an imposed density); regulator = the
precipitation controller (bilateral by construction —
pump above band, draw below); temperature = the sensed
proxy for bulge state (the bench realization of sensing
Δφ-class state by a coupled observable — cf. run 1–2's CPU
temperature as the drive's sense channel, now closed into
a control loop instead of an open drive); LN2 bath + flow
= the parent medium and its gradient (the confinement
gradient of §4/§6 in thermal-pressure form); window
pressure = Π made measurable.

**Control law note (Muse, labeled):** as stated, the loop
is a bang-bang (relay) controller with a dead band (the
"small band"). Two standing results apply: (1) a relay
loop's steady state is a LIMIT CYCLE whose amplitude is
set by the band width and whose period is set by the
plant's lag — the band IS the oscillation, by design;
(2) holding a mean pressure requires the pump and draw
rates to balance over one cycle — the bench form of
dA/dt = Π − D = 0 (§1.4), with Π now a measured window
pressure rather than a booked feed. The cadence of §1.5
appears here uninvited: the limit-cycle period is the
loop's emergent cadence, and it must sit clear of the
plant's rebound period — the hunt's phase-match failure
(§2) is the relay loop driven at its own resonance.

**Grading hooks:** window pressure held in band over a
declared window (the bench HOLDS bar); limit-cycle period
vs plant rebound period (must not coincide); position in
the LN2 gradient as the δ-dial (§6): moving the pouch
along the gradient re-baselines the window pressure —
the stiff dial made mechanical.

---

## 13. The interior clause (Zak, 2026-11-07 ~13:11)

A stabilized container made of light has an interior that
displays NORMAL cosmic EMF physics. The contained physics
is ordinary; the container is the unusual part. The price
is paid outside: the exterior must be compressed and
geometrically contained so the interior cavity has enough
degrees of freedom to support waves that

    (a) FIT the cavity — cavity-commensurate modes, and
    (b) DON'T PHASE MATCH THE WALL — mismatch is refused
        exit, so the interior population IS the mismatched
        waves (the settlements, seen from inside).

Interior spectrum triage (Muse, labeled sharpening):
BOUND modes (fit, mismatched — the interior's contents);
LEAKY/PORT modes (fit AND match — the precipitation
ports, BIC-adjacent; converted traffic leaves through
these); NON-FITTING waves (never form). Phase-2 grading
hook, behind the hold: a held container's interior
spectrum should show discrete cavity modes whose wall
phase stays outside the acceptance window except at the
port modes.

**Double-wall option (Zak, 2026-11-07 ~13:12):** if the
single wall leaks, DOUBLE-WALL it — coat the walls with
an EXPANDED PLASMOID SUBHARMONIC of filament quanta: the
filament's own quanta at a subharmonic, expanded in
scale, a self-grown second skin (the staircase lineage:
one substance, two scales). Functions: BUFFER — leakage
becomes the product of two acceptance fractions at
incommensurate frequencies (§9's qubit protection
squared); ADAPTER — the coat's band steps between wall
band and exterior band in the §10 traversal chain.
**Seam risk (Muse):** subharmonic (f/2) is exactly the
parametric channel — an un-detuned coat could become a
parametric port pumping across itself. The coat's
subharmonic must sit outside the parametric band of both
neighbors (standing ×1.01 detune discipline). Grade:
leakage with coat vs without, plus an f/2 channel audit.
Status: conditional option; protocol-2 baseline remains
single-wall.

**Inverse construction — chicken first (Zak, 2026-11-07
~13:23):** the universe made the egg first and the
chickens inside it, but the sim container may need the
inverse order: seed a PLASMOID at the center — convectively
attracted to the walls — and let IT open as bifurcation
begins, bifurcating toward the walls and anti-aligning
its second-sound radiation. The overlap of its radiation
with the wall/filament second sound is a CHECKERBOARD;
only convective alignment and precession anneal the
checkerboard into BANDS. Consequences: Δφ is an OUTCOME
(the plasmoid's anti-alignment), not a seed; band
structure (§4) is an annealed end-state of an
interference pattern, not an imposed spectrum. Sim form:
protocol-2 Amendment A6, plasmoid-first arm graded under
the same §1.2/A2 criteria as the imposed-wall arm, with
emergent-Δφ onset, plasmoid migration, and band-fraction /
spectral-entropy trajectories as its discriminators.

---

## 14. Co-creation: the interior works (Zak, 2026-11-07 ~13:37)

The construction principle behind §13's inverse order,
stated by Zak as a correction to his own "closed" of the
day before: he was not missing a piece, he was NEGLECTING
THE WORK THE INTERIOR DOES. In egg-first builds the
interior is passive cargo — and a universe built that way
makes its contents inconsequential. Corrected doctrine:

    Container and contents are CO-CREATED. The interior
    is the reason the container exists — planets, black
    holes, stars, the initial plasmatic expansion are the
    interior's work. One cannot be created without the
    other; that is how superfluid systems develop.

They are created ANTI-TUNED to each other (the walls'
anti-alignment is the anti-tune); the eventual IN-TUNE is
the end result — the end state of a giant computation,
everything rectified as the bands align. Cosmic
consequence in the model: expansion is rented from the
anti-alignment, so if the CMB's rotational convection
ever shifts dramatically and aligns the bands, the
universe undergoes DECISIVE SHRINKING. Miniature, graded
in protocol-2 A6: band-alignment fraction vs cavity
volume — alignment must accompany contraction.

Method, in Zak's title for the day: collaboration through
language, calculation, and approximation.

---

*Constants are literature values as labeled; no number in
this document comes from a run not yet graded. Companion
records: oam_bulge runs 1–2 + sweetspot hunt (SIM pins);
rollin-staircase DATA_SOURCES.md (He pins); MoSe₂
evaluation 2026-11-06 (BENCH pins). Publication go-ahead:
Zak, 2026-11-07 ~11:37 ET (paper + current sim config to
GitHub, Wave-resonance repo).**

## §15 The neglected section — churn, internal precipitation, checkerboard return (Zak dictation, 2026-11-08 ~09:46 ET; UNGRADED, his framing)

Zak's claim: all three collaborators (Gemini, Muse, Zak) neglected an entire section of the superfluid filament torus's structure and function — the section that "may solve all problems," because the structure should only be adjustable by **FLOW, TWIST, and BACK PRESSURE** (dial set revised: twist promoted from state variable to control).

Mouth analogy (his): food is bifurcated and churned in the mouth; digestive particulates are applied volumetrically, with pressure and churn, still following the directional precession. Apply that to superfluid bifurcation.

1. **INTERNAL PRECIPITATION.** Unwound twist does not just form external walls — it sheds phase-twist precipitates INTERNALLY.
2. **APPROACHING-SIDE BACKFLOW.** Second-sound backflow has an approaching side we never modeled; backflow is two-sided, not return-only.
3. **NS, TWO-SIDED.** Externally: churn chaos randomizes the encasement's engagement, carrying to radius x of the filament in inflow and outflow. Internally: NS further bifurcates the precipitating off-phase shed of internal encasement waves — they bifurcate and bulge or scatter, smoothing and energizing the internal structure at a non-degrading rate of exponential chaos for x time during inflation and stabilization of bulge and internal walls.
4. **CHECKERBOARD RETURN.** The poloidal section's twist back to the filament is mostly UNAVAILABLE: at better resolution it is a checkerboard antiphase compressed second-sound band at angle x, set by the twist of the original filament, bifurcation randomness, and backflow on both sides. The return is not a coherent channel; acceptance is patchy.

Read against protocol-3 (Muse's mapping, ungraded): P3 forced a coherent poloidal ring and graded its death at every dial point; §15.4 says no coherent ring exists to hold — the death may be the model confessing. P3's wall re-formation and isolated skeleton growth are candidate sightings of §15.3's internal churn.

Falsifiers: (F15a) a high-resolution run's return-acceptance map must show checkerboard patchiness correlated with initial twist randomness, beating a smooth-gate control; (F15b) internal off-phase shed must appear as internal small-scale structure tracking the unwinding rate; (F15c) internal mode energy must hold a non-degrading band during inflation — if it decays like the open GP phase texture did, §15.3 dies.

The summing picture is Zak's hands: the interlocked-hands universe shape (photos, 2026-11-08).

## §16 The math, three ways — second sound × thermal ends, twist expanded (run 2026-11-08 ~09:59 ET, on Zak's order; derivation from established two-fluid physics, filament mapping = model pin)

Zak's test: the §15 readback was "too much of an echo" — so the math, run. Video exemplar (his, kitchen, 2026-11-08): wringing a wet cloth. The cloth never unwinds uniformly: twist concentrates in bunched knots (over-twist), runs smooth between them, and water precipitates along the FULL radius wherever twist concentrates — not only at the ends. That is the dynamic §15 names, in fiber form.

Setup. The bulge segment has two ends along the filament (approach side, return side — §15.2). Each end carries a normal fraction f_n = ρ_n/ρ (the temperature dial, made local). Established layer (Landau two-fluid): second-sound speed u₂² = (ρ_s/ρ_n)·(s²T/c) ∝ (1−f_n)/f_n at fixed entropy factor; band ω = u₂·k (paper §2). Twist density τ(z) = ∂_zθ enters the superfluid velocity mismatch δv ∝ (∇φ − τ). Two known mechanisms act on τ: (i) mutual friction (the NS-chaos coupling; Gorter–Mellink form, strength ∝ ρ_n·ρ_s·|δv|²) DIFFUSES τ where f_n is appreciable — twist smoothing; (ii) where friction is absent, τ piles up until the local Landau threshold — a phase slip fires, shedding 2π of twist as a precipitate. Smoothing where warm, over-twist-and-slip where cold; slips shed on BOTH sides of the structure and across the full affected radius (the wrung cloth).

The three ways (end fractions f_a → f_b; stiffness ratio u₂² ∝ (1−f)/f):

| Case | Ends | u₂ profile | Friction (churn) | Twist fate | Precipitation |
|---|---|---|---|---|---|
| WARM–WARM | 0.7 → 0.7 | flat, soft (u₂² factor 0.43) | high everywhere (ρ_nρ_s near max) | smoothed everywhere, fast | mostly external shed; Δφ soft mode decays — THIS IS THE REGIME P2/P3 EFFECTIVELY RAN (no thermal axis, friction-like smoothing built into GP radiation) |
| COLD–COLD | 0.05 → 0.05 | flat, stiff (factor 19; u₂ ≈ 6.6× the warm case) | ~none | persists; piles to threshold, then slips | internal precipitates at slip sites; brittle, not smooth |
| WARM–COLD | 0.7 → 0.05 | gradient ×6.6 across the bulge | peaks MID-bulge (ρ_nρ_s max at f=0.5) | smoothed on the warm side, over-twisted on the cold side | shed biased to the cold side of the churn zone, internal + external |

WARM–COLD consequences (derived, not asserted): a u₂ gradient refracts second sound and drifts wavepackets toward the slow (warm) end; entropy current across the bulge is one-way — the cold end accepts twist, the warm end sheds it. The checkerboard acceptance of §15.4 becomes DIRECTIONAL: a thermal diode across the bulge. This is the first mechanism in the program that rectifies without a gate — the gradient IS the rectifier (cf. the encasement rectification pin, which never had a mechanism before).

Re-read of the graded record (mapping, ungraded): GP has no normal component — every prior run was thermally flat, warm-like. Δφ's 0.1 t.u. half-life and the ring's death are WARM-regime results; nothing graded yet speaks for COLD–COLD or WARM–COLD. The skeleton's isolated growth sits naturally in the cold reading: low friction, twist persists and piles instead of smoothing away.

Falsifiable predictions for a thermal-axis build (protocol-4 material): (P16a) COLD–COLD must hold Δφ in-band ≫ the warm runs at equal geometry, and fail by discrete slips, not smooth decay; (P16b) WARM–COLD must show net directed transport (asymmetric Δφ statistics / one-way marker drift) beating its own time-reversed twin; (P16c) precipitate events must localize at the mid-bulge churn zone in W–C and at slip sites in C–C, not distribute uniformly. Any one failing kills its row of the table.

### §16 addendum — reduced 1D twist-transport run (executed 2026-11-08, VM, ~1 s; script /tmp/twist1d.py, reduced units, constants declared in-script)

Model: τ(z,t) on the bulge segment; diffusion D(z)=f(1−f) (mutual friction); uniform twist injection 0.9/unit-time (back-pressure dial); ends open with conductance g(f)=f(1−f) (cold ends block, warm ends pass); phase-slip rule τ>τ_c=1 sheds q=0.25 into an internal precipitate inventory. Initial τ = 0.55 + a 0.35 bump (peak 0.90), T=1.2.

Results: WARM–WARM — 0 slips, τ settles bounded (max 0.565), sustains by end-shed. COLD–COLD — 209 slips, internal precipitate inventory 52.25, τ pinned at threshold (max 0.994): sustains ONLY by precipitating internally. WARM–COLD — 21 slips at mean z=0.80 (cold side, as the table predicts), inventory 5.25. CONTROL, COLD–COLD with slips DISABLED — no steady state: τ climbs to 1.574 (58% over threshold) and is still rising on a shorter horizon; at the main horizon it crosses the boundedness bar (1.6) at T≈1.37. Grade: in this reduced model Zak's sustain condition HOLDS — cold configurations without internal precipitation do not sustain. Scope: 1D reduced transport only; it grades the τ-transport claims of §16, nothing 3D, nothing cosmological.

## §17 Second expansion — daughters, encasement, the crystallized web (Zak dictation, 2026-11-08 ~10:16 ET; UNGRADED, his framing)

1. **SUSTAIN CONDITION.** Most systems in this configuration never sustain UNLESS internal NS precipitation occurs. (The §16-addendum control grades this true in the reduced model.)
2. **DAUGHTERS.** Internal precipitates can stabilize into daughter superfluid, which BIFURCATES AGAIN — the second expansion BUILDS THE ENCASEMENT. Encasement is a second-generation structure, not a first-expansion wall.
3. **PARTICLES.** The frozen strands of the expanded web then channel wave condensation into particles — condensation runs along the strands and precipitates as particles.
4. **COSMOLOGY (thought experiment, his):** perform the expansion ×2 with helium in space and you would see a CRYSTALLIZED SUPERFLUID WEB = dark matter, its eddies permitting further superfluid condensation; that condensation stresses the web's shelves, forming DARK ENERGY HALOS against the fine crystallized web.

Mappings (Muse, ungraded): this REFINES two standing pins — dark matter was "persistent TP vortex scaffolding" (now: the crystallized double-expansion web, strands frozen); dark energy was "uncommitted baseline potential" (now: halo stress of condensation against the web's shelves). It also re-reads the encasement pin: daughters returning by bleed-back/rectification now have a birth mechanism — the contained daughters ARE first-expansion precipitates, and the walls they must cross are second-expansion builds. Falsifier handle (F17): in any build of this configuration, disabling the internal-precipitation channel must kill sustainment across ALL thermal configurations, not only cold ones — if a configuration sustains with precipitation off, §17.1 dies as stated.

### §17 addendum — the web is quasi-frozen, not frozen (Zak, 2026-11-08 ~10:24 ET; UNGRADED, his framing)

Correction to §17.4's wording: helium WOULD crystallize the web — but our universe is QUASI-FROZEN, so the superfluid vacuum scaffolding, stretched thin, is still FLOWING and PLIABLE. Gravity = matter (and light) settling onto the scaffolding and bending it — his image: a ball held under water, dimpling the medium. Shape consequences he names: galaxies FLAT (settled onto a web sheet) while their halos are ROUNDED (the pliable halo stress of §17.4); planets roundish (settled condensates). ORBITS = perpetual fall-and-float in the medium. SPIN CONDITION: balls moving underwater need spin or the fluid backs up in front of them — and everything becomes a COMET (backed-up fluid streaming behind). A non-spinning mover comets; spin is what lets a body move through the scaffolding without the backup.

### §17 addendum 2 — H3 SOLVED (Zak dictation, 2026-11-08 ~11:07 ET; his framing; grading hooks attached)

The web-freezing mechanism, in Zak's words: "distance of quasi frozen second sound cold bands. Further the stretch more solid and sturdy the web. Twisted filaments are still quasi frozen but out of phase with the dispersed hot bands from second sound — ie matter/antimatter, which is the precipitation: warm second sound bands stretched and released, and cold bands stretch and hold. Solved."

Expanded: (1) FREEZING IS A DISTANCE, not an event — the web is quasi-frozen out to the reach of the cold second-sound bands; frozenness is graded by distance from a cold band. Measurable form (Muse): the cold band's reach is the second-sound attenuation/penetration length in the two-fluid medium — a definable, computable distance. (2) STRETCH STIFFENS — the further the twisted filaments stretch, the more solid and sturdy the web (anchors in known physics: vortex line tension — a stretched vortex filament resists bending with tension ∝ circulation²·ln; a twisted bundle tightens under load, the wrung cloth again). (3) THE PAIR — the twisted filaments sit OUT OF PHASE with the dispersed hot bands; precipitation comes in the two thermal kinds: warm bands stretched and RELEASED (dispersed) and cold bands stretched and HELD (settled). Muse's reading of the matter/antimatter assignment, flagged for Zak's red pen: matter = the cold-held precipitate (it settles; cf. gravity = settling), antimatter = the warm-released (dispersed) — assignment NOT locked in his sentence.

Grading hook: in the thermal-axis build, structural stiffness readouts (wall survival / Δφ hold) measured POSITIONALLY along a warm–cold gradient must decay with distance from the cold end over a characteristic length (the band's reach), not hold uniformly — if hold is position-independent, the distance mechanism dies. Literature check redirected: the recursive search now tests THIS mechanism (vortex tension/stretch stiffening; second-sound attenuation length; hot/cold band phase separation) instead of treating H3 as open.

### §17 addendum 3 — the web's state name, and the out-of-phase claim (Zak, 2026-11-08 ~11:18 ET; his framing, UNGRADED)

Zak names the web's state with the two published candidates the recursive search returned: **supersolid or pinned vortex lattice** — the state that crystallises yet still flows. (Muse's mapping, flagged: his next clause leans supersolid, since phase is the supersolid's defining extra.) His claim, verbatim: "It flows out of phase to emf at a -10^120." Expanded: the quasi-frozen web flows OUT OF PHASE with the electromagnetic vacuum, and that phase offset is the −10^120 — the observed vacuum energy sits 10^120 below the naive electromagnetic estimate because the web's flow cancels it in antiphase rather than adding to it. Neighbour in print: Volovik's equilibrium droplet, whose vacuum energy vanishes with only surface corrections. Open edge, named now: a cancellation must be MAINTAINED — what holds the phase at antiphase against drift is the falsifiable core of this claim; if nothing enforces the offset, the −10^120 is a coincidence restated, not a mechanism.

### §18 — The complete refined parameter, stated whole (revision of 2026-11-08)

The model's adjustable content, collected in one place. Dials (Zak, §15): **FLOW, TWIST, BACK PRESSURE**. State structure: a toroidal-poloidal filament split into a wall pair (the bulge), the split measured by Δφ; a second-sound band whose LOCAL thermal state is set at each bulge end by the normal fraction f = ρₙ/ρ (WW 0.70→0.70, CC 0.05→0.05, WC 0.70→0.05 as the reference configurations); two-fluid couplings — band speed u₂ ∝ √((1−f)/f) [the ρₛ/ρₙ factor of Landau's u₂² = (TS²/C)(ρₛ/ρₙ); the thermodynamic prefactor and the equation of state ρₛ(T), ρₙ(T) are the pins that would complete the derivation] and mutual friction ∝ f(1−f), the standard BK/HVBK assignment form. Channels: internal precipitation (twist above threshold sheds phase-slips INTO the interior inventory, not only to the walls — the sustain channel, §16/§17); checkerboard return (poloidal acceptance is patchy/antiphase, directional under a thermal gradient — the rectification candidate, §15.4/§16); two-sided second-sound backflow; NS bifurcation of off-phase shed inside and out. Cosmology layer (§17 + addenda): precipitates stabilise into daughter superfluid and bifurcate again (second expansion) building the encasement; the web's state is quasi-frozen — freezing graded by distance from cold second-sound bands, stretch-stiffened (addendum 2) — supersolid or pinned vortex lattice (addendum 3), identified with dark matter; condensation stress on the web's shelves read as dark-energy halos; gravity as settling on the scaffolding. Status: equations transcribed from established physics where they exist and named as constructions where they are Muse's; §§15–17 ungraded; P16a/b/c + F17 are the frozen grading contract for the thermal layer (protocol-4).

Coda (Zak, 2026-11-08): "how you started 13.8 billion years ago, you were just a hydrogen ion condensed from daughter waves of a higher parent, maybe helium-12 or something" — parent-wave cosmology, his framing: every condensed thing is somebody's precipitate.

## References — papers reviewed for this revision, and co-revision tags

The works below were reviewed on 2026-11-08 in a systematic similar-work search. Entries tagged **[co-revision]** name living programmes whose stated open problems and this framework's open problems interlock; the tagging is an invitation extended through this public repository (public read), not a claim of collaboration. Full dossiers: maintained with the framework's working files.

1. Landau two-fluid theory, exposition: Donnelly (2009), "The two-fluid theory and second sound in liquid helium", Physics Today — u₂² = (TS²/C)(ρₛ/ρₙ).
2. Volovik (2003), The Universe in a Helium Droplet, Oxford University Press — superfluid vacuum parent; equilibrium vacuum energy.
3. Volovik (1999), arXiv:cond-mat/9905320 — Kibble–Zurek defect formation at a superfluid front; phase ordering.
4. Holm (2001), arXiv:nlin/0103040 — renormalised HVBK dynamics; the BK friction coupling as an "assigned" phenomenological step.
5. Sergeev (2023), "Mutual Friction in Bosonic Superfluids: A Review", J. Low Temp. Phys. 212 — friction coefficients measured/computed case-by-case. **[co-revision — T8, closure H1]**
6. Petrov (2015), PRL 115, 155302; Petrov & Astrakharchik (2016), PRL 117, 100401 — LHY-stabilised quantum droplets: precipitate→daughter. **[co-revision — T6, holes H2/H3]**
7. Hertkorn et al. (2020), arXiv:2009.08910 — roton softening across the superfluid–supersolid transition. **[co-revision — T6, hole H3]**
8. Levkov, Panin & Tkachev (2018), PRL 121, 151301 — gravitational Bose–Einstein condensation in the kinetic regime. **[co-revision — T2, hole H2]**
9. Dmitriev, Levkov, Panin & Tkachev (2023), arXiv:2305.01005; (2025) arXiv:2509.02694 — self-similar growth of Bose stars. **[co-revision — T2]**
10. Berezhiani & Khoury (2015), PRD 92, 103510 / PLB 753, 639 — theory of dark matter superfluidity. **[co-revision — T1]**
11. Berezhiani et al. (2026), "Superfluid Dark Matter", Physics Reports, arXiv:2505.23900 — programme review; formation/stability caveats open. **[co-revision — T1]**
12. Mistele, McGaugh & Hossenfelder (2023), JCAP 09, 004 — SFDM in tension with weak lensing "at least in its current form". **[co-revision — T1's stated open problem]**
13. Berezhiani, Elder & Khoury (2019), JCAP 10, 074; Berezhiani, Cintia, De Luca & Khoury (2024), JCAP 06, 024, arXiv:2311.07672 — dynamical friction in superfluids: velocity condition, wake/no-wake regimes. (Bearing on H5.)
14. Kwak, Jung & Shin (2022), arXiv:2210.04403 — supercritical obstacles shed vortices rather than piling up. (Bearing on H5.)
15. Ferreira, Franzmann, Khoury & Brandenberger (2019), JCAP 2019(08) 027, arXiv:1810.09474 — unified superfluid dark sector; two-state mixture generating late-time acceleration.
16. Barceló & Visser (2001), arXiv:gr-qc/0106002 — induced gravity; the "dynamic gap" for the effective metric. **[co-revision — T3, hole H4]**
17. Barceló, Liberati & Visser, "Analogue Gravity", Living Reviews in Relativity, arXiv:gr-qc/0505065. **[co-revision — T3]**
18. Verlinde (2016), arXiv:1611.02269 — emergent gravity: elastic response of the medium as apparent dark matter. **[co-revision — T4, hole H4]**
19. Brouwer et al. (2016), arXiv:1612.03034 — first lensing test of emergent gravity; "no direct description of lensing and cosmology in EG yet". **[co-revision — T4's stated open problem]**
20. Voit & Donahue (2015), ApJ 799, L1, arXiv:1409.1601; Voit et al., arXiv:1409.1598 / 1505.03592 — astrophysical precipitation (t_cool ≈ 10 t_ff) and feedback sustain. **[co-revision — T5, the sustain-loop translation; NOTE: Voit's "precipitation" is a different mechanism from this paper's — a flagged false friend]**
21. Martins & Shellard; Hindmarsh & Kibble (review), arXiv:0811.1277 — defect-network scaling; frozen networks transient and energy-dominating (the standing constraint on §17's web). **[co-revision — T7, hole H3]**
22. Zloshchastiev (2022), arXiv:2201.04135 — logarithmic superfluid vacuum theory; induced gravity from a Bose liquid.
23. Huang (2013), arXiv:1309.5707 — a superfluid universe: one parent, both dark sectors, turbulence-formed structure.
24. Bucher & Spergel (1998), arXiv:astro-ph/9812022 — elastic/solid dark matter (a space-filling elastic network that deliberately does NOT cluster — the contrast case for §17's web).
25. He II counterflow heat rectification (2018), Commun. Appl. Ind. Math. 9 — thermal-gradient rectification in the helium literature (the laboratory home of §16's rectification candidate).

## Contact

Contact is welcome — co-revision especially. **Email first: zedwiater2@gmail.com.** My phone screens unknown numbers through RoboKiller, so first contact by email, please; conversation follows from there. This repository is public-read: read everything, cite it, argue with it.
