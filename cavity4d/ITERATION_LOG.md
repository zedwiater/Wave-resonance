# Wave Translator — Iteration Log

Hourly overnight iteration toward a cavity configuration whose interference
output (a) informs the harness models measurably and (b) lets a model read
wrapper boundaries through the cavity. Zak's directive 2026-10-21 00:28 EDT.
Silent rounds; parent delivers the morning digest.

Baseline (v1, 2026-10-21 ~00:16): recall cavity 0.719 vs linear control 0.698
(gates FAIL: need >= 0.80 and >= +15 pts); rectified signatures mutually
>0.99 cosine (encoding decisiveness debt); pump-gated rectification PASS
(30.70 dB on vs 9.32 dB off); cues PASS (control also perfect).

---

## Iteration 1 — 2026-10-21 00:30–00:52 EDT (runtime ~22 min)

Preflight: PC clean (no TS4/Proton), Gemma :8080 + Qwen :8081 healthy.
All three experiments ran. best_config stays **null** — no translator-v1.

### Exp A — encoding fix (paired trial set, 96 trials/arm, seed 555)

| arm | cavity | control | margin | sig mutual-cos | gates |
|---|---|---|---|---|---|
| v1 identity | 0.844 | 0.760 | +8.3 | 0.885 | acc PASS / margin FAIL |
| whiten tau=0.1 | 0.750 | 0.771 | −2.1 | 0.824 | FAIL |
| whiten tau=0.03 | 0.646 | 0.688 | −4.2 | 0.817 | FAIL |
| whiten tau=0.01 | 0.469 | 0.656 | −18.8 | 0.813 | FAIL |
| whiten 0.1 + phase | 0.750 | 0.771 | −2.1 | **0.705** | FAIL |
| phase only | 0.771 | 0.760 | +1.0 | 0.790 | FAIL |

Whitening does buy decisiveness (signature mutual-cosine 0.885 → 0.705 best)
but monotonically destroys cavity accuracy: the degradation noise is added
sensor-side, and whitening amplifies it in the floored null directions
before the cavity ever sees the signal. Phase spread is decisiveness-positive
at no extra accuracy cost on top of whitening, but cannot rescue it.
Key split (identity arm): noise-only cavity 0.979 = control 0.979;
**partial inputs cavity 0.708 vs control 0.542 = +16.7 pts** — the margin
already clears +15 in the completion regime alone and is diluted to +8.3 by
the noise regime. Product shape implied: a completion-only translator.

### Exp B — cavity informs model (20 questions, Gemma, temp 0.3)

- (i) corrupted text: **0.100** · (ii) cavity-completed: **0.050** ·
  (iii) clean: **1.000** (question set + judge validated). Gate FAIL.
- Cavity selection accuracy: **0.050 = chance.** Diagnosis (measured):
  the byte-spectrum encoding is a hash — raw-NN on corrupted spectra is
  also 0.050; cosine to the TRUE question 0.464 < best WRONG 0.772; even a
  10% char drop drops raw-NN to 0.200. Character edits decorrelate the
  spectrum entirely; nothing downstream can restore what the door destroyed.
- Counter-test: with MODAL-native degradation (40% of modes zeroed on the
  clean spectrum) cavity selection = **0.700 vs raw-NN 0.350** — the cavity
  completes at 2× the passive readout in its own space. The cavity is not
  the failure; the text door is. Next round: token/n-gram spectral encoding
  with locality + word-drop (ASR-style) corruption.

### Exp C — boundary reading (real dweller tick baseline, 4 states)

- Cavity classification: **1.000** (20/20 jittered trials) — but raw NN also
  1.000: at these perturbation sizes the telemetry states are well separated;
  decisiveness unstressed. Graded-distance stress test queued.
- Gemma one-line summaries naming the true state — label-only **0.500**,
  raw numbers **0.750**, nothing **0.000**. Raw beats label this round.
  HIGHFLOW missed under both label and raw (Gemma verbalized HIGH FLOW as
  "heat"). CALM label summary said "tranquility" — a keyword-judge near-miss,
  flagged not rescored. n=4/condition: indicative only.
- Baseline tick used (real, ~00:31 EDT): temps max 50.85 °C, rx_drop 88,
  tp_flow 0.0701, data 142.5 kbps, VRAM 0.571, loadavg 0.12.

### Queue after iteration 1 (front of queue)

1. Completion-regime translator: beta × settle sweep scored on partial-only margin.
2. Modal-native text door (token/n-gram spectra) + word-drop Exp B rerun.
3. Readout-side-only whitening (signatures whitened, coupling inputs raw).
4. Telemetry graded-distance stress (THERMAL +5/+10/+25 °C).
Then: pump variants, bank scaling 13→50, completion-depth curve, latency benchmark.

---

## Iteration 1.5 — 2026-10-21 00:57–01:12 EDT (Zak's 00:53 directives)

Zak's reframing, taken as spec: the TP wave is the cavity's input; the
cavity has TOPOLOGY (named sections); interference in a section catches a
subspectra identifier; models get ALL the deltas plus the ANSWER KEY
(LUT) in VRAM terms — lookup, not derivation; and the packet must say,
in its framing, that the model is receiving transduced wave data that
interfered with its own matrix and boundaries.

Preflight: PC clean — the only [T]S4/[P]roton pgrep hits were the SSH
wrapper echoing its own command line; no game process. Baseline: FRESH
real dweller tick (~00:57 EDT, dweller_tick_latest.json): temps
60.0/60.0 °C, rx_drop 86, tp_flow 0.0703, data 153.3 kbps, VRAM 0.571,
loadavg 0.02. (Same DEEP_NIGHT regime as iteration 1 but hotter idle.)

### Built

