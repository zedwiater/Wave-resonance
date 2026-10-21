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
