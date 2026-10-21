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