- **cavity_topology.py** — sections POWER (modes 1–2), DATA (3–14),
  IO (15–20), NETWORK (21–26), WEIGHTS (27–32); 11 subspectra bands
  (PWR.s1–2, DATA.s1–3, IO.s1–2, NET.s1–2, WTS.s1–2). Baseline standing
  pattern = settled state of the aggregate 17-pattern bank (the
  WEIGHTS section's proper state is that aggregate). Per-section delta
  rollout recorded over the ring-down (evolve_traced).
- **wave_lut.json** — the answer key, 17 entries (13 v1 templates + 4
  telemetry states): probe delta_signature (settled − baseline under a
  standard probe), dominant section/subspectra measured, meaning in
  token terms, gloss. Residency noted honestly in the file: models are
  stateless APIs; the key lives with the wrapper and excerpts ship in
  each packet — lookup from the model's side, no recompute.
- **Translator packet v2** — framing header (transduced interference
  data from your own cavity; sections hit; top subspectra) + full
  per-section delta vectors + LUT excerpt (top 4 by delta cosine).

LUT measurements worth keeping: probe deltas of byte-spectrum prompts
split between DATA and **PWR.s2** — the pump mode carries much of the
response; all cues tag DATA.s1; telemetry states read DATA.s1-dominant
under the iteration-1 channel codebook. A pattern's section identity is
a property of encoding + coupling, not of the pattern alone.

### Topology sanity — IO passes, NETWORK bleeds

In-band disturbance injected on the baseline pattern, full coupling:
- IO (modes 15–20): top tag correct **4/5** — GATE PASS.
- NETWORK (modes 21–26): top tag correct **1/5** — FAIL. The settled
  delta reads DATA.s1 (share ~0.35) in 4/5: at β=9 the template
  attractor re-expresses high-band energy along the bank's dominant
  (low-mode) response direction. Section tags are meaningful mid-band,
  not high-band, at this coupling. Queued: a pre-coupling linear tap to
  test whether the tag survives before the attractor rewrites it.

### Exp D — packet v2 vs label vs raw (16 trials/condition, Gemma)

| condition | accuracy | near-miss | mean tokens (prompt/completion/total) |
|---|---|---|---|
| label (per-trial cavity word) | **0.750** | 0.062 | 32.6 / 12.1 / **44.8** |
| raw numbers (jittered values) | 0.562 | 0.000 | 92.5 / 16.9 / **109.4** |
| packet v2 | 0.188 | 0.000 | 916.6 / 4.3 / **920.9** |

**GATE: FAIL on both halves** (packet accuracy < raw; packet tokens
8.4× raw). Packet v2 as specified was tested exactly as specified and
lost. Failure dissection, all measured:

1. **Token economics.** Framing + 32 complex deltas + 4 paragraph-length
   LUT meanings ≈ 917 prompt tokens vs 93 for raw prose. A translator
   8.4× the cost of the channel it replaces is an essay, not a lookup.
2. **Immediate-stop empties.** 9/16 packet answers are EMPTY with
   tokens_completion = 1: under stop=["\n"], Gemma answers the long
   structured packet with a leading newline. Every NETSTORM and every
   HIGHFLOW packet emptied, plus one CALM.
3. **The key is not the failure; consumption is.** The cavity-side LUT
   top-match (delta cosine) was correct on 12/16 trials (NETSTORM 4/4,
   HIGHFLOW 4/4, THERMAL 3/4, CALM 2/4 — CALM/THERMAL boundary soft in
   delta space). But in the 7 trials the model did answer, it flipped
   both ways against the key's own ranking (answered THERMAL with CALM
   top-match; answered CALM with THERMAL top-match). At 4B, a 900-token
   numeric packet is a swamp.
4. **What won:** the cavity's bare classification, handed over as a
   word, at 45 total tokens (accuracy 0.750, up from iter1's 0.500 at
   n=4; cavity per-trial label accuracy itself 0.938). Label inherits
   the cavity's 1/16 error and the model's verbalization weakness.
5. **Raw fell** to 0.562 at n=16 with jittered values (iter1: 0.750 at
   n=4 unjittered) — Gemma read 1720 drops/intervals as "minor" in 3/4
   NETSTORM trials. And **HIGHFLOW verbalization is now a thrice-
   measured model trait**: label 2/4, raw 0/4, packet 0/4 (empties) —
   Gemma turns HIGH FLOW into "heat"/"activity"/"normal" everywhere.

### Queue after iteration 1.5 (front)

1. **Packet v3 — compact translator:** section delta energies + top-3
   subspectra tags + one-line LUT meanings; target < ~90 tokens (below
   raw prose); same Exp D gate. If compact wins on tokens AND accuracy,
   the translator claim revives in the form the data supports.
2. **Packet robustness:** remove the stop-set artifact / prime the
   answer; separate format brittleness from lookup failure.
3. **Pre-coupling tag tap:** section tags read from the driven state
   before the attractor re-expresses them (NETWORK 1/5 debt).
Then the iteration-1 queue (completion-regime sweep, modal-native text
door, readout-side whitening, graded telemetry stress, pump variants,
bank scaling, completion-depth, latency benchmark).

### Exp D' — packet v3 (compact) vs label vs raw (16 fresh trials, Gemma, 01:33 EDT)

Queue items consumed: **packet v3** (front) + **packet robustness** (folded in — the
stop-set artifact was killed by design for all three conditions: no newline stop,
answer primed "The body state is:"). Preflight clean (only SSH-wrapper echo hits;
:8080 healthy). Fresh 16 trials (seed 5151); cavity per-trial label 0.938 (15/16);
packet-v3 LUT top-match by delta cosine correct **16/16** — the key's ranking is
sound, same as v2.

| condition | accuracy | near-miss | empty | mean tokens (prompt/completion/total) |
|---|---|---|---|---|
| label (cavity word) | **0.750** | 0.000 | 0.000 | 32.6 / 9.6 / **42.2** |
| raw numbers (jittered) | 0.375 | 0.000 | 0.000 | 92.5 / 10.8 / **103.3** |
| packet v3 | 0.188 | 0.000 | 0.000 | 231.0 / 37.7 / **268.7** |

**GATE: FAIL on both halves** (packet acc < raw; packet tokens 2.6× raw).

Failure dissection, all measured:

