# OCEAN DIGEST — wave-ocean-v1

Run 2026-10-21 (VM-side sim + PC model round, preflight clean).
Spec: Gemini-drafted, approved by Zak 2026-10-21 16:52 EDT with
"adjust where needed" — the four mandatory adjustments are applied
throughout and flagged where they bite. Code: `ocean_cavity_sim.py`;
numbers: `ocean_results.json` (v1 + v2 sections); jobs/answers:
`ocean_model_jobs.json`, `ocean_model_answers_{gemma,qwen3b}.json`.
Seeded (SEED 21021), reproducible. Re-run (whole-pattern primary)
2026-10-21 on Zak's 17:15 EDT go — see the dated section below.
Pushed to GitHub 2026-10-21 (cavity4d/; commit SHA recorded in
ITERATION_LOG.md and cavity_iter_state.json).

## What was built

The transducer/cavity pipeline (transducer v2 patterns) driven by
ocean forcing instead of dweller telemetry:

- **Forcing.** Five sea states defined by JONSWAP spectra
  (Pierson-Moskowitz = γ 1): CALM_SWELL (Hs 0.6, Tp 12 s, swell only),
  MODERATE_CHOP (1.3, 5 s), BUILDING_SEA (2.2, 7.5 s), CROSS_SEA
  (swell 1.4 @ 11 s + wind sea 1.1 @ 4.2 s superposed), STORM_FORCE
  (4.8, 9 s, γ 1). Per-scenario jitter (Hs ±10%, Tp ±8%, γ ±15%),
  12 dB modal noise on the forcing.
- **Cavity.** The audio sim's 32-mode RK4 dynamics unchanged (template
  coupling to the 5-state bank, pump on); fields tapped at DRIVE_END
  (0.30 s) and SETTLED (0.50 s) in one run — the dual clock.
- **Wrapper.** Aggregate-referenced LUT node stores per ocean-band
  section (SWELL 1–8 / SEA 9–16 / CHOP 17–24 / SPRAY 25–32), complex
  delta matching, delta-energy-weighted composition (v2 verbatim).
- **Scenarios.** 16: 3 reps × CALM/MODERATE/BUILDING/CROSS, 2 × STORM,
  plus 2 rogue-group transients (phase-aligned broadband burst,
  3× amplitude, mid-drive) on CALM_SWELL and MODERATE_CHOP bases. The
  confusable pairs required by adjustment 4 are in: CROSS_SEA vs
  STORM_FORCE, BUILDING_SEA vs MODERATE_CHOP.

## Scaling disclosure (adjustment 2)

A literal buoy cavity cannot resonate at 0.05–2 Hz — those wavelengths
are kilometre-scale. The sim maps the ocean band 0.04–2.0 Hz
logarithmically onto the 32-mode ladder (mode n ↔ the mapped frequency
in `ocean_results.json`); the cavity's damping/detune/coupling constants
are the audio sim's. This is a scaled software model of the
architecture, the same trick as the audio sim — not a physical buoy
design, and nothing here sizes real hardware.

All power figures are arbitrary simulated units (proxies), never
joules, and there are no "zero-FLOP / zero-cost" claims anywhere in
this program (adjustment 1): the wrapper resolves by lookup in this
code, and the simulation itself runs on a von Neumann machine.

## Gate table (exact numbers)

| gate | result | verdict |
|---|---|---|
| G1 settled node classification ≥ 0.875 | **0.500** (8/16) | **FAIL** |
| G2 dual-clock transient detection | drive-end 2/2, settled 0/2, FP 1/14 + 0/14 | **PASS** |
| G3 S-split ledger closure < 1e-9 | max err 1.58e-16, bleed 0.0000 | **PASS** |
| G4 radiative exit decode ≤ 0.5% rel err | usable 0.199%, remaining 33.38% | **FAIL** (remaining leg) |
| G5 F2 syslog formatter | copy 1.00 both models, staging 0, tokens 66.5 / 66.25 | **FAIL** (token clause) |

### G1 — FAIL as pre-stated, and the failure is the finding

