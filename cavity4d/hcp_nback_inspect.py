"""hcp n-back spectral inspect — subject 106521, 0-back vs 2-back (load contrast).

Pipeline:
1. Load both Wrkmem runs (4D/BTi), notch 60/120 Hz (US mains — St. Louis).
2. Align E-Prime clock to MEG clock EMPIRICALLY: cross-correlate the E-Prime
   SyncSlide onset spike train against each MEG stim channel's trigger train;
   take the lag with the best match. Report the match quality.
3. Label trials 0-back / 2-back from E-Prime BlockType; epoch 0-2.5 s.
4. Per condition: Welch PSD (fine bins), gamma Q, ITPC, harmonic ladder,
   60 Hz subharmonic check (30/90 Hz).
"""
import numpy as np
from pathlib import Path
import csv

DATA = Path("/mnt/storage/neurodata/hcp-nback/106521")
OUT = Path("/mnt/storage/neurodata/hcp-nback-results.txt")
LADDER = [1/4, 1/3, 1/2, 2/3, 1.0, 4/3, 3/2, 2.0, 3.0]


def load_eprime(tab_path):
    with open(tab_path) as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    # trial rows: those with a Stim.OnsetTime and a 0-Back/2-Back BlockType
    trials = []
    for r in rows:
        onset = r.get("Stim.OnsetTime", "").strip()
        bt = r.get("BlockType", "").strip()
        if onset and onset.lstrip("-").isdigit() and bt in ("0-Back", "2-Back"):
            trials.append({"onset_ms": int(onset), "block": bt})
    return trials


def align(trials_ms, trig_times_s, sfreq, label):
    """Cross-correlate E-Prime onset train vs MEG trigger train. Returns lag (s)."""
    t_ep = np.array([t["onset_ms"] for t in trials_ms]) / 1000.0
    t_meg = np.array(trig_times_s)
    # search lags: MEG = E-Prime + lag, lag in [-120, 120] s, 0.5 s steps
    best, best_lag, best_n = -1, None, 0
    for lag in np.arange(-120, 120.5, 0.5):
        shifted = t_ep + lag
        # count coincidences within 1.0 s
        n = 0
        j = 0
        tm = np.sort(t_meg)
        for s in np.sort(shifted):
            while j < len(tm) and tm[j] < s - 1.0:
                j += 1
            if j < len(tm) and abs(tm[j] - s) <= 1.0:
                n += 1
        if n > best_n:
            best_n, best_lag = n, lag
    return best_lag, best_n, len(t_ep)


def gamma_q(freqs, mean_psd):
    gmask = (freqs >= 30) & (freqs <= 80)
    gf, gp = freqs[gmask], mean_psd[gmask]
    peak_idx = int(np.argmax(gp))
    if peak_idx == 0 or peak_idx == len(gp) - 1:
        return "n/a (band-edge max)"
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
    return f"{q:.2f} @ {f0:.1f}Hz"


def main():
    import mne
    from scipy.signal import find_peaks

    lines = []
    all_ep = []
    for run, rundir in [("run1", "6-Wrkmem"), ("run2", "7-Wrkmem")]:
        d = DATA / rundir
        raw = mne.io.read_raw_bti(
            pdf_fname=str(d / "4D" / "c,rfDC"), head_shape_fname=None,
            preload=True, verbose=False)
        raw.notch_filter(freqs=[60, 120], verbose=False)  # US mains
        sf = raw.info["sfreq"]
        trials = load_eprime(d / "EPRIME" / f"106521_MEG_Wrkmem_{run}.tab")
        print(f"{run}: {len(trials)} eprime trials", flush=True)

        # try both stim channels for alignment
        best = None
        for stim in ["STI 013", "STI 014"]:
            try:
                ev = mne.find_events(raw, stim_channel=stim, verbose=False)
            except Exception:
                continue
            lag, n_match, n_ep = align(trials, ev[:, 0] / sf, sf, stim)
            print(f"  {stim}: lag={lag}s matched {n_match}/{n_ep}", flush=True)
            if best is None or n_match > best[1]:
                best = (stim, n_match, lag)
        stim, n_match, lag = best
        frac = n_match / len(trials)
        lines.append(f"{run}: align via {stim}, lag={lag:.1f}s, "
                     f"matched {n_match}/{len(trials)} ({frac:.0%})")
        if frac < 0.5:
            lines.append(f"  ALIGNMENT WEAK — skipping run")
            continue

        events = []
        for t in trials:
            bt = t["block"]
            if bt not in ("0-Back", "2-Back"):
                continue
            code = 1 if bt == "0-Back" else 2
            events.append([int((t["onset_ms"] / 1000.0 + lag) * sf), 0, code])
        if len(events) == 0:
            lines.append(f"{run}: no trials parsed — skipping run")
            continue
        events = np.array(events)
        # keep events inside the recording
        events = events[(events[:, 0] > 0) & (events[:, 0] < len(raw.times))]
        ep = mne.Epochs(raw, events, {"0back": 1, "2back": 2},
                        tmin=0, tmax=2.5, baseline=None,
                        preload=True, verbose=False)
        all_ep.append(ep)
        print(f"  epochs: 0back={len(ep['0back'])}, 2back={len(ep['2back'])}",
              flush=True)

    if not all_ep:
        lines.append("NO RUNS ALIGNED — aborting")
        OUT.write_text("\n".join(lines) + "\n")
        print("\n".join(lines), flush=True)
        return

    epochs = mne.concatenate_epochs(all_ep, on_mismatch="ignore", verbose=False)
    picks_mag = mne.pick_types(epochs.info, meg="mag", exclude="bads")
    print(f"total epochs={len(epochs)}, n_mag={len(picks_mag)}", flush=True)

    for cond in ["0back", "2back"]:
        ep = epochs[cond]
        edata = ep.get_data(picks=picks_mag)
        n_fft = edata.shape[-1]
        psd, freqs = mne.time_frequency.psd_array_welch(
            edata, sfreq=epochs.info["sfreq"], fmin=1, fmax=120,
            n_fft=n_fft, n_per_seg=n_fft, verbose=False)
        mean_psd = psd.mean(axis=(0, 1))
        q_str = gamma_q(freqs, mean_psd)

        peaks, _ = find_peaks(mean_psd, prominence=np.median(mean_psd), distance=2)
        pf, pp = freqs[peaks], mean_psd[peaks]
        order = np.argsort(pp)[::-1][:8]
        f0 = pf[order[0]]
        hits = []
        for m in LADDER:
            target = f0 * m
            if 1 <= target <= 120:
                j = int(np.argmin(np.abs(pf - target)))
                if abs(pf[j] - target) <= 1.5:
                    hits.append(f"{m:g}x={pf[j]:.1f}Hz")
        # 60 Hz subharmonic check
        sub = []
        for t in [30.0, 90.0]:
            j = int(np.argmin(np.abs(freqs - t)))
            local = np.median(mean_psd[max(0, j-3):j+4])
            sub.append(f"P{t:.0f}={mean_psd[j]/local:.1f}x")
        lines.append(f"{cond}: n={len(ep)} Q={q_str}")
        lines.append(f"  peaks: " + ", ".join(f"{pf[i]:.1f}" for i in order))
        lines.append(f"  ladder@{f0:.1f}Hz: " + (", ".join(hits) or "none"))
        lines.append(f"  60Hz subs: " + ", ".join(sub))

    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    print(f"Wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
