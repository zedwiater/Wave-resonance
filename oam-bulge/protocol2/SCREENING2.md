# Protocol 2 — Screening map (A2 grading: Δφ in-band ≥ 80% of passes AND wall-pair survival at T)

Grading per charter FA2/A2. Band = [0.8, 1.25] × Δφ_target. "Survival" = both walls
identifiable (coh± ≥ 0.5) at T — see the instrument caveat in PROTOCOL2_RESULTS.md §5:
coherence stays high even as Δφ → 0, so survival passes everywhere and the Δφ
in-band fraction is the discriminating half of A2 in every run below.
All runs T = 3, χ = 1.00, kz = +1, κ_conf = 32, β = 0.25, books bars met in every
controlled run (N drift ≤ 3.2e-12 rel; max within-interval E drift ≤ 6.0e-04 rel,
bar 1e-3). τ_circ = 0.1608 t.u. (Phase 0).

## Arm A1 — raw FA1 wall-pair seed (Δφ_target = 2.7373, band [2.190, 3.422])

| config | attempts | landed | acceptance | Δφ in-band | survival | Δφ(T) | ΣΔE_twist | ΣΔE_precip | gross/E0 |
|---|---|---|---|---|---|---|---|---|---|
| τ 0.5×, tol π/8 | 37 | 30 | 0.81 | **0.000** | yes | 0.455 | +291.4 | +5.0 | 0.0389 |
| τ 0.5×, tol π/4 | 37 | 34 | 0.92 | **0.000** | yes | 0.467 | +429.3 | +9.8 | 0.0517 |
| τ 0.5×, tol π/2 | 37 | 37 | 1.00 | **0.000** | yes | 0.483 | +572.0 | +2.7 | 0.0758 |

All PARTIAL. Mechanism (tol π/4 drive log): phase correction saturated at the
+0.5 clip on 34/34 landings; the seeded split relaxes to Δφ ≈ 0.3–0.7 within
~0.3 t.u. and the inter-attempt relaxation cancels each correction. Acceptance
0.81 → 1.00 across tol changes nothing: the failure is not gate statistics.

## Arm FA6 — settled seed (Δφ_target = Δφ* = 0.9479, band [0.758, 1.185])

Seed = FA1 pair evolved uncontrolled (confinement on) to t = 1.0 first.

| config | attempts | landed | acceptance | Δφ in-band | survival | Δφ(T) | ΣΔE_twist | ΣΔE_precip | gross/E0 |
|---|---|---|---|---|---|---|---|---|---|
| τ 0.5×, tol π/4 | 37 | 37 | 1.00 | **0.054** | yes | 0.166 | +141.7 | −78.5 | 0.0251 |
| τ 0.5×, tol π/2 | 37 | 37 | 1.00 | **0.054** | yes | 0.166 | +141.7 | −78.5 | 0.0251 |
| τ 1.0×, tol π/4 | 18 | 18 | 1.00 | **0.056** | yes | 0.070 | +79.0 | −34.1 | 0.0135 |
| τ 0.25×, tol π/4 (FA9) | 74 | 74 | 1.00 | **0.041** | yes | 0.135 | +89.5 | −168.0 | 0.0428 |

All PARTIAL. Notes:
- tol π/4 and π/2 rows at τ 0.5× are bit-identical trajectories: in the settled
  state max |mismatch| = 0.323 rad < π/4, so the gate never binds and tol is not
  a live dial there. The settled state's return flow is phase-coherent with the
  core (mean |mismatch| 0.087 rad).
- Attempt Δφ series (τ 1.0×): the state lives at Δφ ≈ 5.7–6.3 (≡ −0.6…0 signed)
  or 0.03–0.43 — |signed Δφ| ≲ 0.6 around agreement. The settle's 0.948 was a
  snapshot of a slow decay, not a plateau: the attractor band is Δφ ≈ 0 ± 0.6,
  below the [0.758, 1.185] target band.
- FA9 (attempt density doubled, 74 attempts): in-band fraction did not rise
  (0.041 vs 0.054). The cadence axis is exhausted for this controller family.

## Arm A6 — plasmoid-first (emergent Δφ, target π, band [2.513, 3.927])

Config = A1 best point by the FA4 rule (τ 0.5×, tol π/8). T = 3.

| attempts | landed | acceptance | Δφ in-band | survival | Δφ(T) | ΣΔE_twist | ΣΔE_precip | gross/E0 |
|---|---|---|---|---|---|---|---|---|
| 37 | 27 | 0.73 | **0.108** | yes | 0.913 | +221.0 | +40.5 | 0.0325 |

PARTIAL — but the highest Δφ in-band fraction of any run. Full A6 readouts in
PROTOCOL2_RESULTS.md §4.

## Uncontrolled construction tests (no controller; does the object persist at all?)

| construction | test | result |
|---|---|---|
| FA1 raw pair | settle T=1 (FA6 prep) | Δφ wanders 2.57 → 0.28 → 6.23 → settles into 0.4–1.5 wandering band crossing zero; coh 0.9–0.99 throughout |
| FA8 phase-pinned stationary pair | release T=1 | Δφ 2.63 → 0.11 (min 0.003); smooth unwind, half-life ≈ 0.1 t.u. Prep converged in 1 imaginary cycle (pin work → ~1e-23), stationarity rms floor 0.0937 at the pinned phase (engine bar 0.05 unreachable under the phase constraint) |
| FA7 TP ring pair | validation T=0.5 | carved core fills in (core density 0.18 → 2.72); Γ_ring 2π → 0.19 by t = 0.5 — ring dead; Δφ climbs freely through π in the relaxation transient, ends 3.88 falling |
| kz = 0.5 flow dial | settle T=1 | trajectory qualitatively identical to kz = 1 (same winding pattern, Δφ* = 0.55 vs 0.95 — same wandering band); flow dial inert for Δφ at 0.5× |

## Arbiter table (steer 4): landing rate vs τ_ex and vs mismatch distribution

| config | τ_ex (t.u.) | tol | mean \|mismatch\| | max \|mismatch\| | acceptance |
|---|---|---|---|---|---|
| raw, τ 0.5× | 0.080 | π/8 | 0.266 | 1.474 | 0.81 |
| raw, τ 0.5× | 0.080 | π/4 | 0.245 | 1.474 | 0.92 |
| raw, τ 0.5× | 0.080 | π/2 | 0.220 | 1.338 | 1.00 |
| settled, τ 0.25× | 0.040 | π/4 | 0.140 | 0.302 | 1.00 |
| settled, τ 0.5× | 0.080 | π/4 | 0.087 | 0.323 | 1.00 |
| settled, τ 1.0× | 0.161 | π/4 | 0.059 | 0.193 | 1.00 |
| plasmoid, τ 0.5× | 0.080 | π/8 | 0.370 | 1.341 | 0.73 |

Reading: acceptance is a function of the mismatch distribution against tol —
when the state is coherent (settled), mismatches sit inside even the π/4 window
and acceptance is 1.00 at every τ_ex; when the state is incoherent (raw,
plasmoid), acceptance tracks the distribution's tail beyond tol. Landing rate
shows no τ_ex-saturation independent of the match distribution on this data:
the paper's acceptance-statistics reading is the one the ledgers support. (A
targeting controller — actuation timed to predicted phase — would be needed to
test the projection reading; this controller waits, by design FA3.)
