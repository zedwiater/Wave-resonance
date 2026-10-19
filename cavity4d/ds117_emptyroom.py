"""ds117 emptyroom control — is the 51.6 Hz gamma peak environmental?
Runs the identical spectral pipeline (Welch PSD, same gamma Q estimator)
on emptyroom noise recordings. If the sharp ~50 Hz peak appears here too,
it is mains/ambient, not neural.
"""
import numpy as np
from pathlib import Path

DATA = Path("/mnt/storage/neurodata/ds000117")
OUT = Path("/mnt/storage/neurodata/ds117-emptyroom-results.txt")


def gamma_q(freqs, mean_psd):
    gmask = (freqs >= 30) & (freqs <= 80)
    gf, gp = freqs[gmask], mean_psd[gmask]
    peak_idx = int(np.argmax(gp))
    if peak_idx == 0 or peak_idx == len(gp) - 1:
        return "n/a (band-edge max)", gf[peak_idx]
    f0 = gf[peak_idx]
    half = gp[peak_idx] / 2
    above = np.where(gp >= half)[0]
    l, r = peak_idx, peak_idx
    while l > 0 and l - 1 in above:
        l -= 1
    while r < len(gp) - 1 and r + 1 in above:
        r += 1
    fwhm = gf[r] - gf[l]
    q = f0 / fwhm if fwhm > 0 else float("nan")
    return f"{q:.2f} @ {f0:.1f}Hz", f0


def main():
    import mne

    lines = []
    files = sorted((DATA / "sub-emptyroom").glob("ses-*/meg/*_task-noise_meg.fif"))
    print(f"Found {len(files)} emptyroom recordings", flush=True)
    for f in files:
        raw = mne.io.read_raw_fif(f, preload=True, verbose=False)
        picks_mag = mne.pick_types(raw.info, meg="mag", exclude="bads")
        # 1.0 s pseudo-epochs: same window length as faces/scrambled epochs
        epochs = mne.make_fixed_length_epochs(raw, duration=1.0, preload=True,
                                              verbose=False)
        edata = epochs.get_data(picks=picks_mag)
        n_fft = min(256, edata.shape[-1])
        psd, freqs = mne.time_frequency.psd_array_welch(
            edata, sfreq=raw.info["sfreq"], fmin=1, fmax=100,
            n_fft=n_fft, n_per_seg=n_fft, verbose=False)
        mean_psd = psd.mean(axis=(0, 1))
        q_str, f0 = gamma_q(freqs, mean_psd)
        # targeted line-noise test: 50 Hz bin vs local median (40-60 Hz)
        band = (freqs >= 40) & (freqs <= 60)
        bf, bp = freqs[band], mean_psd[band]
        i50 = int(np.argmin(np.abs(bf - 50.0)))
        ratio = bp[i50] / np.median(np.delete(bp, i50))
        line = (f"{f.parent.parent.name}: n_ep={len(epochs)} "
                f"Q={q_str} P50/local-median={ratio:.1f}x")
        print(line, flush=True)
        lines.append(line)

    OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
