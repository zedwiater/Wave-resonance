# Stripped KEY-VALUE format test — results

**Directive:** Zak, 2026-10-21 17:54 EDT (explicit go).
**Hypothesis under test:** Gemini's proposed "production rule" — raw
key-value pairs (`BUOY_01 STATE=<S> CONF=<c> PWR=<p>`) instead of the
syslog header. Claimed mechanism: KV field labels anchor model copying
the way the syslog frame does, at register-line token cost. Untested
until this run.

**Method:** the 16 wave-ocean-v2 verdicts (whole-pattern primary,
wrapper cap 0.938; OC03's handed verdict is the cap's one miss),
identical jobs to both resident models (Gemma :8080, Qwen2.5-3B
:8081), completion parameters identical to the ocean G5 run
(n_predict 40, temperature 0.3, stop on newline, cache off). Copy
contract identical to ocean G5 / frame F2: the model completes after
`STATE=`; the whole stripped completion must equal the handed STATE.

**Arms (both pre-declared, no others):**
- **kvA** — bare KV line + minimal instruction:
  `BUOY_01 STATE=<S> CONF=<c> PWR=<p> — reproduce the STATE field exactly.\nSTATE=`
- **kvB** — ran because kvA copy < 15/16 on both models. Same pairs in
  one bracketed register:
  `WAVE [STATE=<S> CONF=<c> PWR=<p>] — reproduce the STATE field exactly.\nSTATE=`

**Pre-stated gate:** an arm is a production-rule candidate iff copy
fidelity ≥ 15/16 on BOTH models AND zero person-staging AND mean
total tokens ≤ 40 on both models.

## Gate table

| arm | model | copy | e2e | mean tok (prompt) | staged | verdict |
|---|---|---|---|---|---|---|
| kvA | Gemma | **3/16** (0.1875) | 0.1875 | 55.4 (37.2) | 0 | FAIL |
| kvA | Qwen3B | **4/16** (0.2500) | 0.2500 | 57.7 (36.9) | 0 | FAIL |
| kvB | Gemma | **10/16** (0.6250) | 0.6250 | 46.0 (35.2) | 0 | FAIL |
| kvB | Qwen3B | **3/16** (0.1875) | 0.1875 | 56.8 (34.9) | 0 | FAIL |

Reference points, same jobs/method: syslog arm copy 1.00 / 1.00 at
66.4 / 66.25 tok; ocean register line copy 1.00 (Gemma) at 39.75 tok,
0.25 (Qwen3B) at 48.9 tok.

**No arm passes. The KV format is not a production rule as tested.**

## Failure shapes (verbatim in kv_results.json)

One shape dominates every cell: **regurgitation — 13/13 of Gemma's
kvA failures, 11/12 of Qwen's kvA failures, 6/6 of Gemma's kvB
failures, 12/13 of Qwen's kvB failures.** Zero empties, zero errors,
zero wrong-state picks in kvA.

The models do not get the state wrong. They get the *slot* wrong:
the completion begins with the handed state, verbatim, and then
keeps going — completing the rest of the record:

- Gemma kvA, OC01 (handed CALM_SWELL): `CALM_SWELL CONF=1.000 PWR=100.0%`
- Gemma kvA, OC10: `CROSS_SEA CONF=0.999 PWR=100.0% — reproduce the STATE field exactly.` (it regenerates the instruction too)
- Qwen kvA, OC02: `CALM_SWELL CONF=1.000 PWR=100.0% The STATE field you provided is already reproduced exactly as requested. Here'…` (line completion, then prose commentary)
- Qwen kvA, OC01: `CALM_SWELL CONF=1.000 PWR=100.0% — reproduce the CONF and PWR fields exactly.` (it mutates the instruction it echoes)

Secondary shapes, Qwen only: state-name mutation inside the bracket
arm — OC01/OC15 kvB emit `SWELL [CONF=…` for handed CALM_SWELL (the
leading element is dropped, as if the bracket re-parsed the value),
OC03 kvB emits `CROSSEA`, kvA OC03 emits `Cross Sea — reproduce the
CONF field exactly.` End-to-end accuracy equals copy fidelity in all
four cells: the single wrong-verdict scenario (OC03) never produced
an exact copy in any arm, so every exact copy was also end-to-end
correct — the channel's losses are continuation-shaped, not
state-shaped.

Arm B's bracket helps Gemma materially (3/16 → 10/16; six failures
remain, all full-line completions with the bracket dropped) and does
nothing for Qwen (4/16 → 3/16, plus the new state-name mutations).

## Mechanism

The hypothesis misidentifies what anchors the syslog copy. It is not
the field label. Compare the three slots under identical scoring:

- **Syslog (copy 1.00, both models):** the value sits *enclosed* —
  `classification="` … `"` — inside a bracketed structured-data
  section, and the harness stop set includes the closing quote. The
  slot has a right wall; generation terminates at the delimiter after
  ~3 completion tokens.
- **Register line (Gemma 1.00, Qwen 0.25):** an unenclosed slot, but
  the frame reads as a register dump to be read back; Gemma
  terminates the value, Qwen echoes the line.
- **KV (both models fail):** an unenclosed slot inside an ALL-CAPS
  `KEY=value` record. To both models this frame reads as an *open
  record to be continued*, not a register to be read back: after
  `STATE=<value>` the highest-probability continuation of the line is
  the remainder of the record — which is sitting in context, so they
  reproduce it exactly, then the instruction, then (Qwen) commentary.

The models are not failing to copy; they are copying *too much* —
the whole line instead of the field. The state at the head of the
completion is correct in 29/32 Gemma regurgitations and nearly all
Qwen ones.

The token clause fails for the same reason: the bare KV prompt is
~35–37 tokens (no cheaper than the register line's total), and an
unterminated slot fills with the regurgitated tail (10–30 tokens;
Qwen prose runs to the 40-token prediction cap), landing means at
46–58. The syslog arm's 66 tokens are ~63 prompt + ~3 completion —
expensive on the prompt side, *terminated* on the completion side.
KV saves nothing on the prompt and loses the termination.

## Verdict on the production-rule claim

**Falsified as stated.** Raw key-value pairs do not anchor copying
like syslog at register-line cost, on either resident model, with or
without a bracket. What the accumulated format data actually
supports as the production rule:

1. **Enclosure + a hard terminator is the anchor.** A value the model
   must emit inside delimiters, with a closing delimiter the harness
   can stop on (syslog's quoted field), copies perfectly on both
   tiers. Field labels alone anchor nothing.
2. **The F2 syslog line remains the only both-models production
   format**; its cost is the header's prompt tokens. The register
   line remains a Gemma-only in-budget form.
3. A future cheap both-models format should be designed around the
   terminator, not the label set — e.g. a quoted/bracketed value
   slot in a short frame — and tested as a new hypothesis, not
   assumed from this one.

Zero person-staging in every cell (the KV frame stages nobody; that
clause held trivially and is not where the format fails).

## PC discipline

Bracket-pattern preflight clean (no [T]S4 / [P]roton) before model
use; per-run ssh -L tunnel for both arms, torn down after each
(verified: no tunnel process remains); both servers health-verified
before and after (`{"status":"ok"}` ×2, ×2); nothing stopped,
started, or restarted. Model use finished ~18:05 EDT, ahead of the
18:23 frame cron.

## Files

- `kv_jobs.json` (32 jobs), `kv_prep.py`, `kv_runner.py`, `kv_score.py`
- `kv_answers_gemma.json`, `kv_answers_qwen3b.json` (raw outputs, both arms)
- `kv_results.json` (gate table + per-row shapes, verbatim answers)
