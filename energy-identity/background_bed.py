#!/usr/bin/env python3
"""Background-bed generator — original, loopable background music.

Give it a chord progression and a mood; it renders a seamless ambient loop
(pad chords + soft arpeggio + sub root). Everything is synthesized from
scratch with numpy: no samples, no melodies copied from anywhere. Chord
progressions, tempo, timbre and mood are the inputs — the notes it plays
are generated, so the output is yours to use under your own content.

Usage:
  python3 background_bed.py --mood calm   --out samples/calm.wav
  python3 background_bed.py --mood night  --out samples/night.wav
  python3 background_bed.py --mood bright --out samples/bright.wav
  python3 background_bed.py --progression "Am F C G" --bpm 76 --minutes 2 \
      --arp-density 0.5 --brightness 0.4 --out custom.wav

Design notes:
- The loop is exactly one progression cycle long and is rendered with a
  wrap-around reverb tail, so it loops seamlessly in any editor/player.
- `wrap-reverb`: the tail that would ring past the end is folded back into
  the start, which is what makes the seam inaudible.
- Deterministic: same seed + same settings = same render.
"""
import argparse
import numpy as np

SR = 44100

NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

def parse_chord(sym):
    """'Am7' -> (root_midi_offset_in_C_major_scale, [intervals]) very small parser."""
    s = sym.strip()
    root = NOTE[s[0].upper()]
    i = 1
    if i < len(s) and s[i] in "#b":
        root += 1 if s[i] == "#" else -1
        i += 1
    rest = s[i:]
    if rest.startswith("maj7"):
        iv = [0, 4, 7, 11]
    elif rest.startswith("m7"):
        iv = [0, 3, 7, 10]
    elif rest.startswith("m"):
        iv = [0, 3, 7]
    elif rest.startswith("7"):
        iv = [0, 4, 7, 10]
    elif rest.startswith("9"):
        iv = [0, 4, 7, 10, 14]
    elif rest.startswith("add9"):
        iv = [0, 4, 7, 14]
    else:
        iv = [0, 4, 7]
    return root, iv

def midi_freq(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)

