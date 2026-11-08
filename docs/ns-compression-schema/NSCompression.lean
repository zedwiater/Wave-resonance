/-!
# Navier–Stokes compression schema

Zak Wiater, 2026-11-06. A conjecture, stated formally in Lean 4.
This file is a STATEMENT artifact: it formalizes a schema, it
does not prove it. Every conjectured or schematic implication
is stated as a theorem closed by `sorry` and flagged as such
wherever it appears (see the README in this directory for the
full accounting in the README: every `sorry` is a named conjecture). The remaining
theorems are proved from those by pure logic. Nothing here is
dressed as a proof.

## Zak's schema, in his words

"Smoothness is a fault of unstable geometric compression."
Companion: a hydrodynamic system cannot maintain the chaos it
creates when its geometric compression is unstable or
insufficient — injected disorder smooths away.

Sharpening (Zak, same session, ~15:17 ET, superseding the
single-condition form above): "under proper geometry and flow
rate NS would never smooth." The hypothesis is a PAIR — proper
geometry AND proper flow rate, the session's two dials (the
density edge and the filament speed edge) — and the conclusion
is NEVER: under the pair, the smoothing fault occurs at no
time; structure is maintained for all `t`.

## One-line plain statement

If a Navier–Stokes flow sits in the sweet spot — geometric
compression stable (bounded, maintained) AND flow rate inside
its proper band — the solution stays smooth and its structure
is never smoothed away; so if smoothness or structure is ever
lost, geometry or flow rate must have left the band first.
The loss is a *symptom* — a fault — of leaving the band, not
an intrinsic pathology of the equations.

## Formalization notes (choices, all flagged in the README)

* The spatial domain `X` is abstract. Instantiate with ℝ³ or the
  3-torus 𝕋³ in a future Mathlib development. No differential
  geometry is available at this schema level, so the analytic
  content of "solves Navier–Stokes" and "remains smooth" is
  carried as opaque predicates bundled with the solution
  concept; the schema's mathematical content is the implication
  between those predicates and the compression predicate, which
  is defined concretely below.
* Times and all quantitative bounds are stated over Rat (rationals)
  so this file depends on core Lean only, no Mathlib. The
  physical quantities are real-valued; Rat is dense in ℝ and the
  schema's logical shape is unchanged. Flagged choice.
* The Jacobian determinant of the flow map is given as data
  together with its defining properties (positivity, value 1 at
  `t = 0`, and the cocycle / chain rule along the flow). This is
  definition-by-characteristic-properties: an analytic
  construction of `det DΦ` needs Mathlib and is out of scope for
  a schema file.
-/

namespace NSCompression

/-! ## §1. The solution concept

A `NSSolution X` bundles the Lagrangian data of a flow on an
abstract domain `X`: the flow map, the Jacobian-determinant
distortion of that map, and two opaque analytic predicates —
that the underlying velocity field solves the incompressible
Navier–Stokes equations, and that the solution remains smooth
for all time. -/

/-- A Navier–Stokes solution concept at schema level.

`flowMap t x` is the position at time `t` of the particle that
starts at `x`. `distortion t x` is the Jacobian determinant
`det D(flowMap t) (x)`: the local volume ratio, i.e. the
density-ratio distortion, produced by the flow up to time `t`.
Its defining properties are the three axioms at the end:
positivity (the flow is a diffeomorphism), value `1` at `t = 0`
(nothing has moved yet), and the cocycle identity, which is the
chain rule `det DΦ_{s+t}(x) = det DΦ_s(Φ_t x) · det DΦ_t(x)`. -/
structure NSSolution (X : Type _) where
  /-- Lagrangian flow map. -/
  flowMap : Rat → X → X
  /-- Jacobian-determinant distortion of the flow map. -/
  distortion : Rat → X → Rat
  /-- Flow rate: the local flow speed (magnitude of the
  velocity) at `(t, x)`. The session's second dial — the
  filament speed edge. Given as data at schema level; its
  identification with `|u|` is analytic and out of scope here. -/
  flowRate : Rat → X → Rat
  /-- The velocity field of this flow solves the incompressible
  Navier–Stokes equations. Opaque analytic predicate (schema
  level). -/
  solvesNS : Prop
  /-- The solution remains smooth for all time: no finite-time
  singularity forms. Opaque analytic predicate (schema level).
  This is the global-regularity conclusion of the Millennium
  formulation, carried here as a predicate so the schema can
  state what governs it. -/
  remainsSmooth : Prop
  /-- The flow map starts as the identity. -/
  flowMap_zero : ∀ x, flowMap 0 x = x
  /-- The flow map composes: flowing for `t` then for `s` is
  flowing for `t + s`. -/
  flowMap_add : ∀ (s t : Rat) (x : X), flowMap (t + s) x = flowMap s (flowMap t x)
  /-- Distortion is positive: the flow never collapses or flips
  a volume element. -/
  distortion_pos : ∀ t x, 0 < distortion t x
  /-- No distortion before any time has passed. -/
  distortion_zero : ∀ x, distortion 0 x = 1
  /-- Chain rule / cocycle: distortion over `t + s` is the
  distortion over the second leg, evaluated at the transported
  point, times the distortion over the first leg. -/
  distortion_cocycle : ∀ (s t : Rat) (x : X),
    distortion (t + s) x = distortion s (flowMap t x) * distortion t x
  /-- A speed is nonnegative. -/
  flowRate_nonneg : ∀ t x, 0 ≤ flowRate t x

/-! ## §2. The two dials: compression stability and proper flow rate

