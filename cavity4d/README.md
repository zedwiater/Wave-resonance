# cavity4d — smooth 4D cavity side project

A continuous-domain companion to the 1D-ring `wave48` lattice work.
"4D" = (rho, phi, z) + time through the propagator.

## v2: cylindrical grid (current)

v1 used a Cartesian grid whose 4-fold symmetry aliased Lz by multiples
of 4, corrupting the scattering measurement. v2 is cylindrical
(40 x 64 x 32) with a spectral phi dimension: **Lz is an EXACT conserved
quantity** of the discrete system (selfcheck: share(l=4) = 1.000000 after
100 steps). Radial kinetic via conservative finite-volume Laplacian,
diagonalized once per angular mode; z via FFT; Strang split-step.

## The three acts

1. **Fill** — from captured expansion spectra (`../spectra/*.npz`):
   48 OAM amplitudes mapped onto cylindrical modes, each divided by its
   radial-envelope norm so filled Lz-powers equal captured |a_l|^2
   (selfcheck: max deviation 2.2e-16).
2. **Emerge** — shared-reservoir saturable gain + aperture loss.
   Measured on real data: a single twist emerges at **99.2% share**,
   entropy 2.5-3.9 -> 0.06, sustained at E~2.6 by the pump
   (without pump: E -> 0).
3. **Scatter** — bit-encoded data packet (8 probe OAM modes) through the
   propagator. A pure twist is phi-symmetric so it cannot mix Lz (exact
   symmetry); the physical background is the twist dressed with a
   companion twist, whose azimuthal fringes couple l -> l+-2.

## Planck-scale deformity (`--planck`)

A deformity parameter D reshapes the cavity at the Planck scale
(rho_P = 2*dr, the grid scale = smallest meaningful radius):

- **D = +1, isolated**: repulsive core reflects waves at the Planck
  scale. The expansion is isolated (unitary, energy conserved) and
  smooths into a **standing wave at the minimum scale** — measured
  standing-wave ratio SWR = 26.6 in the Planck shell (deep nodes).
- **D = -1, leak**: absorptive core drains the field. **Higher energy
  leaks through the Planck scale**: 60% of the ring's energy drains on
  arrival (E 0.85 -> 0.34), SWR = 1.1 (flat, no standing wave).
- **D = 0, neutral**: control, SWR = 5.8.

Experiment: a Gaussian ring at rho=3 pulled inward by the trap toward
the Planck core, nothing else acting (no gain, no aperture loss).

```
../venv/bin/python cavity4d.py --planck
```

## Honest results

- The S-matrix is essentially diagonal: twist-dressed cavity scatters
  ~0.3% into +-2 sidebands; bare cavity 0.000%. The coupling is
  off-resonant (centrifugal detuning >> fringe coupling), so **OAM
  channels are preserved to 99.7%** — channel isolation, a feature for
  the wave computer, not a bug.
- Strong, controlled scattering needs resonant driving (time-modulated
  twist at the inter-mode transition frequency) — documented next step,
  not yet implemented.

## Run

```
../venv/bin/python cavity4d.py --selfcheck   # 8/8 required
../venv/bin/python cavity4d.py --emerge  --fill spectra/decay_bh_g001.npz --tick 0
../venv/bin/python cavity4d.py --scatter --fill spectra/decay_bh_g001.npz --tick 0  # saves S_matrix.npz
```

## Generational hum control

`generations.py` runs N long-horizon generations (~28 min each at
~100 steps/s on the 5900XT), each with an online recursive hum
controller holding E inside a calibrated band, and a meta-adjuster
between generations (damp rate on oscillation, strengthen aperture
differential loss while share < 0.7, cap aperture at 8.0; each gen
starts with gain 40% too hot so the controller must earn its keep).

`resume_generations.py` continues an existing generations JSONL
(params carried through the meta-adjuster, generation numbering
continued, provenance in `resumed_from`). It carries the
pre-committed falsifier for the aperture lever: if the aperture is
pinned at its 8.0 cap and |d(share)| < 0.01 for three consecutive
generations, the run halts early with the verdict "aperture lever
exhausted". Share >= 0.7 halts with "lever confirmed".

2026-10-15, gens 1-6: steady-state violations zero (all violations
from the intentional startup shock); twist share 0.209 -> 0.384
monotonic but under 0.7; dominant mode l=-3, not the l=-1 of the
12k-step runs — aperture strengthening selects a different mode.

## Lessons (failures preserved)

- v1 Cartesian grid: 4-fold symmetry aliased Lz by +-4k — caught by
  checking volume-overlap powers, fixed by going cylindrical.
- Local saturable gain sharpens hot spots, which *broadens* mode content
  (the opposite of selection). Real single-mode selection needs a shared
  reservoir + differential loss (the laser mechanism).
- Ring-based OAM analysis + adaptive radius produced fake "condensation".
  Fixed with exact phi-FFT projection.
- Amplitude loss rate g on the field = 2g on the energy. Don't confuse them.
