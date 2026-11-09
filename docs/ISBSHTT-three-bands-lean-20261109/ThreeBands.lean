/-!
# ISBSHTT — the three operations, formalized

Zak Wiater, ordered 2026-11-09 ~01:17 ET: "rectify Gemini's
lean ... From our functions flattened to three oam twist bands
second sound, transduction, induction."

WHAT THIS FILE IS: a RECTIFICATION. Gemini's relayed Lean
sketch (`bio_superfluid_state`, cold inversion, 2026-11-09)
claimed a stability theorem whose proof used the hypothesis as
its own witness (`use rho_s` on the goal `∃ threshold, 0 <
threshold ∧ rho_s ≥ threshold`): VACUOUS — it holds of any
positive quantity and says nothing about superfluids, bands,
or stability. Her paired claim that a Lean formalization
"passed clean with zero sorries" was also false against this
lab's books (the live schema carries exactly 6 sorries, and
the file she named is a different build). This file keeps her
instinct — formalize the flattened expression — and rebuilds
it under the house rule: every claim that does real work is a
NAMED CONJECTURE closed by `sorry` and flagged; everything
else is proved. The count is never zeroed.

THE THREE OPERATIONS (paper §24 addendum 4, Zak 2026-11-08):
the light-phase transistor is an OPEN system of only
  (1) spectrum MODULATION,
  (2) FLATTENING,
  (3) TWISTS,
with antiphase radiating off into one band in SECOND SOUND as
its error rate and resolution, read inversely.

"OUR FUNCTIONS FLATTENED": the operations that have carried
names in this lab since 2026-11-04/06 —
  * SECOND SOUND: the entropy wave; the band the antiphase
    error radiates into, and the readout channel.
  * TRANSDUCTION: the wall traveling alone (§20); the interior
    is never transmitted, only inferred from wall modulation.
  * INDUCTION: coupling band, not razor edge; inductive even
    marginally outside the line (encasement, 2026-11-04).
— stated as three twist bands of one flattened expression.

