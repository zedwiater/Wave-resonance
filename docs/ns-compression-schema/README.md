# Navier–Stokes compression schema — Lean 4 statement

Zak Wiater, 2026-11-06. **A conjecture, stated formally in
Lean 4.** This is a statement artifact: it formalizes Zak's
schema precisely enough to be attacked. It does not prove it,
and nothing in this directory should be quoted as a proof.

File: `NSCompression.lean` (namespace `NSCompression`).
Toolchain pin: `lean-toolchain` copied from the house staging
project `mhd-zeta-push` (`leanprover/lean4:v4.36.0-rc1`).

## The schema in plain language

Zak's words, 2026-11-06: *"Smoothness is a fault of unstable
geometric compression."*

> If a flow's geometric compression is everywhere stable —
> bounded, and maintained — the solution remains smooth.
> Contrapositively: if smoothness ever fails, the compression
> was unstable somewhere first. Smoothness failure is a
> *diagnostic* of compression instability, not an intrinsic
> pathology of the Navier–Stokes equations.

**Sharpening (Zak, ~15:17 ET, superseding the single-condition
form of his 15:15 ET order):** *"under proper geometry and
flow rate NS would never smooth."* The hypothesis is a **pair**
— proper geometry AND proper flow rate, the session's two
dials: the density edge (compression ratio χ) and the filament
speed edge (v\*). And the conclusion strengthens to **never**:
under the pair, the smoothing fault occurs at no time;
structure is maintained for all t.

Companion physical claim (same session; his evidence is our
own simulation boxes): a hydrodynamic system cannot maintain
the chaos it creates when its geometry or flow rate is out of
band — injected disorder smooths away (selective decay /
Taylor relaxation, observed in every box we ran). Maintained
structure requires the sweet spot: stable geometric
compression at the proper flow rate.

## What each declaration is

| Declaration | Kind | Corresponds to |
|---|---|---|
| `NSSolution` | definition (structure with axioms) | The solution concept: flow map `Φ`, Jacobian distortion `det DΦ`, flow rate, plus two opaque predicates — `solvesNS`, `remainsSmooth` |
| `StableCompression sol C` | definition | Proper geometry: distortion trapped in `[1/C, C]` at all points, all times; `C` is the dial bound |
| `OptimalStableBound sol C` | definition | The tightest stable `C` — how much distortion the flow actually uses |
| `ProperFlowRate sol vLo vHi` | definition | Proper flow rate: speed inside `[vLo, vHi]` everywhere, all times; `vHi` is the v\* edge |
| `InSweetSpot sol C vLo vHi` | definition | The pair, conjoined under one name |
| `sweet_spot_implies_smoothness` | **CONJECTURE** (`sorry`) | The main statement: sweet spot ⇒ remains smooth |
| `exists_sweet_spot_implies_smoothness` | theorem (proved from the conjecture, no new `sorry`) | Same, with the band existentially quantified |
| `blowup_requires_leaving_the_band` | theorem (proved, contraposition) | The diagnostic direction: ¬smooth ⇒ the pair failed, for every band |
| `DisorderExperiment`, `MaintainsDisorder`, `SmoothsAway` | definitions (schematic) | An injection experiment as data; "maintained" and "smooths away" made precise over it |
| `sweet_spot_never_smooths` | **CONJECTURE** (`sorry`) | The NEVER form: in the sweet spot, disorder is maintained at a positive fraction at *every* t |
| `maintained_disorder_requires_sweet_spot` | schematic (`sorry`) | Companion, direction 1: maintained chaos ⇒ some sweet-spot band held |
| `out_of_band_smooths_disorder` | schematic (`sorry`) | Companion, direction 2 (the mirror): geometry out at every bound OR rate out at every band ⇒ disorder smooths away |
| `maintains_and_vanishes_absurd` | theorem (proved) | Bare logical incompatibility of "maintained from T" with "below threshold from T" — definitional only |

