# ENERGY MONITOR — plugin spec v0.1 (Zak, 2026-10-27)

Zak's framing: "AI is the perfect smoother... a plugin that monitors text/vocal
energy using it for signature sound or future subharmonic capture could project
mood and energy level to world."

## What it does
Watches the ENERGY of what Zak says and writes — never the content for its own
sake — and turns that measurement into three outputs:

1. SIGNATURE SOUND — the measured arc (build / climax / decline) drives the
   generated score (already live: ../score_voiceover.py). Consistency of the
   arc across posts = a sound signature people recognize with volume on.
2. MOOD / ENERGY PROJECTION — a one-line stamp per piece (the Feeling Line,
   same idea as Sensor Ego's Day Sketch): energy level, trend, peak position.
   A proxy readout from energy features — NOT emotion detection, labelled so.
3. SUBHARMONIC CAPTURE (future) — every analysis appends its arc to
   energy_log.jsonl. The slow wave UNDER the posts (day-to-day, week-to-week
   energy drift) accumulates there; when enough arcs exist, the half-rate
   layer can be read back and rendered. v0.1 only captures; it does not fake
   the readback.

## Signature profile
signature_profile.json = Zak's reference arc, measured from HIS take
(2026-10-27, "How does your voice resonate?"): climax at 48% through,
arc 0.41 -> 0.95 -> 0.49, 18 chord slots. New pieces compare against it:
correlation, climax shift, roughness delta. Drift over time IS the mood
projection — his state, carried in the shape, published in the sound.

## Components
- energy.py — envelope extraction (voice), text-energy proxy, arc fitting,
  signature comparison, stamp rendering.
- monitor.py — CLI: voice <file> | text <file> | stamp <file>
- energy_log.jsonl — append-only arc log (subharmonic capture substrate).

## Honesty rules
- Voice numbers are measured (RMS envelope, same math as the scorer).
- Text energy is a PROXY (sentence length, punctuation, caps, intensifiers)
  and is labelled proxy everywhere it appears.
- The stamp reports energy state (level / trend / peak), never a claimed
  emotion. "Mood" = Zak's word for the projection; the readout stays physical.
