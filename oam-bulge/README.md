# OAM-Bulge Run — README (frozen before the production run)

Run date: 2026-11-07 (overnight). Machine: Zak's PC
(dezritawre-oma, Ryzen 9 5900XT, 32 threads), idle at launch
(headroom check 00:19 EST: only Zak's Nov-4 desktop sessions,
no games, load ~1.9/32). Batch pinned `taskset -c 0-7`,
`nice -n 10`, FFT workers = 8.

## Zak's spec (his words, 2026-11-07 00:18 ET)

"start next sim using oam as filament and force a bulge and
record the spectrum gradient to the highest resolution you
can. Use a cpu pins temperature curve of the system as the
phase twist flow in the oam filament and allow it to update
twist with pin curve from a core batch of pins that's
processing it or use whole core spectrum whichever provides
highest resolution"

## Named interpretations (declared readings)

1. **OAM filament** = a light-vortex filament in the GP phase
   field: ψ carries azimuthal phase winding ℓ=+1 around a
   straight filament along z, plus axial phase gradient
   kz=+1. Realised by reusing the certified flow-split Arm A
   χ=1.00 filament state (`prep_A_chi1.00_g25.npz`, N=80,
   g=25, norm 248.0502134423986; its target phase is exactly
   θ + z). Engine: `fs_engine.py`, byte-identical copy of the
   flow-split engine (md5 8528e48448a709e8b9588a042d332541),
   implicit-midpoint GP, Picard tol 1e-11, max 16 sweeps.
   The N=80 state is moved to the production grid by Fourier
   zero-padding (exact for resolved modes; verified below).
2. **Force a bulge** = axial Gaussian amplitude swell imposed
   at seeding: ψ ← ψ·(1 + A·exp(−(z−z0)²/2σ²)), z0 = 0 (box
   midplane), A = 0.5, σ = 0.5 (declared construction pins),
   then renormalised to the un-bulged state's total norm.
   Measured t=0 core-profile bulge amplitude: 1.250 (the
   core density ratio at z0; density goes as amplitude²).
3. **Phase twist flow from the CPU pin temperature curve** =
   the filament's axial phase gradient is updated once per
   segment (0.1 time units = 50 steps). At each boundary the
   driver reads the temperature samples that arrived during
   the previous segment window from the live `temp_curve.csv`
   (sampler started before the run, 20 Hz). T̄ = mean over the
   window of the per-sample channel mean. ŝ = causal
   normalisation of T̄ by the running min/max of T̄ including
   the current value (no future data); guard: span < 0.25 °C
   → ŝ = 0.5. Δg = α·ŝ, α = 0.5 (declared).
   **Ramp construction (declared):** ψ ← ψ·exp(i·Δg·sin Z).
   A literal fractional axial ramp is not representable on a
   periodic box (total axial winding is quantised); the
   first-mode periodic ramp is smooth, spectrally clean
   (kz ±1 sidebands only), gives local axial-gradient
   increment Δg·cos Z — i.e. +Δg exactly at the bulge
   midplane — and preserves N exactly. Cumulative twist
   G(t) = Σ Δg is tracked. The drive's energy input ΔE is
   booked at every boundary (E before/after the ramp).
   Every update is logged to `run1/drive_log.csv` (raw
   per-channel window means, latest sample, ŝ, Δg, G, ΔE).
4. **Core batch vs whole core spectrum — decided by
   measurement** (see Sensor decision). 
5. **Spectrum gradient** = region-resolved spectra vs time.
   Three smooth masks (soft edges 0.3), normalised pointwise
   to a partition of unity: FILAMENT FLOOR (r<0.8, outside
   bulge axial window), BULGE SWELL (|z|<1.0 soft, r<1.6),
   OUTSIDE (rest). Per snapshot: shell-summed P(k) of each
   masked field's FFT + exact spectral centroid per region +
   band fractions on edges K² ∈ {25, 169, 1600}. Gradient
   deliverable = centroid(bulge) − centroid(floor) and the
   band ratios, vs time. Snapshots every 10 steps
   (Δt = 0.02), 251 snapshots over T=5.
