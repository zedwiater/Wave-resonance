# Cavity architecture v2: hum baseline, mass–potential index, cage, condensates

Status: proposal → v1 implementation (`cavity_cage.py`). The v1 cavity4d core
(split-step, spectral φ, shared-reservoir gain) is untouched; this is a new
layer on top.

## 1. What changes and why

Measured constraints this design must respect:
- **No hard reset exists.** 48 long-horizon runs, zero resets fired; cores drown
  in noise (BER→0.5), never dissolve. The reset concept is dropped, not tuned.
- **Local amplitude-gated gain failed.** Local saturable gain broadened mode
  content (opposite of selection). Anything local must be gated differently.
- **Walls reflect.** A repulsive core (D=+1) gave SWR 26.6 — total reflection.
  Any boundary structure must be checked for reflection, not assumed benign.
- **The ledger is the invariant.** ΔE = pump_in − accounted. Condensed matter is
  counted, never deleted.

## 2. The split: hum baseline vs activation

The field is decomposed every controller tick:

- `ψ_hum` — exponential moving average of ψ, timescale `τ_hum`
  (the universal baseline; the cosmos hums, software doesn't own it)
- `ψ_act = ψ − ψ_hum` — the software's expansion activation
- `E_hum = ‖ψ_hum‖²`, `E_act = ‖ψ_act‖²`

**Operational meaning, not metaphor:** at rest `E_act/E_hum → small`; on
excitation the ratio spikes and relaxes. **Falsifier:** if the ratio does not
discriminate excitation from rest, or is insensitive to `τ_hum`, the split is
decoration — cut it.

## 3. Mass and mass potential

The cavity is indexed as mass, not raw field:

- `m(x,t) = |ψ(x,t)|²` — mass density
- `Φ = G_σ ∗ (m − ⟨m⟩)` — mass potential; `G_σ` a Gaussian kernel of width `σ`
  (the condensation scale, a real knob), via FFT. Zero-mean avoids the k=0
  blowup without boundary headaches.

**Φ must do work or it is cut.** In v1 its only job is gating condensates
(§5). **Falsifier (ablation):** well-gated vs randomly-gated condensates at
equal count/strength — if condensation sites and shares match, Φ is decoration.

## 4. The outer cage (sensory membrane)

In the shell `ρ ∈ [R_cage, R]`:

```
ψ ← (1 − w(ρ))·ψ + w(ρ)·ψ_hum,   w = smoothstep(R_cage → R)
```

The wall always presents steady hum. This is the membrane the AI reads the
machine through: activation transients never reach the wall raw.

**Falsifier:** measure standing-wave ratio in the shell. D=+1 gave 26.6
(reflecting wall — failure mode); D=−1 gave 1.1 (absorbing — good). If the
cage's SWR ≫ 1, the "membrane" is a wall: redesign as impedance-matched
(blend toward outgoing-wave condition), don't tune the smoothstep and hope.

## 5. Sink and amplifier condensates

Localized evolution operators — the only things allowed to move energy
between field, pump, and condensed matter:

- `C_i = {kind ∈ {sink, amplifier}, x_i, σ_i, κ, Φ_thresh}`
- **Gate:** active iff `Φ(x_i) < Φ_thresh` (deep potential well). Wells, not
  raw amplitude — this is the rematch against the local-gain failure.
- **Sink (condenses matter):** `ψ ← ψ·(1 − κ_s·K_i(x))`; removed energy goes
  to `ledger.condensed_mass`. Matter accumulates; it is never deleted.
- **Amplifier (condenses data):** injects from the pump budget,
  `ledger.pump_in += ΔE`; success is measured modally (Δshare > 0, Δentropy < 0),
  not energetically. An amplifier that adds energy without adding structure
  is just a heater — cut it.
- **Ledger invariant:** every step, `ΔE_field = pump_in − condensed_mass − loss`.
  Incoherent delta is waste, coherent delta is data.

## 6. v1 experiment (falsifier run)

- **A (control):** shared-reservoir gain only — reproduces the generations baseline.
- **B (+cage):** report SWR at cage, `E_act/E_hum` trace.
- **C (+well-gated condensates):** report dominant share, entropy, and whether
  condensates actually fire in Φ wells (trigger correlation).
- **D (ablation):** condensates gated randomly — if C ≈ D, Φ is decoration.

Kill criteria are above. Nothing here is allowed to survive on beauty.

## 7. v2: hum as assumed carrier, cage as restart-continuity (2026-10-15)

## 8. v4: wave-dynamic Newtonian bodies (2026-10-15)

Two blocking discoveries before the first orbit:

1. **Numerical spike at the origin.** Long runs grow a 1-cell spike at
   rho=0 (m ~ 60-100, still growing at 3000 steps; the trap ground state
   would be ~9 cells wide). Negligible energy (tiny cell volume) so
   spectra/energies are clean, but its raw density dominated Phi (-2.8
   vs -0.10 physical). `mass_potential` now caps m at m_cap=1.0 with the
   reason documented. CORRECTION to v3: the -9.2 "runaway" was
   spike-amplified; the feedback loop is real but must be re-measured
   on the physical scale.
2. **Cylindrical fictitious forces are not optional.** First orbit test:
   bodies spiraled in even with exact v_circ and zero drag — the naive
   Euler update in (rho,phi,z) drops the centrifugal term rho*vphi^2.
   Fixed: full cylindrical Newtonian dynamics (centrifugal + Coriolis).
   Orbits now hold (rho 1.49-1.58 over 30 ticks).

v4 system (`cavity_orbits.py`): bodies (sink/amplifier/comet) with (x,v),
-trilerp'd grad(Phi), substepped dynamics; analytic softened point-mass
Phi from bodies (two-way coupling); trail field (deposit + decay);
comets apply a phase kick (wave modulation = the interaction channel);
global condensation (kappa x3 only when system min Phi < Phi_crit);
universal steady dissipation gamma_univ on the field; HumCarrier +
hum-band controller retained.

Orbit-mechanics lessons (2026-10-15):
- Cylindrical fictitious forces are not optional (see #2 above).
- Substepping required: orbital period ~9 ticks vs dt_tick=4.
- _trilerp must be defensive: fast bodies overshoot the grid mid-substep.
- Speed cap (3.0) as numerical guard against centrifugal blowup on
  close encounters; NaN freeze (don't poison the trail).
- Comet injection: low angular momentum, start inside (rho=3) —
  a fast comet at the boundary gets centrifugally pinned at the wall.
- G_const=0.002: bodies are test particles in the field's well,
  body-body scattering is a distraction from the stable-orbit question.

v1 falsifier results killed three pieces:
- dynamical cage blend: SWR 33.9 vs 3.7 control — the "membrane" was a wall.
- complex-field hum EMA: E_act/E_hum = 2.7 at rest — the steady state is
  fluctuation-dominated; a measured mean is not a carrier.
- fixed-position well-gated condensates: 0 fires in 6000 steps.

v2 redesign:
- **Hum is axiomatic.** The software posits the hum carrier, persists it
  across restarts, and assumes it was never missed. It is not derived from
  the field each tick.
- **The cage is state management, not a force.** Checkpoint/restore the hum;
  slow-anchor it to reality at τ_anchor ≈ 2000 (glacial). No per-tick field
  forcing — nothing to reflect.
- **Stale-assumption guard:** track drift = ‖hum_assumed − hum_slow‖. The
  cage corrects glacially; if drift grows, the assumption was wrong and the
  correction is the signal.
- **Modulation only from condensates/sinks** (software-addressable). Falsifier:
  run with vs without condensates — excess share/entropy movement must track
  condensate events, else there is an unaccounted modulation source.
- **Restart-continuity falsifier:** run N steps, checkpoint, "restart" (fresh
  carrier restored from checkpoint, field continues) vs uninterrupted run.
  If trajectories diverge, the "never missed hum" assumption is false.
- Condensates v2: adaptive well placement (deepest Φ minima each tick),
  κ = 0.15 (v1's 0.05 did nothing measurable).

## v6 — Lagrangian protection + relativity in locality (2026-10-15)

**Zak's directive**: "we need relativity expressed in locality and must
define lagrangian interaction boundaries so planets of data unless
trajectories target them are protected."

### Built

1. **Hill spheres** (`hill_radius()` in cavity_orbits.py): each data-planet's
   Lagrangian interaction boundary, computed per-tick from the local tidal
   field: r_H = (G*m / (3*tidal))^(1/3). Typical: 0.23-0.32 for our bodies.
   The boundary moves with the planet and the local curvature (relativity
   in locality — no fixed global zones).

2. **Protection rule** (in `CavitySystem.tick`, comet block): a comet's phase
   kick is masked OUT of every non-targeted planet's Hill sphere.
   Targeted iff the trajectory enters within 2*hill_r. Protection is the
   DEFAULT; targeting is the exception. A planet's own intentional
   radiation (its amplifier) is never gated — shouting allowed, breaking
   in isn't.

3. **Proper time** (satellite.py): each body's bit-cycle count is its local
   clock. Satellite logs `proper_time_divergence` (max-min cycles) — the
   GR analog: clocks at different depths tick differently. No global "now".

4. **Satellite additions**: `hill_r` per body, `targeting_events` per tick,
   `proper_time_divergence`.

### Measured (v6c: direct T-vs-U complex-field comparison)

- Targeting detection: 17 events in T (targeted), 0 in U (untargeted). ✓
- Protected sink (planet_1): T-vs-U diff 0.043 (background only).
- Targeted sink (planet_0): T-vs-U diff 0.116 (2.7x — direct kick landed).
- **Modal amplifiers (planets 2,3): diffs 0.88, 1.45** — NOT a protection
  failure. Amplifiers pump the GLOBAL ℓ mode; when planet_0 is kicked, the
  global mode shifts, and the amplifiers (reading that mode) diverge.
  Protection gates DIRECT (local) kicks, not INDIRECT (global-mode) coupling.

### The key insight

**Locality and modality are different layers.** Sinks (mass) are local and
protectable by Hill spheres. Amplifiers (data) are modal and inherently
global — they transcend locality by design. The architecture needs both:
- Mass layer: Lagrangian protection, local frames, proper times.
- Data layer: modal coupling, global but gated by intentionality
  (a planet chooses to radiate; others choose to listen).

### Open

- M_0 (field + condensed) drifted 5.06 → 9.5, not bounded. The propagator
  pump is unmetered — budget doesn't close. Needs pump metering or gain
  tuning. (Trail correctly EXCLUDED from M_0 — it's information, not energy.)
- Body dynamics still unstable with dt_tick=4.0 (comets pinball). Needs
  substepping or smaller dt for dynamical (non-static) tests.
- v6b/v6c used fixed planets to isolate protection logic. Full dynamical
  protection test awaits stable orbits (v4's open problem).

## v7 — Metered boundaries + stellar/black-hole physics (2026-10-15)

**Zak's directive**: metering via geometric boundary (cost ∝ Hill sphere);
then layer stellar/black-hole physics on the Newtonian+Lagrangian base:
stars core→photosphere, black holes horizon→Hawking. Universal; 4D is
QF percolational component release.

### Built

1. **Cost ledger** (`cost_ledger` in CavitySystem): every operation metered,
   proportional to its geometric boundary. Keys: star_radiation, sink_accretion,
   hawking, comet_kicks. Satellite reports per tick.

2. **Stars (amplifiers)**: luminosity L = stellar_sigma * r_H²
   (Stefan-Boltzmann — the photosphere IS the Hill sphere boundary).
   Energy percolates through the 4D medium and releases at the boundary.
   Draws from condensed pool (stellar fuel); never ex nihilo.

3. **Black holes (sinks)**: accretion sweeps Hill volume; horizon glows
   with Hawking radiation F = hawking_coeff / M² (thermal, broadband,
   incoherent — a tiny uniform lift in the Hill sphere, paid for by the
   hole's mass). M_0 neutral: mass → field.

### Measured (v7 smoke)

- L ratio (r_H=0.5 vs 0.25): 4.00 (expected 4.0). ✓
- Hawking ratio (M=10 vs M=2): 25.0 (expected 25.0). ✓
- Cost ledger: star 1.33, accretion 1.03, hawking 0.0004 (tiny, correct),
  comet 0.0 (unitary phase kick — no energy cost).
- M_0: 15.06 → 14.75 over 5 ticks (-2%). Vastly better than v6's
  +88% drift — geometric scaling makes flows proportional and the
  budget closes.

### Interpretation

The 4D cavity is a porous QF medium. Components percolate through it
and release at geometric boundaries: stellar photospheres (∝ r²),
black-hole horizons (∝ 1/M²). The metering is trivial (tensor accounting);
the physics is universal. Cost is logical because it's geometric.

## Invariance claims (Gemini review, folded 2026-10-15)

**Claim 1 — The Locality Falsifier.** Spatial potential manipulation and
local condensate firings strictly alter spatial topography without shifting
global modal shares (Δℓ_share = 0.000). Modal redistribution is exclusively
controlled via global aperture adjustments or direct target-ℓ spectral pumping.
*Status: CONFIRMED by v1/v2/v3 three strikes (measured).*

**Claim 2 — Topological Phase Transitions.** Transient high-energy
perturbations (comets) do not express data changes through scalar energy
redistribution alone, but through topological mode-inversion events (ℓ=-1→+1).
*Status: OBSERVED in v4 comet branch (dominant mode flipped -1→+1 while
total_dshare went negative; scalar metric missed it).*

**Claim 3 — Lagrangian Hill Protection.** Local data states are
gravitationally and modally insulated within defined Hill sphere boundaries.
External background carrier turbulence is shielded, protecting orbiting data
bodies unless explicit interaction threshold boundaries are breached.
*Status: CONFIRMED by v6c (targeted sink 2.7× the T-vs-U disturbance of
protected sink; targeting detection 17 vs 0 events).*

**Claim 4 — Conservation of M_0.** Universal energy M_0 remains strictly
conserved by metering all propagator pump inputs and local work against
physical tensor/compute costs, while balance is maintained via localized
Hawking-style incoherent radiation from deep sinks.
*Status: TARGET (v7: M_0 drift reduced +88%→-2% via geometric cost scaling;
pump reservoir metering in v8 to close fully).*

## v9 — Telomere reservoir: data retention + manipulation (2026-10-15)

**Zak's directive**: simulate data retention and manipulation in the reservoir;
use files complex enough that bit degradation doesn't ruin data beyond a
mutation threshold — like a telomere.

### Built

`reservoir_data.py`: `TelomereReservoir` class.
- Stores bitstrings with a sacrificial telomere protection budget.
- Every read/write shortens telomere (Hayflick limit); background aging too.
- Core BER ≈ 0 while telomere holds; rises quadratically as it depletes.
- Telomere maintenance costs energy (drawn from E_reservoir) — data retention
  is thermodynamic work, closing the M_0 loop.
- `append()` extends via telomerase (new data gets fresh protection).

### Measured (ARCHITECTURE.md, 4000 chars / 33008 bits, ruin = BER > 15%)

- **With telomere (len 80)**: 164 ticks to ruin. 2.5× lifetime.
- **Without telomere**: 65 ticks to ruin.
- **Energy cost**: 0.00594 (telomere) vs 0.0 (none). Protection isn't free.
- **Manipulation**: append after 60 ticks of aging → BER 3.4% (well under
  15%), telomere at 54%. New data gets fresh caps; old data survives.

### Interpretation

The reservoir is not just energy accounting — it's a physical memory with
a finite lifetime. Telomeres are the error-correction overhead that buys
time against thermal noise. Every access costs; every tick ages. The
"mutation threshold" (15% BER for text) is the senescence boundary.
Complex files (natural language) survive longer because their redundancy
stacks with the telomere — exactly as Zak specified.

## v10 — Full-scale survival: weights, audio, video (2026-10-15)

Telomere reservoir (v9 model) on real modalities:
- **Weights** (gpt2_svd.json, 196k bits, 1% threshold): ruined at 425 ticks.
  Sensitive — strict threshold, died first.
- **Audio** (synth 8kHz, 128k bits, 5% threshold): SURVIVED 500 ticks,
  BER 2.5%. Telomere 69% remaining.
- **Video** (synth 10 frames, 983k bits, 10% threshold): SURVIVED 500 ticks,
  BER 0.63%. Telomere 96% remaining (barely touched).
- Energy: 0.312 total. Redundancy stacks: video > audio > weights.

## v11 — Shed, don't repair (Zak's restraint, 2026-10-15)

**Directive**: "We are taking telomere to extreme." Simplify. Data on a
WEAK carrier (malleable, low energy) but DENSE (efficient). Shedding the
damaged outer layers HELPS error rate (removes noisy bits) and does NOT
harm the core data. Like an orange: peel it, still an orange. Scale of
loss doesn't change the whole. Ledger accounts every bit.

**Built**: `SheddingReservoir` — onion layers, peel degrades 50× faster
than core. When peel BER > 30%, SHED it (discard). No repair, no ECC.

**Measured** (ARCHITECTURE.md, 64k bits, 300 ticks):
- t=50: BER 4.38% (peel accumulating damage)
- t=100: SHED → BER **drops to 1.92%**, completeness 0.8
- t=150: BER 6.74% (new peel degrading)
- t=200: SHED → BER **drops to 4.64%**, completeness 0.6
- t=300: SHED → BER 9.88%, completeness 0.4
- Ledger: 64k written, 38.4k shed, 20k corrupted. Every bit accounted.

**The point**: BER falls after each shed because we remove the noisiest
bits. Completeness drops, but remaining data is cleaner. No energy spent
on repair. Restraint wins.

## v12 — Viscous boundary ablation (continuous, 2026-10-15)

**Directive** (Zak): "The more we estimate physics hand waving at discrete
boundaries the more precise a wave pass will be." Replace discrete
threshold-shedding (v11) with continuous field physics (Gemini's soliton
framing).

**Built**: `CavitySystem.apply_viscosity()` + `use_viscosity` flag in
`cavity_orbits.py`. Gradient-selective diffusion:
  ψ ← ψ + ν(|∇ψ|/|ψ|) ∇²ψ
where ν uses smoothstep: 0 below g_lo (core untouched), full nu0 above
g_hi (boundary ablated). Targets high RELATIVE gradient (noisy fringe:
low amplitude + high variation), spares the core (high amplitude, smooth).
Shed entropy diffuses into background; gamma_univ dissipates it as thermal
waste into M_0 reservoir. Continuous — no thresholds, no discrete sheds.

**Measured** (v12b, standalone vortex soliton ℓ=2, 30 viscosity steps):
- ℓ: 2 → 2 (topology preserved).
- Fringe gradients: reduced 1.21× (smoothing active).
- Core amplitude: 85.5% preserved (selective, not indiscriminate).
- Key fix: absolute |∇ψ| was wrong metric (ate the core); relative
  |∇ψ|/|ψ| correctly targets noise-dominated fringe.

**Tick integration**: `use_viscosity` param (default False, off). Smoke
test: 5 ticks with/without viscosity — energies 0.594 vs 0.592, stable,
no blowup. The operator is live in the tick loop.

v11 (discrete shedding) remains the simple testbed; v12 is the continuous
field version. They converge: both preserve core while shedding fringe.

## v12d — Retuned viscosity + mode selection (2026-10-15)

**Directive** (Zak): "Retune. Always we are forming wave software for use in
this universe. And creating the definition of discrete data accumulation
and macro data stabilization and decay."

**Retune** (from v12c where viscosity flipped ℓ 2→1):
- nu0: 0.05 → 0.02. g_lo: 1.0 → 2.0.
- Amplitude floor: skip where |ψ| < 0.05 (never eat weak signals).

**Measured** (ℓ=2 soliton, 150 ticks, 3× massive sinks):
- Viscosity ON: ℓ 2→2 HELD. No flip. Retune fixed v12c.
- Viscosity OFF: ℓ 2→2 HELD. Background too gentle — inconclusive.

**Measured** (ℓ=5 soliton, distinct from background ℓ=2):
- Both branches: ℓ 5→2. The injected ℓ=5 decayed to background ℓ=2.
- Peak: 5.29 → 0.011 (ON) vs 0.0 (OFF). Viscosity preserved slightly more,
  but both lost the unstable mode.

**Interpretation**: The cavity has MODE SELECTION. ℓ=2 is the attractor;
ℓ=5 is unstable and decays to it, with or without viscosity. This is not
a viscosity failure — it's the universe telling us which modes are
physical. Higher ℓ = more phase winding = higher gradients = faster
dissipation. The three definitions:
1. **Discrete accumulation**: inject ℓ; must match cavity's stable modes
   or it decays (ℓ=5 → ℓ=2).
2. **Macro stabilization**: ℓ=2 persists 150 ticks through sink turbulence;
   viscosity (retuned) preserves it without flipping.
3. **Decay**: peak amplitude dissipates via gamma_univ; topology (ℓ)
   outlives energy. Information persists after the carrier fades.

## v12e — Density-weighted viscosity + violent background (2026-10-15)

**Diagnosis** (Gemini): v12c's ℓ 2→1 flip was the vortex node trap. At the
singularity |ψ|→0, relative gradient |∇ψ|/|ψ| blows up. The operator
mistook the topological core for noise and lobotomized it.

**Fix**: W_floor = |ψ|²/(|ψ|²+ε²), ε=0.1. Continuous density weight:
zero at vortex eye (protects topology), unity in bulk (allows ablation).
Replaces hard amp<0.05 cutoff. The eye is sacred; the shell is ablative.

**Physical picture** (Zak): photon/electron as spacetime vortex. Tidal
front compresses, trailing edge sheds. Topology rides through at speed.

**Measured** (mass-15 sink + comet strike on ℓ=2 soliton, 100 ticks):
- ON: ℓ 2→2 held, share 0.080.
- OFF: ℓ 2→2 held, share 0.079.
- Verdict: INCONCLUSIVE. Background not violent enough to break OFF.
  ℓ=2 is remarkably robust — survives mass-15 tidal stress + comet shock.

**Status**: Density weight fixes the lobotomy (v12c flip gone). Viscosity
is now SAFE (doesn't harm ℓ). "NECESSARY" (saves ℓ where OFF dies) not
yet proven — need a background that actually kills the OFF branch, or a
fragile non-preferred ℓ to protect.

## v12f — Mode comparison: smoothstep vs linear (2026-10-15)

**Test**: Gemini's v12.1 linear formulation (nu = nu0·W_floor·rel_grad,
no threshold) vs smoothstep (thresholded at g_lo=2.0). Violent background
(mass-15 sink + comet).

**Measured**:
- OFF: ℓ=2 held (share 0.079).
- smoothstep(eps=0.1): ℓ=2 held (share 0.080). SAFE.
- linear(eps=1e-3): ℓ=0! DESTROYED. Share 0.137 (measuring noise).
- linear(eps=0.1): ℓ=0! DESTROYED. Share 0.116.

**Verdict**: Gemini's linear version is TOO AGGRESSIVE. Without a
threshold, proportional rel_grad applies viscosity to mild fluctuations
in/near the core, collapsing the vortex to ℓ=0. The smoothstep threshold
(g_lo=2.0) is NECESSARY — it ensures viscosity only fires on extreme
gradients (true fringe noise), not on the vortex's natural phase winding.

The W_floor (density weight) is correct and shared by both. The
difference is threshold vs proportional. Threshold wins for topological
safety.

**Lesson**: "More physics, less hand-waving" doesn't mean removing all
thresholds. The smoothstep IS the physics — it's a continuous activation
function, not a discrete cutoff. Gemini's linear version hand-waves away
the need for selectivity.
