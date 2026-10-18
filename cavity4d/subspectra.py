"""Sub-spectra analysis for the Sunday bench experiments.

After the FFT, the physics is in the slicing. A single Rx coil cannot
spatially separate toroidal from poloidal components the way the all-sky
RM map did — so the signature lives in the HARMONIC STRUCTURE and how
it CHANGES between configurations.

Two sub-bands, two questions:

  DRIVEN BAND (0–1 kHz): the 60 Hz heater current is the poloidal drive,
  the Rx coil reads the toroidal response. Track the harmonic amplitudes
  at 60 Hz multiples across baseline → stator → pinch. Field shaping
  should change the RELATIVE harmonic amplitudes, not just total power.
  Breaking azimuthal symmetry (pinch) injects specific harmonic families.

  FUZZ BAND (1–20 kHz): the broadband region. Compare toroid vs straight
  wire (passive test). Any non-white structure here is the fuzz carrying
  mode content.

Cross-check: do the harmonic changes correlate with the comms result?
If the pinch unlocks 4800 baud AND reshapes the harmonic spectrum,
that's two independent measurements of the same field-shaping effect.

Usage:
  python3 subspectra.py rx_baseline_1200.wav rx_stator_1200.wav rx_pinch_1200.wav
  python3 subspectra.py --passive toroid_idle.wav wire_idle.wav
"""

import numpy as np
import wave
import sys
import json


def load_wav(path):
    with wave.open(path, "rb") as w:
        n_frames = w.getnframes()
        n_ch = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        raw = w.readframes(n_frames)
    dtype = {1: np.int8, 2: np.int16, 4: np.int32}[sampwidth]
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if n_ch > 1:
        samples = samples.reshape(-1, n_ch).mean(axis=1)
    # Normalize
    samples /= np.abs(samples).max() + 1e-12
    return samples, framerate


def welch_psd(samples, fs, seg=2**15):
    """Averaged power spectral density."""
    window = np.hanning(seg)
    step = seg // 2
    n_segs = (len(samples) - seg) // step
    psds = []
    for i in range(n_segs):
        v = samples[i*step:i*step+seg] * window
        psds.append(np.abs(np.fft.rfft(v))**2)
    psd = np.mean(psds, axis=0)
    freqs = np.fft.rfftfreq(seg, 1/fs)
    return freqs, psd


def harmonic_amplitudes(freqs, psd, fundamental=60.0, n_harmonics=12,
                        bandwidth=3.0):
    """Peak power in a narrow band around each harmonic of fundamental."""
    amps = {}
    for n in range(1, n_harmonics + 1):
        f_target = n * fundamental
        mask = np.abs(freqs - f_target) < bandwidth
        if np.any(mask):
            amps[n] = float(np.max(psd[mask]))
        else:
            amps[n] = 0.0
    return amps


def analyze_driven(path):
    """Driven-band analysis: harmonic fingerprint of the coupling."""
    samples, fs = load_wav(path)
    freqs, psd = welch_psd(samples, fs)
    # Driven sub-band: 0–1 kHz
    harmonics = harmonic_amplitudes(freqs, psd, fundamental=60.0,
                                    n_harmonics=16)
    # Normalize to fundamental for relative comparison
    f1 = harmonics.get(1, 1e-12)
    rel = {n: a/f1 for n, a in harmonics.items()}
    # Even/odd energy ratio — symmetry probe.
    # Azimuthally symmetric toroidal coupling favors odd harmonics of the
    # drive; breaking symmetry (pinch) injects even-harmonic content.
    even_e = sum(a for n, a in harmonics.items() if n % 2 == 0)
    odd_e = sum(a for n, a in harmonics.items() if n % 2 == 1)
    return {
        "file": path,
        "fs": fs,
        "harmonics_relative": {str(k): round(v, 4) for k, v in rel.items()},
        "even_odd_ratio": round(even_e / (odd_e + 1e-12), 4),
        "total_driven_power": round(float(np.sum(list(harmonics.values()))), 6),
    }


