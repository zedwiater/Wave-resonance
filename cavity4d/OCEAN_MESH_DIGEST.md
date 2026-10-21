# OCEAN MESH DIGEST — wave-ocean-mesh (distributed buoy array as one cavity)

Run 2026-10-21 ~18:02 EDT, VM-side only (`ocean_mesh_sim.py`, seeded;
results: `ocean_mesh_results.json`). Directive: Zak 2026-10-21 17:54
EDT — explicit go for the mesh sim. Parent: `ocean_cavity_sim.py` v2
(whole-pattern settled readout as primary classifier, drive-end
transient tap), imported and reused, not re-implemented.

**Headline: the pre-stated falsifier trips. At this scale, in this
model, the array does not beat the single buoy.** Best fusion ties the
baseline (0.9375); coherent field fusion is well below it (0.7500);
the transient detector that works at a single point detects nothing
anywhere in the array, and localization — the capability only an
array can offer — fails on both events. Two gates pass: the uplink
aggregation count (M3) and the ledger (M4). The failures are
dissected to mechanism below; they are the findings.

## Architecture modelled

12 buoys on a hexagonal lattice around one central hub (the
high-voltage power+data anchor): 6 buoys at 24 m, 6 at 48 m, cluster
diameter 96 m, every buoy ≤ 2 induction hops from the hub. Each buoy
runs the proven ocean node (whole-pattern settled readout;
drive-end phase-coherence transient detector, threshold calibrated
on 30 disjoint trials × 12 positions). Buoys relay readouts
hop-by-hop to the hub; the hub fuses them into one array verdict and
emits one aggregated uplink line per scenario.

One wave field drives the whole cluster: buoy at projected
coordinate s (propagation axis +x) sees mode n phase-shifted by
exp(−i·k_n·s), k_n = (2πf_n)²/g on the parent sim's mapped ocean
band (0.04–2.0 Hz log-mapped onto the 32-mode ladder — frequency
scaling inherited from the parent and disclosed there: this is a
scaled model of the architecture, not a physical buoy design).
Per-buoy references are position-matched (the same shift applied to
the clean bank), so no buoy is judged against another position's
field.

## Declared assumptions (modelling choices, NOT measurements)

- **A1 Induction range.** Seawater is conductive; skin depth ≈ 25 m
  @ 100 Hz, ≈ 8 m @ 1 kHz. Links capped at 25 m/hop, multi-hop relay.
  Kilometre-spaced free-drifting buoys are **out of scope** — an
  induction mesh cannot span them and this sim does not pretend
  otherwise.
- **A2 Relay efficiency.** Per-hop efficiency η is a *declared*
  parameter. Sensitivity run at η = 0.90 and η = 0.70; both reported.
- **A3 Propagation.** Deep-water dispersion as above; the rogue
  group's sim-time envelope (t0, width) is identical at every buoy
  (declared simplification — sim time is scaled ladder time, not
  physical travel time across the cluster).