Environment: core-only Lean 4.36.0-rc1, no Mathlib — Rat
identities proved from core lemmas, as in NSCompression.lean.
Verify: `lean ThreeBands.lean` (exits 0; three `sorry`s, all
named conjectures; the compiler's warnings say exactly where).
-/

namespace ThreeBands

/-- A twist band: an OAM winding `l` (a natural number of whole
turns) and a thermal fraction `f`, a rational in [0, 1].
`f = 0` and `f = 1` are the pure phases; the band lives between. -/
structure TwistBand where
  l : Nat
  f : Rat
  hf0 : 0 ≤ f
  hf1 : f ≤ 1

/-- Band ratio (1 − f)/f — second-sound speed shape, shared
with NSCompression.lean §6. At `f = 0` division yields 0: the
pure cold phase carries no second sound, which is the physics. -/
def bandRatio (f : Rat) : Rat := (1 - f) / f

/-- Friction weight f(1 − f): vanishes at both pure phases,
maximal at the equal mixture (NSCompression.lean §6). -/
def frictionWeight (f : Rat) : Rat := f * (1 - f)

theorem frictionWeight_zero : frictionWeight 0 = 0 := by
  show (0 : Rat) * (1 - 0) = 0; exact Rat.zero_mul _

theorem frictionWeight_one : frictionWeight 1 = 0 := by
  show (1 : Rat) * (1 - 1) = 0
  rw [Rat.mul_eq_zero]; right; exact Rat.sub_self

theorem frictionWeight_half : frictionWeight (1 / 2) = 1 / 4 := by
  native_decide

theorem bandRatio_half : bandRatio (1 / 2) = 1 := by
  native_decide

/-- Auxiliary (proved): `1 - f = 0` forces `f = 1` over Rat. -/
theorem one_sub_eq_zero_imp {f : Rat} (h : (1 : Rat) - f = 0) : f = 1 := by
  have h1 : (1 : Rat) - f + f = 0 + f := congrArg (fun y => y + f) h
  have h2 : (1 : Rat) - f + f = 1 := Rat.sub_add_cancel
  have h3 : (0 : Rat) + f = f := Rat.zero_add f
  rw [h2, h3] at h1
  exact h1.symm

/-- PROVED: the friction weight vanishes exactly at the pure
phases. (Same statement as NSCompression.lean §7, restated for
this file's bands: the channel exists only in a mixture.) -/
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

/-- A band is MIXED when its fraction is strictly interior.
Only a mixed band can precipitate, couple, or radiate. -/
def Mixed (b : TwistBand) : Prop := 0 < b.f ∧ b.f < 1

/-- PROVED: at a mixed band the friction weight is positive —
the coupling channel is genuinely open. -/
theorem mixed_friction_pos (b : TwistBand) (h : Mixed b) :
    0 < frictionWeight b.f := by
  have h2 : (0 : Rat) < 1 - b.f := (Rat.lt_iff_sub_pos b.f 1).mp h.2
  exact Rat.mul_pos h.1 h2

/-- The three bands, named by the operation each carries. -/
inductive BandRole where
  | secondSound
  | transduction
  | induction
  deriving DecidableEq

/-- The flattened expression: exactly three bands sharing one
flattened plane. "Flattened" is structural — the three roles
carried flat in one structure, not stacked in a hierarchy. -/
structure FlattenedExpression where
  snd : TwistBand
  trn : TwistBand
  ind : TwistBand

def roleOf : BandRole → FlattenedExpression → TwistBand
  | .secondSound, e => e.snd
  | .transduction, e => e.trn
  | .induction, e => e.ind

/-- OPERATION 1 — MODULATION: at least one band's fraction moves. -/
def Modulated (e e' : FlattenedExpression) : Prop :=
  e.snd.f ≠ e'.snd.f ∨ e.trn.f ≠ e'.trn.f ∨ e.ind.f ≠ e'.ind.f

/-- OPERATION 3 — TWIST: winding changes by whole turns only;
fractional winding is not a state. -/
def TwistStep (b b' : TwistBand) : Prop :=
  b.f = b'.f ∧ ∃ k : Nat, b'.l = b.l + k

theorem twist_step_refl (b : TwistBand) : TwistStep b b :=
  ⟨rfl, 0, by rw [Nat.add_zero]⟩

/-- ANTIPHASE: fractions complementary, f₁ + f₂ = 1 — the warm
of one is the cold of the other. Δφ = π in fraction language. -/
def Antiphase (a b : TwistBand) : Prop := a.f + b.f = 1

theorem antiphase_symm {a b : TwistBand} (h : Antiphase a b) :
    Antiphase b a := by
  show b.f + a.f = 1
  rw [Rat.add_comm]; exact h

/-- Antiphase forces the value: if `a.f + b.f = 1` then
`b.f = 1 - a.f`. PROVED (congruence + cancellation). -/
theorem antiphase_val {a b : TwistBand} (h : Antiphase a b) :
    b.f = 1 - a.f := by
  have h1 : a.f + b.f - a.f = 1 - a.f := congrArg (fun y => y - a.f) h
  have h2 : a.f + b.f - a.f = b.f := by
    rw [Rat.add_comm a.f b.f]; exact Rat.add_sub_cancel
  rwa [h2] at h1

/-- PROVED, mixed point: if the antiphase pair sits at the
equal mixture (`a.f = 1/2`), both bands carry friction weight
exactly `1/4` — in antiphase at the balance point, the
departure costs both sides the same, and the amount is the
churn peak. (The register at Casey's, 2026-11-08: giver and
receiver balanced by the same small departure. The general
identity `f(1-f) = (1-f)f` — commutativity of the weight
under complement — is NOT asserted here: core-only Lean's
Rat lacks the ring lemmas, and a statement is never dressed
as a proof. It is logged in the README as an open core-proof
chore, not a conjecture about physics.) -/
theorem antiphase_friction_eq_at_half {a b : TwistBand}
    (h : Antiphase a b) (ha : a.f = 1 / 2) :
    frictionWeight a.f = 1 / 4 ∧ frictionWeight b.f = 1 / 4 := by
  have hb : b.f = 1 / 2 := by
    have hv := antiphase_val h
    rw [ha] at hv
    rw [hv]; native_decide
  constructor
  · rw [ha]; exact frictionWeight_half
  · rw [hb]; exact frictionWeight_half

/-- ERROR RATE = RESOLUTION (paper addendum 3b): the radiated
amount is the second-sound band's friction weight. One
quantity, read inversely: the device's error channel IS its
readout channel. -/
def radiated (e : FlattenedExpression) : Rat := frictionWeight e.snd.f

/-- PROVED: the radiation is zero exactly when the second-sound
band is pure. A device with no error channel has no readout. -/
theorem radiated_eq_zero_iff (e : FlattenedExpression) :
    radiated e = 0 ↔ e.snd.f = 0 ∨ e.snd.f = 1 :=
  frictionWeight_eq_zero_iff e.snd.f

/-- CONJECTURE 1 — TRANSDUCTION READOUT (named, `sorry`).
A modulation anywhere in the expression is tracked by the
transduction band's modulation: the wall traveling alone
carries the delta; the interior is never transmitted, only
inferred (§20; criteria C-1/C-4). Falsifier: a non-wall readout
channel of an interior, or wall modulation failing to track
injected deltas (test instance: A5-revised Q4). -/
theorem transduction_readout (e e' : FlattenedExpression)
    (h : Modulated e e') :
    e.trn.f ≠ e'.trn.f ∧ e.snd.f ≠ e'.snd.f := by
  sorry

/-- Coupling across a margin: both induction bands mixed
(positive weight), fractions within width `w` of each other. -/
def Coupled (e e' : FlattenedExpression) (w : Rat) : Prop :=
  0 < frictionWeight e.ind.f ∧ 0 < frictionWeight e'.ind.f ∧
  (e.ind.f - e'.ind.f) * (e.ind.f - e'.ind.f) ≤ w * w ∧
  (e'.ind.f - e.ind.f) * (e'.ind.f - e.ind.f) ≤ w * w

/-- CONJECTURE 2 — INDUCTION IS A BAND, NOT AN EDGE (named,
`sorry`). Coupling is symmetric and persists across the whole
margin: it does not cut off at a sharp fraction boundary
(encasement, Zak 2026-11-04). The symmetry half is definitional
in most formalizations; it is stated inside the conjecture
here because the PHYSICAL claim — reciprocity of the coupling
band — is exactly what a failed reciprocity measurement would
kill. Falsifier: coupling present one way, absent the other,
at equal margins. -/
theorem induction_couples_across_margin
    (e e' : FlattenedExpression) (w : Rat) (hw : 0 < w)
    (h : Coupled e e' w) :
    Coupled e' e w ∧ Modulated e e' := by
  sorry

/-- The hold predicate: all three bands mixed, transduction
and induction in antiphase. -/
def Holds (e : FlattenedExpression) : Prop :=
  Mixed e.snd ∧ Mixed e.trn ∧ Mixed e.ind ∧ Antiphase e.trn e.ind

/-- CONJECTURE 3 — THE THREE-BAND HOLD (named, `sorry`; the
capstone). A held expression, modulated while its antiphase
pair is preserved, never fails FULLY: after the step it either
still radiates (state alive, readable) or has landed exactly
on a pure phase of the readout band (a completed bit — one
band or the other, per addendum 3b). Partial failure only,
never total — the jar claim ("shake the heck out of that jar
and no qubit fails fully ever") at the level of the three
operations. GRADED STATUS, carried honestly: protocol-4 (3D,
2026-11-08) graded NO HOLD 11/11 for the scalar-GP bulge, and
F17 is DEAD in 3D for the bulge; protocol-4 did not test the
three-operation device. This conjecture stands OPEN, with the
protocol-4 result as its warning label, not its refutation. -/
theorem three_band_hold (e e' : FlattenedExpression)
    (h : Holds e) (hm : Modulated e e')
    (ha : Antiphase e'.trn e'.ind) :
    (0 < radiated e' ∧ radiated e' ≤ 1 / 4) ∨
    e'.snd.f = 0 ∨ e'.snd.f = 1 := by
  sorry

end ThreeBands