def adsr_env(n, attack, release):
    env = np.ones(n)
    a = min(int(attack * SR), n // 2)
    r = min(int(release * SR), n // 2)
    if a > 0:
        env[:a] = np.linspace(0.0, 1.0, a) ** 1.5
    if r > 0:
        env[-r:] *= np.linspace(1.0, 0.0, r) ** 1.5
    return env

def tone(freq, dur, partials, phase=0.0):
    """Additive tone with a slow tremolo swell per partial."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, (mult, amp) in enumerate(partials):
        swell = 0.85 + 0.15 * np.sin(2 * np.pi * 0.07 * t + phase + k * 1.7)
        out += amp * swell * np.sin(2 * np.pi * freq * mult * t + phase + 0.13 * k)
    return out

def one_pole_lowpass(x, cutoff_norm):
    y = np.empty_like(x)
    a = float(np.clip(cutoff_norm, 0.001, 1.0))
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y

def render(progression, bpm, bars_per_chord=1, beats_per_bar=4,
           arp_density=0.5, brightness=0.45, pad_level=0.50,
           arp_level=0.16, sub_level=0.20, base_octave=3, seed=7):
    rng = np.random.default_rng(seed)
    sec_per_beat = 60.0 / bpm
    chord_dur = sec_per_beat * beats_per_bar * bars_per_chord
    chords = [parse_chord(c) for c in progression]
    total_dur = chord_dur * len(chords)
    n = int(total_dur * SR)
    mix = np.zeros(n + int(1.6 * SR))  # slack for pad release + reverb tail, folded back later

    pad_partials = [(1.0, 0.55), (2.0, 0.22), (3.0, 0.10), (4.0, 0.05 * brightness * 4)]
    arp_partials = [(1.0, 0.6), (2.0, 0.18 * brightness * 2), (3.0, 0.06)]

    for ci, (root_pc, iv) in enumerate(chords):
        start = int(ci * chord_dur * SR)
        root_midi = 12 * (base_octave + 1) + root_pc
        # PAD: chord tones one octave span, crossfaded into neighbours
        seg_len = int((chord_dur + 1.2) * SR)
        pad = np.zeros(seg_len)
        for ivl in iv:
            f = midi_freq(root_midi + ivl + 12)
            pad += tone(f, chord_dur + 1.2, pad_partials,
                        phase=rng.uniform(0, 2 * np.pi))
        pad *= adsr_env(seg_len, attack=1.1, release=1.2)
        mix[start:start + seg_len] += pad * (pad_level / len(iv))
        # SUB: root two octaves under the pad root, plain sine
        sub_n = int(chord_dur * SR)
        t = np.arange(sub_n) / SR
        sub = np.sin(2 * np.pi * midi_freq(root_midi - 12) * t)
        sub *= adsr_env(sub_n, attack=0.4, release=0.6)
        mix[start:start + sub_n] += sub * sub_level
        # ARP: soft plucks walking the chord tones, octave up
        steps = beats_per_bar * bars_per_chord * 2  # 8th notes
        order = [0, 2, 1, 3, 2, 0, 1, 2][:max(steps, 1)]
        for st in range(steps):
            if rng.random() > arp_density:
                continue
            ivl = iv[order[st % len(order)] % len(iv)]
            f = midi_freq(root_midi + ivl + 24)
            pluck_dur = 0.55
            pl = tone(f, pluck_dur, arp_partials, phase=rng.uniform(0, 6.28))
            pl *= np.exp(-np.arange(int(pluck_dur * SR)) / (0.16 * SR))
            pos = start + int(st * (chord_dur / steps) * SR)
            mix[pos:pos + len(pl)] += pl * arp_level
    # gentle master lowpass for "background" softness
    lp = one_pole_lowpass(mix, 0.10 + 0.25 * brightness)
    mix = 0.65 * mix + 0.35 * lp
    # simple generated reverb: few decaying taps
    rev = np.zeros_like(mix)
    for delay_s, gain in [(0.11, 0.22), (0.19, 0.16), (0.31, 0.11), (0.47, 0.07)]:
        d = int(delay_s * SR)
        rev[d:] += mix[:-d] * gain
    mix = mix + rev
    # wrap the tail past the loop point back into the head -> seamless loop
    core = mix[:n].copy()
    tail = mix[n:]
    core[:len(tail)] += tail
    # stereo: slight width from a short offset copy of the pad-heavy mix
    left = core
    right = np.roll(core, int(0.008 * SR)) * 0.92
    stereo = np.column_stack([left, right])
    # normalize: target RMS, peak cap
    rms = np.sqrt(np.mean(stereo ** 2))
    stereo *= (0.16 / max(rms, 1e-6))
    peak = np.max(np.abs(stereo))
    if peak > 0.89:
        stereo *= 0.89 / peak
    return stereo

MOODS = {
    # name: (progression, bpm, arp_density, brightness, base_octave)
    "calm":   (["Am", "F", "C", "G"],          72, 0.45, 0.35, 3),
    "night":  (["Dm7", "Bbmaj7", "F", "Am7"],  66, 0.35, 0.28, 3),
    "bright": (["C", "G", "Am", "F"],          84, 0.60, 0.60, 3),
    "deep":   (["Cm", "Ab", "Eb", "Bb"],       60, 0.30, 0.22, 2),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mood", choices=list(MOODS), default=None)
    ap.add_argument("--progression", default=None,
                    help='e.g. "Am F C G" (overrides mood progression)')
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--repeats", type=int, default=2,
                    help="how many progression cycles in the file (loops cleanly)")
    ap.add_argument("--bars-per-chord", type=int, default=2)
    ap.add_argument("--arp-density", type=float, default=None)
    ap.add_argument("--brightness", type=float, default=None)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    prog, bpm, dens, bright, octv = MOODS.get(args.mood, MOODS["calm"])
    if args.progression:
        prog = args.progression.split()
    if args.bpm:
        bpm = args.bpm
    if args.arp_density is not None:
        dens = args.arp_density
    if args.brightness is not None:
        bright = args.brightness

    one = render(prog, bpm, bars_per_chord=args.bars_per_chord,
                 arp_density=dens, brightness=bright,
                 base_octave=octv, seed=args.seed)
    audio = np.tile(one, (args.repeats, 1))
    pcm = (audio * 32767).astype(np.int16)
    import wave
    with wave.open(args.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    dur = len(audio) / SR
    loop_dur = len(one) / SR
    print(f"wrote {args.out}: {dur:.1f}s total, seamless loop every {loop_dur:.1f}s, "
          f"progression {'-'.join(prog)} @ {bpm} bpm")

if __name__ == "__main__":
    main()
