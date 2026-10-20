"""HCP n-back induced frequency reflections: carrier harmonics, subharmonics, and sidebands.

If the grid carrier (60 Hz) transduces through the boundary into the recording,
any neural modulation of it shows up as reflections: harmonics (120, 180),
subharmonics (30, 20), and sidebands at 60 +/- f_neural (54/66 for 6 Hz theta,
47.6/72.4 for 12.4 Hz). Each is measured vs local median -> 1.0x = clean null.

Output: /mnt/storage/neurodata/hcp-induced-reflections.txt
"""
import mne, numpy as np, csv
from pathlib import Path

base = Path("/mnt/storage/neurodata/hcp-nback/106521")
out = Path("/mnt/storage/neurodata/hcp-induced-reflections.txt")
lines = []
L = lines.append

def load_eprime(path):
    with open(path) as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    trials = []
    for r in rows:
        onset = r.get("Stim.OnsetTime", "").strip()
        bt = r.get("BlockType", "").strip()
        if onset and onset.lstrip("-").isdigit() and bt in ("0-Back", "2-Back"):
            trials.append({"onset_ms": int(onset), "block": bt})
    return trials

def align(eprime, stimch, sf):
    ep_ms = np.array([t["onset_ms"] for t in eprime])
    st = np.asarray(stimch).ravel()
    thresh = np.abs(np.diff(st))
    trig = np.where(thresh > 0.5 * np.max(np.abs(thresh)))[0]
    if len(trig) == 0:
        return 0.0, 0
    tt = trig.astype(float) / sf
    best_n, best_lag = 0, 0.0
    for lag in np.arange(-120.0, 120.5, 0.5):
        t_ep = ep_ms / 1000.0 + lag
        if len(t_ep) == 0:
            continue
        idx = np.searchsorted(tt, t_ep)
        idx = np.clip(idx, 0, len(tt) - 1)
        n = int(np.sum(np.abs(tt[idx] - t_ep) < 1.0))
        if n > best_n:
            best_n, best_lag = n, float(lag)
    return best_lag, best_n

def local_median(psd, freqs, f0, halfwin=10.0, exclude=2.0):
    m = (np.abs(freqs - f0) <= halfwin) & (np.abs(freqs - f0) > exclude)
    vals = psd[m]
    return float(np.median(vals)) if len(vals) else float("nan")

def peak_ratio(psd, freqs, f0, tol=0.75):
    m = np.abs(freqs - f0) <= tol
    med = local_median(psd, freqs, f0)
    return float(np.max(psd[m]) / med) if (len(psd[m]) and med > 0) else float("nan")

def main():
    L("induced reflections — HCP n-back sub 106521")
    L("(carrier harmonics, subharmonics, modulation sidebands; ratios vs local median, 1.0x = clean null)")
    all_ep = {1: [], 2: []}
    run_psds = []
    for i, run in enumerate(["6-Wrkmem", "7-Wrkmem"]):
        rdir = base / run
        raw = mne.io.read_raw_bti(pdf_fname=str(rdir / "4D/c,rfDC"), head_shape_fname=None,
                                  preload=True, verbose=False)
        sf = raw.info["sfreq"]
        picks = mne.pick_types(raw.info, meg="mag")
        eprime = load_eprime(rdir / "EPRIME" / f"106521_MEG_Wrkmem_run{i+1}.tab")
        stimch = raw["STI 013"][0][0]
        lag, n = align(eprime, stimch, sf)
        L(f"run{i+1}: aligned {n}/{len(eprime)} trials, lag={lag:.1f}s")
        events = []
        for t in eprime:
            code = 1 if t["block"] == "0-Back" else 2
            events.append([int((t["onset_ms"] / 1000.0 + lag) * sf), 0, code])
        events = np.array(events)
        events = events[(events[:, 0] > 0) & (events[:, 0] < len(raw.times))]
        ep = mne.Epochs(raw, events, event_id={"0back": 1, "2back": 2},
                        tmin=0, tmax=2.5, baseline=None, picks=picks,
                        preload=True, verbose=False)
        for nm in ("0back", "2back"):
            e = ep[nm]
            psd, freqs = e.compute_psd(fmin=1, fmax=200, verbose=False).average().get_data(
                return_freqs=True)
            all_ep[1 if nm == "0back" else 2].append(psd.mean(axis=0))
        # full-run resting PSD (all mags) for carrier harmonic structure
        p0, f0 = mne.time_frequency.psd_array_welch(
            raw.get_data(picks=picks), sfreq=sf, fmin=1, fmax=200,
            n_fft=int(sf * 4), verbose=False)
        run_psds.append((f0, p0.mean(axis=0)))

    neur = {"theta6": 6.2, "alpha12": 12.4, "alpha10": 10.0}
    for cid, cname in ((1, "0-back"), (2, "2-back")):
        psd = np.mean(all_ep[cid], axis=0)
        # freqs from last epoch compute — recompute once for the shared grid
        L(f"\n== {cname} (n={len(all_ep[cid])} runs averaged) ==")
        # carrier harmonics
        for f0, lbl in ((60, "carrier 60"), (120, "2nd harmonic 120"),
                        (180, "3rd harmonic 180")):
            L(f"  {lbl}: {peak_ratio(psd, freqs, f0):.2f}x local median")
        # subharmonics
        for f0, lbl in ((30, "subharmonic 30 (f/2)"), (20, "subharmonic 20 (f/3)")):
            L(f"  {lbl}: {peak_ratio(psd, freqs, f0):.2f}x local median")
        # modulation sidebands: carrier +/- neural
        for nn, fn in neur.items():
            for side, fs in (("lo", 60 - fn), ("hi", 60 + fn)):
                L(f"  sideband 60{'-' if side=='lo' else '+'}{fn}Hz ({fs:.1f}Hz): {peak_ratio(psd, freqs, fs):.2f}x")
            for side, fs in (("lo", 120 - fn), ("hi", 120 + fn)):
                L(f"  sideband 120{'-' if side=='lo' else '+'}{fn}Hz ({fs:.1f}Hz): {peak_ratio(psd, freqs, fs):.2f}x")

    L("\n== full-run carrier harmonic structure (resting, both runs) ==")
    for i, (f0, p0) in enumerate(run_psds):
        har = ", ".join(f"{f}Hz={peak_ratio(p0, f0, f):.1f}x" for f in (60, 120, 180, 30))
        L(f"  run{i+1}: {har}")

    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())

if __name__ == "__main__":
    main()