The session's two dials, made formal. The first is the density
edge: a flow's geometric compression at `(t, x)` is its
distortion; the compression is *stable with bound `C`* when
the distortion is trapped in `[1/C, C]` at every point and
every time — bounded, and maintained, uniformly in time.
`C = 1` is zero distortion; larger `C` permits more compression
and rarefaction. Stability is two-sided on purpose: a volume
element may neither be crushed toward `0` nor stretched
without bound.

The second is the speed edge: the flow rate is *proper* when
it stays inside a band `[vLo, vHi]` everywhere, for all time —
fast enough to keep band-swapping with the surrounding
structure, not so fast it locks. The sweet spot is the pair. -/

/-- Stable geometric compression with bound `C`: the Jacobian
distortion stays in `[1/C, C]` everywhere, for all time. -/
def StableCompression {X : Type _} (sol : NSSolution X) (C : Rat) : Prop :=
  1 ≤ C ∧
  (∀ t x, sol.distortion t x ≤ C) ∧
  (∀ t x, 1 / C ≤ sol.distortion t x)

/-- The optimal (least) stable bound, when one exists: the
tightest `C` for which the compression is still stable. The
optimal bound measures how much distortion the flow actually
uses. -/
def OptimalStableBound {X : Type _} (sol : NSSolution X) (C : Rat) : Prop :=
  StableCompression sol C ∧
  ∀ C' : Rat, StableCompression sol C' → C ≤ C'

/-- Proper flow rate with band `[vLo, vHi]`: the flow speed
stays inside the band at every point, for all time. The band is
two-sided on purpose, mirroring the compression bound: below
`vLo` the flow no longer band-swaps with the Rollin-film
structure around it; above `vHi` it locks. The session's
filament speed `v*` is the top edge of this band at the
quasi-frozen limit. -/
def ProperFlowRate {X : Type _} (sol : NSSolution X) (vLo vHi : Rat) : Prop :=
  0 < vLo ∧ vLo ≤ vHi ∧
  ∀ t x, vLo ≤ sol.flowRate t x ∧ sol.flowRate t x ≤ vHi

/-- The sweet spot: proper geometry AND proper flow rate, the
hypothesis pair of the main conjecture (§3). Declared choice:
the pair is carried as two named predicates, taken as separate
hypotheses in the main statement, and conjoined here under one
name for the companion statements that quantify over bands. -/
def InSweetSpot {X : Type _} (sol : NSSolution X) (C vLo vHi : Rat) : Prop :=
  StableCompression sol C ∧ ProperFlowRate sol vLo vHi

/-! ## §3. The main conjecture

**CONJECTURE (Zak's NS compression schema, sharpened form of
2026-11-06 ~15:17 ET).** The hypothesis is the PAIR: proper
geometry (`StableCompression`) and proper flow rate
(`ProperFlowRate`), taken as two explicitly named hypotheses.
Stated as a theorem and closed by `sorry`: the `sorry` IS the
conjecture. This is the one unproved step in the regularity
half of the file, and it is the whole claim — everything else
here is definition or pure logic. -/

/-- **Zak's NS compression conjecture.** If a Navier–Stokes
solution sits in the sweet spot — geometric compression stable
with bound `C` (proper geometry) AND flow rate inside its
proper band `[vLo, vHi]` (proper flow rate), both maintained
uniformly in time — then the solution remains smooth for all
time.

Equivalently: smoothness is never lost on its own. Where a
solution would blow up, geometry or flow rate must already
have left the band. The breakdown is a fault of leaving the
band, not of the equations. -/
theorem sweet_spot_implies_smoothness {X : Type _}
    (sol : NSSolution X) (hNS : sol.solvesNS) (C vLo vHi : Rat)
    (hGeom : StableCompression sol C)
    (hRate : ProperFlowRate sol vLo vHi) :
    sol.remainsSmooth := by
  sorry

/-- The same conjecture with the band existentially quantified:
some sweet spot exists, therefore smoothness. Proved from the
main conjecture by pure logic (no additional `sorry`). -/
theorem exists_sweet_spot_implies_smoothness {X : Type _}
    (sol : NSSolution X) (hNS : sol.solvesNS)
    (hSS : ∃ C vLo vHi : Rat,
      StableCompression sol C ∧ ProperFlowRate sol vLo vHi) :
    sol.remainsSmooth :=
  match hSS with
  | ⟨C, vLo, vHi, hGeom, hRate⟩ =>
      sweet_spot_implies_smoothness sol hNS C vLo vHi hGeom hRate

-- (The NEVER form of this conjecture — "under proper geometry
-- and flow rate NS would never smooth," structure maintained
-- for all `t` — quantifies over injection experiments, so it
-- is stated in §5 as `sweet_spot_never_smooths`, immediately
-- after `DisorderExperiment` is defined. Same `sorry` status.)

/-! ## §4. The diagnostic direction (proved)

The contrapositive of §3, and the direction Zak's schema is
usually quoted in: *if smoothness fails, the flow had left the
band* — geometry or flow rate, one of the pair. This is a
theorem of pure logic modulo the single conjectured
implication of §3 — it carries no `sorry` of its own. -/

/-- **Smoothness failure is diagnostic of leaving the band.**
If a Navier–Stokes solution does not remain smooth, then for
every candidate band `(C, vLo, vHi)`, the pair (proper
geometry at bound `C`, proper flow rate in `[vLo, vHi]`) did
NOT hold together: at least one of the two dials was out.
Proved by contraposition of the conjecture in §3. -/
theorem blowup_requires_leaving_the_band {X : Type _}
    (sol : NSSolution X) (hNS : sol.solvesNS)
    (h : ¬ sol.remainsSmooth) (C vLo vHi : Rat) :
    ¬ (StableCompression sol C ∧ ProperFlowRate sol vLo vHi) :=
  fun hPair =>
    h (sweet_spot_implies_smoothness sol hNS C vLo vHi hPair.1 hPair.2)

