# Sweet-Spot Hunt — Charter (FROZEN before any screening run)

Campaign: overnight 2026-11-07, Zak's PC (dezritawre-oma, Ryzen 9
5900XT, 32 threads). Zak's order (2026-11-07 01:30 ET): "find
that sweet spot by morning please iterate all night on pc at
full tilt."

## Objective

Find the SWEET SPOT of the closed-loop superfluid protocol
(run 2's protocol: pin-temp feedback + compression sweet-spot
maintenance + precipitation feed, frozen in
`~/oam_bulge/run2/README.md`): the region of
**(compression χ, twist gain kP, precipitation coefficient β)**
where the loop HOLDS, and the operating ratios at the best
configuration. Run 2 itself is the (χ=1.00, kP=1.0, β=0.5)
T=10 point, run by another agent; it is NOT disturbed by this
campaign, and its result enters the final table as the
baseline.

## Frozen protocol (identical to run 2 unless a grid axis says otherwise)

- Engine `fs_engine.py` (byte-identical flow-split copy),
  implicit-midpoint GP, g=25, dt=0.002, N=128, Picard tol
  1e-11, ≤16 sweeps.
- Seeding: certified Arm A prep at the point's χ
  (`prep_A_chi{χ}_g25.npz`; norms 248.050@1.00, 372.075@1.50,
  558.113@2.25), spectral resize 80→128 (run 1's verified
  procedure), forced bulge A=0.5, σ=0.5, renormalised.
- Loop per segment (50 steps = 0.1 t.u.): sense temps
  (own sampler file per run, 20 Hz; ŝ = causal running
  min/max normalisation of the window channel-mean, span
  guard 0.25 °C, exactly runs 1–2) + sense state
  (A_k = prof(z0)/median(prof(|z|>2)) − 1;
  C_k = max_{|z|<1} prof / median(prof(|z|>2)));
  targets A(0), C(0) of the run's own seed;
  twist Δg_k = clip(kP·e_k + α·(ŝ−0.5), −0.5, +0.5),
  **α = 0.5 fixed**; precipitation feed iff e_k > 0 with
  β_k = β·e_k, mass drawn from the outside region, N
  conserved exactly by construction (run 2's bisection;
  declared fallback flagged, never silent).
- Band: C_k ∈ [0.8, 1.25]·C(0). Maintenance score =
  fraction of boundary readings in-band.
- Readout: snapshots every 10 steps; region spectra,
  centroids, band fractions, KE>1600 fraction (oam_common,
  identical to runs 1–2).

## Grid (screening, T=3 = 30 segments per point)

Axes: χ ∈ {1.00, 1.50, 2.25}; kP ∈ {0.5, 1.0, 2.0};
β ∈ {0.25, 0.5, 1.0}. Base set (11 points, in launch order):
the 9-point (kP, β) face at χ=1.00, plus the χ axis at
(kP=1.0, β=0.5): (1.50, 1.0, 0.5), (2.25, 1.0, 0.5).
Screening verdict per point (FROZEN, run 2's criteria):
**HOLDS iff A(T)/A(0) ≥ 0.80 AND maintenance ≥ 0.80**,
A(T) = snapshot bulge_amp at t=T (analyze_oam2 definition).
Also recorded per point: A_k min/max (boundary senses),
snapshot A min, maintenance, total booked ΔE_twist /
ΔE_precip, shortfalls, books maxima.

Adaptive expansion (only after the base 11, time permitting,
in this priority): (a) if a HOLDS point sits on a grid edge,
extend that axis one step — kP→4.0 or 0.25, β→2.0 or 0.125,
χ→3.40 (certified prep exists) — to bound the region;
(b) if HOLDS points are isolated, probe face midpoints
(kP or β = geometric mean of neighbours) around the best
point; (c) χ face at the best (kP, β) if the χ axis moves
the verdict. No point launches after 06:30 ET.

## Confirmation (Phase 2)

Best screening config — highest min(A ratio, maintenance);
ties broken by lowest total booked |ΔE| — plus its nearest
FAILING neighbour on the most sensitive axis (the axis along
which the verdict flips closest to the best point), each at
**T=10** with full run-2 readout (501 snapshots, spectrum
gradient, twist correlation). If NO screening point holds,
confirmation = the least-bad point by the same ranking, and
the report states the spot was not found in the grid and
maps where it is not. Confirmation launches by ~06:45 ET;
if only one T=10 fits the wall, the best config takes it.

## Phase 3 (ratios + deltas at the confirmed best config)

From the confirmation run's artifacts: drive pitch (segment
cadence 0.1 t.u.; dominant period of the realised Δg series
via FFT of the drive log), bulge specs (realised A mean/range
over the last 20% of the run, C̄ compression ratio), flow
ratio (mean |Δg| per segment vs filament kz=+1), and
DELTA-STREAM STATISTICS: per-segment delta vector = bulge
region shell-spectrum at the segment-end snapshot minus the
segment-start snapshot (snapshots at steps 50k, 50(k+1));
report dimensionality (shell bins), per-component variance,
noise floor estimated from the outside region's
snapshot-to-snapshot jitter at matched cadence, and
distinguishable-states proxy = Π_i max(1, σ_i/σ_noise,i)
(log2 reported as effective bits) — labelled a FIRST
CAPACITY PROXY, not a channel-capacity proof.

