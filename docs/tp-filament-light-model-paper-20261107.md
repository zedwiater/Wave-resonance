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

*Constants are literature values as labeled; no number in
this document comes from a run not yet graded. Companion
records: oam_bulge runs 1–2 + sweetspot hunt (SIM pins);
rollin-staircase DATA_SOURCES.md (He pins); MoSe₂
evaluation 2026-11-06 (BENCH pins). Publication go-ahead:
Zak, 2026-11-07 ~11:37 ET (paper + current sim config to
GitHub, Wave-resonance repo).**
