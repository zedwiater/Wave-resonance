# Protocol 2 — Results (verdict first)

## 0. Verdict

**No configuration HOLDS. There is no confirmed container, and the qubit arm
(A5-revised) therefore does not run** — Zak's sequencing (steer 3) gates it
behind a confirmed A2 hold at T = 10, and no arm reached a T = 3 hold.

Eight controlled screening runs across three seeding arms, plus four
uncontrolled construction tests, all land on the same mechanism, stated in §3:
in this scalar Gross–Pitaevskii filament (N = 128, g = 25, confinement
κ = 32), the inter-wall phase difference Δφ is an **unprotected soft mode**.
Every construction of the wall pair — raw phase imprint, freely settled pair,
phase-pinned constrained-stationary pair, vortex-ring (TP) pair, emergent
plasmoid — relaxes toward phase agreement (Δφ ≈ 0, wandering ±0.6 rad) on a
~0.1 t.u. timescale, and the phase-gated bilateral controller (correction clip
±0.5 rad, attempts up to every 0.040 t.u.) cannot hold it away from that
attractor: its corrections decay between attempts. Wall-pair *survival* (both
sheets phase-coherent) passes in every run; Δφ *in-band* fraction is
0.000–0.108 against the 0.80 bar everywhere. The explored volume and its edges
are mapped in SCREENING2.md; that map, the Phase-0 rate measurement, and the
mechanism below are the deliverable.

## 1. Phase 0 — the system's own rates (feeds the paper directly)

Uncontrolled kz = 1 density-bulge seed, T = 2 (phase0.md, phase0_numbers.json):

- Γ_tor (azimuthal loop, r₀ = 1.0, z = 0): **6.2828 ± 0.0007** — the 2π
  unit-winding quantum, rock-stable.
- Γ_pol (poloidal loop, ρ = 0.75): **0.0641 ± 0.2577**.
- R = Γ_tor − Γ_pol: **6.2188 ± 0.2578**, sign-constant; well-defined on the
  full window and on both halves (6.262 / 6.176). The paper §8.1 closure
  quantity is computable in this system.
- **τ_circ := 1/|R̄| = 0.1608 t.u.** — the cadence unit for all A4/FA9 grids.
  (A(t) rebound fallback measured 0.11, not needed.)
- Confinement calibration (C3 rule, C(0.5) closest to 2.25): κ = 0 → 0.778,
  2 → 0.714, 4 → 0.687, 8 → 0.707, 16 → 0.814, 32 → 0.992 → **κ_conf = 32**,
  at the scan edge, with the caveat on record that no scanned κ held the
  compression class on the density seed (the swell disperses regardless);
  κ = 32 was carried as fixed background for all wall-pair work.
- Books: N drift 1.88e-10, E drift 8.27e-05, Picard ≤ 10 sweeps.

Construction honesty: Γ are line integrals of v = Im(ψ\*∇ψ)/|ψ|² on the
declared loops with low-density points excluded and arcs renormalized; R is a
*rate by the charter's definition*, and τ_circ inherits that construction.

## 2. Screening summary

Full tables in SCREENING2.md. Headlines:

- **A1 raw pair** (target 2.737): in-band **0.000** at tol π/8, π/4, π/2
  (τ 0.5×). Correction saturated at clip on effectively every landing;
  ΣΔE_twist +291…+572 (gross 3.9–7.6% of E0) bought nothing.
- **FA6 settled pair** (target 0.948): in-band **0.054 / 0.054 / 0.056** at
  (τ 0.5×, π/4), (τ 0.5×, π/2), (τ 1.0×, π/4); **0.041** at the FA9 cadence
  edge (τ 0.25×, 74 attempts, all landed). Gentler pumping (gross 1.3–4.3%),
  same verdict.
- **A6 plasmoid** (emergent, target π): in-band **0.108** — the best score of
  the campaign, still 7.4× under the bar.
- Best point overall by the A4 rule: plasmoid arm config for A6; within the
  A1/FA6 family, settled (τ 1.0×, tol π/4) — highest in-band (0.056) at the
  lowest gross feed (1.35% of E0). No T = 10 confirmation was run: A4/A2
  confirmation presupposes a T = 3 hold, and running T = 10 on a PARTIAL
  would re-confirm a negative at 4× the cost. Delta-stream statistics and
  the confirmation spectrum readout are likewise not applicable — they are
  defined on the confirmed config. For the least-bad config (settled
  τ 1.0×, π/4), the snapshot spectra show no band concentration developing
  under control: bulge second-sound-band share falls 0.137 → 0.092
  (first→last quartile means); spectral centroid 3.63 → 3.17 and high-k
  energy fraction 0.0004 → 0.0141 (first→last snapshot).
