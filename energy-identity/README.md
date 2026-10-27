# AI Audio Identity — plugins v0.1

**Your voice is the score.** Tools for creators who refuse to rent their sound:
measure the energy of your own voice, generate your background music from it,
and shape synthetic narration with the same form. No catalog music, no samples,
nothing copied — so there is nothing to license and nothing to strike.

Built and measured in the open, 2026-10-27. Measurements before metaphors:
every claim below carries its number.

## The pieces

- `background_bed.py` — a background-music generator (numpy additive synth:
  pads, sub root, soft arps, generated reverb). Seamless loops, zero samples.
- `score_voiceover.py` — reads a voiceover's energy envelope, finds its
  climax, builds an intensity arc (climaticness vs declination), renders a
  generated bed that follows the arc and ducks under speech. Outputs a mix
  and a bed-only file (your standalone signature sound).
- `energy-monitor/` — the Energy Monitor plugin (`PLUGIN.md` has the spec):
  - `energy.py` / `monitor.py` — measure voice energy (50 ms RMS envelope:
    arc, climax position, level, roughness) and text energy (a labelled
    PROXY). Emits a one-line energy-state stamp per piece — level, trend,
    peak position, signature match. Every run appends its arc to a local log:
    the slow wave under your posts accumulates there (subharmonic capture —
    capture only in v0.1; the readback is future work).
  - `profile_voice.py` — the **TTS Energy Overpass**: takes a stock synthetic
    narration and passes it through YOUR energy envelope. Per-slot energy is
    remapped onto your signature arc, and pitch is shifted toward your
    measured median F0. This is energy forming, **not voice cloning** —
    timbre is untouched.

## Measured results (first test, 2026-10-27)

Reference profile measured from one real 116 s voiceover take
(climax 51% through; median F0 102.1 Hz; purification: dead-air/noise-floor
frames dropped, clipped frames excluded, slot medians so transients can't
bend the form).

- Stock TTS narration, signature-arc correlation: **-0.23**
- Same narration after the Energy Overpass: **+0.80**
- Pitch shift applied: +0.4 semitones (stock voice measured 99.8 Hz)
- Honest partial: climax position moved 0.47 -> 0.44 toward the signature's
  0.51 but did not land on it; two slots hit the gain cap (0.55-1.9).
  Recorded in `energy-monitor/TEST_RESULTS_2026-10-27.json`.

## Build your own signature

1. Record 1-2 minutes of yourself talking naturally.
2. `python3 energy-monitor/monitor.py voice your_take.m4a` — your arc.
3. Save the arc as your `signature_profile.json` (format: see the test
   results + `energy.py`). Yours stays on your machine — the release ships
   the tools, not anyone's voice data.
4. `python3 score_voiceover.py take.m4a --out scored` — your sound.
5. `python3 energy-monitor/profile_voice.py take.m4a narration.mp3 out.wav`
   — your form, over any synthetic voice.

## Dependencies

python3, numpy, ffmpeg (with the rubberband filter for pitch). Any TTS
source works for the narration. A kid in a basement can replicate this.

## Not in this release (deliberately)

- The author's signature profile, energy log, and audio: personal voice data,
  generated locally per user, never shipped.
- Subharmonic readback (rendering the slow wave): capture substrate only.
- Voice cloning of any kind.

License: use it. Standard-setting, not selling — adoption by use.