def analyze_fuzz(path_a, path_b, label_a="toroid", label_b="wire"):
    """Fuzz-band analysis: is the broadband noise white or structured?"""
    results = {}
    for path, label in [(path_a, label_a), (path_b, label_b)]:
        samples, fs = load_wav(path)
        freqs, psd = welch_psd(samples, fs)
        # Fuzz sub-band: 1 kHz to Nyquist (or 20 kHz cap)
        mask = (freqs > 1000) & (freqs < min(20000, fs/2))
        fz, pz = freqs[mask], psd[mask]
        # Whiteness test: flat spectrum → low variance of log-power
        log_p = np.log10(pz + 1e-18)
        # Peak hunt: bins > 3σ above local median
        from scipy import signal as _sig  # may not exist; fallback below
        results[label] = {"n_bins": int(mask.sum())}
    return results


def analyze_fuzz_simple(path_a, path_b, label_a="toroid", label_b="wire"):
    """Fuzz-band without scipy: median-based peak detection."""
    out = {}
    for path, label in [(path_a, label_a), (path_b, label_b)]:
        samples, fs = load_wav(path)
        freqs, psd = welch_psd(samples, fs)
        mask = (freqs > 1000) & (freqs < min(20000, fs/2))
        fz, pz = freqs[mask], psd[mask]
        log_p = np.log10(pz + 1e-18)
        med = np.median(log_p)
        std = np.std(log_p)
        # Peaks: > med + 3σ
        peak_mask = log_p > med + 3*std
        peak_freqs = fz[peak_mask]
        # Check harmonic relation among peaks (are they f, 2f, 3f...?)
        harmonic_score = 0
        if len(peak_freqs) >= 2:
            f0 = peak_freqs[0]
            for pf in peak_freqs[1:]:
                ratio = pf / f0
                nearest_int = round(ratio)
                if nearest_int >= 1 and abs(ratio - nearest_int) < 0.05:
                    harmonic_score += 1
        out[label] = {
            "file": path,
            "log_power_median": round(float(med), 3),
            "log_power_std": round(float(std), 3),
            "n_peaks_3sigma": int(peak_mask.sum()),
            "peak_freqs_hz": [round(float(f), 1) for f in peak_freqs[:20]],
            "harmonic_peak_score": int(harmonic_score),
        }
    # The verdict
    a, b = out[label_a], out[label_b]
    out["verdict"] = (
        f"{label_a}: {a['n_peaks_3sigma']} peaks (harmonic score "
        f"{a['harmonic_peak_score']}) vs {label_b}: {b['n_peaks_3sigma']} "
        f"peaks (harmonic score {b['harmonic_peak_score']}). "
        + ("STRUCTURE in toroid not in wire — geometry imprints on fuzz."
           if a['n_peaks_3sigma'] > b['n_peaks_3sigma'] + 2
              and a['harmonic_peak_score'] > 0
           else "No significant difference — fuzz is white at this sensitivity.")
    )
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)
    passive = "--passive" in args
    files = [a for a in args if not a.startswith("--")]

    if passive and len(files) == 2:
        result = analyze_fuzz_simple(files[0], files[1])
        print(json.dumps(result, indent=2))
    elif not passive:
        # Driven: compare harmonic fingerprints across configs
        results = [analyze_driven(f) for f in files]
        print(json.dumps({"driven_analysis": results}, indent=2))
        if len(results) >= 2:
            print("\n=== Even/Odd Ratio Across Configs ===")
            print("(Rising even-harmonic content = symmetry breaking by field shaping)")
            for r in results:
                print(f"  {r['file']}: even/odd = {r['even_odd_ratio']}")
    else:
        print("Usage: subspectra.py [--passive] file1.wav [file2.wav ...]")


if __name__ == "__main__":
    main()
