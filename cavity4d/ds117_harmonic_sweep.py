"""ds117 harmonic/subharmonic reflection sweep — sub-01, faces vs scrambled.

The fMRI analogy: slow hemodynamic windows reflect fast neural dynamics
through nonlinear down-transduction. Subharmonics (f/2, f/3, ...) are its
spectral fingerprint. This sweep hunts them: fine frequency resolution
(~1 Hz), full 1-120 Hz band, peak detection + harmonic-ladder test,
after 50/100 Hz notch.
"""
import numpy as np
from pathlib import Path

DATA = Path("/mnt/storage/neurodata/ds000117")
SUB = "sub-01"
OUT = Path("/mnt/storage/neurodata/ds117-harmonic-sweep.txt")

LADDER = [1/4, 1/3, 1/2, 2/3, 1.0, 4/3, 3/2, 2.0, 3.0]


def main():
    import mne
    from scipy.signal import find_peaks

    meg_dir = DATA / SUB / "ses-meg" / "meg"
    runs = sorted(meg_dir.glob(f"{SUB}_ses-meg_task-facerecognition_run-*_meg.fif"))
    print(f"Found {len(runs)} runs", flush=True)

    face_ids = [5, 6, 7, 13, 14, 15]
    scram_ids = [17, 18, 19]
    flat_id = {f"faces_{c}": c for c in face_ids}
    flat_id.update({f"scram_{c}": c for c in scram_ids})

    all_epochs = []
    for f in runs:
        r = mne.io.read_raw_fif(f, preload=True, verbose=False)
        r.notch_filter(freqs=[50, 100], verbose=False)
        ev = mne.find_events(r, stim_channel="STI101", verbose=False)
        ep = mne.Epochs(r, ev, flat_id, tmin=-0.2, tmax=0.8,
                        baseline=(-0.2, 0), preload=True, verbose=False)
        ep = mne.epochs.combine_event_ids(ep, [f"faces_{c}" for c in face_ids],
                                          {"faces": 1}, copy=False)
        ep = mne.epochs.combine_event_ids(ep, [f"scram_{c}" for c in scram_ids],
                                          {"scrambled": 2}, copy=False)
        all_epochs.append(ep)
    epochs = mne.concatenate_epochs(all_epochs, on_mismatch="ignore", verbose=False)
    raw0 = mne.io.read_raw_fif(runs[0], verbose=False)
    picks_mag = mne.pick_types(raw0.info, meg="mag", exclude="bads")
    print(f"n_mag={len(picks_mag)}, total epochs={len(epochs)}", flush=True)

    lines = []
    for cond in ["faces", "scrambled"]:
        ep = epochs[cond]
        edata = ep.get_data(picks=picks_mag)
        n_fft = edata.shape[-1]  # full 1.0 s window -> ~1 Hz resolution
        psd, freqs = mne.time_frequency.psd_array_welch(
            edata, sfreq=raw0.info["sfreq"], fmin=1, fmax=120,
            n_fft=n_fft, n_per_seg=n_fft, verbose=False)
        mean_psd = psd.mean(axis=(0, 1))

        peaks, _ = find_peaks(mean_psd, prominence=np.median(mean_psd), distance=2)
        pf, pp = freqs[peaks], mean_psd[peaks]
        order = np.argsort(pp)[::-1][:8]
        lines.append(f"{cond}: n={len(ep)} top peaks (Hz): " +
                     ", ".join(f"{pf[i]:.1f}" for i in order))

        f0 = pf[order[0]]
        tol = 1.5
        hits = []
        for m in LADDER:
            target = f0 * m
            if 1 <= target <= 120:
                j = int(np.argmin(np.abs(pf - target)))
                if abs(pf[j] - target) <= tol:
                    hits.append(f"{m:g}x={pf[j]:.1f}Hz")
        lines.append(f"  ladder around {f0:.1f}Hz: " +
                     (", ".join(hits) if hits else "no ladder matches"))

        for t in [25.0, 75.0]:
            j = int(np.argmin(np.abs(freqs - t)))
            local = np.median(mean_psd[max(0, j-3):j+4])
            lines.append(f"  P{t:.0f}/local-median={mean_psd[j]/local:.1f}x")

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    print(f"Wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
