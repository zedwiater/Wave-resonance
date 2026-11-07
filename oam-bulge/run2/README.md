# OAM-Bulge Run 2 — Closed-Loop Protocol (FROZEN before the production run)

Run date: 2026-11-07 (overnight). Machine: Zak's PC
(dezritawre-oma, Ryzen 9 5900XT, 32 threads), idle at launch
(headroom check ~01:20 EST: only Zak's Nov-4 desktop sessions,
no games, no active family user; background services only).
Batch pinned `taskset -c 0-7`, `nice -n 10`, FFT workers = 8.
Sampler pinned to CPU 15.

## Why this run exists — Zak's correction (2026-11-07 01:16 ET, his words)

"Man run it again and this time follow superfluid protocol
flow and compression sweet spot maintenance the system is
itself. The pin temp was for you to make a feed back to allow
stable inflation bulge that formed the drum precipitation on
the filament to drive the system indefinitely. Lock this down
as first principles in superfluid dynamics working memory has
to have a system circuit to utilize superfluid circuit
protection"

Run 1 (same seeding, same box) drove the filament's twist
OPEN-LOOP from CPU temperature: the temperature curve was a
feed-FORWARD signal, nothing sensed the bulge and nothing fed
back. The forced bulge decayed: A(T)/A(0) = 0.075.

## First principle (locked down by this protocol)

**Working memory has to have a system circuit to utilize
superfluid circuit protection.** A pattern is maintained only
by a closed circuit that senses its own state and feeds back
to hold the compression sweet spot; maintenance IS the
system. An open-loop drive, however physical its signal, is
not a circuit and confers no protection. Run 2 is run 1 with
the circuit closed — the temperature curve becomes one input
to a feedback loop whose controlled variables are the bulge
amplitude and the compression ratio, and whose return leg is
a precipitation feed (the drum): mass drawn from the outside
region is precipitated back into the bulge window, and the
twist is actuated bilaterally (signed) by the loop error.

## Seeding (identical to run 1 — protocol-vs-protocol comparison)

- Certified flow-split Arm A χ=1.00 filament
  (`prep_A_chi1.00_g25.npz`, N=80, g=25, norm
  248.0502134423986; target phase θ + z: OAM ℓ=+1, kz=+1),
  spectrally resized (Fourier zero-padding) to **N=128**.
- Forced bulge at seeding: ψ ← ψ·(1 + A·exp(−z²/2σ²)),
  A = 0.5, σ = 0.5, z0 = 0, renormalised to the un-bulged
  norm. Seed verified against run 1's `psi_seg00.npz`
  before launch (max |Δψ| recorded in the run log).
- Engine: `fs_engine.py`, byte-identical copy of the
  flow-split engine (md5 8528e48448a709e8b9588a042d332541),
  implicit-midpoint GP, Picard tol 1e-11, ≤16 sweeps.
  dt = 0.002. Canonical `~/flow_split` NOT modified.
- Region masks identical to run 1 (smooth, soft edges 0.3,
  partition of unity): BULGE (|z|<1.0 soft, r<1.6), FLOOR
  (r<0.8, outside bulge window), OUTSIDE (rest).

## The closed loop (segments of 0.1 time units; T=10 → 100 segments, 5000 steps)

At each segment boundary k = 0..99, IN ORDER:

### 1. SENSE
(a) **Temperature** — segment-window means of
Tctl/Tccd1/Tccd2 from the live sampler (fresh sampler,
`run2/temp_curve2.csv`, 20 Hz, started before the run).
ŝ = causal normalisation of the window channel-mean T̄ by
the running min/max of T̄ including the current value (no
future data); guard: span < 0.25 °C → ŝ = 0.5. Exactly
run 1's construction.
(b) **State** — from ψ at the boundary (= the latest
snapshot; identical masks/definitions to run 1):
- Bulge amplitude A_k = prof(z0)/median(prof(|z|>2)) − 1,
  prof = |ψ|² averaged over r<0.8 at each z.