Per-state settled node accuracy: CALM_SWELL 0.75, MODERATE_CHOP 0.50,
BUILDING_SEA 0.33, CROSS_SEA 0.67, **STORM_FORCE 0.00**. The confusions
are exactly the mandated hard pairs: BUILDING ↔ CROSS, BUILDING →
STORM, CROSS → BUILDING, STORM → CROSS/BUILDING — the broad-spectrum
states form one mutually-confused cluster under section-local deltas.

Same scenarios, other readouts (all measured, none substituted for the
gate): node composition at DRIVE_END 0.6875; amplitude-delta arm
0.750 / 0.250 (drive-end / settled); **whole-pattern power-spectrum
nearest-neighbour at SETTLED 0.938** (15/16; its only miss is OC03
CALM_SWELL → CROSS_SEA).

Mechanism: ocean states are broad, heavily overlapping spectra. What
distinguishes them is the joint 32-mode shape — peak position, width,
bimodality taken together. Per-section delta matching slices that
shape into four 8-mode cosines and throws the joint information away;
then the settled attractor partially collapses the broad states toward
the aggregate (STORM_FORCE, the broadest, is pulled furthest and reads
0/2 under every node arm). This inverts the telemetry pattern from
transducer v2, where section deltas carried the state. Ocean identity
is global, not sectional. A wrapper for this domain should resolve on
the whole-pattern readout (0.938, which clears the gate number) and
demote the section nodes to taggers — the architecture survives, the
section-composition readout does not.

### G2 — PASS, with the detector's history attached

Shipped detector: spike-band phase coherence of the complex delta,
threshold **0.796 calibrated on the 30 disjoint calibration trials**
(background max 0.776 + 0.02), same threshold at both taps. Transients:
OC15 coherence 0.859 (drive-end) / 0.789 (settled), OC16 0.884 / 0.781
— both caught pre-collapse, both missed settled, as the dual-clock
claim requires. One false positive: OC04 (MODERATE_CHOP) at 0.814
drive-end. Margin honesty: the settled transient values (0.78–0.79)
sit just under the threshold — the settled tap misses by a hair, not
by a mile; n = 2 events is a demonstration, not a certification.

Two earlier detectors were built and rejected on measured grounds
(full detail in the code and results file): raw coherence at a fixed
0.50 threshold (FP 11/14 and 12/14 — it measures the codebook's phase
structure, not the event), and matched-subtraction residual share
(FP 12/14 and 14/14, shares generically > 1 — a single clean reference
per state does not span the state's realization cloud in this
nonlinear settle). One more design iteration was tried and reverted:
per-realization random phases collapsed the template coupling
(settled classification 0.438, exit decode unusable at 211% rel err);
the lab's shared-phase-codebook convention stands.

### G3 — PASS

Mean S-split over the 16 scenarios (fractions of through-flow):
tapped 0.0993, transmitted (S21) 0.6042, reflected (S11) 0.2958,
residual second cavity 0.0007, bleed 0.0000 at matched coupling.
Closure error max 1.58e-16 against the 1e-9 tolerance. As in v2, the
closure is bookkeeping-exact by construction; the content is in the
split, not the sum.

### G4 — FAIL on the remaining leg (constructed-channel check)

Per adjustment 3, this is a **constructed-channel bookkeeping check**:
the exit spectrum is computed from the same state variables as the
ledger ground truth, so a pass verifies decode consistency, not a
discovered physical channel. Usable (tapped) power decodes at
**0.199%** mean relative error (arm A, v2 features) — the leg that
carried the ~0.1% headline in v2 replicates. Remaining (residual)
power fails at **33.38%**: its ground truth is a near-zero difference
quantity (mean 0.0036 units = 0.06% of through-flow), and the linear
decoder's absolute error floor (0.0119% of P_in) is 33% of that tiny
target. Arm B (per-section absolute exit energies added) improves it
only to 25.86% — the information about the residual's fluctuations is
largely not in the exit intensity at this feature grain. Verdict:
the exit channel publishes the usable-power book faithfully and the
residual book only in absolute terms (~0.01% of through-flow), not to
0.5% of itself.

