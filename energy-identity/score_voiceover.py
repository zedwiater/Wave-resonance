#!/usr/bin/env python3
"""Score a voiceover: generate a background bed whose arc follows YOUR voice.

Pipeline (Zak's spec, 2026-10-27):
  1. Read the voiceover (any format ffmpeg can decode: m4a/wav/mp3/...).
  2. Measure its energy envelope — where you get loud/animated, where you
     pause, where the explanation naturally builds and resolves.
  3. Map that to a musical arc: intensity per chord slot blends
       - your measured energy in that stretch, and
       - a narrative prior (quiet open -> build -> climax near your energy
         peak -> decline/resolve at the end).
     Intensity drives pad level, arp density and brightness together —
     that's the "climaticness versus declination" knob, automated.
  4. Duck the bed under your voice (gain follows your envelope down when
     you speak, swells back in pauses and at build moments), so the music
     breathes with your rhythm instead of fighting it.
  5. Write two files: <out>_mix.wav (voice + bed, bed ducked under your
     voice so it breathes with you) and <out>_bed.wav (bed only, arc
     applied, NO ducking — the shaped sound itself, for posts where the
     platform takes a separate sound).

Usage:
  python3 score_voiceover.py voice.m4a --mood calm --out scored/demo
  python3 score_voiceover.py voice.wav --mood night --duck 0.55 --bed-gain 0.9

The bed is the same original generator as background_bed.py — no samples,
no copied melodies. Progressions/moods live there.
"""
import argparse
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from background_bed import MOODS, SR, parse_chord, midi_freq, adsr_env, tone, one_pole_lowpass

WIN = int(0.05 * SR)  # 50 ms envelope windows


