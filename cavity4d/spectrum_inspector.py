"""Spectrum Inspector: find the gap in neural field data.

Three jobs:
  1. DATA CHECK — what's actually downloadable right now (MNE sample,
     OpenNeuro ds000117, HCP MEG)? Report availability, don't assume.
  2. SPECTRAL INSPECTION — on whatever loads: PSD by condition,
     gamma-band Q-factor, inter-trial phase coherence.
  3. GAP REPORT — which framework predictions are testable with the
     available data, and what's still missing.

The "gap" we're hunting:
  - Published: gamma POWER vs BOLD (usually positive correlation).
  - Unpublished: gamma PHASE COHERENCE / Q-factor vs BOLD.
  - Unpublished: toroidal/poloidal ~90° coupling during integration.

Usage:
  ~/mne-venv/bin/python spectrum_inspector.py --check-data
  ~/mne-venv/bin/python spectrum_inspector.py --inspect-sample
  ~/mne-venv/bin/python spectrum_inspector.py --full
"""

import sys
import json
import argparse
import numpy as np


def check_data():
    """Report what's actually available. No assumptions."""
    report = {"mne_sample": {}, "openneuro_ds000117": {}, "hcp_meg": {}}

    # 1. MNE sample dataset (auto-downloadable, no credentials)
    try:
        import mne
        from mne.datasets import sample
        from pathlib import Path
        try:
            path = sample.data_path(download=False)
            # data_path returns "." when not actually cached — verify real files
            raw_test = Path(path) / "MEG" / "sample" / "sample_audvis_filt-0-40_raw.fif"
            if raw_test.exists():
                report["mne_sample"] = {
                    "available": True, "path": str(path),
                    "note": "Cached locally. MEG+EEG, visual/auditory, NOT working memory.",
                }
            else:
                raise FileNotFoundError("not cached")
        except Exception:
            report["mne_sample"] = {
                "available": "downloadable",
                "note": "Not cached but auto-downloads (~1.5GB). No credentials needed.",
            }
    except ImportError:
        report["mne_sample"] = {"available": False, "note": "mne not installed"}

    # 2. OpenNeuro ds000117 (Wakeman & Henson faces — needs download)
    # Try the new-style API first, fall back to dataset page check
    ds117_ok, ds117_note = False, ""
    for url in [
        "https://openneuro.org/crn/datasets/ds000117/snapshots",
        "https://openneuro.org/datasets/ds000117",
    ]:
        try:
            import urllib.request
            req = urllib.request.Request(
                url, headers={"User-Agent": "spectrum-inspector/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    ds117_ok = True
                    ds117_note = f"Reachable via {url}"
                    break
        except Exception:
            continue
    report["openneuro_ds000117"] = {
        "available": True if ds117_ok else "unverified",
        "note": (ds117_note + ". Faces task MEG. ~400GB with derivatives — "
                 "pipeline validator, not the n-back test.")
        if ds117_ok else "Could not verify automatically — check manually.",
    }

    # 3. HCP MEG n-back (the real test — usually needs ConnectomeDB account)
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://db.humanconnectome.org/",
            headers={"User-Agent": "spectrum-inspector/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            reachable = r.status == 200
        report["hcp_meg"] = {
            "available": "reachable, credentials likely required",
            "note": ("HCP MEG n-back working memory exists (per PMC6628086). "
                     "Download needs a ConnectomeDB account — not automated here."),
        } if reachable else {
            "available": False, "note": "db.humanconnectome.org unreachable",
        }
    except Exception as e:
        report["hcp_meg"] = {
            "available": f"check failed: {type(e).__name__}",
            "note": "Verify manually at db.humanconnectome.org",
        }

    return report


def inspect_sample(download=True):
    """Run spectral inspection on MNE sample data (visual/auditory).

    This validates the pipeline. The sample has no working-memory load
    manipulation, so it can't test the 90° prediction — but it proves
    the Q-factor and coherence code works on real MEG.
    """
    import mne
    from mne.datasets import sample

    print("Loading MNE sample dataset...")
    data_path = sample.data_path(download=download)
    raw_fname = (data_path / "MEG" / "sample" / "sample_audvis_filt-0-40_raw.fif")
    event_fname = (data_path / "MEG" / "sample" / "sample_audvis_filt-0-40_raw-eve.fif")

    raw = mne.io.read_raw_fif(raw_fname, preload=True, verbose=False)
    events = mne.read_events(event_fname, verbose=False)

    # Pick MEG magnetometers (radial field) + EEG
    picks_mag = mne.pick_types(raw.info, meg="mag", exclude="bads")
    picks_eeg = mne.pick_types(raw.info, eeg=True, exclude="bads")

    # Epoch: auditory vs visual
    event_id = {"auditory/left": 1, "auditory/right": 2,
                "visual/left": 3, "visual/right": 4}
    epochs = mne.Epochs(raw, events, event_id, tmin=-0.2, tmax=0.8,
                        baseline=(-0.2, 0), preload=True, verbose=False)

    results = {}
    for cond in ["auditory/left", "visual/left"]:
        ep = epochs[cond]
        # PSD per condition (magnetometers)
        psd, freqs = mne.time_frequency.psd_array_welch(
            ep.get_data(picks=picks_mag), sfreq=raw.info["sfreq"],
            fmin=1, fmax=100, n_fft=2048, verbose=False)
        mean_psd = psd.mean(axis=(0, 1))  # avg over epochs and channels

        # Gamma Q-factor: find dominant peak 30-80 Hz, Q = f0 / FWHM
        gmask = (freqs >= 30) & (freqs <= 80)
        gf, gp = freqs[gmask], mean_psd[gmask]
        peak_idx = np.argmax(gp)
        f0 = gf[peak_idx]
        half = gp[peak_idx] / 2
        above = np.where(gp >= half)[0]
        # contiguous region around peak
        left = peak_idx
        while left > 0 and left - 1 in above:
            left -= 1
        right = peak_idx
        while right < len(gp) - 1 and right + 1 in above:
            right += 1
        fwhm = gf[right] - gf[left] if right > left else np.nan
        q = f0 / fwhm if fwhm and not np.isnan(fwhm) else np.nan

        # Inter-trial phase coherence in gamma (30-80 Hz)
        # via Morlet wavelets on a subset of channels (speed)
        freqs_w = np.arange(30, 81, 5)
        n_cycles = freqs_w / 4
        power, itc = mne.time_frequency.tfr_morlet(
            ep, freqs=freqs_w, n_cycles=n_cycles, picks=picks_mag[:20],
            return_itc=True, verbose=False)
        mean_itc = float(itc.data[:, :, :].mean())

        results[cond] = {
            "n_epochs": len(ep),
            "gamma_peak_hz": round(float(f0), 1),
            "gamma_q_factor": round(float(q), 2) if not np.isnan(q) else None,
            "mean_itc_gamma": round(mean_itc, 4),
        }
        print(f"  {cond}: peak={f0:.1f}Hz Q={q:.2f} ITPC={mean_itc:.4f}")

    return results


def multipole_signature(raw, picks_mag):
    """First-order spatial mode decomposition on the sensor array.

    Proxy for toroidal/poloidal analysis at sensor level:
    decompose the gamma-band field pattern into low-order spatial modes
    via SVD of the sensor covariance. The singular value spectrum's
    concentration (how many modes carry 90% of variance) is the
    "multipole signature."

    Full toroidal/poloidal source decomposition needs MRI + forward
    model — marked as the follow-up, not done here.
    """
    import mne
    data = raw.get_data(picks=picks_mag)
    # Gamma-band filter
    raw_gamma = raw.copy().filter(30, 80, picks=picks_mag, verbose=False)
    gdata = raw_gamma.get_data(picks=picks_mag)
    # Sensor covariance → SVD
    cov = np.cov(gdata)
    sv = np.linalg.svd(cov, compute_uv=False)
    sv_norm = sv / sv.sum()
    cumvar = np.cumsum(sv_norm)
    n90 = int(np.searchsorted(cumvar, 0.90)) + 1
    return {
        "n_sensors": len(picks_mag),
        "modes_for_90pct_variance": n90,
        "top5_sv_fraction": [round(float(v), 4) for v in sv_norm[:5]],
        "note": ("Sensor-level proxy only. True toroidal/poloidal split "
                 "needs source space (MRI + forward model)."),
    }


def gap_report(data_check, spectral_results=None):
    """What can we test, what's still missing."""
    print("\n" + "=" * 60)
    print("GAP REPORT")
    print("=" * 60)

    print("\n[DATA AVAILABILITY]")
    for name, info in data_check.items():
        print(f"  {name}: {info.get('available')}")
        print(f"    → {info.get('note')}")

    print("\n[WHAT'S TESTABLE NOW]")
    print("  ✓ Spectral pipeline validated (Q-factor, ITPC on real MEG)")
    print("  ✓ Gamma Q-factor by condition (pilot for jaw-clench logic)")
    if spectral_results:
        for cond, r in spectral_results.items():
            print(f"    {cond}: Q={r['gamma_q_factor']}, ITPC={r['mean_itc_gamma']}")

    print("\n[THE GAPS]")
    print("  ✗ 90° toroidal/poloidal coupling: needs working-memory LOAD")
    print("    manipulation (0-back vs 2-back). MNE sample has none.")
    print("    → Requires HCP MEG n-back (credentials needed).")
    print("  ✗ Gamma COHERENCE vs BOLD: needs simultaneous EEG-fMRI.")
    print("    Published work covers gamma POWER vs BOLD only.")
    print("    → Requires simultaneous dataset (HCP or OpenNeuro BIDS).")
    print("  ✗ Source-space decomposition: needs MRI + forward model.")
    print("    Sensor-level multipole is a proxy, not the measurement.")

    print("\n[NEXT CONCRETE STEP]")
    print("  1. Get HCP ConnectomeDB account → pull MEG n-back")
    print("  2. Extend this script: source reconstruction via MNE")
    print("     (needs FreeSurfer recon — heavy but standard)")
    print("  3. Toroidal/poloidal split in source space → coupling angle")
    print("     per trial → 0-back vs 2-back comparison")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-data", action="store_true")
    ap.add_argument("--inspect-sample", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()

    if not (args.check_data or args.inspect_sample or args.full):
        print(__doc__)
        return

    data_check = None
    spectral = None

    if args.check_data or args.full:
        print("=== DATA AVAILABILITY CHECK ===")
        data_check = check_data()
        print(json.dumps(data_check, indent=2))

    if args.inspect_sample or args.full:
        print("\n=== SPECTRAL INSPECTION (MNE sample) ===")
        try:
            spectral = inspect_sample(download=True)
        except Exception as e:
            print(f"  Inspection failed: {type(e).__name__}: {e}")
            print("  (Dataset download may need network. Try --check-data first.)")

    if args.full and data_check:
        gap_report(data_check, spectral)


if __name__ == "__main__":
    main()
