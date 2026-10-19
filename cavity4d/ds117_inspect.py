"""ds117 spectral inspection — sub-01, faces vs scrambled.
Runs on the PC against /mnt/storage/neurodata/ds000117.
Outputs: gamma Q-factor, ITPC, multipole signature per condition.
"""
import numpy as np
from pathlib import Path

DATA = Path("/mnt/storage/neurodata/ds000117")
SUB = "sub-01"
OUT = Path("/mnt/storage/neurodata/ds117-sub01-results.txt")


def main():
    import mne

    meg_dir = DATA / SUB / "ses-meg" / "meg"
    runs = sorted(meg_dir.glob(f"{SUB}_ses-meg_task-facerecognition_run-*_meg.fif"))
    print(f"Found {len(runs)} runs", flush=True)

    # Wakeman&Henson codes — group simply: face-like vs scrambled
    face_ids = [5, 6, 7, 13, 14, 15]
    scram_ids = [17, 18, 19]
    # MNE Epochs needs int event_id values: epoch per code, merge after
    flat_id = {f"faces_{c}": c for c in face_ids}
    flat_id.update({f"scram_{c}": c for c in scram_ids})

    # Load each run, epoch separately (head positions differ between runs —
    # concatenate_raws refuses), then combine epochs
    all_epochs = []
    raws_ref = None
    for f in runs:
        r = mne.io.read_raw_fif(f, preload=True, verbose=False)
        if raws_ref is None:
            raws_ref = r
            print(f"sfreq={r.info['sfreq']:.1f}", flush=True)
        ev = mne.find_events(r, stim_channel="STI101", verbose=False)
        ep = mne.Epochs(r, ev, flat_id, tmin=-0.2, tmax=0.8,
                        baseline=(-0.2, 0), preload=True, verbose=False)
        ep = mne.epochs.combine_event_ids(ep, [f"faces_{c}" for c in face_ids],
                                   {"faces": 1}, copy=False)
        ep = mne.epochs.combine_event_ids(ep, [f"scram_{c}" for c in scram_ids],
                                   {"scrambled": 2}, copy=False)
        all_epochs.append(ep)
        print(f"  {f.name}: {len(ep['faces'])} faces, {len(ep['scrambled'])} scrambled", flush=True)
    epochs = mne.concatenate_epochs(all_epochs, on_mismatch="ignore", verbose=False)
    raw = raws_ref  # reference for sfreq/picks
    picks_mag = mne.pick_types(raw.info, meg="mag", exclude="bads")
    print(f"n_mag={len(picks_mag)}, total epochs={len(epochs)}", flush=True)

    lines = []
    for cond in ["faces", "scrambled"]:
        ep = epochs[cond]
        if len(ep) == 0:
            lines.append(f"{cond}: NO EPOCHS")
            continue
        edata = ep.get_data(picks=picks_mag)
        n_times = edata.shape[-1]
        n_fft = min(256, n_times)
        psd, freqs = mne.time_frequency.psd_array_welch(
            edata, sfreq=raw.info["sfreq"], fmin=1, fmax=100,
            n_fft=n_fft, n_per_seg=n_fft, verbose=False)
        mean_psd = psd.mean(axis=(0, 1))

        gmask = (freqs >= 30) & (freqs <= 80)
        gf, gp = freqs[gmask], mean_psd[gmask]
        peak_idx = int(np.argmax(gp))
        if peak_idx == 0 or peak_idx == len(gp) - 1:
            q_str = "n/a (band-edge max)"
        else:
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
            q_str = f"{q:.2f} @ {f0:.1f}Hz"

        freqs_w = np.arange(30, 81, 5)
        _, itc = mne.time_frequency.tfr_morlet(
            ep, freqs=freqs_w, n_cycles=freqs_w / 4,
            picks=picks_mag[:20], return_itc=True, verbose=False)
        mean_itc = float(itc.data.mean())

        # Multipole: gamma-band sensor covariance SVD
        rg = raw.copy().filter(30, 80, picks=picks_mag, verbose=False)
        cov = np.cov(rg.get_data(picks=picks_mag))
        sv = np.linalg.svd(cov, compute_uv=False)
        sv /= sv.sum()
        n90 = int(np.searchsorted(np.cumsum(sv), 0.90)) + 1

        line = (f"{cond}: n={len(ep)} Q={q_str} "
                f"ITPC={mean_itc:.4f} modes90={n90}")
        print(line, flush=True)
        lines.append(line)

    OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