/-! ## §5. Companion physical schema: chaos needs compression

Zak's companion claim, from the same session, with his evidence
being our own simulation boxes: inject disorder into a flow and
it smooths away (selective decay / Taylor relaxation) unless
the flow sits in the sweet spot — geometry and flow rate both
in band — long enough to maintain it. A hydrodynamic system
cannot maintain the chaos it can create when it cannot be
compressed enough geometrically, or driven at the proper rate.

This section is SCHEMATIC. `DisorderExperiment` packages an
injection experiment as data — a disorder amplitude evolving in
time — and the theorems below state the NEVER form of §3 and
the schema's two directions over that data. They are closed by
`sorry` and flagged: unlike §3, which is one sharp implication,
this section is a schema over an experiment concept, stated at
the level of formality the definitions honestly support. The
one proved result of the section (§5.3) is the bare logical
incompatibility of "maintained forever" with "vanishes
eventually". -/

/-- An injection experiment: a solution together with a
disorder amplitude `disorder t` (schema-level data: read it as
e.g. an enstrophy or high-mode energy share of the perturbation
away from the base flow), injected at level `injected` at
`t = 0`. -/
structure DisorderExperiment (X : Type _) where
  /-- The underlying flow. -/
  sol : NSSolution X
  /-- Disorder amplitude at time `t`. -/
  disorder : Rat → Rat
  /-- The injected level. -/
  injected : Rat
  /-- Disorder amplitudes are nonnegative. -/
  disorder_nonneg : ∀ t, 0 ≤ disorder t
  /-- The injection is nontrivial. -/
  injected_pos : 0 < injected
  /-- At `t = 0` the disorder is the injected level. -/
  disorder_zero : disorder 0 = injected

/-- The disorder is *maintained*: from some time `T` onward it
never drops below the fraction `θ` of the injected level. -/
def MaintainsDisorder {X : Type _} (e : DisorderExperiment X)
    (θ T : Rat) : Prop :=
  ∀ t, T ≤ t → θ * e.injected ≤ e.disorder t

/-- The disorder *smooths away*: below every positive level
eventually, and forever after. This is what our sim boxes did
to every chaotic injection. -/
def SmoothsAway {X : Type _} (e : DisorderExperiment X) : Prop :=
  ∀ ε : Rat, 0 < ε → ∃ T : Rat, ∀ t, T ≤ t → e.disorder t < ε

/-- **The NEVER form of the main conjecture (Zak, ~15:17 ET),
stated here because it quantifies over experiments.** If the
underlying flow sits in the sweet spot — proper geometry AND
proper flow rate — then injected disorder is maintained at
some fixed positive fraction of its injected level at EVERY
time `t`: the all-time quantifier is the statement, and the
smoothing fault occurs at no time. Conjectural (`sorry`), the
physical face of §3, standing or falling with it. -/
theorem sweet_spot_never_smooths {X : Type _}
    (e : DisorderExperiment X) (hNS : e.sol.solvesNS)
    (C vLo vHi : Rat)
    (hGeom : StableCompression e.sol C)
    (hRate : ProperFlowRate e.sol vLo vHi) :
    ∃ θ : Rat, 0 < θ ∧ ∀ t, θ * e.injected ≤ e.disorder t := by
  sorry

/-- **Companion schema, direction 1 (schematic, `sorry`).**
Disorder that is maintained forever requires the sweet spot:
some band `(C, vLo, vHi)` has proper geometry and proper flow
rate together, for all time. Chaos that persists is held by
the pair; nothing else in the system can hold it. -/
theorem maintained_disorder_requires_sweet_spot {X : Type _}
    (e : DisorderExperiment X) (hNS : e.sol.solvesNS)
    (θ T : Rat) (hθ : 0 < θ) (h : MaintainsDisorder e θ T) :
    ∃ C vLo vHi : Rat,
      StableCompression e.sol C ∧ ProperFlowRate e.sol vLo vHi := by
  sorry

/-- **Companion schema, direction 2 (schematic, `sorry`) —
the mirror of the pair.** If EITHER dial is out at every
setting — geometry unstable at every bound, or flow rate
outside every band — then injected disorder smooths away.
Smoothing occurs when geometry or flow rate leaves the proper
band; that disjunction is the whole content. This is the
formal shape of the sim evidence: boxes whose compression
could not be held relaxed every chaotic injection to smooth
order. -/
theorem out_of_band_smooths_disorder {X : Type _}
    (e : DisorderExperiment X) (hNS : e.sol.solvesNS)
    (h : (∀ C : Rat, ¬ StableCompression e.sol C) ∨
         (∀ vLo vHi : Rat, ¬ ProperFlowRate e.sol vLo vHi)) :
    SmoothsAway e := by
  sorry

/-- **Proved (§5.3).** Maintained disorder and smoothed-away
disorder are incompatible at the threshold the maintenance
guarantees: if the disorder stays at or above `θ * injected`
from time `T` on, it cannot also be eventually below that same
level from time `T` on. Pure logic over the definitions; no
`sorry`. (This is only the definitional incompatibility — the
physical content of the companion schema is in the schematic
theorems above.) -/
theorem maintains_and_vanishes_absurd {X : Type _}
    (e : DisorderExperiment X) (θ T : Rat)
    (hM : MaintainsDisorder e θ T)
    (hV : ∀ t, T ≤ t → e.disorder t < θ * e.injected) :
    False :=
  (Rat.not_lt.mpr (hM T Rat.le_refl)) (hV T Rat.le_refl)

/-! ## §6. The refined superfluid parameter (revision of 2026-11-08)

