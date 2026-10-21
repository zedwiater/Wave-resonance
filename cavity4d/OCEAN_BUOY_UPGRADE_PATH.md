# OCEAN BUOY UPGRADE PATH — how the upgrade should take place

Written 2026-10-21, from the measured record only: `OCEAN_DIGEST.md`
(wave-ocean v1 + the whole-pattern re-run, "v2"), `OCEAN_MESH_DIGEST.md`
(distributed array sim), `KV_FORMAT_RESULTS.md` (stripped-format test).
Every number below is copied from those runs. Losses and falsified
claims get the same prominence as wins — that is the house style, and
it is also the point of this document: the upgrade sequence is built
out of what failed, in the order the failures say to fix things.

Labels used on every claim and step:

- **MEASURED** — a number this program actually produced, in sim.
- **PROPOSAL** — a design idea on record, not yet tested.
- **UNTESTED** — a named next step with a gate, not yet run.

Nothing in this document sizes real hardware. The parent sims are
scaled software models (ocean band 0.04–2.0 Hz log-mapped onto a
32-mode ladder); all power figures are arbitrary simulated units
(proxies), never joules.

---

## 1. The production sensing rule (MEASURED)

One buoy, one cavity, two clocks:

- **Primary classifier = whole-pattern power-spectrum readout at
  SETTLED.** Accuracy **0.938** (15/16) on the 16-scenario ocean suite
  (v2, gate G1' PASS at the ≥ 0.875 line). Per-state: MODERATE_CHOP
  1.00, BUILDING_SEA 1.00, CROSS_SEA 1.00, STORM_FORCE 1.00,
  CALM_SWELL 0.75. The single miss is OC03, CALM_SWELL → CROSS_SEA.
- **Transient detection = the drive-end (pre-collapse) tap**, using
  the spike-band phase-coherence detector, threshold 0.796 calibrated
  on 30 disjoint trials. Gate G2 PASS: drive-end catches both rogue
  events (coherence 0.859 / 0.884), the settled tap catches neither
  (0.789 / 0.781, just under threshold). One false positive in 14
  non-event scenarios (OC04 MODERATE_CHOP, 0.814). Honest caveat:
  n = 2 events is a demonstration, not a certification — more reps
  are owed before the detector is called real.
- **Per-section node composition is RETIRED as the classifier.** It
  scored **0.500** settled (v1, gate G1 FAIL): CALM_SWELL 0.75,
  MODERATE_CHOP 0.50, BUILDING_SEA 0.33, CROSS_SEA 0.67,
  STORM_FORCE 0.00. Mechanism: ocean identity lives in the joint
  32-mode spectral shape; slicing it into per-section deltas throws
  the joint information away, and the settled attractor collapses the
  broad states toward each other. Section nodes are demoted to
  taggers. Node-composition voting adds nothing over a direct readout
  — this was measured twice, here and in the mesh vote below.

Upgrade rule, stated once: **a buoy ships with the whole-pattern
settled readout as its verdict, the drive-end tap as its transient
alarm, and no section-vote classifier.**

## 2. The mesh: both fusion methods, and their losses (MEASURED)

The array sim modelled 12 buoys on a hex-lattice ring around one hub
(6 at 24 m, 6 at 48 m, 96 m across, ≤ 2 induction hops each), same 16
scenarios and seeds as the single-buoy runs. The single-buoy baseline
was reproduced in-process and asserted (0.9375, lone miss OC03) before
any array number was trusted.

**The pre-stated falsifier: if the array scores ≤ the single buoy on
identical scenarios, the distributed-cavity accuracy claim fails at
this scale. It tripped. The claim FAILS at this scale. Do not soften
this:**

- **Verdict-vote fusion: 0.9375 — exactly the single buoy.** Its only
  miss is OC03, the baseline's own miss, untouched. OC03 reads 0/12 at
  *every* buoy, with or without the extra per-buoy noise (ablation:
  mean per-buoy accuracy 0.7865 → 0.8073 noise-free; both fusions
  unchanged). Why: all 12 buoys see the *same* jittered realization
  from different positions. Positional diversity does not decorrelate
  a shared realization — the array gets 12 looks at one ambiguous
  draw, not 12 independent draws.
- **Coherent field fusion (derotated complex mean): 0.7500 — worse.**
  It fixes OC03 (CALM_SWELL → 1.00) but reads **every CROSS_SEA as
  CALM_SWELL**. Why: the settled field's phase is set by the cavity's
  nonlinear dynamics, not by the propagation path, so derotating by
  the path factor does not re-align settled fields across positions.
  The complex average cancels the superposed structure that *is*
  cross-sea's identity and leaves the swell-like common part.
  Design constraint, measured: **fuse verdicts or power spectra,
  never raw settled fields.**

So the mesh is not an accuracy upgrade. Any future array proposal
that claims an accuracy gain has to answer these two mechanisms
first — independent realizations (buoys far enough apart to draw
independent jitter) are exactly what the induction range forbids
(section 4). That tension is the honest open problem.

## 3. What the hub and cluster ARE for (MEASURED)

Bandwidth and logistics, not accuracy:

- **Uplink aggregation — gate M3 PASS.** One aggregated hub line per
  scenario carries the array verdict in **12 fields vs 120** for
  twelve individual lines; over the 16 scenarios, **192 vs 1920
  fields = 90.0% fewer transmitted fields** (whitespace field count,
  same method both sides). The satellite-tax argument survives as a
  measured count.
- **Power/data routing.** The hub is the through-flow anchor: buoys
  relay compact readouts hop-by-hop (≤ 2 hops in the modelled
  cluster) instead of each carrying a long-haul transmitter. This is
  an architecture property of the model; the relay's cost is itemized
  in section 4.
- One honest blemish: in the mesh run the aggregated lines' transient
  fields read "none" on the two rogue scenarios — the format carries
  the fields; the detector never fired to fill them (section 5).

## 4. The induction budget, with its losses (MEASURED losses on DECLARED parameters)

- **Hop range: ≤ 25 m.** Basis (declared modelling assumption, not a
  measurement): seawater is conductive; skin depth ≈ 25 m @ 100 Hz,
  ≈ 8 m @ 1 kHz. Links are capped at 25 m/hop with multi-hop relay.
- **Relay loss (gate M4 PASS, loss itemized in the ledger):**
  **13.8% of the tapped proxy at per-hop efficiency η = 0.90**
  (1.36% of total through-flow), and **38.9% at η = 0.70** (3.84% of
  through-flow). η is a *declared* parameter, run at both values —
  nobody has measured a real hop yet. That measurement is step 4 of
  the sequence.
- **Kilometre-spaced free-drifting buoys are OUT of induction scope.**
  An induction mesh cannot span them. A wide array needs a different
  long-haul link; that link is an **open requirement** — named here,
  not solved here.

## 5. The transient-detection upgrade (MEASURED failure → UNTESTED fix)

- **The borrowed single-point detector is dead at displaced taps —
  gate M2 FAIL, 0/2.** The detector that catches both rogue events at
  a buoy sitting at the phase origin (0.859 / 0.884 vs threshold
  0.796) detects *nothing anywhere in the array* (array maxima
  0.645 / 0.600 vs calibrated threshold 0.747). Mechanism: the rogue
  group is phase-aligned at one point and disperses as it propagates
  — ~100 radians of phase spread across the spike band over 48 m.
  At the geometric entry buoy (s = −48 m) the coherence is **0.064,
  the lowest in the array**: the packet is most dispersed exactly
  where it arrives first, so localization — the one capability only
  an array can offer — is what fails. A dispersion-compensated
  variant (diagnostic D2) does not rescue it: compensation inflates
  the background maximum to 0.888 (the cavity's shared-codebook
  response gets re-aligned too); one event still misses
  (0.897 vs 0.908) and the other localizes to the wrong buoy.
- **The upgrade (UNTESTED): packet-matched per-position templates** —
  a stored, dispersed-packet template for each tap position, matched
  against that position's drive-end field, instead of a coherence
  statistic borrowed from the origin. Gate, stated now: **detect
  AND correctly localize both rogue events at array level, or it
  fails.** M2 killed the borrowed detector, not every detector —
  but the replacement has to earn it.

## 6. The format rule, with its loss (MEASURED)

- **F2 syslog is the only verified both-models production format.**
  Copy fidelity **1.00 on Gemma and 1.00 on Qwen2.5-3B**, zero
  person-staging, end-to-end accuracy 0.9375 at the v2 wrapper cap.
  Its loss is prompt-side: mean **66.4 / 66.25 total tokens**, of
  which the RFC 5424 header + instruction are ≈ **63 prompt tokens**
  before the model writes anything; the completion itself is ~3
  tokens because the quoted field terminates it. On a token-priced
  link this format fails a 40-token budget structurally.
- **The stripped key-value format is FALSIFIED.** Gemini's proposed
  production rule (`BUOY_01 STATE=… CONF=… PWR=…`) was tested behind
  a pre-stated gate (copy ≥ 15/16 on both models, zero staging,
  ≤ 40 mean tokens). No arm passes:
  - kvA (bare KV): Gemma copy **3/16** @ 55.4 tok; Qwen3B **4/16**
    @ 57.7 tok.
  - kvB (bracketed KV): Gemma **10/16** @ 46.0 tok; Qwen3B **3/16**
    @ 56.8 tok (plus state-name mutations: `SWELL` for CALM_SWELL,
    `CROSSEA`).
  - Mechanism — **regurgitation, 42 of 45 failures**: the models do
    not get the state wrong; they copy it verbatim and *keep going*,
    completing the rest of the record, often regenerating the
    instruction itself. An unenclosed ALL-CAPS `KEY=value` slot reads
    as an open record to continue, not a register to read back. The
    syslog anchor was never the field label — it is **enclosure plus
    a closing delimiter the harness can stop on.** The token clause
    fails by the same mechanism: the bare prompt is ~35–37 tokens
    (no cheaper than the alternatives) and the unterminated slot
    fills with the regurgitated tail.
  - For reference, the F2 register line is a Gemma-only in-budget
    form (copy 1.00 @ 39.75 tok; Qwen3B copy 0.25 — echo failure).
    Not a both-models rule.
- **Next format step (PROPOSAL): a terminator-designed format** — a
  short frame built around a quoted/bracketed value slot with a hard
  closing delimiter, designed from the mechanism above. It is
  adopted only if it passes the same gate the KV format failed
  (≥ 15/16 copy on both models, zero staging, ≤ 40 mean tokens).
  Until then, syslog is the production format and its header cost is
  the accepted loss; on a token-priced link, transmit the register
  line only where a Gemma-class formatter is on the receiving end,
  and render syslog at the ground station where tokens are free.

## 7. Power accounting boundaries (MEASURED, with the labels kept on)

- **Per-node S-split ledgers close.** Single node: max closure error
  **1.58e-16** (bleed 0.0000 at matched coupling; mean split: tapped
  0.0993, transmitted 0.6042, reflected 0.2958, residual 0.0007 of
  through-flow). Mesh: all 192 per-node ledgers close, max error
  **2.12e-16**, relay loss itemized as a first-class line (section 4).
  The accounting layer scales to the array unchanged — this is a
  genuine, measured strength of the architecture.
- **Radiative usable-power decode is a constructed-channel
  bookkeeping check, NOT an independent audit.** The exit spectrum is
  computed from the same state variables as the ledger ground truth,
  so its **0.199%** mean relative error on usable (tapped) power
  verifies decode consistency. It does not show that a physical
  radiated signal can be audited from outside a real buoy.
- **The remaining-power leg is NOT readable — do not spec it.**
  Remaining (residual) power decodes at **33.38%** relative error
  (best variant 25.86%): its ground truth is a near-zero difference
  quantity (0.06% of through-flow) and the decoder's absolute error
  floor is a third of the target. The upgrade must not promise
  remaining-power readout from the exit channel.

## 8. Origin of the array architecture (PROPOSAL — Zak, 2026-10-21)

Recorded in `OCEAN_DIGEST.md` as a design note, attributed to Zak,
labelled proposal, not measurement. The wavelength objection (ocean
wavelengths are kilometre-scale; no buoy-sized cavity resonates at
0.05–2 Hz) is answered two ways:

(a) **Wavelength handled internally** — each node's transduction maps
the long-wave forcing onto its own scaled modal ladder (the frequency
scaling the sims disclose as a modelling device is, in the proposal,
a physical transduction step inside each buoy).

(b) **Hub-and-array variant** — one low-cost high-voltage power+data
source in the middle of a field of thousands of buoys, cross-talking
over an induction network; the array's effective aperture is the
network's extent, not one buoy's size, and the magnetic-coupler /
through-flow thesis (power and data on the same inductive channel)
applies at array scale. The hub is the through-flow source; each
buoy is a tap.

Status after the mesh sim: the hub's aggregation and routing role is
supported by measured counts (section 3); the array-as-aperture
accuracy hope is **not** supported at cluster scale (section 2), and
the induction physics caps the cluster at tens of metres per hop
(section 4). The proposal stands as the architecture's origin; the
measurements above are its current boundaries.

## 9. The phased upgrade sequence

Steps in order. A step starts only when the previous step's gate has
passed. Labels are per step.

### Step 1 — Node production rule (MEASURED, ready)
Fit each buoy with the section-1 rule: whole-pattern settled readout
as primary classifier (0.938), drive-end coherence tap for transients
(2/2 at the buoy itself), section nodes demoted to taggers,
node-composition voting removed.
**Gate already passed in sim** (G1' 0.938 ≥ 0.875; G2 2/2). Owed
before any hardware claim: more transient reps (n = 2 → 12+) against
the calibrated threshold, watching OC04-class chop false flags.

### Step 2 — Terminator-designed uplink format (PROPOSAL, gated)
Design the short format of section 6 around enclosure + a closing
delimiter; test on both resident model tiers under the KV gate.
**Gate: copy ≥ 15/16 on BOTH models, zero person-staging, mean total
tokens ≤ 40 on both.** Pass → it replaces syslog on token-priced
links. Fail → syslog stays, header cost accepted, and the format
question is closed rather than re-guessed.

### Step 3 — Per-position transient templates (UNTESTED, gated)
Build the packet-matched detector of section 5: one dispersed-packet
template per tap position, matched at the drive-end tap.
**Gate: detect AND correctly localize both rogue events at array
level** (the exact test M2 failed 0/2), then expanded reps before
the array's transient field is trusted in the aggregated uplink.

### Step 4 — Dense cluster pilot around one hub (PROPOSAL, gated)
Build the smallest physical version of the modelled cluster: buoys
at ≤ 25 m hops around one hub anchor. The pilot's job is to replace
declared parameters with measurements — above all the real per-hop
induction efficiency η.
**Gate: measured η and relay loss land inside the budget lines of
section 4** (relay loss at or better than the η = 0.70 line, 38.9%
of tapped, with η = 0.90 / 13.8% as the target). If real hops are
worse than η = 0.70, the power budget breaks and the cluster design
goes back, not forward.

### Step 5 — Wider array (PROPOSAL, blocked on an open requirement)
Only after steps 1–4 pass. A wider array additionally requires the
long-haul link for kilometre spacing named in section 4 — unsolved,
not assumed — and a fresh answer to the section-2 mechanisms: an
accuracy claim for a wide array must show independent realizations
or not be made. **Gate: steps 1–4 passed, long-haul link specified
and costed, fusion claim re-stated with its falsifier before any
build.**

---

*Companion files: `OCEAN_DIGEST.md` (node gates G1–G5, v1 + v2),
`OCEAN_MESH_DIGEST.md` (array gates M1–M4 + falsifier),
`KV_FORMAT_RESULTS.md` (format gate, both arms), `ocean_results.json`,
`ocean_mesh_results.json`, `kv_results.json`.*
