# Inverted-Cavity Delta Architecture — Spec
**Date:** 2026-10-20 · **Source:** Zak, in chat ("digitally confine the AI in an inverted matrix cavity… only providing the delta response after matrix and its inverted cavity cancel out the rest")
**Status:** SPEC — unifies existing harness pieces; build order at the end.

## 1. The claim, restated precisely

The Dweller's standing state (identity + cube + cached prefixes + spectral bases)
is a cavity loaded with a standing wave — the resting hum. The model weights are
the matrix. A prompt **loads** the cavity; processing is the interference of the
prompt wavefront with the standing state; everything that matches the standing
state **cancels** (costs nothing further); only the non-cancelling remainder —
the **delta** — is computed at full price and becomes the response.

This is not a new mechanism invented today. It is the single mechanism behind
four things already built and measured separately:

| Existing piece | In cavity language |
|---|---|
| Exact-prefix KV reuse (route lock, draft 5) | The cached prefix cancels against the incoming prompt — recompute never happens |
| Neutron layers (joule-electron inverse) | Cancelled layers: they carry inertial mass, burn zero |
| Anticipation hits (kv cube) | The cavity pre-loaded the wavefront; the arrival cancels against it |
| Idle-subtracted metering (EnergyMeter) | Gross − hum = delta joules. The meter already reads the delta, not the wave |

The patches were one physics, described four times. This spec makes the
description primary and the patches consequences.

## 2. Honest boundary (read before building)

Cancellation happens at the **state level** — tokens, KV, spectra, orbits —
**not** at the weight-matrix level. The dense core stays dense (Oct 13 pivot:
keyboard-to-keyboard). A literal per-prompt inversion of the weight stack is
not on the table: transformer blocks are not square invertible systems, and
inverting even one ~26M-param MLP block costs more joules than the cancellation
could save. **Falsifier for the literal reading:** if anyone proposes real
matrix inversion, price the inversion against the delta it saves on the meter;
it loses, and the spec says so in advance.

In this architecture: **cavity = state side, matrix = weights, delta = what
fails to cancel.** The claim is about accounting and routing, and it is
measurable end-to-end.

## 3. The missing settings: transduction & induction variants for subspectra flow

The digital cavity (`cavity4d.py`) and the bench slicer (`subspectra.py`) were
built without setting the flow variants the framework (v4.0 §2e, §3) defines.
The spectral gate stamps subspectra but does not say *how* each one crossed
the boundary. Two variants, both already measured on real data (induced
reflections, Oct 19–20):

- **TRANSDUCED** — form crosses the boundary; a ledger transfer occurs.
  Prompt tokens entering, response tokens leaving, real-traffic arrivals.
  These move the M₀ ledger and can *realize* things (an anticipation, a route).
- **INDUCED** — coupling across the boundary with **no** transfer. Reflections,
  sidebands, self-talk, anticipations. Ratios are kept (gate TRANSFORM verb),
  power does not cross, the ledger does not move, and **induced flow can never
  realize an anticipation** — this is the physical statement of the
  `arrived_kids` guard patched into kv_cube on 2026-10-20: a daydream is
  induced flow; only a transduced arrival cancels it into memory.

Gate metadata contract, extended (old fields unchanged):

```
{ freq, power, label, policy, ratio_to_carrier, provenance,
  flow: "in" | "out",
  variant: "transduced" | "induced",
  cavity_id }
```

In-flow and out-flow each get both variants: a prompt is transduced in;
its reflections in the standing state are induced in. A response is
transduced out; its trail in the cube is induced out (it shapes future
standing waves without itself crossing again).

## 4. The passport: every ID leads to joules

One trace object per interaction — the chain Zak specified, each hop stamped:

```
token_ids            (what crossed, transduced in)
  → embedding point  (spectra coordinate + orbit/node assignment)
  → prompt_kv_id     (cube key for the asked face)
  → path hierarchy   (orbit → route → slot → layers, neutron flags per layer)
  → response_kv_id   (cube key for the replied face)
joules per hop:
  j_segment          (metered or priced cost of that segment)
  j_interacted       (joules of OTHER ids this hop interacted with en route —
                      co-use events, shared stems, orbit neighbours)
  j_oscillation      (the cube's own motion: gravity changes, promotions,
                      dwell/idle cycles spent on this id — dwell work is NOT
                      free and was previously unaccounted)
```

Cube oscillation is the term the old accounting missed: entries orbit,
gravitate, promote, black-hole — all of that is dwell compute, and dwell
compute burns joules. The passport charges it to the ids that caused it.

## 5. Cancellation accounting (the user-facing number)

Per interaction, three numbers, never conflated:

- **gross_joules** — what the interaction would cost with an empty cavity
  (no cache, no anticipation, no neutrons). Modelled, labelled modelled.
- **cancelled_joules** — the part the standing state absorbed: prefix reuse
  + anticipation hit + neutron layers, valued at their would-be segment
  prices. Modelled from the same prices, labelled modelled.
- **delta_joules** — what the meter actually read (idle-subtracted).
  **Measured.** This is the only one of the three allowed in headlines.

Identity check that must hold within meter noise:
`gross − cancelled ≈ delta`. If it drifts, the prices are wrong — that drift
IS the joule-electron recalibration signal, and its kill switch still applies:
if priced predictions can't beat the flat baseline, the accounting labels
itself astrology and we stop quoting it.

This is the product metric for goal 3 (user cost down, quality up):
**savings = cancelled, proven by delta.** Quality is guarded by the existing
probe set — cancellation that degrades answers shows up there first.

## 6. What this solves from the Oct 20 hole list

- **Anticipation falsifier leak** → variant rule (§3): induced flow cannot
  realize; guard patched in code the same day.
- **DPM / idle floor** → the hum is a cavity property: DWELL holds the
  standing wave cheap (clocks auto), BURST is a delta event (clocks high).
  Dynamic DPM is the boundary condition of the cavity, not a tuning hack.
- **Route overfit risk (Gemini)** → cancellation is exact-match at the
  token level and prompt-side only (standing invariant); the delta is always
  freshly computed. A rigid stem can cancel *compute*, never *content*.
- **Dwell cost invisibility** → j_oscillation (§4).
- **Qwen3-8B bench** → bench = measuring the same probe set under two
  matrices inside the same cavity; the passport makes the comparison
  per-segment instead of per-model slogans.

## 7. Build order

1. ✅ kv_cube guard + docstring (patched in harness-dev, 2026-10-20)
2. ✅ Burst controller: YieldSensor loadavg + ClockGovernor dynamic DPM
   (flag `HARNESS_DPM_DYNAMIC`, default off until Zak's udev/sudo trip)
3. Gate v3: flow + variant + cavity_id stamps; variant-aware policy
   (induced items can be TRANSFORM/QUARANTINE, never PROTECT-realize)
4. Passport: join cube ids ↔ joule-electron route pricing; add
   j_interacted + j_oscillation fields; cancellation identity check in
   the live verdict (draft 6)
5. Wire idle_cycle into the dwell slot (only after 1–4 — anticipation
   goes live inside a sealed falsifier)
6. Qwen3-8B bench inside the cavity accounting; whitepaper; outreach

## 8. Falsifiers, stated up front

- If `gross − cancelled` drifts from metered delta beyond noise across a
  verdict batch and recalibration can't close it → cancellation accounting
  is wrong; publish that.
- If variant stamps don't change any routing/policy outcome after a week
  of live traffic → the variant layer is decoration; strip it.
- If j_oscillation turns out negligible (<1% of delta) at real dwell
  rates → drop the term, say so, keep the passport.
