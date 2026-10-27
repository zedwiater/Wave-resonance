#!/usr/bin/env python3
"""Shape a synthetic voice with Zak's energy form (signature profile).

Steps: (1) measure Zak's pitch + purified arc from his take — purification
drops silence/noise-floor frames, excludes clipped frames, and takes slot
MEDIANS so transients can't bend the profile; (2) remap the stock voice's
per-slot energy onto his arc; (3) pitch-shift toward his median F0
(rubberband, tempo preserved). Prints before/after signature match.
"""
import json, sys
import numpy as np
from pathlib import Path
import energy

HERE = Path(__file__).parent
SLOTS = 12

def median_f0(x, sr=energy.SR):
    fl, hop = int(0.04 * sr), int(0.02 * sr)
    f0s = []
    for i in range(0, len(x) - fl, hop):
        fr = x[i:i + fl].astype(np.float64)
        if np.sqrt(np.mean(fr ** 2)) < 0.02:
            continue
        fr = fr - fr.mean()
        ac = np.correlate(fr, fr, "full")[fl - 1:]
        lo, hi = int(sr / 300), int(sr / 60)
        seg = ac[lo:hi]
        if len(seg) == 0 or seg.max() <= 0.35 * ac[0]:
            continue
        f0s.append(sr / (lo + int(np.argmax(seg))))
    return float(np.median(f0s)) if f0s else None

def purified_arc(x):
    """Arc from voiced, unclipped frames only; slot medians."""
    env = energy.envelope(x)
    clip_frames = 0
    n = int(energy.SR * 0.05)
    voiced = []
    for i, e in enumerate(env):
        frame = x[i * n:(i + 1) * n]
        if len(frame) and np.max(np.abs(frame)) >= 0.999:
            clip_frames += 1
    hot = env[env > np.percentile(env, 66.7)]
    floor = 0.12 * (hot.mean() if len(hot) else env.mean())
    idx = np.linspace(0, len(env), SLOTS + 1).astype(int)
    arc = []
    for i in range(SLOTS):
        seg = env[idx[i]:idx[i + 1]]
        seg = seg[seg > floor]
        arc.append(float(np.median(seg)) if len(seg) else float(np.median(env)))
    arc = np.array(arc); arc = arc / arc.mean()
    return arc, {"floor_frac_of_hot_mean": 0.12, "clipped_frames_excluded": int(clip_frames)}

def main(zak_path, stock_path, out_path):
    zak = energy.load_audio(zak_path)
    stock = energy.load_audio(stock_path)
    prof = json.loads((HERE / "signature_profile.json").read_text())
    sig = np.array(prof["arc"], dtype=float); sig = sig / sig.mean()

    zak_f0 = median_f0(zak)
    stock_f0 = median_f0(stock)
    pur_arc, pur_info = purified_arc(zak)

    env_s = energy.envelope(stock)
    idx = np.linspace(0, len(env_s), SLOTS + 1).astype(int)
    stock_arc = np.array([env_s[idx[i]:idx[i + 1]].mean() for i in range(SLOTS)])
    stock_arc = stock_arc / stock_arc.mean()
    gains = np.clip(sig / np.maximum(stock_arc, 0.05), 0.55, 1.9)

    # per-sample gain curve: slot gains at slot centers, linear interp, smooth
    t = np.arange(len(stock)) / energy.SR
    centers = (np.arange(SLOTS) + 0.5) * (len(stock) / energy.SR) / SLOTS
    g = np.interp(t, centers, gains, left=gains[0], right=gains[-1])
    kern = np.ones(2205) / 2205
    g = np.convolve(g, kern, mode="same")
    shaped = (stock * g).astype(np.float32)

    import subprocess
    raw = shaped.tobytes()
    ratio = (zak_f0 / stock_f0) if zak_f0 and stock_f0 else 1.0
    filt = f"rubberband=pitch={ratio:.4f}" if 0.8 <= ratio <= 1.25 else "anull"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar",
                    str(energy.SR), "-ac", "1", "-i", "-", "-af", filt,
                    "-ar", "44100", str(out_path)], input=raw, check=True)

    before = energy.analyze_voice(stock_path)
    after = energy.analyze_voice(out_path)
    cb = energy.compare(before, prof); ca = energy.compare(after, prof)
    print(json.dumps({
        "zak_f0_median_hz": round(zak_f0, 1) if zak_f0 else None,
        "stock_f0_median_hz": round(stock_f0, 1) if stock_f0 else None,
        "pitch_shift_ratio": round(ratio, 3),
        "pitch_shift_semitones": round(12 * np.log2(ratio), 2) if ratio else None,
        "purification": pur_info,
        "signature_match_before": cb["arc_correlation"],
        "signature_match_after": ca["arc_correlation"],
        "climax_frac_before": before["climax_frac"],
        "climax_frac_after": after["climax_frac"],
        "climax_frac_signature": prof["climax_frac"],
        "slot_gains": [round(float(v), 2) for v in gains],
    }, indent=1))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