- **A4 Noise.** Each buoy adds independent 12 dB modal noise (the
  parent's figure) on top of the scenario's own 12 dB draw. The
  baseline buoy carries no second draw and sits at s = 0 — it is the
  parent v2 run, reproduced in-process and asserted before any array
  number was trusted (0.9375, lone miss OC03 ✓).
- **A5 Energy.** All power figures are arbitrary simulated units
  (labelled proxies) — never joules, never measured savings.
- **A6 Tokens.** Whitespace-delimited field counts of the actual line
  strings, same method both sides. (Context: the parent's G5 measured
  ~66 real model tokens per syslog line including prompt overhead;
  the *ratio* is what transfers.)

## Gate table (pre-stated; nulls kept)

| Gate | Requirement | Result | Verdict |
|---|---|---|---|
| M1 array fusion | best fusion ≥ 0.938 **and** CALM_SWELL strictly > baseline 0.75 | vote 0.9375 (CALM 0.75); field 0.7500 (CALM 1.00) | **FAIL** (both fusions, both clauses split) |
| M2 transient + localization | both rogue events detected at array level AND first-detector = geometric entry buoy | 0/2 detected (max coherence 0.645 / 0.600 vs threshold 0.747); localization moot | **FAIL** |
| M3 uplink | one aggregated line; measured token counts | 192 vs 1920 fields over 16 scenarios (12 vs 120 per scenario) = 90.0% fewer | **PASS** (counting result) |
| M4 ledger + relay | per-node closure < 1e-9; relay loss itemized at both η | max closure 2.12e-16 over 192 node ledgers; relay loss 13.8% of tapped proxy @ η=0.90, 38.9% @ η=0.70 | **PASS** |
| Falsifier | array ≤ single buoy on identical scenarios → claim fails at this scale | best fusion 0.9375 = baseline; field fusion 0.7500 < baseline | **CLAIM FAILS at this scale** |

Diagnostics (not gates): majority vote 0.9375; incoherent power-mean
fusion 0.8125; mean per-buoy accuracy 0.7865 (with A4 noise) / 0.8073
(noise ablated, D1); dispersion-compensated detector (D2) — see M2
dissection.

## Failures, dissected

**M1 — vote ties, field fusion destroys a class.** The vote's only
miss is OC03 — the baseline's own miss, untouched. OC03 is 0/12 at
*every buoy, with or without the extra noise* (D1): all 12 buoys see
the *same* jittered realization from different positions, and that
realization sits closer to CROSS_SEA in settled-field space wherever
you stand. Positional diversity does not decorrelate a shared
realization; the array gets 12 looks at one ambiguous draw, not 12
independent draws. Field fusion (derotated complex mean) does fix
OC03 — CALM_SWELL goes to 1.00 — but it reads **every CROSS_SEA as
CALM_SWELL** (OC10/11/12) plus OC16 as STORM_FORCE. Mechanism: the
settled field's phase is set by the cavity's nonlinear dynamics
(detune + template coupling), not by the propagation path, so
derotating by the input propagation factor does not re-align the
settled fields across positions. The complex average cancels the
cross-sea's discriminating superposed structure and leaves the
low-mode swell-like common part — the joint spectrum resembles the
state that resembles the average. Fusion preserves CALM (whose
identity *is* that common part) and destroys CROSS (whose identity is
the superposition). Net: asymmetric, and worse than one buoy.

**Per-buoy deficit is not the noise.** Removing the A4 second noise
draw moves mean per-buoy accuracy 0.7865 → 0.8073 and changes neither
fusion at all. The deficit is structural: each buoy's settled field
is a phase-rotated nonlinear image, judged against a single clean
position-matched reference that does not span the state's realization
cloud — the same failure the parent sim recorded for its
matched-subtraction detector.

**M2 — the transient detector is a single-point instrument.**
The rogue group is phase-aligned at s = 0 by construction and
disperses as it propagates: across the spike band (modes 5–24) the
phase spread over 48 m is ~100 radians. At the geometric entry buoy
(B10, s = −48 m) the shipped coherence is 0.064 (OC15) — the *lowest*
in the array. Every buoy sits at |s| ≥ 12 m, where the packet is
already dephased below the calibrated background (threshold 0.747;
array maxima 0.645 / 0.600). The parent node at s = 0 detects these
same events at 0.859 / 0.884. The array's unique promised capability
— *where* the event entered — is exactly what fails: the entry point
is where the signal is least coherent. The D2 diagnostic
(dispersion-compensated coherence, threshold recalibrated on
compensated backgrounds) does not rescue it: compensation inflates
the background maximum to 0.888 (vs 0.727 uncompensated) because the
drive-end delta's phase is dominated by the cavity's response to the
shared phase codebook, and derotation re-aligns that too. OC15 still
misses (0.897 vs 0.908); OC16 detects (0.926) but localizes to B07
(s = +24 m), not the entry buoy. With or without compensation, this
statistic cannot separate packet from codebook at a displaced tap.

**Design history (disclosed).** Run 1's layout generator (grow by
largest radius, angle tie-break) produced a one-sided 10-hop chain —
connected, but not the specified cluster-around-a-hub, and it made
the farthest relay the entry buoy. Run 1 gates with that layout:
M1 FAIL (vote 0.875, field 0.6875), M2 FAIL (max coherences
0.462 / 0.612 vs 0.793), M4 PASS. Layout replaced with the ring
layout above; gates unchanged; the run reported here is run 2.

## What this does and does not establish

**Established (inside this model):**
- Uplink aggregation arithmetic: one hub line carries the array
  verdict in 12 fields vs 120 for twelve individual lines — a 90.0%
  reduction in transmitted fields, a measured count under a declared
  counting method. (In this run the aggregated lines' transient
  fields read "none" on OC15/OC16 — the format carries the fields;
  the detector never fired to fill them. Consequence of M2, stated
  not hidden.)
- The accounting layer scales to the array unchanged: 192 per-node
  S-split ledgers all close (max error 2.12e-16), and the relay stage
  itemizes cleanly — at the declared η = 0.90, 13.8% of the tapped
  proxy is lost in relay (1.36% of total through-flow); at η = 0.70,
  38.9% (3.84% of through-flow). Relay loss is a first-class ledger
  citizen, as designed.
- Three mechanisms, each a design constraint on any real array node:
  (1) shared-realization ambiguity is not cured by position;
  (2) coherent cross-position fusion is destructive when the settled
  phase belongs to the cavity rather than the path — fuse verdicts or
  power spectra, never raw settled fields; (3) a phase-coherence
  transient detector must be dispersion-matched to the packet *at its
  tap position*, and in this architecture the codebook background
  defeats the borrowed single-point statistic outright.

**Not established:**
- Anything about physical buoys, real seawater induction links
  (η declared, not measured), or real ocean wave packets (dispersion
  declared, envelope timing simplified per A3).
- That a *packet-matched* detector (a stored dispersed-packet
  template per position, rather than a coherence statistic) would
  fail — it was not run. M2 kills the borrowed detector, not every
  detector.
- That fusing over *independent realizations* (buoys far enough
  apart to draw independent jitter — kilometres, where induction
  can't reach, per A1) would fail. The array that physics allows
  this architecture is precisely the array whose looks are
  correlated. That tension is the honest open problem the sim
  leaves behind.

## Files

- `ocean_mesh_sim.py` — the sim (seeded, runnable: `python3
  ocean_mesh_sim.py`).
- `ocean_mesh_results.json` — geometry, baseline reproduction,
  per-buoy/per-scenario detail, gate table, D1/D2 diagnostics,
  design history.
- Parent: `ocean_cavity_sim.py`, `OCEAN_DIGEST.md`.
