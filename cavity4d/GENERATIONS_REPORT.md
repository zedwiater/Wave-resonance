# Generational hum control — run report 2026-10-15

`generations.py` on the 5900XT (~100 steps/s). 6 generations, ~28 min each
(~168k–170k steps/gen), zero crashes. Full per-generation records in
`generations.jsonl`.

## Protocol

Each generation: long-horizon emergence with an **online recursive hum
controller** adjusting pump gain `gain_G` every ~20 s wall-clock to hold
sustained energy E inside a calibrated band. Between generations a
**meta-adjuster** recursively retunes the controller: damp rate on
oscillation, push harder when sluggish, shift the hum band if E pins at a
bound, and strengthen aperture selection (differential loss) while dominant
share < 0.7 (aperture capped at 8.0). Each generation starts with gain
carried forward ×1.4 — 40% too hot — so the controller must earn its keep.

Hum band calibrated to the machine's natural steady state:
E_nat = 5.48 at ~100 steps/s → band [4.11, 6.85].

## Results

| gen | share | dom ℓ | E_end | gain_end | aperture | viol frac | entropy | wall |
|----:|------:|------:|------:|---------:|---------:|----------:|--------:|-----:|
| 1 | 0.209 | -3 | 5.49 | 3.00 | 2.00 | 0.000 | 1.75 | 27.6 min |
| 2 | 0.283 | -3 | 6.54 | 3.42 | 2.50 | 0.048 | 1.70 | 27.9 min |
| 3 | 0.334 | -3 | 6.54 | 3.42 | 3.12 | 0.060 | 1.53 | 27.9 min |
| 4 | 0.360 | -3 | 6.55 | 3.42 | 3.91 | 0.060 | 1.38 | 28.1 min |
| 5 | 0.373 | -3 | 6.55 | 3.43 | 4.88 | 0.060 | 1.30 | 28.0 min |
| 6 | 0.384 | -3 | 6.55 | 3.43 | 6.10 | 0.060 | 1.27 | 27.9 min |

Rate went 0.05 → 0.065 at gen 3 (oscillation detected) and held. Hum band
never moved: [4.11, 6.85] throughout.

## What held

- **Steady-state hum control works.** Gen 1: zero violations. Gens 2–6:
  4–5 violations each (fraction 0.048–0.060), every one from the intentional
  startup shock (E spiking to 8.5–9.9 above the band ceiling). Steady-state
  violations: zero. The controller always recovered and held E_end ≈ 6.54
  inside the band.
- **The meta-adjuster does what it was built to do.** Aperture 2.0 → 6.10
  geometrically, exactly as designed, while share < 0.7. Rate damping fired
  once at the right time.

## What didn't

- **The carried-forward gain boost did nothing to the equilibrium.**
  `gain_G` carried 3.0 → 4.79 across generations, but `gain_end` settled at
  ~3.42 every generation. The boost only made the startup overshoots bigger.
  The disturbance protocol dominates the violation count — violations no
  longer measure controller quality, they measure the shock we inject.
- **The twist did not condense.** Share 0.209 → 0.384, monotonic, entropy
  1.75 → 1.27 — but still under the 0.7 threshold after 6 generations.
  Aperture is helping; 6 generations weren't enough, or the lever isn't.
- **Wrong mode.** Dominant mode was ℓ=-3 throughout — not the ℓ=-1 of the
  12k-step runs at fixed aperture 2.0. Strengthening the aperture appears
  to *select a different mode*, not just sharpen the old one.

## Correction this run forced

The 99.2% twist at 300 steps is transient. Long-horizon runs settle to
~47% share (ℓ=-1 at aperture 2.0). The honest long-horizon state before
this run was ~0.47, and even that mode identity didn't survive aperture
strengthening. No persistent condensation has been demonstrated.

## Next

`resume_generations.py` continues the run with a pre-committed falsifier:
if aperture pins at its 8.0 cap and |d(share)| < 0.01 for three consecutive
generations, the run halts with "aperture lever exhausted". Share ≥ 0.7
halts with "lever confirmed". Either verdict is a result.