- Books in every controlled run: N drift ≤ 3.2e-12 rel (bar 1e-7);
  within-interval E drift ≤ 6.0e-04 rel (bar 1e-3). No aborts in any
  screening run. One flagged exception in an uncontrolled record run:
  the FA7 validation's max E drift 3.23e-03 exceeds the bar — reported as
  measured; it is a diagnostic trajectory, not a graded run.

## 3. Mechanism — why the container does not form here

1. **Δφ has no topological protection in this construction.** The split is a
   phase texture imprinted on a simply connected region of an ℓ = 1 filament;
   no winding number quantizes it. The filament's phase dynamics smooths the
   texture by sound radiation on a ~0.1 t.u. timescale (pinned-settle decay:
   2.63 → 1.09 in the first 0.1 t.u.).
2. **It is not a preparation artifact.** The FA8 prep — imaginary-time
   relaxation with the split phase pinned, the engine's own stationary-state
   method — converges to a constrained-stationary pair (pin work → 1e-23,
   residual floor 0.0937 set by the phase constraint itself). Released, it
   unwinds to Δφ = 0.11 within T = 1, same as the raw imprint.
3. **It is not the controller's cadence or gate.** Acceptance reaches 1.00
   (the gate is nearly always open in coherent states; §6), attempt density
   doubled with no gain (FA9), tolerance from π/8 to π/2 changes nothing once
   the state is coherent. The correction's leverage per landing is ~full
   (measured in batch 1) — it is the *relaxation between landings* that wins.
4. **It is not the flow dial at 0.5×.** The kz = 0.5 settle trajectory is a
   qualitative copy of kz = 1: same winding pattern, same late wandering band.
5. **The TP route as built does not supply the missing winding.** The carved
   vortex ring is not a stationary state either: its core fills in and
   Γ_ring collapses (2π → 0.19) within ~0.45 t.u. A ring prepared by
   constrained relaxation (phase-pinned in the poloidal plane, the FA8 method
   applied to the ring) is the one construction this campaign did not try;
   it is the natural next construction if the line continues — named here as
   an untested branch, not a result.

Relation to the paper: the closure equation's quantities are all measurable
(§1), the acceptance statistics behave as the paper's §9 reading predicts
(§6), and the wall pair exists as a coherent phase configuration at all
times — what fails is the paper's maintenance clause for Δφ as
operationalized here: the split is not self-sustaining and the exchange
machinery cannot sustain it either. In Zak's first-principles language: the
circuit was closed (sense → gate → bilateral actuate, books exact), but the
thing being maintained is not a protected variable of this system — circuit
protection showed up for the *filament* (Γ_tor = 2π, exact, everywhere) and
not for the *split*.

## 4. A6 plasmoid arm — the four readouts

Arm at (τ 0.5×, tol π/8), target π. Control = same seed without the packet,
lockstep checkpoints every 20 steps (plasmoid_ctrl_ckpts.npz, PC only, 2.5 GB).

1. **Centroid migration:** no convective attraction into the wall region. The
   δψ difference field's centroid leaves the bulge center axially
   (cz: 0.04 → 1.80 by T = 3) and its wall-region energy fraction collapses
   (0.331 → 0.005). Caveat: once the controller (absent in the control)
   actuates, δψ also measures run divergence; the exit trend is already set
   in the early segment.
2. **Δφ onset:** coherence-based instrument onset t = 0.02 is an artifact of
   the seed's coh = 0.82 at t = 0 (declared at seed time). Departure-based
   onset (|signed Δφ| > 0.5 sustained): **t ≈ 0.14**. Emergent Δφ then
   wanders the full circle (quartile means 2.21, 1.44, 2.94, 2.07) and
   *crosses* π almost exactly (min |Δφ − π| = 0.002 at t = 1.96) without
   settling — in-band fraction 0.108.
3. **Second-sound annealing:** not confirmed as predicted. SS-band fraction
   rises mid-run then falls back (quartiles 0.135, 0.163, 0.231, 0.182;
   first→last 0.135 → 0.176 by run summary, last snapshot 0.094), and the
   bulge spectral entropy *rises* (1.758 → 1.881) where the prediction
   required it to fall.
