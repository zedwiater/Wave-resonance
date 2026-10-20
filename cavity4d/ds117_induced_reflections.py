"""ds000117 induced frequency reflections: 50 Hz carrier harmonics, subharmonics, sidebands.

Same protocol as hcp_induced_reflections.py, UK grid (50 Hz carrier).
NO notch filter — the carrier is the signal here.
Conditions: faces (codes 5,6,7,13,14,15) vs scrambled (17,18,19), sub-01, 6 runs.
Sidebands: 50 +/- neural (10, 7, 15, 20 Hz = measured peaks).
Output: /mnt/storage/neurodata/ds117-induced-reflections.txt
"""
import mne, numpy as np
from pathlib import Path

DATA = Path("/mnt/storage/neurodata/ds000117")
SUB = "sub-01"
out = Path("/mnt/storage/neurodata/ds117-induced-reflections.txt")
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
    L("induced reflections — ds000117 sub-01 (UK 50 Hz grid carrier), no notch")
    meg_dir = DATA / SUB / "ses-meg" / "meg"
    runs = sorted(meg_dir.glob(f"{SUB}_ses-meg_task-facerecognition_run-*_meg.fif"))
    face_ids = [5, 6, 7, 13, 14, 15]
    scram_ids = [17, 18, 19]
    flat_id = {f"faces_{c}": c for c in face_ids}
    flat_id.update({f"scram_{c}": c for c in scram_ids})
    all_psd = {"faces": [], "scrambled": []}
    freqs = None
    for f in runs:
        r = mne.io.read_raw_fif(str(f), preload=True, verbose=False)
        picks = mne.pick_types(r.info, meg="mag", exclude="bads")
        ev = mne.find_events(r, stim_channel="STI101", verbose=False)
        ep = mne.Epochs(r, ev, flat_id, tmin=0, tmax=1.0, baseline=None,
                        picks=picks, preload=True, verbose=False)
        ep = mne.epochs.combine_event_ids(ep, [f"faces_{c}" for c in face_ids],
                                          {"faces": 1}, copy=False)
        ep = mne.epochs.combine_event_ids(ep, [f"scram_{c}" for c in scram_ids],
                                          {"scrambled": 2}, copy=False)
        for nm in ("faces", "scrambled"):
            e = ep[nm]
            if len(e) == 0:
                continue
            psd, freqs = e.compute_psd(fmin=1, fmax=200, verbose=False).average().get_data(
                return_freqs=True)
            all_psd[nm].append(psd.mean(axis=0))

    neur = {"10": 10.0, "7": 7.0, "15": 15.0, "20": 20.0}
    for cname in ("faces", "scrambled"):
        psd = np.mean(all_psd[cname], axis=0)
        L(f"\n== {cname} (n={len(all_psd[cname])} runs averaged) ==")
        for f0, lbl in ((50, "carrier 50"), (100, "2nd harmonic 100"),
                        (150, "3rd harmonic 150")):
            L(f"  {lbl}: {peak_ratio(psd, freqs, f0):.2f}x local median")
        for f0, lbl in ((25, "subharmonic 25 (f/2)"), (16.7, "subharmonic 16.7 (f/3)")):
            L(f"  {lbl}: {peak_ratio(psd, freqs, f0):.2f}x local median")
        for nn, fn in neur.items():
            for side, fs in (("lo", 50 - fn), ("hi", 50 + fn)):
                L(f"  sideband 50{'-' if side=='lo' else '+'}{fn}Hz ({fs:.1f}Hz): {peak_ratio(psd, freqs, fs):.2f}x")
            for side, fs in (("lo", 100 - fn), ("hi", 100 + fn)):
                L(f"  sideband 100{'-' if side=='lo' else '+'}{fn}Hz ({fs:.1f}Hz): {peak_ratio(psd, freqs, fs):.2f}x")

    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())

if __name__ == "__main__":
    main()