**`sorry` accounting (nothing hidden): exactly 4** —
`sweet_spot_implies_smoothness`,
`sweet_spot_never_smooths`,
`maintained_disorder_requires_sweet_spot`,
`out_of_band_smooths_disorder`. Every other theorem in the
file is proved from definitions and those four by pure logic.

## Formalization choices (each one a choice, flagged)

1. **Abstract domain.** The space is an abstract type `X`.
   Instantiate with ℝ³ or the 3-torus 𝕋³ in a future Mathlib
   development; the schema's implications do not depend on the
   choice, so the schema does not make it.
2. **Rationals, core Lean only.** Times, distortions, speeds
   and bounds are `Rat`-valued, so the file needs no Mathlib.
   The physical quantities are real-valued; `Rat` is dense in ℝ
   and the logical shape of every statement is unchanged.
   This is the price of a Mathlib-free statement file.
   (The 2026-11-06 typecheck found the first draft's `ℚ` notation
   is Mathlib-only, not core Lean — `Rat` is the core spelling.)
3. **Determinant by characteristic properties.** `distortion`
   is structure data constrained by positivity, value 1 at
   `t = 0`, and the cocycle identity (the chain rule
   `distortion (t+s) x = distortion s (Φ t x) * distortion t x`).
   An analytic construction of `det DΦ` from `Φ` requires
   Mathlib differential geometry and is out of scope here.
   Likewise `flowRate` is data (with nonnegativity); its
   identification with `|u|` is analytic.
4. **Opaque analytic predicates.** `solvesNS` and
   `remainsSmooth` are `Prop` fields of the solution concept,
   not unfolded definitions. The schema's content is the
   implication *between* the compression/rate predicates
   (fully defined) and these analytic predicates. Unfolding
   them is PDE theory, not schema.
5. **Conjecture as theorem + `sorry`.** House discipline for
   statement artifacts: the conjectured implications are
   stated as theorems so their exact logical form is checkable,
   closed by `sorry` so nothing pretends to be proved, and
   counted above.
6. **The pair as two hypotheses + one conjunction.** Declared
   choice per Zak's 15:17 refinement: `StableCompression` and
   `ProperFlowRate` are separate named predicates, taken as
   separate hypotheses (`hGeom`, `hRate`) in the main
   statement, and conjoined as `InSweetSpot` for the companion
   statements that quantify over bands.
7. **"Never" as an all-time quantifier.** The strengthened
   conclusion is `∃ θ > 0, ∀ t, θ * injected ≤ disorder t` —
   maintenance at *every* time, not merely eventual
   maintenance. Stated over `DisorderExperiment` in §5 (it
   needs that definition) and cross-referenced from §3.

## Compile status

**TYPECHECKED 2026-11-06 ~16:25 ET — `lean NSCompression.lean`
exits 0 under the pinned toolchain
(`leanprover/lean4:v4.36.0-rc1`, installed on this VM via
elan, `~/.elan/bin/lean`). Exactly 4 `sorry` warnings, one
per named conjecture (lines 192, 298, 311, 327); the three
proved theorems carry no warnings. Re-check with a bare
`lean NSCompression.lean` from this directory.

The first check (same day, same toolchain) FAILED — the file
as delivered did not compile under core Lean. Three
mechanical fixes, all meaning-preserving, applied 2026-11-06
and re-verified by the passing check:
1. `Type*` → `Type _` (15×) — `Type*` is Mathlib notation,
   not core Lean syntax.
2. `ℚ` → `Rat` (24×) — the `ℚ` notation is Mathlib-only;
   `Rat` is the core type, with the same order/arithmetic.
3. Two binder annotations (`flowMap_add`,
   `distortion_cocycle`: `∀ (s t : Rat) (x : X)`) — untyped
   binders left `t + s` stuck at elaboration.
4. The proved §5.3 theorem re-proved with core lemmas
   (`Rat.not_lt`, `Rat.le_refl`) — the original
   `lt_irrefl` / `lt_of_lt_of_le` / `le_refl` are Mathlib,
   not core. The anonymous-constructor pattern in
   `exists_sweet_spot_implies_smoothness` was fine, as
   flagged. No theorem statement, hypothesis, or `sorry`
   count changed: same 4 conjectures, same 3 proved results.