## Books bars (as runs 1–2; violations are results)

Cumulative relative N drift < 1e-7; within-segment relative
E drift < 1e-3 (boundary actuation ledgers excluded,
reported). Crash/NaN/abort = the point's result, preserved,
never silently re-run.

## Declared confounds / perturbations

- PARALLEL SCREENING shares the hardware temperature
  channels: each run's sampler reads the same k10temp
  sensors, so ŝ reflects TOTAL machine load, not the run's
  own cores. Accepted for screening (ŝ is per-run
  causal-normalised); declared here and in the report.
  Confirmation runs run at most 2-parallel.
- PHASE-0 SMOKE: a single 3-segment run at (1.00, 1.0, 0.5)
  pinned to cores 24–31 while run 2 is live, to validate
  the parameterised driver (seed senses must reproduce
  run 2's A(0)=1.250, C(0)=2.249995, N0=248.05021344239853).
  ~3 min of added heat on CCD2; run 2's books (N/E) are
  unaffected by construction.
- Run 2 occupies cores 0–7 until it completes (~02:43 ET
  projected). NO screening production launches before
  run 2's status reads DONE/ABORTED; headroom (who /
  loginctl / game processes) re-verified before Phase 1
  and before every later production launch. Full tilt is
  authorised only while no family user is active; if one
  becomes active, production launches pause until idle
  (noted in the report).

## Wall discipline (ET)

Screening complete by ~06:30; confirmations launched by
~06:45, complete by ~08:15; deliverables mirrored to
~/workspace/harness-dev/oam_bulge/sweetspot/ and
SWEETSPOT_RESULTS.md written by ~08:30. Cut order if the
wall closes in: adaptive points first, second confirmation
second, never confirmation quality.

## Phase-0 outcome (recorded 2026-11-07 ~01:47 ET)

Smoke run (3 segments, (1.00, 1.0, 0.5), cores 24–31, run 2
live on 0–7): seed senses reproduce run 2 EXACTLY — A(0) =
1.249995, C(0) = 2.249995, N0 = 248.05021344239853,
E0 = 3771.7612501444573; segment-1 state senses and
precipitation β also identical. Segment-1 Δg differs
(0.273 vs run 2's clipped 0.500) solely through ŝ — the live
temperature signal at a different physical moment; expected,
not a driver discrepancy. Books bars pass. Driver validated.
One fix during Phase 0: launcher sets PYTHONPATH to
~/oam_bulge (fs_engine import). Screening point
(1.00, 1.0, 0.5) will NOT be re-run: its T=3 screening row is
computed from run 2's artifacts (snapshots ≤ step 1500,
first 30 boundary readings), same definitions.

## Phase-1 preamble (recorded 2026-11-07 ~01:48 ET)

RUN 2 ABORTED at segment 26 (t=2.6): SolverNonConvergence —
Picard resid 4.964e-11 after the 16-sweep cap (tol 1e-11),
during the loop's violent recovery phase (G_cum 13.0 by
t=2.6). That is run 2's atomic result; it is not re-run.
Consequence for this campaign: the (1.00, 1.0, 0.5) screening
row can no longer be borrowed from run 2 (it never reached
t=3.0), so all 11 base points are launched by this campaign
at T=3, including (1.00, 1.0, 0.5) as a chartered grid point
under the identical protocol. If it (or any point) aborts on
solver non-convergence, that is its recorded result.
Run 2's partial data (boundary senses to t=2.6) still enters
the final report's baseline discussion, labelled ABORTED.

## Amendment — run-2 baseline folded in (2026-11-07 ~01:55 ET)

Run 2's graded result (run2/RESULTS.md): FAIL + ABORT at
t=2.6; controller saturated (Δg at clip all 26 boundaries,
feed every boundary, ΣΔE_precip = +4568.54 = 121% of E0;
max density 5.12; KE>1600 1.66e-02; maintenance 0.074;
one genuine save at t=0.2). Directives applied:
- (1.00, 1.0, 0.5) is a KNOWN-FAIL grid point; it stays in
  the grid (an abort ~t=2.6 is its expected screening
  result and costs less wall than a full T=3).
- Adaptive expansion is weighted toward LOWER kP and β
  first (extensions kP→0.25, β→0.125 get priority over the
  upward extensions in the charter's adaptive list).
- Every screening row logs ΣΔE_precip/E0; a point whose
  feed ledger exceeds ~25% of E0 is flagged PUMPING —
  pumping is reported as such whatever A(T) says.
