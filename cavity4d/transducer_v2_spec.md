# Transducer v2 spec (drafted 2026-10-21, from v1 dissection + Gemini review + Zak 12:15 directives)

## Carried from v1 (measured, not negotiable)
- Node stores referenced to the AGGREGATE bank baseline; LUT-style delta matching per section; PARALLEL component kept (state identity lives in the rectified autocorrelation signature — CALM-referenced cancellation erases it).
- Power ledger must close per configuration: in = tapped + transmitted + reflected + residual_second_cavity + bleed (S11/S21 SPLIT: v1 lumped reflected+transmitted as "passed" — v2 separates them).

## New in v2
1. CASCADE-TIMED NODE SAMPLING (Gemini's flag, Zak confirmed overlooked): each node samples at its section's cascade window, not at settled state. Rule from iter3/iter4: section-localized events tap at DRIVE END; whole-pattern states tap SETTLED. Node spec carries a tap_time per section; test both windows per section and report the matrix.
2. OPEN-LOOP OUTPUT DECODING (Zak): the system is an OPEN loop — what exits the far side gets decoded into ESTIMATED USABLE POWER and REMAINING POWER. v2 reports the exit channel as a first-class output: exit spectrum -> usable power estimate + remaining power estimate, with the estimation error vs the sim's ground truth stated.
3. RADIATIVE SUBSPECTRA HYPOTHESIS (Zak): the exit channel may be strictly radiative subspectra — v2 tests whether the exit/radiated band alone carries enough structure to decode the state (classification from exit spectrum only, vs full internal readout). If exit-only classification collapses, the hypothesis fails as stated.
4. STEP-DOWN VOCABULARY (Zak): a consistent lexicon naming each cascade step-down stage and its data-processing role — the vocabulary IS the system's language map. Draft lexicon (to be ratified in the run):
   - THROUGH-FLOW (TP field; power+data in transit; no processing)
   - TAP (impedance-matched sampling; role: meter + divert)
   - NODE RING-DOWN (section-local resonance; role: classify by interference)
   - STEP-DOWN (cascade to lower band; role: compress + re-tag subspectra id)
   - RADIATIVE EXIT (what leaves; role: publish usable/remaining power + verdict)
   Every stage transition in v2 logs use these names only.
5. SCALE DISCIPLINE (Zak): through-flow is VAST vs the tap (power-wire/picotesla regime). Report tap/bleed/residual as FRACTIONS with stability across a through-flow amplitude sweep (0.1x/1x/10x), not absolute proxy units alone. A ratio that drifts with amplitude is not a universal ratio.

## Gates (pre-registered at run time)
- Node classification (aggregate-referenced, cascade-timed) >= whole-cavity same-run accuracy.
- Exit-only classification reported; radiative hypothesis verdict stated.
- Ledger closes with S11/S21 split; bleed ratio stable across amplitude sweep (state tolerance at run time).
- Verdict packet (wrapper-LUT resolution, verdict + 1 metadata line) vs Gemma: accuracy >= label at <= 60 total tokens.
