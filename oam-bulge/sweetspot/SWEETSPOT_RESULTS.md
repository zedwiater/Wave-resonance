# SWEET-SPOT HUNT — RESULTS

**Overnight campaign 2026-11-07 (Zak's order 01:30 ET: "find that sweet spot by morning…
iterate all night on pc at full tilt"). Charter: `charter.md` (frozen before screening).
Full screening table: `SCREENING.md`. All numbers read from disk artifacts.**

## VERDICT — THE SPOT WAS NOT FOUND IN THE EXPLORED VOLUME (honest null)

**14 screening points (T=3) + 2 confirmations at T=10: zero HOLDS, zero PARTIAL.**
Every completed run ends with the bulge collapsed or inverted (A(T)/A(0) ≤ +0.06); every
run with a precipitation feed strong enough to matter either aborts the solver or pumps.
This is a complete map of where the spot **isn't** for the frozen run-2 protocol, with the
edges measured on each axis and the failure mechanism identified — the protocol has two
failure modes and nothing between them (diagnosis below).

## The confirmation pair (T=10, most sensitive axis = β)

| config (χ, kP, β) | verdict | A(T)/A(0) | maintenance | ΣΔE_precip | books |
|---|---|---|---|---|---|
| **(1.00, 1.0, 0.25)** — best screening point | FAIL (completes, degrades) | **−0.281** | **0.040** | +3121 = 83% E0 (98 feeds) | N 7.5e-11 ✓, E 9.3e-4 ✓ |
| (1.00, 1.0, 0.50) — run 2 baseline | FAIL (ABORT t=2.6) | −0.173 | 0.074 | +4569 = 121% E0 | N ✓, E ✓ |

The best T=3 point (A +0.057, M 0.200) does **not** survive T=10: maintenance collapses to
0.040 (4 of 100 readings in-band), the bulge ends as a depression (A last-20% mean −0.118,
compression ratio C̄ → 0.988 ≈ 1.0 = no bulge left), and the feed ledger keeps growing to
83% of E0 — slow pumping even at β=0.25. The **completes-vs-aborts edge on β sits between
0.25 and 0.50** at (χ=1.00, kP=1.0).

## Axis edges (from SCREENING.md)

- **β (precipitation gain) — the lethal axis.** 0.125: completes, bulge collapses
  unopposed (feed 3% E0 — too weak to matter). 0.25: completes, least-bad. 0.50: aborts
  (t = 2.6 / 1.3 / 0.3 at χ = 1.00 / 1.50 / 2.25). 1.00: aborts at t=0.4 at **every** kP,
  with within-segment E-book anomalies (≤1.7e-1) at death — flagged as results.
- **kP (twist gain) — inert inside this protocol.** Δg pins at the ±0.5 clip whenever the
  error ≳ 0.5 (nearly always), so the actuator saturates before the gain matters:
  (kP=2.0, β=0.50) reproduces (kP=1.0, β=0.50) **digit-for-digit, including the abort
  residual 4.964e-11**. No kP edge exists to find at these error scales.
- **χ (compression) — higher dies earlier.** At (kP=1.0, β=0.5): abort t = 2.6 → 1.3 →
  0.3 for χ = 1.00 → 1.50 → 2.25. χ=1.00 is the only compression where any point completes.

## Diagnosis — why there is no spot for this protocol as frozen

1. **Positive-only feed = no brake.** The precipitation feed fires only when e_k > 0
   (bulge below target). The bulge's natural dynamics (run 1) are collapse-then-rebound;
   a feed applied on the 0.1-t.u. sense cadence lands during the rebound and overshoots
   (A_k reaches +1.37…+1.53 in completed runs), then the overshoot crashes through zero.
   The loop phase-matches the oscillation it is trying to kill — driven oscillation
   A_k ∈ [−0.8, +1.5] in every mid-strength run.
2. **Energy accumulation erases the operating point.** Every feed injects net energy
   (ΣΔE_precip 19–133% of E0 at T=3; 83% at T=10 even for β=0.25); the spectrum gradient
   that defines the bulge erodes toward zero (−1.390 → −0.163 at T=3 in run 2; → **+0.491,
   sign flipped**, by T=10 in the confirmation — feed energy parks in the bulge window,
   KE>1600 fraction reaches 0.20) until Picard can no longer converge or nothing bulge-like
   remains. A maintainer must be able to *draw*, not only feed — a bilateral feed and/or a
   faster sense cadence are **protocol changes**, outside this charter's frozen design;
   flagged here, not tried.
3. **What did work:** sense→actuate is real (mid-collapse pull-backs in several runs;
   run 2's t=0.2 save is the same signature), and the pipeline is cross-validated exactly
   (Phase-0 smoke + the (1.00, 1.0, 0.50) screening point reproducing run 2 to all printed
   digits). The null grades the frozen gains/feed-sign, not the sensing or the engine.

## Phase 3 — ratios & delta statistics at the confirmed best config (1.00, 1.0, 0.25), T=10

- **Drive pitch:** segment cadence 0.1 t.u.; realized Δg dominant period **14.3 segments
  = 1.43 t.u.** (FFT of the drive log); Δg range [−0.30, +0.50], G_cum = +48.17.
- **Flow ratio:** mean |Δg| per segment **0.488** vs filament kz = +1 → **0.49** — the loop
  applies on average a half-quantum-equivalent twist increment per segment, pinned near
  the clip most of the time.
- **Bulge specs (realized):** A last-20% mean **−0.118**; C̄ last-20% **0.988** (C0 = 2.250);
  A_k span [−0.75, +1.37]; C_k span [0.70, 2.40]; max density 4.29 (seed 1.89).
- **Spectrum gradient:** −1.390 → **+0.491** (first-20% mean −1.082, last-20% +0.267).
- **Twist correlations (T=10):** bulge r = −0.109 (lag control +0.045); floor −0.232;
  outside −0.409 (inseparable from its lag). Run 1's clean open-loop bulge signature
  (r = −0.50) does **not** survive closing the loop at these gains — Δg is error-driven and
  saturated, leaving little variance to correlate.
- **Delta-stream statistics (first capacity proxy for the encoding vision — NOT a
  channel-capacity proof):** per-segment delta vector = bulge-region shell-spectrum
  difference vs previous snapshot; dimensionality **112** bins, 100 samples. Variance is
  concentrated: top-5 components hold **97.1%**; **participation ratio 2.8** effective
  dimensions. Against the outside-region noise floor, only **2 of 112** components exceed
  SNR 1 (max 1.7, none > 3); **effective-bits proxy = 1.4 bits/segment ≈ 2.7
  distinguishable delta states per segment**. Reading: at this *failing* operating point
  the delta stream is dominated by the pump oscillation — a ~3-dimensional, low-SNR
  signal. This is a **floor** measurement for the encoding idea, not a ceiling: the
  variance budget here is spent on the failure mode. A holding configuration (under a
  bilateral protocol) would spend it on controlled deltas instead.

## Books & discipline

- Every completed run passes both bars (worst N drift 7.5e-11 at T=10; worst
  within-segment E 9.3e-4). The three β=1.0 aborts carry E-book violations at death
  (≤1.7e-1) — reported, preserved, never re-run. 7 of 14 screening points aborted
  (t=0.4 ×3, t=2.6 ×2 incl. the run-2 reproduction, t=1.3, t=0.3); all artifacts kept.
- Headroom: PC verified idle (Zak's desktop sessions only, no games/users) before every
  launch (01:40, 02:52, 03:20, 04:00, 06:10 ET) — full tilt legitimate all night. Run 2
  was never disturbed (disjoint cores; its sampler ran independently to completion).
- Wall: screening complete 05:10, confirmation complete 06:13 (it ran concurrently with
  the last screening batches), this report ~06:20 ET — ahead of the 06:30 / 08:15 / 08:30
  marks.

## Artifacts

VM mirror `~/workspace/harness-dev/oam_bulge/sweetspot/`: `charter.md`, `SCREENING.md`,
this file, per-point dirs (results.json, books.json, drive logs, run summaries, status,
snapshots, analyze logs for all 14 screening points), `conf_c1.00_k1.0_b0.25/` (full T=10
artifact set incl. psi_seg00/psi_seg100 checkpoints; intermediate checkpoints on the PC),
tooling (`ss_driver.py`, `ss_analyze.py`, launchers). PC originals:
`~/oam_bulge/sweetspot/` (dezritawre@100.82.181.57). Run-2 baseline: `../run2/RESULTS.md`.