- Compression ratio C_k = max_{|z|<1.0} prof(z) /
  median(prof(|z|>2)) — peak core density inside the bulge
  window over filament-floor density.

### 2. CONTROL (all gains frozen here)
Targets: **A_target = A(0)**, **C_target = C(0)** (the
boundary-0 sensed values of this run's seed).
Error **e_k = A_target − A_k**.
- **Twist actuation — BILATERAL (signed)**:
  Δg_k = clip(1.0·e_k + 0.5·(ŝ − 0.5), −0.5, +0.5),
  applied via run 1's declared ramp ψ ← ψ·exp(i·Δg_k·sin Z)
  (local axial-gradient increment Δg_k·cos Z, +Δg_k at the
  bulge midplane; preserves N exactly). G_cum tracked.
- **Precipitation feed (the drum return)** — only if
  e_k > 0: gain field F(x) = 1 + β_k·w(z)·W_bulge(x) with
  β_k = 0.5·e_k, w(z) = exp(−z²/2σ²) the seeding Gaussian
  (σ = 0.5, peak 1), W_bulge the run's bulge mask weight;
  ψ ← ψ·F. The added mass is then drawn by a compensating
  field 1 − (1−s)·W_outside(x) with s ∈ [0,1] solved by
  bisection so the total norm returns to its pre-feed value
  — **total N conserved exactly by construction** (to
  bisection tolerance ≤1e-12 relative; achieved N before/
  after booked per boundary). Declared fallback: if even
  s = 0 cannot draw enough mass, global renormalisation is
  applied and the boundary is flagged `precip_shortfall=1`.
- Both actuations' energy changes are booked per boundary:
  ΔE_twist (E after twist − E before boundary) and
  ΔE_precip (E after feed − E after twist). These ledgers
  are excluded from the integrator E-drift verdict, exactly
  as run 1 excluded its drive ΔE.

### 3. SWEET-SPOT BAND
Compression is in-band iff
**C_k ∈ [0.8·C_target, 1.25·C_target]**.
Maintenance score = fraction of the 100 boundary readings
in-band.

## FROZEN VERDICTS (grade exactly these)

- **LOOP HOLDS** iff A(T)/A(0) ≥ 0.80 AND maintenance
  score ≥ 0.80.
- **PARTIAL** iff exactly one of the two holds.
- **FAIL** otherwise.
- Headline comparison: run 1 open-loop, same seeding —
  A(T)/A(0) = 0.075, bulge DECAYED. (Run 1 has no
  maintenance score; its loop was open.)

## Readout (identical to run 1, for comparability)

- Snapshots every 10 steps (Δt = 0.02) → 501 snapshots:
  per-region shell spectra P(k), exact spectral centroids,
  band fractions on K² ∈ {25, 169, 1600}, KE fraction above
  K²=1600, bulge amplitude, max density.
- Spectrum gradient = centroid_bulge − centroid_floor vs t.
- Twist-signature correlation recomputed identically:
  Pearson r of Δg_k vs the centroid change over segment k,
  per region and for the gradient, lag+1 pairing as control.

## Books / bars (flow-split line, as run 1)

- Cumulative relative N drift < 1e-7 (twist preserves N
  exactly; the feed conserves N by construction; this
  grades the integrator).
- Within-segment relative E drift < 1e-3 (segments are
  actuation-free; boundary ΔE ledgers reported separately).
- Picard: tol 1e-11, ≤16 sweeps/step.
- Violations are RESULTS: flagged in RESULTS.md, never
  silently re-run. A crash/NaN/non-convergence aborts the
  run atomically: ABORT record + last state preserved.

## Files

- `driver_oam2.py`, `analyze_oam2.py` (in `~/oam_bulge/`)
- `run2/` — README.md (this file), drive_log2.csv,
  temp_curve2.csv, books.json, snapshots.jsonl,
  status.json, run_summary.json, ψ checkpoints
  (seg 00/10/…/100), results.json, RESULTS.md