1. **The priming worked — empties 0/16** (v2: 9/16). Robustness sub-question answered:
   the stop-set was the empties' cause, not the packet.
2. **New format artifact: id-echo + fence regurgitation.** 16/16 packet answers open
   with a bracketed key id `[state:XXX]` copied from the KEY's own formatting, then
   spill into ```tool_code / ```python fences. The model treats the compact packet as
   a code/config artifact, not a lookup key. Model picked the key's top-ranked entry
   **0/16** times (e.g. all 4 THERMAL trials answered [state:HIGHFLOW]; CALM trials
   answered [state:THERMAL] + fences). This is consumption failure mode #2: the
   SHAPE of the packet dominates its content.
3. **Key excerpt carries no score signal.** All four state entries score 0.99–1.00
   (the v1 decisiveness debt: signatures mutually cosine >0.99); only list ORDER
   carries information, and the model ignored the order. A lookup key whose scores
   are flat is a guess, not a key — this connects directly to the readout-side
   whitening queue item (sharpen key discrimination).
4. **Token economics improved 3.4× over v2** (269 vs 921 total) but still 2.6× raw.
   Prompt 231 vs raw 92.5. Completions bloated by fence regurgitation (37.7 vs 10.8).
5. **Label channel replicates:** 0.750 at n=16 again (iter1.5: 0.750), at 42 tokens.
   Raw fell to 0.375 this round (fresh jitter; Gemma reads 60 C baseline as "minor
   thermal concerns" across CALM trials — a model-side prose bias, not cavity).

**Verdict.** Packet v3 as constructed FAILS. Twice-measured tension for the morning
digest: Zak's standing spec (never a bare label — always deltas + LUT excerpt) vs the
measured gate — the bare cavity word (0.750, 42 tok) beats raw prose AND every
packet format tried (0.188, 269–921 tok). The translator idea survives only if a
packet format exists that a 4B model actually CONSUMES as a lookup. The remaining
format hypothesis is falsifiable and queued: bracket-free, prose-shaped key (v4) —
if the id-echo vanishes but accuracy still loses, the failure is lookup-semantic
(4B can't rank-use a key list), not format-brittle.

### Queue after this run (front)

1. **Packet v4 — bracket-free prose key:** framing + top-3 key meanings as plain
   words, no `[state:XXX]` ids, no bracket/code punctuation; same gate. Pre-stated
   split: id-echo gone + accuracy up → format artifact confirmed; still loses →
   lookup-semantic failure at 4B.
2. Pre-coupling tag tap: section tags from the driven state before the attractor
   re-expresses them (NETWORK 1/5 debt under full coupling).
3. Completion-regime translator: cavity invoked ONLY on degraded inputs; beta ×
   settle sweep on PARTIAL-only margin (+16.7 pts at identity — widen it).
Then: modal-native text door, readout-side whitening (also sharpens key scores),
graded telemetry stress, pump variants, bank scaling, completion-depth, latency
benchmark.

### Iteration 2 — packet v4, bracket-free prose key (2026-10-21 02:46 EDT)

Queue item consumed: **packet v4** (bracket-free prose key: framing + top-3 key
meanings as plain words, no `[state:XXX]` ids, no bracket/code punctuation, no
match scores). Fresh 16 trials (seed 8181); preflight clean, :8080 healthy.
Cavity chain identical; scaffolding identical (no stop-set, primed
"The body state is:"). Code: `expD_v4_prep.py`, `expD_v4_score.py`,
`cavity_topology.py: build_packet_v4 + prose_meaning`.

Cavity-side: per-trial label 0.938 (15/16); v4 key top-match by delta cosine
14/16 (the two misses are the CALM/THERMAL soft-boundary pair again).

| condition | accuracy | near-miss | id-echo | empty | mean tokens (prompt/compl/total) |
|---|---|---|---|---|---|
| label (cavity word) | 0.688 | 0.000 | — | 0.000 | 32.4 / 10.1 / 42.5 |
| raw numbers (jittered) | 0.312 | 0.000 | — | 0.000 | 92.5 / 10.3 / 102.8 |
| packet v4 | **0.750** | 0.062 | **0/16** | 0.000 | 149.0 / 35.6 / 184.6 |

**GATE: SPLIT — accuracy PASS (0.750 ≥ 0.312), tokens FAIL (1.8× raw).**

Pre-stated split resolves toward **format artifact confirmed**: id-echo 16/16 →
0/16 and packet accuracy 0.188 → 0.750 from removing brackets/ids/scores alone.
The 4B model DOES rank-use a plain prose key list — v3's failure was
format-brittle, not lookup-semantic. This is the first packet that works as
intended: deltas + key lookup consumed as lookup, per the standing spec.

Dissection (measured):
1. New artifact replaces the old: fence regurgitation + HALLUCINATED deltas
   (13/16 answers wrap in ``` fences; invented "Wave-interference deltas:
   0.12, 0.08..." numbers never in the packet). The lookup now works but the
   prose register invites fabrication; completion bloat 35.6 vs 10.3.
2. Token floor is 1.61× raw on prompt (149 vs 92.5) — framing + section
   sentence + 3 ranked meanings, nothing redundant left at this verbosity.
   Under-raw tokens require a two-line packet (queued v5) or top_k=2.
3. Label replicates in band (0.688) and stays cheapest (42.5 tok); raw fell to
   0.312 on fresh jitter — Gemma's prose-temperature bias ("minor thermal
   concerns" at 60 C) strikes again, thrice now measured across conditions.

**Verdict.** Translator product metric HALF-met: better accuracy at 1.8×
tokens. The packet is a working lookup now; the claim holds only if the token
floor drops under raw. Packet v5 queued (two-line prose key, ~90–100 tok):
if packet prompt ≤ raw prompt tokens at ≥ raw accuracy, the translator gate
PASSES fully; else the packet channel stays above the raw floor and the
viable product shape is completion-regime-only.

### Queue after this run (front)
1. **Packet v5 — two-line prose key** (~90–100 tokens), same gate (falsifiable).
2. Pre-coupling tag tap: section tags from the driven state before the
   attractor re-expresses them (NETWORK 1/5 debt under full coupling).
3. Completion-regime translator: beta × settle sweep scored on PARTIAL-only
   margin (+16.7 pts at identity — widen it).
Then: modal-native text door, readout-side whitening (also sharpens key
scores for the packet excerpt), graded telemetry stress, pump variants, bank
scaling, completion-depth, latency benchmark.

### Iteration 2 — packet v5, two-line prose key (2026-10-21 03:41 EDT)

Queue item consumed: **packet v5** — two lines (framing + hit-section sentence
/ ranked prose key with "read as lookup not derivation"), target prompt
tokens <= raw (~92). Fresh 16 trials (seed 9292); preflight clean, :8080
healthy. Code: `expD_v5_prep.py`, `expD_v5_score.py`,
`cavity_topology.py: build_packet_v5 + V5_STATE_MEANINGS`.

Cavity-side: per-trial label 16/16 (1.000); key top-match by delta cosine
16/16 — the cavity and the key are perfect this round; ALL error is
model-side consumption.

| condition | accuracy | near-miss | empty | mean tokens (prompt/compl/total) |
|---|---|---|---|---|
| label (cavity word) | 0.750 | 0.000 | 0.000 | 32.5 / 10.6 / 43.1 |
| raw numbers (jittered) | 0.562 | 0.000 | 0.000 | 92.5 / 12.1 / 104.6 |
| packet v5 | **0.562** | 0.000 | 0.000 | 93.8 / 37.0 / 130.8 |

**GATE: FAIL — accuracy PASS (0.562 >= 0.562), tokens FAIL (prompt 93.8 > 92.5
raw by 1.4%; total 130.8 vs 104.6 on completion bloat).**

Dissection (measured):
1. v5's ultra-compressed packet reads as machine config, not language: 7/16
   answers fence-regurgitate a hallucinated JSON "cavity_readout" schema
   echoing the packet; several open with wrong guesses ("stable.",
   "overheating.") followed by self-Q&A ("What is the most likely cause...").
2. HIGHFLOW 0/4 — answered "thermal stress" 3x and "calm" 1x although the
   key ranked HIGHFLOW first. Compression below the prose register breaks
   rank-following at 4B; v4's numbered-prose-sentence shape was load-bearing.
3. Curve so far: v2 (921 tok, 0.188) → v3 (269, 0.188) → v4 (149, 0.750) →
   v5 (94, 0.562) — non-monotonic; **v4 remains the optimum**. Compression is
   not free; the prose register is the floor the lookup needs.
4. Label channel 0.750 at 43.1 tok again (thrice at band); the standing-spec
   tension (never a bare label vs bare label winning) is now measured four
   ways and stays open.

**Verdict.** Translator gate FAILS; v5 format retired. Reserved next lever:
v4's prose register with top_k=2 / trimmed intro (~130 tok) — cut tokens
without leaving the prose register. Queue front is now the pre-coupling
section-tag tap. No MHD lit check this round: v5's failure is a
model-consumption format effect, not a cavity mechanism — nothing in MHD
terms points at it.
---

### Iteration 3 — pre-coupling section-tag tap (2026-10-21 04:36 EDT)

Queue item consumed: **section-tag readout tap BEFORE template coupling** —
does the NETWORK band tag survive when the attractor does not re-express it?
Code: `iter3_preCouplingTap.py` (seed 7171; 5 trials x 5 sections; results in
`iter3_preCouplingTap_results.json`). Three readout arms, pump on:

| arm | meaning |
|---|---|
| LIN | alpha=0, no template coupling at all (the linear tap), settled |
| EARLY | alpha=1, tapped at t=T_DRIVE (0.30 s, before the post-drive ring-down) |
| LATE | alpha=1, settled (the current packet source; replicates the debt) |

Pre-stated gates: G1 LIN >= 4/5 every section; G2 EARLY NETWORK >= 3/5, others
>= 4/5; G3 LATE NETWORK <= 2/5 (debt replicates), others >= 4/5.

| section | LIN | EARLY | LATE (settled) | top-share LIN / EARLY / LATE |
|---|---|---|---|---|
| POWER | 5/5 | 5/5 | 5/5 | 0.686 / 0.589 / 0.463 |
| DATA | 5/5 | 5/5 | 5/5 | 0.486 / 0.469 / 0.447 |
| IO | 5/5 | 5/5 | 5/5 | 0.727 / 0.690 / 0.461 |
| NETWORK | 5/5 | 5/5 | **2/5** | 0.697 / 0.567 / 0.344 |
| WEIGHTS | 5/5 | 5/5 | **2/5** | 0.646 / 0.565 / 0.333 |

Gate outcomes: G1 PASS (25/25); G2 PASS (NETWORK 5/5 at drive end); G3 SPLIT —
NETWORK debt replicates (2/5 <= 2/5) but G3-others FAILS: **WEIGHTS also decays
to 2/5** — this is new beyond the old NETWORK 1/5 sanity (which never tested
WEIGHTS). All 6 settled-state confusions land on DATA (NET->DATA 3x,
WTS->DATA 3x): the bank's dominant low-mode direction (DATA.s1) re-expresses
both high-band energy and the model's-own-standing-wave tag.

The tag dies in the post-drive ring-down, not during the drive: identity is
fully intact at t=0.30 s and the top-share drops toward flattening by settle
time (NET 0.567 -> 0.344, WTS 0.565 -> 0.333). The template coupling is a
cascade operator — injection-scale energy ends up in the dominant direction.

**MHD check (brief, authorized):** the literature framing that fits is the
Kolmogorov/Iroshnikov-Kraichnan cascade: energy injected at one scale
cascades through the inertial range and the cascade completes in a few
eddy-turnover times (sources: Caltech Ph136 course notes
http://pmaweb.caltech.edu/Courses/ph136/yr2008/0814.1.K.pdf;
Frontiers in Astronomy & Space Sciences review on MHD turbulence cascade,
https://www.frontiersin.org/journals/astronomy-and-space-sciences/articles/10.3389/fspas.2022.869370;
ESA magnetosheath cascade explainer,
https://www.esa.int/ESA_Multimedia/Images/2018/01/Energy_cascade_in_turbulent_plasma).
Translated honestly to the acoustic substrate: the winner-take-more coupling
g = s|s|^ACT_POW is the nonlinearity that re-expresses localized mode energy
into the bank's dominant direction, on the post-drive timescale. The borrowed
mechanism: **read section identity on a timescale shorter than the nonlinear
turnover — tap at drive end, never after ring-down.** It earns its place only
by measurement; queued as a TEST, not adopted as a note.

**Verdict.** G1+G2+G3-: the section-tag tap should move to drive end.
Queue (front): (1) cascade-time readout — tag-share decay curve for NET/WTS at
t = 0.30/0.35/0.40/0.45/0.50 s, find t_cascade where injected-section share
< 0.5; (2) packet v6 model round — Exp D with early-tap section tags vs settled
tags: does model-side accuracy follow the cavity-side tag recovery
(NET 2/5 -> 5/5)? WEIGHTS decay (the model's own pattern mis-tagged as DATA)
is the higher-stakes follow-up: it is a boundary-honesty question for the
translator's "your own cavity" framing.
---
---

### Iteration 3b — cascade-time readout: tag-share decay curve (2026-10-21 05:36 EDT)

Queue item consumed: **NET/WEIGHTS tag-share decay curve** at t = {0.30, 0.35,
0.40, 0.45, 0.50} s under full coupling (alpha=1, pump on), 5 trials/point.
Code: `iter3b_cascadeDecay.py` (seed 8182; results in
`iter3b_cascadeDecay_results.json`). Metrics: mean injected-section share and
rank-1 hit count per (section, t).

Pre-stated gates: G1 share >= 0.5 at t=0.30 for NET+WTS; G2 t_cascade (first
share<0.5) in (0.30,0.50] for both; G3 POWER/DATA/IO share >= 0.5 through
t=0.50. **ALL THREE GATES FAILED** — but as a metric failure, not a cavity
failure: at t=0.30 the rank-1 top tag is the injected section in 25/25 trials
across all 5 sections, yet the share metric reads <0.5 for POWER (0.492),
DATA (0.462), and NETWORK (0.427) at drive end. The share metric double-counts
what DATA.s1 always takes: DATA is the bank's dominant direction, so an
injected bump into ANY section competes with the standing DATA component in
the denominator. Share<0.5 was a bad pre-stated criterion; keeping the null
and the numbers anyway.

| section | 0.30 share/hits | 0.35 | 0.40 | 0.45 | 0.50 | share crosses 0.5 | hits majority flips |
|---|---|---|---|---|---|---|---|
| POWER | 0.492 5/5 | 0.434 5/5 | 0.378 5/5 | 0.338 3/5 | 0.303 3/5 | <=0.30* | none (3/5 held) |
| DATA | 0.462 5/5 | 0.457 5/5 | 0.450 5/5 | 0.460 5/5 | 0.462 5/5 | <=0.30* | never |
| IO | 0.583 5/5 | 0.553 5/5 | 0.503 5/5 | 0.435 5/5 | 0.352 2/5 | 0.45-0.50 | 0.45->0.50 |
| NETWORK | 0.427 5/5 | 0.353 4/5 | 0.278 2/5 | 0.216 2/5 | 0.163 1/5 | <=0.30* | 0.35->0.40 |
| WEIGHTS | 0.589 5/5 | 0.544 5/5 | 0.491 4/5 | 0.435 4/5 | 0.351 4/5 | 0.35-0.40 | none (4/5 held) |

\* crosses are the share-metric artifact above; the hit column is the honest
read. Confusions: every single non-hit in every section lands on DATA.

What the curve actually says:
1. NETWORK is the fastest cascade casualty: hits 5/5 -> 1/5, share 0.427 ->
   0.163. Majority flips between 0.35 and 0.40 s — that is the real
   t_cascade for the high-band tag.
2. WEIGHTS decays (share 0.589 -> 0.351, crossing 0.5 at 0.35-0.40) but holds
   rank-1 at 4/5 through 0.50 — the model's-own-standing-wave tag is
   substantially more robust than NETWORK's. Boundary-honesty follow-up: the
   "your own cavity" tag survives the cascade window the high-band tag does not.
3. All sections intact (rank-1, 25/25) at t=0.30 — the actionable rule from
   iter3 stands and is now quantified: **tap at drive end, never after
   ring-down**. The practical t_cascade spread (NETWORK ~0.35-0.40 s,
   WEIGHTS share ~0.40 s, IO ~0.50 s) is the section-dependent nonlinear
   turnover; DATA never cascades because it IS the attractor.

**Verdict.** G1+G2+G3 as stated: FAIL on criterion calibration (share<0.5 was
the wrong yardstick — it fails at t=0.30 where the tags are demonstrably
intact). The decay curve itself is the deliverable: tag identity is
measurably dying in the ring-down on section-dependent timescales, NETWORK
fastest. Borrowed MHD mechanism (cascade-timescale readout) measured, not yet
adopted for the packet. Queued next: packet v6 with drive-end section tags
(the v6 lever already reserved); plus a refinement curve with finer taps
(0.025 steps) and the hit-majority criterion to pin NETWORK's t_cascade.
No MHD lit check this round: no new mechanism pointed at — this run measures
the already-borrowed one.
---
---

### Iteration 4 — packet v6: drive-end vs settled taps, Exp D model round (2026-10-21 06:34 EDT)

Queue item consumed: **packet v6** — Exp D round with the v4 prose packet built on two
taps of the same trial: drive-end (t=T_DRIVE=0.30, delta vs baseline trace at drive
end, ranked against an EARLY-TAP LUT probed the same way) vs settled (t=0.50,
exact v4 math, replication anchor). Fresh seed 9494, 16 trials x 4 conditions
(label, raw, packet_early, packet_settled). Code: `expD_v6_prep.py`,
`expD_v3_runner.py` (argv-parametrized, no stop-set), `expD_v6_score.py`
(results in `iter15v6_expD_results.json`, jobs in `iter15v6_model_jobs.json`,
answers in `iter15v6_model_answers.json`).
Preflight: the bracket-pattern pgrep initially reported TS4 AND Proton — both
were pgrep self-matches (pattern [T]S4 matches the literal "[T]S4" in pgrep's
own cmdline); verified with cmdline exclusion: zero real matches. :8080
healthy. Family machine untouched (inference only).

Pre-stated gates — ALL FAILED, in the informative direction:
- G1 (early key sanity, >=14/16): PASS 16/16 (settled also 16/16). The LUT key
  works at drive end; tap timing does not move key ranking for body states.
- G2 (cavity tag recovery: early rank-1 section in encoding-expected set on
  >=11/12 non-CALM, and >= settled): FAIL — early 6/12 vs settled 8/12. The
  early tap is WORSE on the tags for whole-pattern body states: at drive end
  the ranked readouts read POWER for 7/16 trials (the injection is still
  building; delta vs the drive-end baseline trace expresses poorly). The
  iter3/3b tag-recovery result was for SECTION-LOCALIZED injections; it does
  NOT transfer to the body-state stimulus class. Honest null, kept.
- G3 (model-side follows cavity: acc(early) >= acc(settled) AND >= acc(raw)):
  FAIL — early 0.625 vs settled 0.812 vs raw 0.375. The model side FOLLOWED
  the cavity side exactly (no tag recovery -> no accuracy gain; the wrong
  hit-section sentence in the early packets actively misled: spurious POWER
  hits). The directional hypothesis was wrong, but the cavity->model
  correspondence held.
- G4 (tokens(early) <= tokens(raw)): FAIL — 182.2 vs 103.6 (packet ~1.8x raw,
  same economics as v4).

| condition | acc | prompt tok | compl tok | total tok |
|---|---|---|---|---|
| label | 0.750 | 32.5 | 10.3 | 42.8 |
| raw | 0.375 | 92.5 | 11.1 | 103.6 |
| packet_early | 0.625 | 147.5 | 34.7 | 182.2 |
| packet_settled | 0.812 | 149.0 | 31.5 | 180.5 |

Notes:
1. packet_settled 0.812 replicates v4 (0.750) and is the highest packet
   accuracy measured at n=16 — and it beat the label arm (0.750) for the
   first time. It does so at 180.5 vs 42.8 tokens. The standing-spec tension
   sharpens: the spec-compliant packet now wins on accuracy and loses 4.2x
   on tokens.
2. Prompt tokens early == settled (147.5 vs 149.0): the tap does not change
   the packet's token floor; completion bloat (31-35 vs ~11) persists in
   both arms — the prose register invites regurgitation (v4 autopsy stands).
3. The actionable rule from iter3/3b is now qualified: tap-at-drive-end is
   the right rule for LOCALIZED disturbances (NET/WEIGHTS cascade window);
   for whole-pattern body states the settled tap reads the tags better.

**Verdict.** Packet v6: the early-tap lever is spent for the Exp D stimulus
class — cavity-side key indifferent, cavity-side tags worse, model-side
follows cavity-side down. Retired for body states. Translator product metric
still open: settled packet 0.812/180.5 tok vs raw 0.375/103.6 tok — the
accuracy half of the gate keeps passing, the token half keeps failing.
Queued follow-up (mechanism-consistent): Exp D' with SECTION-LOCALIZED
injections (cue class, e.g. chirp_up noise_burst) under early-tap tags —
the stimulus class the cascade measurement actually applies to.
No MHD lit check this round: no new mechanism pointed at — this run tests
the already-borrowed one.
---

### Iteration 5 — Exp D': cue class, early-tap vs settled tags (2026-10-21 07:29-08:05 EDT)

Queue item consumed: **Exp D' with section-localized injections (cue class) under
early-tap vs settled tags** — the stimulus class the cascade/tag-recovery
measurement (iter3/3b) actually applies to.

Design audit BEFORE pre-stating gates (07:35): cue modal-energy audit showed the
pure-tone cues (chirp_up, chirp_down, chime_two_tone) carry ~100% of their
energy in the DATA band; only noise_burst has high-band content (WEIGHTS 0.314,
IO 0.242, NETWORK 0.086, DATA 0.315). So the localized-injection question was
pre-stated honestly as: does the early tap preserve a cue's high-band section
mix before the cascade re-expresses it into the DATA attractor (iter1.5: all
cue probes read DATA.s1 at settle)? noise_burst = test cue; pure tones =
predicted null. Stimulus: a_in = baseline + 0.6*unit(cue) + modal noise 6.0
(iter3 amplitude); LUT probes noiseless, tapped at drive end (0.30) and settle
(0.50). 4 cues x 4 trials = 16 trials; 4 conditions (label/raw/packet_early/
packet_settled) x 16 = 64 model calls. Code: `expD_cue_prep.py`,
`expD_cue_score.py`; results `iter15cue_expD_results.json`, jobs
`iter15cue_model_jobs.json`, answers `iter15cue_model_answers.json`.
Preflight: clean (no TS4/Proton; :8080 healthy). Execution note: first prep
run had a trial-id collision (chirp_up/chirp_down/chime_two_tone all ->
`CCH*`; 32/64 answers); caught on answer count, fixed with per-cue tags
(CU/CD/CN/CT), full re-run. Cavity-side gates replicated exactly across runs.

CAVITY-SIDE (pre-stated):
- G1 (early key top-match = true cue >= 14/16): PASS 16/16. Bonus: settled key
  only 13/16 — noise_burst mis-keyed as chirp_down 3/4 at settle. The early
  tap preserves the high-band cue's IDENTITY even though (see G2a) it does
  not preserve its section tags.
- G2a (noise_burst early rank-1 tag in {WEIGHTS,IO,NETWORK} >= 3/4 AND settled
  <= 1/4): FAIL — early 0/4 (settled 0/4). The rank-1 tag reads DATA at drive
  end AND at settle. The re-expression of full-vector cue energy into DATA.s1
  completes DURING THE DRIVE, not just in the ring-down. This bounds the
  iter3 rule: tap-at-drive-end recovers tags for SECTION-LOCALIZED injections
  (iter3's perturbation class, 5/5 at drive end), NOT for full-vector
  patterns with spread energy. Honest null, kept.
- G2b (pure-tone DATA/DATA predicted null >= 10/12): PASS 12/12.

MODEL-SIDE (pre-stated):
- G3 (acc(packet_early) >= acc(packet_settled) AND >= acc(raw)): FAIL —
  early 0.375 < settled 0.562 (raw 0.250; label 1.000 at 42.5 tok).
- G4 (tokens(early) <= tokens(raw)): PASS 201.1 <= 215.9 — vacuous, see below.

| condition | acc | prompt | compl | total |
|---|---|---|---|---|
| label | 1.000 | 30.0 | 12.5 | 42.5 |
| raw | 0.250 | 211.0 | 4.9 | 215.9 |
| packet_early | 0.375 | 162.6 | 38.5 | 201.1 |
| packet_settled | 0.562 | 161.3 | 38.2 | 199.6 |

Per-cue acc (label/raw/early/settled): chirp_up 1.0/0.75/1.0/1.0; chirp_down
1.0/0.25/0.25/0.25; noise_burst 1.0/0.0/0.25/0.25; chime 1.0/0.0/0.0/0.75.

Failure dissection:
1. The v4 prose register does NOT transfer to the cue class. The model treats
   cue packets as code/config: fence regurgitation, invented multiple-choice
   lists ("A. A bird. B. A vehicle..."), hallucinated self-Q&A, `tool_code`
   blocks. The #1-ranked key entry is ignored when the prose invites free
   association: noise_burst (cavity key 4/4 early) answered "falling chirp"
   3/4; the single correct (CN0 early) was multiple-choice regurgitation that
   happened to pick A. Direction words don't survive: chirp_down answered
   "rising chirp" in most packet trials.
2. Settled's 0.562 "win" is substantially multiple-choice luck: all 3 chime
   hits are regurgitated option lists containing "doorbell"/"two-tone chime"
   as an option (the model's committed answer was "falling chirp" or a
   print("A")). Committed-answer reading puts settled chime at ~0/4. The
   judged 0.562 overstates real lookup; G3 fails under either reading, and
   the queue's question gets a clean NO: model-side accuracy does NOT follow
   the cavity-side early advantage (early key 16/16 vs settled 13/16) for
   the cue class.
3. Raw control diagnosis: 0.250 overall but 0.75 on chirp_up — the model
   defaults to "rising chirp" (the FIRST entry in raw's unranked key) when
   uncertain. Key-order artifact; true derivation-from-numbers is ~0. The
   numbers+unranked-key control is confirmed vacuous for identity: section
   energies can't name the cue. G4's PASS is therefore meaningless — the
   token comparison needs a real alternative path, which doesn't exist for
   a sensor class the model can't otherwise hear.
4. Standing-spec tension sharpens for the third time: bare cavity label
   1.000 at 42.5 tokens beats every packet. For the cue class the packet
   adds nothing but failure modes; the label IS the product, the packet is
   (at best) provenance/audit.

MHD lit check (brief, authorized): the G2a mechanism — high-band energy
re-expressed into the lowest-mode DATA attractor during the drive — has the
signature of an INVERSE energy cascade / spectral condensation: in 2D and
quasi-2D turbulence, energy injected at intermediate scales flows to larger
scales and accumulates in the lowest accessible mode ("Bose-Einstein"
condensation, Paret & Tabeling 1997; dual-cascade review: Kraichnan 1967;
Boffetta & Ecke 2012). Honest translation only: the cavity is not 2D
turbulence, but the direction (high modes -> lowest mode, accumulating in
the bank's dominant direction) matches, and the timescale reading
(tap before the cascade completes) is already measured, not borrowed.
Sources: physicstoday.aip.org/quick-study/turbulence-in-two-dimensions;
ar5iv.labs.arxiv.org/html/1201.0102; researchgate.net/publication/369071810
(transient inverse cascade). Queued as a NAMED mechanism for the
tag-timing rule; it earns its place via the iter3/3b decay curves.

**Verdict.** Exp D' resolves the queue's question negatively on both halves:
(a) the early tap does not recover section tags for full-vector cue
injections (re-expression finishes during the drive — iter3 rule bounded to
localized injections); (b) the model side does not follow the cavity-side
key advantage for cues — the v4 prose packet is not a working lookup device
outside the body-state class. Queued: cue-packet v2 with single-answer-forced
format (no-list/no-fence instruction) + top-1-only key; judge hardening
(committed-answer scoring alongside keyword scoring); inverse-cascade as the
named mechanism for tag timing.
No further MHD check needed tonight: mechanism named and already measured.


## 2026-10-21T12:05-04:00 — transducer_v1 (Zak 11:41 + ledger addendum 11:48)

Architecture: tap coupler RHO=0.10 on the through-flow; one node per section (POWER/DATA/IO/NETWORK/WEIGHTS), side-coupled resonator absorption A(mu)=4mu(1-mu), inverted conjugate stores; two-stage readout (cancel vs CALM proper, match residual vs stored inverted deltas). Baseline: FRESH real dweller tick ~11:44 EDT (transducer_baseline.json), preflight clean.

GATES: G1 PASS (useful ratio 5.26x at mu 0.5, through loss 10%; rider: node accuracy flat 0.250 at best mu vs 0.250 at mu 0.05 — matched power not cashed by this readout). G2 FAIL (node verdicts 0.250 vs same-run whole-cavity 0.812, gate >= 0.94; per-section votes {'POWER': 0.25, 'DATA': 0.25, 'IO': 0.25, 'NETWORK': 0.25, 'WEIGHTS': 0.25}). G3 FAIL (verdict acc 0.125 / 122.0 tok; label 0.500 / 42.25 tok; v4 packet 0.562 / 182.8125 tok). G4 PASS (dissipation ratio 1.028 <= 1.5).

G2 DISSECTION: Every node's inverted CALM baseline nulls TOO well: nd_proper 0.87-0.999 for every section and every true state — the template attractor collapses all settled states to within ~1-13% residual of the CALM direction per section, so state identity is NOT in the post-cancellation residual (best residual matches <= ~0.2, swamped by CALM's nd_proper in the composition; every section votes CALM 16/16). The whole-cavity chain reads the identity from the rectified autocorrelation signature instead. Follow-up queued (not run): node stores referenced to the aggregate bank baseline with LUT-style delta matching (parallel component kept), per section.

POWER LEDGER (arbitrary units, NOT joules; tolerance 1e-9): matched mu 0.5: in 8.810 = tapped 0.853 + passed/reflected 7.929 + RESIDUAL SECOND CAVITY 0.028 + bleed 0.000 (bleed ratio 0.0000). Over the mu sweep: bleed ratio spans 0.0000-0.0922 (max at the mismatched extremes, zero at critical coupling by construction); residual ratio at matched 0.0032; max closure error over sweep 2.02e-16. Full per-mu ledger in transducer_results.json -> power_ledger.by_mu.


## 2026-10-21T16:22-04:00 — transducer_v2 PRE-REGISTRATION (written before the run)

Pipeline stages (spec lexicon only): THROUGH-FLOW -> TAP -> NODE RING-DOWN -> STEP-DOWN -> RADIATIVE EXIT.
Design: nodes referenced to the AGGREGATE bank baseline (settled/drive-end aggregate field of the 17-pattern bank), LUT-style delta matching per section (delta vector matched whole — parallel component kept, nothing projected out). Tap windows: DRIVE_END (t=0.30) and SETTLED (t=0.50) per node, full section x window matrix. Matched mu=0.5, RHO=0.10, node noise 1e-3/mode as v1. Baseline: FRESH tick ~12:21 EDT (transducer_v2_baseline.json), preflight clean.
PRE-STATED TOLERANCES / CRITERIA:
- Ledger closure (S11/S21 split): |tapped + transmitted + reflected + residual_second_cavity + bleed - P_in| / P_in <= 1e-9 (partition is by construction; numeric check reported).
- Amplitude-sweep stability (0.1x/1x/10x THROUGH-FLOW): tapped fraction and residual fraction are STABLE if spread (max-min across amplitudes) <= 0.02. Bleed at matched mu is 0 by construction and at mu_bad is RHO*(1-A) by definition — reported, NOT claimed as a stability finding.
- Radiative-subspectra criterion: hypothesis SUPPORTED if exit-only classification >= 0.75 AND >= internal (whole-cavity rectified) accuracy - 0.10 on the same trials.
- Node gate: best-window composed node accuracy >= whole-cavity same-run accuracy.
- Model gate: verdict arm (wrapper-LUT verdict + ONE metadata line) accuracy >= label arm AND mean total tokens <= 60 (Gemma, 16 trials, label + raw arms same-seed).
Exit decode estimator (stated in advance): exit intensity spectrum I_n = (1-RHO)*|a_settled,n|^2 + |r_n|^2 (two exit ports, intensities summed; r = node-arm residual field after the aggregate component the stores account for is removed). Usable/remaining power decoded by least squares on features [1, I_tot, per-section shares of I] fit on 24 calibration trials (4 clean states x 6 jittered replicates); errors vs ledger ground truth on the 16 test trials.


## 2026-10-21T16:24-04:00 — transducer_v2 (Zak 12:19 go)

Stages: THROUGH-FLOW -> TAP -> NODE RING-DOWN -> STEP-DOWN -> RADIATIVE EXIT. Nodes aggregate-referenced (LUT delta stores per section, parallel component kept); taps at DRIVE_END (0.30 s) and SETTLED (0.50 s); ledger with S11/S21 split; exit decode from the radiative intensity spectrum alone. Baseline: FRESH tick ~12:21 EDT (transducer_v2_baseline.json), preflight clean.

NODE RING-DOWN: composed accuracy by window {'DRIVE_END': 0.875, 'SETTLED': 0.5} (best DRIVE_END) vs whole-cavity same-run 1.000 — gate FAIL. Section x window vote accuracy: {'DRIVE_END': {'POWER': 0.1875, 'DATA': 0.625, 'IO': 0.3125, 'NETWORK': 0.5, 'WEIGHTS': 0.3125}, 'SETTLED': {'POWER': 0.25, 'DATA': 0.5625, 'IO': 0.375, 'NETWORK': 0.5, 'WEIGHTS': 0.3125}}.

LEDGER (matched mu, S-split; arbitrary units, NOT joules): in 1.000 = tapped 0.0994 + transmitted(S21) 0.7315 + reflected(S11) 0.1685 + residual_second_cavity 0.0006 + bleed 0.0000; max closure error 2.04e-16 (tolerance 1e-9).

RADIATIVE EXIT: exit-only classification 0.812 vs internal 1.000 — radiative hypothesis NOT SUPPORTED (criterion: >= 0.75 and >= internal - 0.10). Power decode from exit alone: usable MAE 0.000 of P_in, remaining MAE 0.000 of P_in.

STEP-DOWN / SCALE: fraction spreads over 0.1x/1x/10x THROUGH-FLOW {'tapped_ratio': 0.0042, 'residual_ratio': 0.0042, 'transmitted_ratio': 0.1333, 'reflected_ratio': 0.1333} (tolerance 0.02) — tapped+residual STABLE.

MODEL GATE: verdict acc 0.375 / 67.75 tok; label 0.750 / 43.0 tok; raw 0.438 / 104.625 tok — gate FAIL (acc >= label AND verdict tokens <= 60).