Not pushed anywhere. The `mhd-zeta-push` staging project was
read for conventions only and not modified.

## Revision of 2026-11-08 — the refined superfluid parameter

Zak's order (2026-11-08 ~10:40 ET): revise the equation set with the refined parameter and run it through Lean.

**Added (§6 of the file):**
- `ThermalConfig` — the thermal layer: a local normal-fraction field `f = ρₙ/ρ` (bounded 0 ≤ f ≤ 1) and a twist inventory field, bundled as structure data exactly as §1 bundles `distortion`/`flowRate`.
- `bandRatio f = (1 − f)/f` — the ρₛ/ρₙ factor of Landau's u₂²; `frictionWeight f = f·(1−f)` — the BK/HVBK mutual-friction form (declared coupling, phenomenological in helium too; the √(TS²/C) prefactor and the equation of state remain pins, flagged in the paper).
- Four PROVED definitional lemmas (no sorry): friction weight vanishes at both pure endpoints; friction weight at the equal mixture is 1/4 (the §16 churn peak); band ratio at the equal mixture is 1.
- `PrecipitationActive` / `TwistSustains` — the channel and the maintenance shape.
- **Fifth named conjecture, `sustain_requires_precipitation` (sorry, at line 467):** twist sustains only where internal precipitation is active — the schema form of paper §17.1. Its contrapositive `no_precipitation_no_sustain` is derived by pure logic (no additional sorry) and is the form protocol-4's precipitation-off controls grade (falsifier F17).

**Verified 2026-11-08:** `lean NSCompression.lean` (elan, Lean 4.36.0-rc1) exits **0** with exactly **5 sorry warnings** at lines 192/298/311/327/467 — the four original named conjectures plus the sustain conjecture. Nothing else changed: the original four conjectures and all proved theorems stand as they were.

## Revision of 2026-11-08 (later) — literature refinement; the true stragglers

Zak's follow-up (~11:30 ET): do any of the reviewed papers refine the sorries further — and where a paper is publicly usable, take the derivative and name the true stragglers.

**Audit (checked, not assumed):** the 12 downloaded papers were text-searched in full — NONE is a Navier–Stokes regularity paper (no Beale–Kato–Majda, Prodi–Serrin, or Caffarelli–Kohn–Nirenberg anywhere in the set). The smoothness family (§3/§5) therefore receives **no discharge** from this set. The set DOES bear on §6's sustain conjecture: Levkov/Dmitriev prove Bose-star nucleation in the kinetic regime (no scattering channel, no condensation in their equations); Petrov's droplets exist only via the Lee–Huang–Yang channel; Voit's cores sustain only while the precipitation channel runs — instances of the sustain implication, each in its own system.

**Added (§7 of the file), all PROVED, no new `sorry`:**
- `frictionWeight_eq_zero_iff` — the friction weight vanishes exactly at the pure phases.
- `precipitationActive_iff_mixed_point` — precipitation is active iff some point is a genuine mixture, 0 < f < 1.
- `not_precipitationActive_iff_pure` — **precipitation-off = pure-phase everywhere**: protocol-4's F17 controls are the conjecture's exact hypothesis class, not an approximation.
- `sustain_implies_mixed_point` — the sustain conjecture's conclusion made pointwise (derived from it; no new sorry).
- `VorticityControl` + `smoothness_reduces_to_band_controls_vorticity` — the BKM-shaped decomposition of §3, proved by pure logic: given a vorticity-control witness, the main conjecture reduces to the single implication *band ⇒ vorticity bound* (the criterion carried as data, as §1 carries its opaque predicates; BKM itself is NOT in the reviewed set and is flagged as such).

**Verified 2026-11-08:** `lean` exits **0**, sorry count **unchanged at 5** (lines 192/298/311/327/467). Nothing was discharged; what changed is how much of each conjecture is now pinned.