4. **Cavity volume vs band alignment:** wall separation is flat
   (1.00 → 1.03; full range 0.97–1.09) while the alignment fraction varies
   0.09–0.23; correlation **+0.21** (weak positive). The miniature claim —
   alignment ↑ ⇒ cavity contracts — is contradicted as operationalized:
   volume does not respond to alignment in either direction materially.

## 5. Instrument caveats (construction choices, on record)

- **Wall survival is a weak clause as operationalized.** Identifiability =
  coherence of each half-window's unwound phase ≥ 0.5. A fully healed,
  phase-uniform filament scores coh ≈ 0.98 with Δφ ≈ 0 — the settled runs'
  "survival: yes" coexists with Δφ(T) = 0.07–0.17. Δφ in-band is the real
  discriminator; survival only rules out phase *incoherence* (which never
  occurred). Any future grading should add a structural criterion (e.g. a
  phase-step edge in the unwound field) to the survival clause.
- **Δφ band test is literal on [0, 2π) values** (A2 multiplicative band);
  the state's wandering across the 0/2π seam is reported via the signed
  picture in the analysis above — under the signed reading the settled
  target band would sit at the edge of the natural wandering band, and the
  in-band fractions would change by factors of order unity, not by the
  15× needed to reach the bar. The negative does not hinge on the seam.
- **Γ_pol loop reading for axisymmetric rings is ~0 by symmetry** (FA7.1):
  the ρ = 1.30 loop encloses both ring cores with opposite winding; ring
  persistence was graded on Γ_ring (single-core loop) + core density.
- One process (tp_val2, full T = 1.5 TP validation) died silently at ~36 min
  with no output and no traceback (cause undetermined; no OOM evidence in
  the journal). It was replaced by the T = 0.5 ringdiag run, which produced
  the Γ_ring numbers above. Recorded here per atomic-run discipline: the
  lost run is not counted anywhere.

## 6. Arbiter note (steer 4 — Gemini's projection reading vs the paper's)

The attempt ledgers discriminate as follows (table in SCREENING2.md):
acceptance tracks the measured mismatch distribution against tol in every
config — 0.73–0.92 when the state's mismatch tail crosses tol (raw,
plasmoid), 1.00 whenever the state is coherent enough that mismatches sit
inside the window (settled, all τ_ex ∈ {0.25, 0.5, 1.0}×). No config shows
landing saturation independent of the match distribution. On this data the
paper's acceptance-statistics reading holds; the projection reading is not
falsified in general — it posits a *targeting* actuator, which FA3's
wait-for-the-gate controller is not.

## 7. What was NOT run, and why

- **A5-revised qubit arm** (Q1–Q4 + thermal/band addendum): gated behind a
  confirmed hold by Zak's sequencing. No hold exists. Not run.
- **T = 10 confirmation:** presupposes a T = 3 hold (A4). Not run.
- **kz = 1.5 settle/screen:** the 0.5× settle is a qualitative copy of 1.0×;
  a third flow point would decorate an inert dial. Not run.
- **Ring by constrained relaxation** (FA8 method in the poloidal plane):
  identified in §3.5 as the one untested construction. Not run — it is a new
  construction, and the honest close of this campaign is the map above;
  whether to open that branch is Zak's call.

## 8. Provenance / reproducibility

Engine: fs_engine copy in ~/oam_bulge (md5 8528e48448a709e8b9588a042d332541),
N = 128, dt = 0.002, g = 25; PC venv python; PYTHONPATH=~/oam_bulge:
~/oam_bulge/protocol2. Canonical ~/flow_split untouched. All runs atomic
(aborts preserved; none in screening). Drivers: p2_screen.py (A1/FA6/FA9),
p2_tpseed.py (settle/tpseed/validate + kz settles), p2_pinned.py (FA8),
p2_plasmoid.py (A6 seed/control/run), p2_common.py (C1–C6 constructions),
charter.md (doctrine + C1–C6 + FA1–FA9 + A6 + A5-revised-as-received).
Per-run artifacts in tag directories (results2.json, drive_log2.csv,
snapshots2.jsonl, status.json; psi_final.npz on PC). Large payloads kept on
PC only: plasmoid_ctrl_ckpts.npz (2.5 GB), per-run psi_final.npz files.
Everything else mirrored to ~/workspace/harness-dev/oam_bulge/protocol2/.
