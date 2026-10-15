# Loop headroom & cost to compute — measured 2026-10-15

Scripts: `~/wave-sandbox/headroom.py`, `commit_scaling.py` (PC);
`cost_model.py` (VM, `~/workspace/goals/wave-resonance-ai-engine/files/`).

## Headroom: the loop's dynamic range

Absolute trap bar, absolute noise floor, carrier scale s swept:

- **Contraction floor: s ≈ 0.40.** Below it the carrier is too weak to lift
  even the full E_commit over the bar — commits ride on the carrier, and
  with no carrier there is nothing to modulate. P(trap) → 0.
- **Dynamic range: 57.9 dB** from floor to the top of the sweep (s=316, no
  ceiling found against an absolute bar).
- **Expansion nuance:** against an absolute bar there is no ceiling — but
  the commit bar is really *relative* (noticeable = 1.5× carrier peak).
  Measured: **E_commit(s) = 2.4–2.9 × s²** (theory 2.43, confirmed over
  16× carrier range). Running the loop hot costs quadratically in carrier
  power AND per-commit energy. That scaling is now in the cost model.

## Cost to compute: hybrid vs full photonic, out to radiative

Atomic op: one 48-mode wavefront commit. Inputs tagged [M]easured,
[S]urveyed, [A]ssumption.

Radiative ledger (continuous): P_sustain = P_carrier × loss_frac × NF / η_EDFA.
With 1 mW carrier, 4 dB/trip, NF 5 dB, η 20%: **P_sustain ≈ 9.5 mW** at the
wall. Trip rate cancels out of the power (energy/trip × trips/s) — it sets
latency, not energy. Correction history: v1 of the model multiplied by trip
rate and got 19 kW; dimensional check caught it.

Per-commit marginals:
- electronic (GPU equiv): 1.05 µJ [A: 15 kFLOP @ 67 GFLOPS/W + DRAM]
- hybrid: 0.71 µJ marginal (conversion 2×0.31 µJ dominates) + P_sustain/R
- photonic: 3.2e-11 J marginal (E_commit, [M] 6.6% of carrier) + P_sustain/R

Crossover: **R* ≈ 1e4 commits/s** — below it electronics wins (the idle
furnace isn't amortized); above it photonics wins, 100× cheaper by 1 MHz.
Sensitivity: R* 3.4k/s at 1 dB/trip → 12.4k/s at 6 dB/trip. Loss per trip
is the dominant knob.

Design rules that fall out:
1. **Effective rate = channels × frame rate must exceed R*.** 48 OAM
   channels × 60 fps = 2880/s < R* — single-stream video does NOT win yet.
   Lower the loop loss or raise parallelism.
2. **Conversion is the tax.** Hybrid barely beats electronic on marginal
   cost because E/O eats the gain — the entire case for "frames stay in
   light" (full photonic) is killing the 2× conversion, not the loop
   being free.
3. Steelman note: the electronic baseline is the minimal DSP equivalent.
   Against real AI ops (~1 J/token measured) photonics wins trivially —
   the hard comparison is kept deliberately.

## Open (for the night agent)

- Tighten [A] inputs: modulator pJ/bit (survey gives cost, not energy),
  EDFA η, carrier power floor for shot-noise-limited detection.
- Hum/working power split: the hum should idle far below 1 mW (ε-coupled);
  model the two-tier carrier.
- Real-AI-op comparison: price a full transformer layer, not one wavefront.