### G5 — FAIL on tokens; the copy contract itself is perfect

Syslog arm (the gated format), both models, 16 jobs each: **copy
fidelity 1.00, zero person-staging** — Gemma and Qwen2.5-3B both
reproduce the classification field exactly inside lines like:

`<134>1 2026-10-21T17:04Z BUOY_01 WAVE_CAVITY - - [state@41021 classification="CROSS_SEA" power_est="100.0%" confidence="0.495"]`

But mean total tokens are **66.5 (Gemma) / 66.25 (Qwen3B)**, max 68 —
the ≤ 40 clause fails structurally: the RFC 5424 header + instruction
+ completion slot costs ~63 prompt tokens before the model writes
anything. The F2 register line from the frame rounds carries the same
contract in ~37. Diagnostic register arm here: Gemma copy 1.00 at
39.9 mean tokens (mirrors rounds 1–3), but Qwen3B copy collapses to
0.3125 at 49.4 tokens — it echoes/regurgitates the register line
instead of filling the slot (the config-echo failure seen in frame
round 2's compressed arm; the ocean register line's noisier match
scores, 0.42–0.69 vs the dweller's 0.91–0.94, may invite it).
End-to-end accuracy is 0.50 in every arm — exactly the G1 wrapper cap
showing through a faithful copy channel: the models lost nothing, the
wrapper verdict they copied was right half the time.

PC discipline: preflight bracket checks clean (no [T]S4/[P]roton),
both resident servers health-verified before and after, nothing
stopped, started, or left running.

## What this sim does and does not establish

Does establish, in software, at this scale: the transducer architecture
ports to a second domain (ocean spectral forcing) without structural
change; the dual-clock readout separates transient events from settled
state in the direction the theory requires, with a calibration-set
threshold; the S-split ledger and the usable-power exit decode
replicate their v2 behaviour; and the F2 copy contract is
domain-independent (perfect field reproduction, zero staging, in a
syslog frame).

Does not establish: that per-section LUT composition classifies ocean
state (it fails here — whole-pattern readout is the working
classifier); that the residual power leg is exit-decodable to 0.5% of
itself (it is not); that a syslog-formatted report fits a 40-token
edge budget (it does not — the register line does); anything about
physical buoys, real hydrodynamics, real energy, or hardware sizing —
the frequency scaling is a modelling device (adjustment 2), all power
figures are proxies (adjustment 1), and the exit channel is a
constructed bookkeeping check (adjustment 3).

## Re-run: whole-pattern primary (2026-10-21)

Zak's go, 2026-10-21 17:15 EDT ("Yes and push to GitHub"). One change
only: the whole-pattern power-spectrum readout at SETTLED — v1's
control arm — is promoted to PRIMARY classifier; the LUT verdict handed
to the edge formatter now comes from it. The per-section / drive-end
readouts keep only their G2 job (transient detection). Same 16
scenarios, same seed, nothing else redesigned. Gates pre-stated before
the run: G1' primary ≥ 0.875; G2/G3 unchanged, must still pass; G4
unchanged, reported as-is; G5 re-run with the new verdicts, copy
fidelity and token counts reported separately (syslog token clause
expected to fail structurally again).

Determinism check: the v2 cavity-side run reproduced every v1 number
exactly (node settled 0.500, drive-end 0.6875, amplitude arms
0.750/0.250, G2 coherences, G3 closure 1.58e-16, G4 to the fourth
decimal) — the seed/protocol are untouched; only the verdict source
moved. All v1 numbers remain in `ocean_results.json` under "v1"; the
v2 run lives under "v2".

| gate | v1 | v2 | verdict |
|---|---|---|---|
| G1 / G1' primary classification ≥ 0.875 | 0.500 (node composition) | **0.938** (15/16, whole-pattern) | v1 FAIL → **v2 PASS** |
| G2 dual-clock transient | drive-end 2/2, settled 0/2, FP 1/14 + 0/14 | identical | **PASS** |
| G3 S-split ledger closure < 1e-9 | max err 1.58e-16, bleed 0.0000 | identical | **PASS** |
| G4 radiative exit decode ≤ 0.5% | usable 0.199%, remaining 33.38% | identical (arm B remaining 25.86%) | **FAIL** (remaining leg, unchanged) |
| G5 syslog formatter | copy 1.00 / 1.00, e2e 0.50, tok 66.5 / 66.25 | copy 1.00 / 1.00, e2e **0.9375**, tok 66.4 / 66.25 | **FAIL** (token clause, as pre-stated) |

G1' per-state (primary): MODERATE_CHOP 1.00 (4/4), BUILDING_SEA 1.00
(3/3), CROSS_SEA 1.00 (3/3), **STORM_FORCE 1.00 (2/2 — was 0.00 under
every node arm in v1)**, CALM_SWELL 0.75 (3/4). The single miss is
OC03, CALM_SWELL → CROSS_SEA — the same lone miss the whole-pattern
readout made as v1's control. The broad-state cluster that collapsed
under section deltas (STORM → CROSS/BUILDING, BUILDING ↔ CROSS)
resolves completely under the joint-shape readout; what remains is
one calm-swell realization whose settled spectrum sits closer to the
cross-sea reference.

G5 detail: with the wrapper cap raised, the faithful copy channel now
shows it end-to-end — **both models, both arms' syslog lines carry
0.9375 end-to-end accuracy** (v1: 0.50), copy fidelity 1.00, zero
person-staging. The token clause fails structurally again, exactly as
pre-stated: RFC 5424 header + instruction ≈ 63 prompt tokens before
the model writes (means 66.4 Gemma / 66.25 Qwen3B, max 68). Register
diagnostic arm: Gemma copy 1.00 at 39.75 mean tokens (inside the
40-token budget, e2e 0.9375 — the register line remains the
transmittable form); Qwen3B register copy 0.25 at 48.9 tokens (v1:
0.3125) — the register echo failure persists at the new cap; it is a
Qwen3B register-arm trait, not a verdict-quality effect, since its
syslog copy is perfect. PC preflight clean (no family workload), both
servers health-verified, tunnel torn down, nothing stopped or left
running.

## Design note — PROPOSAL, not measurement (Zak, 2026-10-21)

The wavelength objection to a physical buoy cavity (adjustment 2:
ocean wavelengths are kilometre-scale, no buoy-sized cavity resonates
at 0.05–2 Hz) is answered two ways in Zak's proposal:

(a) **Wavelength handled internally.** Each node's transduction maps
the long-wave forcing onto its own scaled modal ladder — the
frequency scaling this sim discloses as a modelling device is, in the
proposal, a physical transduction step inside each buoy, not a
property the ocean has to provide.

(b) **Hub-and-array variant.** One low-cost high-voltage power+data
source sits in the middle of a field of thousands of buoys; the buoys
cross-talk over an induction network. The array's effective aperture
is then the network's extent — kilometres — not one buoy's size: the
long wavelength is spanned by the *array*, and the magnetic-coupler /
through-flow thesis (power and data on the same inductive channel)
applies at array scale. The hub is the through-flow source; each buoy
is a tap.

This is recorded as a design proposal attributed to Zak. Nothing in
this sim measures it: the sim models one node's scaled cavity, not
array coupling, induction cross-talk, or hub power delivery.

## Next steps the data suggests

1. ~~Rebuild the ocean wrapper around the whole-pattern settled readout
   (0.938) with section nodes demoted to transient/tag duty~~ — DONE in
   the v2 re-run above (G1' PASS 0.938); the 0.875 classification gate
   is now met by the architecture's settled clock, with section nodes
   on transient duty only.
2. More transient reps (n = 2 → 12+) against the calibrated threshold
   before calling the detector real; watch OC04-class chop false flags.
3. Transmit the register line, not the syslog line, on any token-priced
   link; render syslog at the ground station where tokens are free.
