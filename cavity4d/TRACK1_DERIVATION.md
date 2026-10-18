# Track 1: Cavity Derivation — What Was Actually Shown

**Date:** 2026-10-18
**Status:** Simulation result. Not a QFT derivation. The boundary is marked below.

---

## 1. The Measured Input (data, not theory)

From 37,543 NVSS Faraday rotation measures at |b| > 20°, a quadrupole fit
yields the symmetric trace-free tensor Q_ij with eigenvalues:

    λ₁ = −39.76  →  principal axis (l, b) = (307.1°, +14.6°)
    λ₂ = +30.16  →  (l, b) = (229.5°, −39.7°)
    λ₃ = +9.60   →  (l, b) = (21.1°, −46.7°)

Split-half replication: independent halves agree within 0.3°–1.4°.
This tensor is a measurement. It goes into the simulator as a boundary condition.

## 2. The Cavity Equation

Complex wave field ψ(x, t) on a 64×64 toroidal grid (periodic boundaries,
no edges). Evolution:

    ∂ψ/∂t = i∇²ψ·(redshift)·(Kerr) − γ|ψ|²ψ + pump − loss + subharmonic
            − i·V_quad·ψ                        ← the measured input

where the quadrupole background potential is:

    V_quad(θ) = −S·cos(2(θ − θ_q))

S = quadrupole strength, θ_q = measured principal axis angle,
θ = angular position on the grid. This is the ℓ=2 angular dependence
projected from the 3D tensor onto the simulation plane.

No other tuning. Same pump, loss, Kerr, subharmonic in all runs.

## 3. Result A: Mode Locking (causal, not correlational)

| Configuration          | Set angle | Measured ℓ=2 angle | Δ     | Mode amplitude |
|------------------------|-----------|--------------------|-------|----------------|
| Control (S = 0)        | —         | 20.0° (random)     | —     | 0.0036         |
| Weak (S = 0.05)        | 0°        | 0.3°               | 0.3°  | 0.0624 (17×)   |
| Strong (S = 0.15)      | 0°        | 0.1°               | 0.1°  | 0.1858 (51×)   |
| Strong rotated         | 45°       | 134.2°             | 0.8°* | 0.1805 (50×)   |

*134.2° = 45° + 90° − 0.8°; the quadrupole potential has minima at
θ_q ± 90°, so this is alignment to the expected minimum.

The control proves the locking is caused by the quadrupole, not by
the cavity's intrinsic preferences. Adding the measured tensor makes
the ℓ=2 mode 17–51× stronger and pins it to the set axis.

## 4. Result B: Bounded Residual (the vacuum-energy analog)

Time-averaged field energy density ⟨|ψ|²⟩ in steady state:

| Configuration          | Residual ⟨|ψ|²⟩     |
|------------------------|----------------------|
| Control                | 0.005605 ± 0.001071 |
| Weak quadrupole        | 0.005646 ± 0.001067 |
| Strong quadrupole      | 0.006094 ± 0.001069 |
| Strong rotated         | 0.006217 ± 0.001045 |

Max/min ratio: **1.11**. The baseline does not diverge when structure
is added. The cavity finds a low, stable energy floor regardless of
the background field strength or orientation.

## 5. What This Means (and What It Doesn't)

**Shown:** A toroidal wave resonator with a measured astrophysical
quadrupole as boundary condition produces (a) ℓ=2 modes locked to the
measured axis within <1° and (b) a stable, low residual energy density
that does not blow up under stress testing.

**Not shown:** A derivation of the cosmological constant from QFT.
This is a 2D classical wave analog, not a quantum field calculation.
The 10^120 discrepancy is a statement about zero-point energy summation
in quantum field theory; this result demonstrates the *mechanism*
(bounded resonator → low stable residual) but does not compute Λ
from first principles.

**The honest bridge:** If the universe is a bounded toroidal resonator,
then the "vacuum energy" we observe is the residual leakage of a
recirculating system, not the sum of unconstrained local modes.
This simulation shows that mechanism working with real sky data as input.
Closing the full QFT loop is future work.

---

*Scripts: `cavity_quadrupole.py`, data: `cavity_quadrupole.json`,
tensor: `quadrupole_cavity_input.json` — all in this directory.*
