# Protocol 2 — Phase 0 results (before any control)

## P0a: uncontrolled kz=1 filament + bulge, T=2, no confinement

- Seed: A(0) = 1.2500, C(0) = 2.2500; A(2) = -0.0258 (uncontrolled decay, as runs 1-2).
- Books: N drift rel 1.884e-10; E drift rel 8.275e-05; Picard max 10 sweeps, max resid 9.993e-12. Wall 2538 s.
- Gamma_tor (r0=1.0 loop): mean 6.2828 +- 0.0007 (2pi = 6.2832 for a unit-winding filament).
- Gamma_pol (rho=0.75 loop): mean 0.0641 +- 0.2577.
- R = Gamma_tor - Gamma_pol over the full window: mean 6.2187678410630145, std 0.2578332079724507, n = 101, well-defined (C2 test) = True.
- First half: mean 6.262013974732102, ok = True; second half: mean 6.176369670799203, ok = True.
- Rebound period from A(t) (fallback): 0.11000000000000008.
- **Derived cadence: dt_cad = 0.1608 t.u. (source: R).**

Construction honesty (C2): Gamma_tor/Gamma_pol are line
integrals of v = Im(psi* grad psi)/|psi|^2 on the declared
loops, dimensionless in the sim's bookkeeping; R is used
as a rate by the charter's definition, and dt_cad = 1/|R|
inherits that construction. The angular-rate cross-check
(Omega = Gamma/(2 pi r^2)) is NOT what the controller
uses; it is recorded in phase0a/gamma_series.csv raw data
for any re-reading.

## P0b: confinement calibration (C3 rule, target C = 2.25)

| kappa | C(0) | C(0.5) | A(0.5) | E drift rel | aborted |
|---|---|---|---|---|---|
| 0 | 2.2500 | 0.7783 | -0.3846 | 5.215e-05 | None |
| 2 | 2.2500 | 0.7139 | -0.4335 | 4.779e-05 | None |
| 4 | 2.2500 | 0.6867 | -0.4512 | 3.902e-05 | None |
| 8 | 2.2500 | 0.7070 | -0.4116 | 6.094e-06 | None |
| 16 | 2.2500 | 0.8139 | -0.2791 | 1.328e-04 | None |
| 32 | 2.2500 | 0.9918 | -0.1181 | 3.155e-04 | None |

- **kappa_conf = 32** (min |C(0.5) - 2.25|, ties to smaller kappa).
