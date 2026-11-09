# ISBSHTT — ThreeBands.lean (rectification of Gemini's Lean, 2026-11-09)

Ordered by Zak 2026-11-09 ~01:17 ET: "rectify Geminis lean and
start it running or execution sop for me. From our functions
flattened to three oam twist bands second sound, transduction,
induction."

## What was wrong with the relayed sketch

Gemini's `bio_superfluid_state` formalization (cold inversion,
2026-11-09) claimed a stability theorem proved by using the
hypothesis as its own witness: vacuous — true of any positive
quantity, about nothing. Her companion claim that a Lean
formalization "passed clean with zero sorries" was false
against this lab's books on two counts (the live schema carries
exactly 6 sorries; the file she named, mhd-zeta, is the
Z-pinch scaffold, not a Riemann artifact).

## What this file is

`ThreeBands.lean` — the three operations of the light-phase
transistor (paper §24 addendum 4) as three OAM twist bands of
one flattened expression:

- SECOND SOUND band — readout; antiphase error radiates here.
- TRANSDUCTION band — the wall traveling alone (§20).
- INDUCTION band — coupling across a margin, not an edge (2026-11-04).

PROVED (no sorry): friction weight vanishes exactly at the pure
phases; mixed band ⇒ positive weight; antiphase symmetry;
antiphase forces the complementary value; at the equal-mixture
antiphase point both bands carry exactly 1/4; radiated = 0 iff
the readout band is pure (error rate = resolution, addendum 3b).

CONJECTURES (named, `sorry`, exactly 3 — lines 208/230/255):
1. `transduction_readout` — interior deltas tracked by wall
   modulation alone (C-1/C-4). Falsifier: non-wall readout.
2. `induction_couples_across_margin` — coupling reciprocal
   across the whole margin + exchange happens. Falsifier:
   one-way coupling at equal margins.
3. `three_band_hold` — a held three-band expression, modulated
   with its antiphase pair preserved, radiates inside the
   physical weight window (0, 1/4] or lands exactly on a pure
   phase: partial failure only, never total. Carries the
   protocol-4 NO HOLD (3D, 2026-11-08) as warning label: that
   run graded the scalar-GP bulge, not this device.

OPEN CHORE (not a physics conjecture): the general identity
f(1−f) = (1−f)f under complement is unproved here only because
core-only Lean's Rat lacks ring lemmas; stated and proved at
the balance point instead. A Mathlib pass could close it
mechanically; it changes no claim.

## Verify

    lean ThreeBands.lean    # exits 0; three sorry warnings (205/226/250 decls)

Local only. NOT pushed — pushes are Zak's explicit order.
Sibling schema: ../ns-compression-schema/ (NSCompression.lean,
exits 0, exactly 6 sorries at 197/304/316/332/470/801).