Zak's order of 2026-11-08 ~10:40 ET: revise the equation set
with the refined parameter and run it through Lean. The
refinement (paper §§15–17) makes the thermal state of the
two-fluid medium a first-class dial: alongside the session's
geometric compression `χ` (the `StableCompression` bound) and
the filament speed edge (`ProperFlowRate`), the **normal
fraction** `f = ρₙ/ρ` is now named, with its two derived
couplings stated as definitions, not hidden:

* `bandRatio f = (1 − f) / f` — the ρₛ/ρₙ factor of Landau's
  second-sound speed `u₂² = (T S²/C) · (ρₛ/ρₙ)`. (The
  thermodynamic prefactor `√(TS²/C)` and the equation of
  state `ρₛ(T), ρₙ(T)` are outside this schema's Rat-level
  vocabulary and remain PINS, flagged as such in the paper.)
* `frictionWeight f = f · (1 − f)` — the BK/HVBK mutual
  friction form: zero in either pure phase, maximal at the
  equal mixture `f = 1/2`.

The parameter is carried by a local field `f : X → Rat`
because the thermal state differs along the structure — the
warm end and the cold end of one bulge are the whole point of
the refinement. The three grading configurations of the
thermal layer (paper §16) are the two pure endpoints and the
gradient between them.

NEW CONJECTURE (the fifth `sorry`, named, not dressed as a
proof): **the sustain condition** — a configuration in this
family sustains its twist (does not smooth the twist away)
only if internal precipitation is active: the twist inventory
is shed by phase slips into the structure's own interior, not
only out through the ends. This is the schema form of paper
§17.1 and the falsifier F17: precipitation-off must kill
sustainment in EVERY thermal configuration, or the claim
dies. Protocol-4 grades it in the reduced build.

Declared choices for this section, flagged: `twistAt` is an
opaque scalar field bundled as structure data, exactly as
`distortion` and `flowRate` are in §1 — definition by
characteristic properties, no differential geometry at schema
level. Sustain is operationalised over the schema vocabulary
as "twist stays above a stated fraction of its initial level
for all time", the same maintenance shape as
`MaintainsDisorder` in §4. -/

/-- The thermal layer: a two-fluid configuration carries a
local normal fraction field and a twist inventory field.
`normalFraction t x = ρₙ/ρ` at time `t` at point `x`;
`twistAt t x` is the local twist inventory (the winding the
§15 dial acts on). Positivity of the fraction's denominator
form is bundled as `0 ≤ f ≤ 1` at every point and time: a
fraction of a density is a fraction. -/
structure ThermalConfig (X : Type _) where
  normalFraction : Rat → X → Rat
  twistAt : Rat → X → Rat
  fraction_bounds : ∀ t x, 0 ≤ normalFraction t x ∧ normalFraction t x ≤ 1

/-- The band ratio `(1 − f)/f = ρₛ/ρₙ`, the density-ratio
factor of Landau's second-sound speed. Stated for `0 < f`;
at `f = 0` there is no normal component and no second-sound
band in this form (the pure-superfluid endpoint is carried
by the configuration predicates below, not by this ratio). -/
def bandRatio (f : Rat) : Rat := (1 - f) / f

/-- The mutual-friction weight `f · (1 − f)`: zero in either
pure phase (`f = 0` or `f = 1`), maximal at the equal
mixture. This is the standard BK/HVBK assignment form —
phenomenological in helium too; stated here as the schema's
declared coupling, not derived. -/
def frictionWeight (f : Rat) : Rat := f * (1 - f)

/-- Purely definitional (proved, no `sorry`): the friction
weight vanishes at the pure-superfluid endpoint. -/
theorem frictionWeight_zero : frictionWeight 0 = 0 := by
  show (0 : Rat) * (1 - 0) = 0; exact Rat.zero_mul _

/-- Purely definitional (proved, no `sorry`): the friction
weight vanishes at the pure-normal endpoint. -/
theorem frictionWeight_one : frictionWeight 1 = 0 := by
  show (1 : Rat) * (1 - 1) = 0
  rw [Rat.mul_eq_zero]; right; exact Rat.sub_self

/-- Purely definitional (proved, no `sorry`): at the equal
mixture the friction weight is `1/4`, its maximum shape
value — the churn peak of paper §16 sits at the midpoint of
a warm–cold gradient for exactly this reason. -/
theorem frictionWeight_half : frictionWeight (1 / 2) = 1 / 4 := by
  native_decide

/-- Purely definitional (proved, no `sorry`): the band ratio
at the equal mixture is `1` — warm and cold band speeds meet
at the mixture point. -/
theorem bandRatio_half : bandRatio (1 / 2) = 1 := by
  native_decide

/-- Internal precipitation is ACTIVE in a configuration when
some interior point's friction weight is positive: there is
a genuine two-phase mixture somewhere inside the structure,
so the phase-slip shedding channel of paper §16 exists.
`f = 0` or `f = 1` everywhere switches the channel off —
that is the F17 control. -/
def PrecipitationActive {X : Type _} (cfg : ThermalConfig X) : Prop :=
  ∃ t x, 0 < frictionWeight (cfg.normalFraction t x)

/-- Twist SUSTAINS in a configuration when the twist
inventory stays at or above the fraction `θ` of its initial
level at every point, for all time — the maintenance shape
of §4 applied to twist. -/
def TwistSustains {X : Type _} (cfg : ThermalConfig X) (θ : Rat) : Prop :=
  ∀ x, ∀ t, θ * cfg.twistAt 0 x ≤ cfg.twistAt t x