**The true stragglers:**
- **S1** main smoothness — core located: *band ⇒ vorticity-integral bound*. No published form exists (bounded Jacobian distortion controls volume ratios; nothing bridges it to a vorticity bound). The live core of the NS claim.
- **S2** never-smooths — S1's physical face over experiments; untouched by the set.
- **S3** maintained ⇒ sweet spot — the converse; least anchored of the five.
- **S4** out-of-band ⇒ smooths away — best empirical support (every box this program ran), still unproved.
- **S5** sustain ⇒ precipitation — refined as above; instances proved in print, the universal schema form open; protocol-4 grades it under F17.

## Revision of 2026-11-08 (third) — the NS canon audit: S1 SUPERSEDED, repair S1R, bounded-domain discharge; Riemann cross-reference

Zak's order (~11:37 ET): grab and compare the NS papers and Riemann, cross-reference the same way, update citations and Lean accordingly. The canon (Leray; Prodi–Serrin–Ladyzhenskaya; Beale–Kato–Majda; Caffarelli–Kohn–Nirenberg; Constantin–Fefferman; Escauriaza–Seregin–Šverák; Neustupa–Penel; Tao) was located and read; 16 full texts are downloaded in the co-revision files (`papers-ns-riemann/`), titles verified.

**HEADLINE FINDING — the §1 determinant reading is VACUOUS for incompressible NS.** §1 defines `distortion` as `det DΦ` (volume ratio) and `solvesNS` as the incompressible equations. For incompressible flow `det DΦ ≡ 1` identically, so `StableCompression` holds for EVERY incompressible solution at any C ≥ 1 — the geometric half of the main conjecture was empty as formalized on 2026-11-06 (a compressible density-ratio notion imported into an incompressible claim). Pure linear algebra agrees: singular values (M, 1, 1/M) have determinant 1 and unbounded norm; bounded det bounds neither vorticity nor strain. **S1 is therefore marked SUPERSEDED — not proved, not refuted as physics: discharged as vacuous under its stated reading.** The finding and its evidence are recorded in §8 of the file, not hidden.

**The repair (new in §8):** `DeformationData` — distortion as the full deformation gradient's magnitude (singular-value band; axioms: ≥ 1, 1 at t = 0, submultiplicative cocycle) — and `StableDeformation`. **S1R `repaired_sweet_spot_implies_smoothness` (sixth sorry, line 796)** is the live main conjecture, located in the BKM/Neustupa–Penel neighbourhood (d/dt DΦ = (∇u)DΦ), with §7's decomposition core unchanged: deformation-band ⇒ vorticity bound, no published form.

**The discharge the canon gives:** on bounded domains the SPEED band alone sits inside Prodi–Serrin (and at the ESS endpoint) — `ProdiSerrinWitness` + `smoothness_from_speed_band_on_bounded_domain`, PROVED by pure logic modulo the literature criterion carried as witness data. On ℝ³ even that fails (no decay). CKN adds a neighbour for S4 (unconditional bound on the singular set's size — not a discharge). Tao 2016 stands as the method boundary: no energy-level argument can settle regularity, so the schema's formal validity does not advance the physical claim without structural input.

**Riemann cross-reference (in §8):** NO published work connects NS regularity to RH — recorded as an analogy (band rhyme), not a bridge. Genuine shared machinery one level down: Gaussian multiplicative chaos (Kahane, for the Kolmogorov–Obukhov turbulence cascade model) and Saksman–Webb's PROOF that ζ's critical-line statistics are a GMC; Fyodorov–Keating freezing predictions for log|ζ| largely proved (values, not zero locations; RH-agnostic). Bender–Brody–Müller flagged CONTESTED (Bellissard's comment). Migdal's 2025–26 loop-space turbulence↔zeros claims flagged UNVERIFIED — recorded as a flagged preprint, never a result.

**Verified 2026-11-08:** `lean` exits **0** with exactly **6 sorry warnings** (192/298/311/327/467/796): S1 superseded-but-retained for the record, S2/S3/S4 stragglers, S5 refined, S1R the live main conjecture.
