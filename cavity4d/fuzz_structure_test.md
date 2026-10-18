# The Fuzz Structure Test — Basement Experiment Spec

**Date:** 2026-10-18
**Question:** Is electronic "noise" actually white, or does it carry toroidal
mode structure from unresolved eddy boundaries?
**Status:** Spec. Not yet run.

---

## The Claim

Standard physics treats Johnson/thermal noise as fundamentally random —
flat spectrum, no structure, just the universe shrugging. The nested-eddy
framework predicts otherwise: what looks like fuzz is the boundary-layer
turbulence of toroidal micro-eddies. If true, the noise spectrum of a
toroidal conductor should carry harmonic mode content that a geometrically
trivial conductor (straight wire) lacks — same material, same temperature,
same Johnson floor, different geometry.

## The Prediction

A toroidal inductor's idle noise spectrum will show harmonic peaks
superimposed on the white Johnson floor, at frequencies related to the
toroid's geometry (circumference / wave speed → resonant modes). A straight
wire of identical copper length and DC resistance, measured identically,
will show a flat spectrum. The difference is the toroidal boundary
imprinting on the "random" fuzz.

Stronger version: the harmonic spacing in the toroid's noise peaks should
relate to the same ℓ=2 (quadrupole) dominance seen at galactic scale —
the lowest stable mode of a toroidal boundary.

## The Falsifier

Identical white spectra from both geometries = geometry does not imprint
on the noise. The cascade stops at lab scale. The fuzz really is just
thermal. We publish that too.

## Apparatus (basement budget, ~$30–50)

- **DUT A (toroidal):** toroidal inductor or small toroidal power transformer,
  primary winding unpowered, just sitting at room temperature. (A toroidal
  ferrite core with ~50 turns of magnet wire also works — wind it yourself.)
- **DUT B (control):** straight length of the same magnet wire, same total
  copper length and matched DC resistance (±5%), laid out straight, same
  room, same temperature.
- **Preamp:** low-noise audio preamp (even a cheap USB audio interface with
  mic preamp works — we need ~40–60 dB gain, noise floor below the DUT noise).
- **Digitizer:** USB sound card, 96 kHz sampling if available (gives 48 kHz
  Nyquist — plenty for audio-band noise).
- **Software:** any FFT spectrum analyzer (free: REW, Audacity spectrum view,
  or a 20-line Python script with numpy).

## Protocol

1. **Thermal soak.** Both DUTs in the same room for ≥1 hour. Same temperature
   = same Johnson floor. Verify with a thermometer (±1°C).
2. **Measure DUT B (control) first.** Record 60 seconds of noise, compute
   averaged power spectral density (Welch's method, 1 Hz bins if possible).
   Confirm flat spectrum — this validates the measurement chain.
3. **Measure DUT A (toroid).** Identical gain, identical duration, identical
   processing. Do not move the preamp or change any settings between runs.
4. **Swap and repeat.** Measure B again, then A again (ABBA sequence kills
   drift confounds).
5. **Compare.** Subtract the control spectrum from the toroid spectrum.
   Look for harmonic peaks rising above the white floor.

## What Counts as a Hit

- Reproducible peaks (present in both A runs, absent in both B runs) at
  harmonically related frequencies: f, 2f, 3f... or the toroidal ℓ=2
  signature (dominant 2nd harmonic).
- Peak frequencies within 20% of the predicted toroidal resonant modes
  f_n = n·v/(2πr), where r = toroid mean radius, v ≈ speed of EM wave
  in the winding (~0.6c for magnet wire).
- Statistical bar: peaks ≥3σ above the local white floor, in both A runs.

## What Counts as a Miss

- Flat spectra from both DUTs (within measurement noise). Cascade stops.
- Peaks present but identical in A and B (environmental pickup, not geometry).
- Peaks in A that don't repeat between runs (measurement artifact).

## Cost of Being Wrong

One evening, ~$40 in parts most of us already own. If it misses, we've
bounded the framework — the eddy cascade holds from cosmic to galactic
to local-interstellar scales (measured), but not to lab scale. That's
a real constraint, not a failure.

## Why This Matters

Every scale we've measured so far — CMB → Fermi bubbles → RM quadrupole
→ local B-field → IBEX — shows the same nested harmonic structure. The
lab is the next tier down. If the pattern holds in a $5 toroid on a
workbench, the framework isn't just astrophysics — it's physics, all
the way down. And if it doesn't, we know exactly where the boundary is.

---

*"A kid in a basement should be able to replicate it."*
*This is that experiment.*