def load_voice(path):
    """Decode any audio to mono float32 at SR via ffmpeg."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
         "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    if len(x) < SR:
        raise SystemExit("voiceover is under 1 second — nothing to score")
    peak = np.max(np.abs(x))
    if peak > 0:
        x *= 0.89 / peak
    return x


def envelope(x):
    n = len(x) // WIN
    e = np.sqrt(np.mean(x[:n * WIN].reshape(n, WIN) ** 2, axis=1) + 1e-12)
    # smooth ~0.4 s
    k = max(1, int(0.4 / 0.05))
    e = np.convolve(e, np.ones(k) / k, mode="same")
    return e  # one value per 50 ms


def smoothstep(a):
    return a * a * (3 - 2 * a)


def build_arc(env, chord_bounds_s):
    """Intensity 0..1 per chord slot: measured energy + narrative prior."""
    dur_s = len(env) * 0.05
    e = env / (np.percentile(env, 95) + 1e-9)
    e = np.clip(e, 0, 1)
    # climax = centroid of the top-energy third, time-wise
    thr = np.percentile(e, 66)
    hot = np.where(e >= thr)[0]
    climax_t = (hot.mean() * 0.05) if len(hot) else dur_s * 0.7
    arcs = []
    for (s0, s1) in chord_bounds_s:
        mid = 0.5 * (s0 + s1)
        seg = e[int(s0 / 0.05):max(int(s1 / 0.05), int(s0 / 0.05) + 1)]
        meas = float(seg.mean()) if len(seg) else 0.3
        # narrative prior: rise to climax, decline after
        if mid <= climax_t:
            prior = 0.25 + 0.75 * smoothstep(mid / max(climax_t, 1e-6))
        else:
            frac = (mid - climax_t) / max(dur_s - climax_t, 1e-6)
            prior = 1.0 - 0.55 * smoothstep(frac)
        arcs.append(float(np.clip(0.45 * meas + 0.55 * prior, 0.08, 1.0)))
    return np.array(arcs), climax_t


def render_bed_automated(progression, bpm, bars_per_chord, total_s,
                         base_density, base_brightness, arcs, seed=7):
    """Render bed for total_s with per-chord-slot intensity from arcs."""
    rng = np.random.default_rng(seed)
    sec_per_beat = 60.0 / bpm
    chord_dur = sec_per_beat * 4 * bars_per_chord
    chords = [parse_chord(c) for c in progression]
    n_slots = int(np.ceil(total_s / chord_dur))
    n = int(total_s * SR)
    mix = np.zeros(n + int(1.6 * SR))
    bounds = []
    for slot in range(n_slots):
        s0 = slot * chord_dur
        bounds.append((s0, min(s0 + chord_dur, total_s)))
        inten = float(arcs[slot % len(arcs)]) if len(arcs) else 0.5
        root_pc, iv = chords[slot % len(chords)]
        root_midi = 12 * 4 + root_pc
        start = int(s0 * SR)
        pad_partials = [(1.0, 0.55), (2.0, 0.22),
                        (3.0, 0.10 * (0.4 + base_brightness)),
                        (4.0, 0.20 * base_brightness * inten)]
        seg_len = int((chord_dur + 1.2) * SR)
        pad = np.zeros(seg_len)
        for ivl in iv:
            pad += tone(midi_freq(root_midi + ivl + 12), chord_dur + 1.2,
                        pad_partials, phase=rng.uniform(0, 2 * np.pi))
        pad *= adsr_env(seg_len, attack=1.0, release=1.2)
        end = min(start + seg_len, len(mix))
        mix[start:end] += pad[:end - start] * ((0.20 + 0.52 * inten) / len(iv))
        sub_n = int(chord_dur * SR)
        t = np.arange(sub_n) / SR
        sub = np.sin(2 * np.pi * midi_freq(root_midi - 12) * t)
        sub *= adsr_env(sub_n, attack=0.4, release=0.6)
        end = min(start + sub_n, len(mix))
        mix[start:end] += sub[:end - start] * (0.10 + 0.12 * inten)
        steps = 4 * bars_per_chord * 2
        order = [0, 2, 1, 3, 2, 0, 1, 2]
        dens = base_density * (0.35 + 0.85 * inten)
        arp_partials = [(1.0, 0.6), (2.0, 0.36 * base_brightness), (3.0, 0.06)]
        for st in range(steps):
            if rng.random() > dens:
                continue
            ivl = iv[order[st % len(order)] % len(iv)]
            pl = tone(midi_freq(root_midi + ivl + 24), 0.55, arp_partials,
                      phase=rng.uniform(0, 6.28))
            pl *= np.exp(-np.arange(len(pl)) / (0.16 * SR))
            pos = start + int(st * (chord_dur / steps) * SR)
            end = min(pos + len(pl), len(mix))
            if end > pos:
                mix[pos:end] += pl[:end - pos] * (0.05 + 0.13 * inten)
    lp = one_pole_lowpass(mix, 0.10 + 0.25 * base_brightness)
    mix = 0.65 * mix + 0.35 * lp
    rev = np.zeros_like(mix)
    for delay_s, gain in [(0.11, 0.22), (0.19, 0.16), (0.31, 0.11), (0.47, 0.07)]:
        d = int(delay_s * SR)
        rev[d:] += mix[:-d] * gain
    mix = mix + rev
    return mix[:n], chord_dur


def duck(bed, env, duck_depth):
    """Gain-reduce bed under speech: gain = 1 - depth * normalized env."""
    e = env / (np.percentile(env, 95) + 1e-9)
    e = np.clip(e, 0, 1)
    g = 1.0 - duck_depth * e
    g_full = np.repeat(g, WIN)
    if len(g_full) < len(bed):
        g_full = np.pad(g_full, (0, len(bed) - len(g_full)), mode="edge")
    g_full = g_full[:len(bed)]
    # smooth gain ~120 ms so ducking breathes instead of pumping
    k = int(0.12 * SR)
    g_full = np.convolve(g_full, np.ones(k) / k, mode="same")
    return bed * g_full, g_full


def write_wav(path, mono_or_stereo):
    x = mono_or_stereo
    if x.ndim == 1:
        x = np.column_stack([x, x])
    peak = np.max(np.abs(x))
    if peak > 0.95:
        x = x * (0.95 / peak)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice")
    ap.add_argument("--mood", choices=list(MOODS), default="calm")
    ap.add_argument("--out", required=True, help="prefix: writes <out>_mix.wav and <out>_bed.wav")
    ap.add_argument("--duck", type=float, default=0.55, help="0..1 how far the bed dips under speech")
    ap.add_argument("--bed-gain", type=float, default=0.85, help="overall bed level vs voice")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    prog, bpm, dens, bright, octv = MOODS[args.mood]
    voice = load_voice(args.voice)
    total_s = len(voice) / SR
    env = envelope(voice)
    sec_per_beat = 60.0 / bpm
    chord_dur = sec_per_beat * 4 * 2
    n_slots = int(np.ceil(total_s / chord_dur))
    bounds = [(i * chord_dur, min((i + 1) * chord_dur, total_s)) for i in range(n_slots)]
    arcs, climax_t = build_arc(env, bounds)
    bed, _ = render_bed_automated(prog, bpm, 2, total_s, dens, bright, arcs, seed=args.seed)
    # normalize bed to a bed-like RMS, then duck
    rms = np.sqrt(np.mean(bed ** 2)) + 1e-9
    bed *= (0.14 / rms) * args.bed_gain
    bed_ducked, gain = duck(bed, env, args.duck)
    stereo_bed = np.column_stack([bed, np.roll(bed, int(0.008 * SR)) * 0.92])
    stereo_ducked = np.column_stack([bed_ducked, np.roll(bed_ducked, int(0.008 * SR)) * 0.92])
    mix = np.column_stack([voice, voice]) * 0.9 + stereo_ducked
    write_wav(f"{args.out}_bed.wav", stereo_bed)
    write_wav(f"{args.out}_mix.wav", mix)
    print(f"voice {total_s:.1f}s | mood {args.mood} {'-'.join(prog)} @ {bpm}bpm | "
          f"climax at {climax_t:.1f}s | arc per chord slot: "
          f"{' '.join(f'{a:.2f}' for a in arcs)} | "
          f"duck depth {args.duck} (bed gain under speech dips to {gain.min():.2f})")
    print(f"wrote {args.out}_mix.wav and {args.out}_bed.wav")


if __name__ == "__main__":
    main()