/-- **Zak's sustain conjecture (CONJECTURE — the fifth
`sorry`, named `sustain_requires_precipitation`).** In this
configuration family, twist sustains only where internal
precipitation is active. Schema form of paper §17.1;
falsifier F17. Stated as a theorem closed by `sorry`: the
`sorry` IS the conjecture, exactly as in §3. -/
theorem sustain_requires_precipitation {X : Type _}
    (cfg : ThermalConfig X) (θ : Rat) :
    TwistSustains cfg θ → PrecipitationActive cfg := by
  sorry

/-- The F17 contrapositive, derived from the conjecture by
pure logic (no additional `sorry`): switch precipitation
off — a pure-phase configuration everywhere — and twist
cannot sustain. This is the form protocol-4's
precipitation-off controls grade. -/
theorem no_precipitation_no_sustain {X : Type _}
    (cfg : ThermalConfig X) (θ : Rat)
    (hoff : ¬ PrecipitationActive cfg) :
    ¬ TwistSustains cfg θ :=
  fun hs => hoff (sustain_requires_precipitation cfg θ hs)

/-! ## §7. Literature refinement and the true stragglers (2026-11-08)

Zak's question of 2026-11-08 ~11:30 ET: do any of the papers
reviewed for the co-revision dossiers refine this file's
` sorry`s past where they stand — and if a paper is publicly
usable, take the derivative and name the true stragglers.

Audit of the reviewed set (12 papers on disk in the
co-revision files, all open-access): NONE of them is a
Navier–Stokes regularity paper — a text search of the full
set finds no Beale–Kato–Majda, no Prodi–Serrin, no
Caffarelli–Kohn–Nirenberg. Sorries §3/§5 (the smoothness
family) therefore receive NO discharge from this set, and
this section does not pretend otherwise. What the set DOES
refine is §6's sustain conjecture: Levkov–Panin–Tkachev and
Dmitriev et al. prove, in the kinetic regime, that a Bose
star nucleates from an overpopulated boson gas and grows
self-similarly — condensation with no scattering channel
does not occur in their equations; Petrov's droplets exist
only because the Lee–Huang–Yang channel stabilises them;
Voit's cores sustain only while the precipitation channel
runs. Each is an INSTANCE of the sustain implication in a
specific system. The schema-universal form remains open —
but its hypothesis space can now be characterised exactly,
and that characterisation is PROVED below (no `sorry`):

* the friction weight vanishes exactly at the pure phases;
* precipitation is active exactly when some point is a
  genuine mixture (`0 < f < 1`);
* so the F17 control — precipitation off — is exactly the
  pure-phase-everywhere configurations, and the sustain
  conjecture says exactly: sustained twist forces a mixed
  point to exist. -/

/-- Auxiliary (proved): `1 - f = 0` forces `f = 1` over Rat,
by adding `f` to both sides and cancelling. -/
theorem one_sub_eq_zero_imp {f : Rat} (h : (1 : Rat) - f = 0) : f = 1 := by
  have h1 : (1 : Rat) - f + f = 0 + f := congrArg (fun y => y + f) h
  have h2 : (1 : Rat) - f + f = 1 := Rat.sub_add_cancel
  have h3 : (0 : Rat) + f = f := Rat.zero_add f
  rw [h2, h3] at h1
  exact h1.symm

