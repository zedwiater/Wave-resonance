#!/usr/bin/env python3
"""Energy Monitor core: measure the energy shape of voice and text.

Voice: 50 ms RMS envelope (same math as score_voiceover.py), arc fit,
signature comparison. Text: per-sentence energy PROXY (labelled as such).
Outputs are physical readouts: level, trend, peak position, roughness.
"""
import json, math, re, subprocess, sys
import numpy as np

SR = 22050

# ---------- voice ----------
def load_audio(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
         "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)

def envelope(x, win_ms=50.0):
    n = max(1, int(SR * win_ms / 1000.0))
    m = (len(x) // n) * n
    return np.sqrt(np.mean(x[:m].reshape(-1, n) ** 2, axis=1) + 1e-12)

def arc_of(env, slots=12):
    idx = np.linspace(0, len(env), slots + 1).astype(int)
    arc = np.array([env[idx[i]:idx[i + 1]].mean() if idx[i + 1] > idx[i] else env[idx[i]]
                    for i in range(slots)])
    lo, hi = arc.min(), arc.max()
    return (0.15 + 0.85 * (arc - lo) / max(hi - lo, 1e-9)).round(3).tolist()

def climax_frac(env):
    thr = np.percentile(env, 66.7)
    hot = np.maximum(env - thr, 0)
    return float((hot * np.arange(len(env))).sum() / max(hot.sum(), 1e-9) / len(env))

def roughness(env):
    e = env / max(env.mean(), 1e-9)
    return float(np.mean(np.abs(np.diff(e))))

def analyze_voice(path, slots=12):
    x = load_audio(path)
    env = envelope(x)
    return {
        "kind": "voice", "source": str(path),
        "duration_s": round(len(x) / SR, 1),
        "arc": arc_of(env, slots),
        "climax_frac": round(climax_frac(env), 3),
        "climax_s": round(climax_frac(env) * len(x) / SR, 1),
        "level": round(float(np.clip(env.mean() * 6, 0, 1)), 3),
        "roughness": round(roughness(env), 3),
    }

# ---------- text (PROXY — labelled) ----------
INTENSIFIERS = set("never always everything nothing nobody everybody must "
                   "exactly literally really truly actually stop look "
                   "listen now here free own yours mine".split())

def sentence_energy(s):
    words = s.split()
    if not words:
        return 0.2
    caps = sum(1 for w in words if w.isupper() and len(w) > 1) / len(words)
    inten = sum(1 for w in words if w.strip(".,!?—-").lower() in INTENSIFIERS) / len(words)
    punct = (0.25 * s.count("!") + 0.12 * s.count("?") + 0.05 * s.count("—")) 
    punch = 0.15 if len(words) <= 6 else 0.0          # short sentence = jab
    body = min(len(words) / 40.0, 0.3)                  # long sentence = swell
    return float(np.clip(0.25 + body + punch + punct + 1.2 * caps + 1.5 * inten, 0.05, 1.0))

def analyze_text(path, slots=12):
    text = open(path).read()
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]
    if not sents:
        return {"kind": "text", "source": str(path), "error": "no sentences"}
    e = np.array([sentence_energy(s) for s in sents])
    es = np.convolve(e, np.ones(3) / 3, mode="same")   # the smoother
    idx = np.linspace(0, len(es), slots + 1).astype(int)
    arc = np.array([es[idx[i]:idx[i + 1]].mean() if idx[i + 1] > idx[i] else es[idx[i]]
                    for i in range(slots)])
    lo, hi = arc.min(), arc.max()
    arc = (0.15 + 0.85 * (arc - lo) / max(hi - lo, 1e-9)).round(3).tolist()
    hot = np.maximum(es - np.percentile(es, 66.7), 0)
    cf = float((hot * np.arange(len(es))).sum() / max(hot.sum(), 1e-9) / len(es))
    return {
        "kind": "text-proxy", "source": str(path), "sentences": len(sents),
        "arc": arc, "climax_frac": round(cf, 3),
        "level": round(float(np.clip(es.mean(), 0, 1)), 3),
        "roughness": round(float(np.mean(np.abs(np.diff(e)))), 3),
    }

# ---------- compare + stamp ----------
def compare(a, profile):
    x = np.array(a["arc"], dtype=float); y = np.array(profile["arc"], dtype=float)
    n = min(len(x), len(y))
    corr = float(np.corrcoef(x[:n], y[:n])[0, 1]) if n > 2 else 0.0
    return {"arc_correlation": round(corr, 3),
            "climax_shift_frac": round(a["climax_frac"] - profile["climax_frac"], 3)}

def stamp(a, cmp=None):
    lvl = a["level"]
    level_w = "high" if lvl > 0.62 else "mid" if lvl > 0.38 else "low"
    arc = a["arc"]; third = max(1, len(arc) // 3)
    trend = ("rising" if arc[-third:] and np.mean(arc[-third:]) > np.mean(arc[:third]) + 0.08
             else "falling" if np.mean(arc[:third]) > np.mean(arc[-third:]) + 0.08
             else "peaked-mid" if int(np.argmax(arc)) in range(third, 2 * third)
             else "level")
    peak_w = ("early" if a["climax_frac"] < 0.38 else "mid" if a["climax_frac"] < 0.62
              else "late")
    s = f"energy {level_w} · {trend} · peak {peak_w} ({a['climax_frac']:.0%} through)"
    if cmp:
        s += f" · signature match {cmp['arc_correlation']:.2f}"
    return s