6. **Bulge amplitude** A(t) = n̄_core(z0)/median(n̄_core(|z|>2))
   − 1, n̄_core = |ψ|² averaged over r<0.8 at each z.
   Fate grading (frozen): A(T)/A(0) < 0.5 DECAYED; > 2
   RUNAWAY; otherwise PERSISTED.

## Sensor decision (measured, cadence_test.json)

Hardware: k10temp exposes exactly **3 CPU temperature
channels — Tctl, Tccd1, Tccd2. No per-core channels exist**
on this sensor, so a per-core "core batch" signal is not
available; that is the finding. Cadence test (20 s, tight
loop): sysfs read rate 24,774 Hz for all 3 channels
(dt median 0.039 ms); Tctl took 151 distinct values with
159 changes (smooth, SMU-filtered, ~8 Hz effective update);
Tccd1/Tccd2 took 86/94 distinct values and differed from
each other in 99.995% of samples → the three channels are
genuinely independent readings. Tccd channels are unfiltered
instantaneous sensors (large jitter when polled at kHz
rates); the drive therefore uses the **segment-window mean**
of samples, not a single instantaneous read.

**Decision: whole core spectrum** — all 3 k10temp channels,
3 independent channels × full cadence beats the 1 channel
(Tccd1) a CCD batch could offer, and per-core does not
exist. The sim workers are pinned to CPUs 0–7 (physical
cores 0–7 = CCD1 by the standard Zen 3 enumeration; cpu16
reports core_id 0 = SMT sibling of cpu0), so "the pins
processing it" is a fact and Tccd1 is their die sensor; all
raw channels are logged so a Tccd1-only drive can be
reconstructed post-hoc. Sampler pinned to CPU 15 (CCD2) so
its own heat does not contaminate CCD1.

## Resolution choice (bench.json, measured on the bulged state)

| N | s/step (drop 1st) | max | Picard sweeps max/mean | snapshot analysis | projected wall (2500 steps + 250 snaps) |
|---|---|---|---|---|---|
| 96 | 0.199 | 0.221 | 10 / 9.05 | 0.177 s | 542 s (0.15 h) |
| 128 | 0.663 | 0.786 | 10 / 9.05 | 0.434 s | 1767 s (0.49 h) |

Resized un-bulged state at both N: norm 248.0502134423983 /
…987 (certified …986), stationarity rms 0.011657 / 0.011654
(certified N=80: 0.011656) — the resize is exact.

**Chosen: N=128** — largest N whose projected wall (0.49 h)
fits the ≤2.5 h budget with >5× margin. dt = 0.002, T = 5,
2500 steps, 50 segments, 251 snapshots.

## Frozen bars (flow-split line)

- Cumulative relative N drift < 1e-7 (phase ramps preserve
  N exactly; this grades the integrator).
- Within-segment relative E drift < 1e-3 (segments are
  drive-free; the drive's own ΔE is booked separately and
  excluded from the integrator verdict).
- Picard: tol 1e-11, ≤16 sweeps/step (engine-frozen).
- KE fraction above K²=1600 recorded per snapshot.
- Violations are RESULTS: flagged in RESULTS.md, never
  silently re-run. A crash/NaN/non-convergence aborts the
  run atomically: last state + ABORT record preserved.

## Files

- `sampler.py`, `oam_common.py`, `bench.py`, `driver_oam.py`,
  `analyze_oam.py`, `fs_engine.py` (copy), `cadence_test.py/json`
- `bench.json` — benchmark record
- `temp_curve.csv` — live temperature archive (20 Hz)
- `run1/` — drive_log.csv, books.json, snapshots.jsonl,
  status.json, run_summary.json, psi checkpoints,
  results.json, RESULTS.md