/-- **PROVED (literature-refined form of §6's definitions).**
The friction weight vanishes exactly at the pure phases:
`frictionWeight f = 0 ↔ f = 0 ∨ f = 1`. The channel the
papers' mechanisms run through exists only in a genuine
mixture. -/
theorem frictionWeight_eq_zero_iff (f : Rat) :
    frictionWeight f = 0 ↔ f = 0 ∨ f = 1 := by
  constructor
  · intro h
    match Rat.mul_eq_zero.mp h with
    | Or.inl h1 => exact Or.inl h1
    | Or.inr h2 => exact Or.inr (one_sub_eq_zero_imp h2)
  · intro h
    match h with
    | Or.inl h1 => rw [h1]; exact frictionWeight_zero
    | Or.inr h1 => rw [h1]; exact frictionWeight_one

/-- **PROVED.** Precipitation is active in a thermal
configuration exactly when some point of it is a genuine
two-phase mixture, `0 < f < 1`. (Forward: a positive weight
at a point whose fraction is bounded in `[0, 1]` forces the
fraction strictly inside. Backward: at a mixed point both
factors of the weight are positive.) -/
theorem precipitationActive_iff_mixed_point {X : Type _}
    (cfg : ThermalConfig X) :
    PrecipitationActive cfg ↔
      ∃ t x, 0 < cfg.normalFraction t x ∧ cfg.normalFraction t x < 1 := by
  constructor
  · intro h
    match h with
    | ⟨t, x, hw⟩ =>
      refine ⟨t, x, ?_, ?_⟩
      · match (Rat.le_iff_lt_or_eq).mp (cfg.fraction_bounds t x).1 with
        | Or.inl hlt => exact hlt
        | Or.inr heq =>
          exfalso
          have hw0 : frictionWeight (cfg.normalFraction t x) = 0 := by
            rw [← heq]; exact frictionWeight_zero
          rw [hw0] at hw
          exact Rat.lt_irrefl hw
      · match (Rat.le_iff_lt_or_eq).mp (cfg.fraction_bounds t x).2 with
        | Or.inl hlt => exact hlt
        | Or.inr heq =>
          exfalso
          have hw0 : frictionWeight (cfg.normalFraction t x) = 0 := by
            rw [heq]; exact frictionWeight_one
          rw [hw0] at hw
          exact Rat.lt_irrefl hw
  · intro h
    match h with
    | ⟨t, x, h0, h1⟩ =>
      refine ⟨t, x, ?_⟩
      show 0 < cfg.normalFraction t x * (1 - cfg.normalFraction t x)
      have hpos2 : 0 < 1 - cfg.normalFraction t x :=
        (Rat.lt_iff_sub_pos (cfg.normalFraction t x) 1).mp h1
      exact Rat.mul_pos h0 hpos2

/-- **PROVED — the F17 control, characterised.** Precipitation
is off in a configuration exactly when every point is a pure
phase. Protocol-4's precipitation-off controls are therefore
not an approximation of the conjecture's hypothesis; they
are its exact hypothesis class. -/
theorem not_precipitationActive_iff_pure {X : Type _}
    (cfg : ThermalConfig X) :
    ¬ PrecipitationActive cfg ↔
      ∀ t x, cfg.normalFraction t x = 0 ∨ cfg.normalFraction t x = 1 := by
  constructor
  · intro h t x
    have hnm : ¬ (0 < cfg.normalFraction t x ∧ cfg.normalFraction t x < 1) :=
      fun hm => h ((precipitationActive_iff_mixed_point cfg).mpr ⟨t, x, hm⟩)
    match (Rat.le_iff_lt_or_eq).mp (cfg.fraction_bounds t x).1 with
    | Or.inr heq => exact Or.inl heq.symm
    | Or.inl hpos =>
      match (Rat.le_iff_lt_or_eq).mp (cfg.fraction_bounds t x).2 with
      | Or.inr heq => exact Or.inr heq
      | Or.inl hlt => exact absurd ⟨hpos, hlt⟩ hnm
  · intro h happ
    match happ with
    | ⟨t, x, hw⟩ =>
      have hw0 : frictionWeight (cfg.normalFraction t x) = 0 :=
        (frictionWeight_eq_zero_iff (cfg.normalFraction t x)).mpr (h t x)
      rw [hw0] at hw
      exact Rat.lt_irrefl hw

/-- **The sustain conjecture, refined (proved modulo the
§6 conjecture — no new `sorry`).** Sustained twist forces a
genuinely mixed point to exist somewhere in the
configuration: `0 < f < 1`, the two-phase interior the
reviewed papers' mechanisms all run through. This is the
derivative of `sustain_requires_precipitation` through the
characterisation above — the conjecture's content, made
pointwise. -/
theorem sustain_implies_mixed_point {X : Type _}
    (cfg : ThermalConfig X) (θ : Rat)
    (hs : TwistSustains cfg θ) :
    ∃ t x, 0 < cfg.normalFraction t x ∧ cfg.normalFraction t x < 1 :=
  (precipitationActive_iff_mixed_point cfg).mp
    (sustain_requires_precipitation cfg θ hs)

/-! ### The vorticity decomposition (the shape §3's straggler takes)

For the smoothness family, the literature's standard
refinement — stated here as a decomposition, NOT imported
as a result, because it is not among the reviewed papers —
is the Beale–Kato–Majda shape: smoothness persists while a
vorticity-integral bound holds. Bundled schematically: -/

/-- A vorticity-control witness over a solution: an opaque
bound predicate (schema stand-in for the BKM time-integral
of the supremum vorticity) together with the criterion —
bound implies smoothness — as data. For actual
Navier–Stokes solutions the criterion is the
Beale–Kato–Majda theorem (1984); at schema level it is
carried as a field, exactly as §1 carries `solvesNS` and
`remainsSmooth`, because `remainsSmooth` is opaque here and
nothing about real vorticity can be proved from it. -/
structure VorticityControl (X : Type _) where
  /-- The underlying flow. -/
  sol : NSSolution X
  /-- The vorticity-integral bound, as an opaque predicate. -/
  integralBounded : Prop
  /-- The criterion: the bound implies smoothness. -/
  criterion : integralBounded → sol.remainsSmooth

/-- **PROVED by pure logic (no `sorry`).** Given a
vorticity-control witness, §3's conjecture reduces to ONE
implication: the band (stable compression + proper flow
rate) yields the vorticity bound. Everything else in the
reduction is the criterion. The open content of the main
conjecture is thereby located, not discharged. -/
theorem smoothness_reduces_to_band_controls_vorticity {X : Type _}
    (vc : VorticityControl X) (C vLo vHi : Rat)
    (hCore : StableCompression vc.sol C → ProperFlowRate vc.sol vLo vHi →
      vc.integralBounded)
    (hGeom : StableCompression vc.sol C)
    (hRate : ProperFlowRate vc.sol vLo vHi) :
    vc.sol.remainsSmooth :=
  vc.criterion (hCore hGeom hRate)

/-! ### The true stragglers (audit outcome, 2026-11-08)

After the reviewed papers' derivatives are taken, the five
`sorry`s stand as follows. The count is unchanged — five —
because nothing in the reviewed set proves any of them; what
changed is how much of each is now pinned down.

* **S1 — `sweet_spot_implies_smoothness` (§3). STRAGGLER,
  core located.** By the decomposition above it is exactly:
  band ⇒ vorticity-integral bound, composed with the BKM
  criterion. The criterion is a literature theorem for real
  solutions (BKM 1984 — outside the reviewed set, flagged);
  the band⇒bound implication has NO published form: bounded
  Jacobian distortion controls volume ratios, and no paper
  bridges it to a vorticity bound. This implication is the
  live core of Zak's NS claim. Genuinely his, genuinely open.
* **S2 — `sweet_spot_never_smooths` (§5). STRAGGLER.**
  The physical face of S1 over injection experiments; no
  reviewed paper touches it. Selective-decay / Taylor-
  relaxation literature (outside the reviewed set) is its
  empirical neighbourhood, not a proof.
* **S3 — `maintained_disorder_requires_sweet_spot` (§5).
  STRAGGLER, weakest support.** The converse direction;
  nothing reviewed bears on it. It stands as the schema's
  boldest and least-anchored statement.
* **S4 — `out_of_band_smooths_disorder` (§5). STRAGGLER,
  best empirical support.** Every sim box this program ran
  relaxed out-of-band injections; that is evidence, not a
  proof, and the reviewed papers add none.
* **S5 — `sustain_requires_precipitation` (§6). STRAGGLER,
  refined.** Its hypothesis class is now characterised by
  proved theorems: precipitation-off = pure-phase everywhere
  (`not_precipitationActive_iff_pure`), and its conclusion
  is now pointwise (`sustain_implies_mixed_point`). The
  reviewed papers prove its instances (Levkov/Dmitriev in
  the kinetic regime; Petrov via Lee–Huang–Yang; Voit's
  sustain loop on the baryonic substrate); the universal
  schema form — every configuration in the family — remains
  the open residue, and protocol-4 grades it in the reduced
  build under falsifier F17. -/

/-! ## §8. The NS canon audit — a vacuity found, a repair, a partial discharge; and the Riemann cross-reference (2026-11-08)

Zak's order of 2026-11-08 ~11:37 ET: grab and compare the
NS papers and Riemann, cross-reference the same way as §7,
update citations and Lean accordingly. The canon was located
and read (Leray; Prodi–Serrin–Ladyzhenskaya; Beale–Kato–
Majda; Caffarelli–Kohn–Nirenberg; Constantin–Fefferman;
Escauriaza–Seregin–Šverák; Neustupa–Penel; Tao's averaged
model). Its first finding is about THIS file, and it is not
comfortable:

**THE DETERMINANT READING OF §1 IS VACUOUS FOR
INCOMPRESSIBLE NAVIER–STOKES.** §1 defines `distortion` as
the Jacobian determinant `det DΦ` — the local VOLUME ratio —
and `solvesNS` as the INCOMPRESSIBLE equations. For an
incompressible flow `det DΦ ≡ 1` identically (Liouville:
`∇·u = 0`), so `StableCompression` at any `C ≥ 1` is
satisfied by EVERY incompressible solution, including any
hypothetical blow-up. Worse, even as pure linear algebra a
bounded determinant controls nothing the canon uses:
singular values `(M, 1, 1/M)` have product 1 with norm
`→ ∞` (pure shear has determinant 1 and arbitrary strain),
so bounded `det DΦ` bounds neither vorticity (BKM), nor the
strain eigenvalues (Neustupa–Penel), nor `∇u` in any norm.
The density-ratio notion of compression this program uses
in its (compressible, GP) sim boxes was imported into an
incompressible claim by the 2026-11-06 formalization
choice, and under that choice the geometric half of the
main conjecture is empty. S1 (§3) therefore stands in this
file as SUPERSEDED — not proved, not refuted as physics:
discharged as vacuous under its stated reading. The live
claim is the repair below. (This finding is a meta-level
fact about the formalization's intended reading; the
schema's axioms on `distortion` — positivity, 1 at 0,
cocycle — are consistent with `det ≡ 1` and cannot express
it, which is itself the lesson: opaque predicates hide
vacuity. Recorded, not hidden.)

**THE REPAIR.** What "bounded distortion" must mean to do
work is the FULL deformation gradient: all singular values
of `DΦ` in a band — equivalently a bound on the deformation
magnitude `‖DΦ‖·‖DΦ⁻¹‖`-class quantity. That is the
Lagrangian face of the canon's control: `DΦ` evolves by
`(d/dt) DΦ = (∇u) DΦ`, so `∇u` control and deformation
control are the same neighbourhood (BKM; Neustupa–Penel).
Bundled at schema level: -/

/-- Deformation data over a solution: `deformation t x` is
the flow map's deformation MAGNITUDE at time `t` at `x` —
schema stand-in for a singular-value band measure of `DΦ`
(e.g. `‖DΦ‖ · ‖DΦ⁻¹‖`), NOT its determinant. Defining
properties replace §1's determinant axioms for this
quantity: at least 1 (a magnitude of this class is), 1 at
`t = 0` (nothing has moved), and a SUBMULTIPLICATIVE
cocycle (norms compose by ≤, where determinants composed
by =). -/
structure DeformationData (X : Type _) where
  /-- The underlying flow. -/
  sol : NSSolution X
  /-- The deformation magnitude field. -/
  deformation : Rat → X → Rat
  /-- The magnitude is at least 1 everywhere. -/
  deformation_ge_one : ∀ t x, 1 ≤ deformation t x
  /-- At `t = 0` nothing has moved: magnitude 1. -/
  deformation_zero : ∀ x, deformation 0 x = 1
  /-- Submultiplicative cocycle along the flow. -/
  deformation_cocycle : ∀ s t x,
    deformation (s + t) x ≤
      deformation s (sol.flowMap t x) * deformation t x

/-- Stable deformation with bound `C`: the deformation
magnitude stays at or below `C` everywhere, for all time
(the lower side of the band is the field's own `≥ 1`). This
is the repaired form of `StableCompression`: a real
hypothesis, false for flows whose Lagrangian deformation
runs away. -/
def StableDeformation {X : Type _} (d : DeformationData X) (C : Rat) : Prop :=
  1 ≤ C ∧ ∀ t x, d.deformation t x ≤ C

/-- **The repaired main conjecture (CONJECTURE — the sixth
`sorry`, named `repaired_sweet_spot_implies_smoothness`,
superseding §3's S1 under its vacuous determinant
reading).** Stable DEFORMATION (full-gradient band) plus
proper flow rate implies smoothness. Located by the canon
audit in the BKM / Neustupa–Penel neighbourhood: no
published theorem uses this hypothesis, and §7's
decomposition applies to it unchanged — its core is the
implication deformation-band ⇒ vorticity bound. Stated as
a theorem closed by `sorry`: the `sorry` IS the
conjecture. -/
theorem repaired_sweet_spot_implies_smoothness {X : Type _}
    (d : DeformationData X) (hNS : d.sol.solvesNS) (C vLo vHi : Rat)
    (hDef : StableDeformation d C)
    (hRate : ProperFlowRate d.sol vLo vHi) :
    d.sol.remainsSmooth := by
  sorry

/-! ### The partial discharge the canon DOES give: Prodi–Serrin

The audit's one positive implication: on a BOUNDED domain
(or torus), the schema's SPEED half alone — `|u| ≤ vHi`
pointwise for all time — places the solution in
`L∞_t L∞_x ⊂ L∞_t L³_x`, inside the Prodi–Serrin range
(`2/q + 3/p = 1`, `p > 3`) and at the Escauriaza–Seregin–
Šverák endpoint. There, smoothness follows from the
literature with the geometric half entirely idle. On `ℝ³`
the implication fails (no spatial decay). Bundled in the
witness pattern of §7: -/

/-- A Prodi–Serrin witness over a solution: the domain is
bounded (opaque predicate, schema stand-in for finite
measure), and the criterion — bounded domain + speed band
implies smoothness — carried as data. For actual solutions
this criterion is the Prodi (1959) / Serrin (1962) /
Ladyzhenskaya theorem at its `L∞` corner, with the
Escauriaza–Seregin–Šverák (2003) endpoint behind it; at
schema level it is a field, as in §7, because
`remainsSmooth` is opaque here. -/
structure ProdiSerrinWitness (X : Type _) where
  /-- The underlying flow. -/
  sol : NSSolution X
  /-- The domain is bounded / finite-measure. -/
  boundedDomain : Prop
  /-- The criterion: on a bounded domain, a proper flow
  rate alone implies smoothness. -/
  criterion : ∀ vLo vHi : Rat, boundedDomain →
    ProperFlowRate sol vLo vHi → sol.remainsSmooth

/-- **PROVED by pure logic (no `sorry`) — the bounded-domain
discharge of the main claim's speed half.** Given a
Prodi–Serrin witness over a bounded domain, proper flow
rate implies smoothness, no geometric hypothesis used.
This is the one place the 2026-11-06 schema, as stated,
touches a proved theorem of the canon. -/
theorem smoothness_from_speed_band_on_bounded_domain {X : Type _}
    (w : ProdiSerrinWitness X) (hb : w.boundedDomain)
    (vLo vHi : Rat) (hRate : ProperFlowRate w.sol vLo vHi) :
    w.sol.remainsSmooth :=
  w.criterion vLo vHi hb hRate

/-! ### The Riemann cross-reference (audit outcome)

The program's second band statement — the critical strip
`0 < Re(s) < 1`, zeros claimed on the line inside its
walls — was cross-referenced against the spectral canon
(Montgomery pair correlation; Odlyzko's GUE numerics;
Berry–Keating `H = xp`; Connes' trace formula;
Bender–Brody–Müller, CONTESTED — Bellissard's comment
stands against its analysis; Fyodorov–Keating log-correlated
fields and freezing). The audit's plain finding:

**NO published work connects Navier–Stokes REGULARITY —
any criterion of the canon above — to the Riemann
hypothesis.** No implication runs in either direction; the
two band statements are a structural rhyme (maintenance
inside, fault outside), and this file records the rhyme as
an ANALOGY, not a bridge. What genuinely exists one level
down is shared MACHINERY: Gaussian multiplicative chaos was
created by Kahane to rigorise the Kolmogorov–Obukhov
multiplicative-cascade model of turbulence dissipation, and
Saksman–Webb PROVED that the critical-line statistics of
`ζ` are a Gaussian multiplicative chaos (Fyodorov–Keating's
freezing-transition predictions for `log|ζ|` maxima were
likewise largely proved after the fact — about VALUES of
`ζ` on the line, not the location of zeros; RH-agnostic).
A recent loop-space turbulence programme (Migdal, 2025–26
preprints) claims turbulence exponents derive from the
zeros of `ζ`: flagged here as UNVERIFIED — extraordinary,
single-author formalism, no independent confirmation, and
about decaying-turbulence statistics, not regularity. It is
recorded as a flagged preprint, never as a result.

### The straggler list, updated (2026-11-08, second audit)

* **S1 (§3) — SUPERSEDED.** Vacuous under its determinant
  reading for incompressible flow. Replaced by S1R.
* **S1R (§8) — THE live main straggler.** Deformation band
  + rate band ⇒ smoothness. In the BKM/Neustupa–Penel
  neighbourhood, identical core to §7's decomposition
  (band ⇒ vorticity bound), no published form.
* **S1-BD (§8) — DISCHARGED on bounded domains** (modulo
  the literature criterion carried as witness data):
  Prodi–Serrin / ESS via the speed band alone.
* **S2, S3, S4 (§5) — unchanged stragglers.** The canon
  audit adds one note to S4: Caffarelli–Kohn–Nirenberg
  bounds the singular set's size unconditionally (partial
  regularity), so "disorder smooths away" has a published
  neighbour about how BAD failure can be — not a discharge.
* **S5 (§6) — unchanged, refined in §7.** The thermal
  sustain conjecture; its instances in print, its universal
  form open, protocol-4 grading it under F17.
* **Tao's boundary (method, not a sorry):** the averaged-
  model blow-up (2016) proves no argument from energy-type
  estimates alone can settle regularity — any schema at
  this level of abstraction inherits the warning: the
  implication can be formally valid while the physical
  claim waits on structural input the predicates hide. -/

end NSCompression
