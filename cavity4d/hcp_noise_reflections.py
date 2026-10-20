"""HCP noise scans: carrier harmonic structure without a subject.

Decisive control for the 120 Hz doubling: if the empty room shows the same
120/60 ratio as the task data, the doubling is room/instrument, not the brain.
Output: /mnt/storage/neurodata/hcp-noise-reflections.txt
"""
import mne, numpy as np
from pathlib import Path

base = Path("/mnt/storage/neurodata/hcp-nback/106521")
out = Path("/mnt/storage/neurodata/hcp-noise-reflections.txt")
lines = []
L = lines.append

def local_median(psd, freqs, f0, halfwin=10.0, exclude=2.0):
    m = (np.abs(freqs - f0) <= halfwin) & (np.abs(freqs - f0) > exclude)
    vals = psd[m]
    return float(np.median(vals)) if len(vals) else float("nan")

def peak_ratio(psd, freqs, f0, tol=0.75):
    m = np.abs(freqs - f0) <= tol
    med = local_median(psd, freqs, f0)
    return float(np.max(psd[m]) / med) if (len(psd[m]) and med > 0) else float("nan")

def main():
    L("carrier harmonic structure — HCP noise scans (no subject)")
    for nm, d in (("1-Rnoise (room noise)", "1-Rnoise"), ("2-Pnoise (phantom noise)", "2-Pnoise")):
        rdir = base / d / "4D"
        raw = mne.io.read_raw_bti(pdf_fname=str(rdir / "c,rfDC"), head_shape_fname=None,
                                  preload=True, verbose=False)
        sf = raw.info["sfreq"]
        picks = mne.pick_types(raw.info, meg="mag")
        p0, f0 = mne.time_frequency.psd_array_welch(
            raw.get_data(picks=picks), sfreq=sf, fmin=1, fmax=200,
            n_fft=int(sf * 4), verbose=False)
        psd = p0.mean(axis=0)
        L(f"\n== {nm} (sfreq={sf:.1f} Hz) ==")
        for f, lbl in ((60, "carrier 60"), (120, "2nd harmonic 120"),
                       (180, "3rd harmonic 180"), (30, "subharmonic 30")):
            L(f"  {lbl}: {peak_ratio(psd, f0, f):.2f}x local median")
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())

if __name__ == "__main__":
    main()
