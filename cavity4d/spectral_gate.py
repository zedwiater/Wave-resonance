"""spectral_gate.py — grounded frequency exclusion + source-scale labeling.

The exclusion list is NOT a hand-waved bandpass. It is GROUNDED in measured
carriers (2026-10-19/20 MEG campaign: HCP n-back + noise scans, ds000117):

  US grid: f0=60 Hz. Task spectrum: 60=17-19x, 120=31x (doubling ratio ~1.7);
           emptyroom 60=59x, 120=10.5x (ratio 0.18); phantom ratio 0.49.
  UK grid: f0=50 Hz. 50=22-23x, 100=1.12x (NO doubling).
  Sidebands at carrier +/- neural (6.2, 12.4, 10 Hz): 0.91-1.02x — NULL.
  Subharmonics (f0/2, f0/3): ~1.0x — NULL.

Every spectral bin gets a LABEL by source scale so downstream code never
mistakes a carrier for a signal (the ds117 lesson: 51.6 Hz 'gamma' was grid):

  labels: grid-carrier | grid-harmonic | grid-subharmonic |
          boundary-reflection | planetary-cavity | neural | unknown

Transport-side: exclusion_mask() zeroes carrier bins for phase-lock work.
Harvest-side: label_spectrum() annotates peaks with their scale.
"""
import numpy as np

# --- measured carrier tables (provenance: GitHub Wave-resonance, cavity4d) ---
CARRIERS = {
    "us": {
        "f0": 60.0,
        "harmonics": [120.0, 180.0, 240.0],
        "subharmonics": [30.0, 20.0],
        "doubling_ratio_task": 1.7,      # subject in dewar
        "doubling_ratio_emptyroom": 0.18,
        "doubling_ratio_phantom": 0.49,
    },
    "uk": {
        "f0": 50.0,
        "harmonics": [100.0, 150.0, 200.0],
        "subharmonics": [25.0, 16.7],
        "doubling_ratio_task": 1.12 / 22.6,  # ~0.05 — effectively no doubling
        "doubling_ratio_emptyroom": None,    # measured: ds117 emptyroom 50 Hz dominant
    },
}

# --- acceptance windows (the scales we care about) ---
WINDOWS = {
    "neural": (4.0, 14.0),          # theta+alpha; measured n-back fundamental 6.2 Hz
    "planetary-cavity": (7.0, 9.0), # Schumann 7.83 Hz +/- tolerance
}

NEURAL_FREQS = [6.2, 12.4, 10.0]    # measured neural peaks (HCP n-back)


def _near(freq, targets, tol):
    return any(abs(freq - t) <= tol for t in targets)


def label_bin(freq, grid="us", tol=1.5, carrier_tol=2.5):
    """Assign a source-scale label to one frequency bin.

    carrier_tol is deliberately wider than tol: line frequency drifts and
    spectral bins are wide (ds117 taught us 51.6 Hz on a 50 Hz grid).
    When in doubt, the gate over-labels the grid — a false carrier flag
    is cheap; a missed one ships a fake discovery.
    """
    c = CARRIERS[grid]
    if _near(freq, [c["f0"]], carrier_tol):
        return "grid-carrier"
    if _near(freq, c["harmonics"], tol):
        return "grid-harmonic"
    if _near(freq, c["subharmonics"], tol):
        return "grid-subharmonic"
    # boundary reflections: carrier/harmonic modulated by a neural freq
    for base in [c["f0"]] + c["harmonics"]:
        for fn in NEURAL_FREQS:
            if _near(freq, [base - fn, base + fn], tol):
                return "boundary-reflection"
    lo, hi = WINDOWS["planetary-cavity"]
    if lo <= freq <= hi:
        return "planetary-cavity"   # overlaps neural; cavity wins the label
                                    # because it's the environmental scale
    lo, hi = WINDOWS["neural"]
    if lo <= freq <= hi:
        return "neural"
    return "unknown"


def label_spectrum(freqs, psd, grid="us", tol=1.5, carrier_tol=2.5):
    """Return [(freq, power, label), ...] for every bin."""
    return [(float(f), float(p), label_bin(float(f), grid, tol, carrier_tol))
            for f, p in zip(freqs, psd)]


def exclusion_mask(freqs, grid="us", tol=1.5, carrier_tol=2.5):
    """True = keep. Carrier bins (and their harmonics/subs) are excluded
    so a phase-lock loop never latches onto the grid by mistake.
    Boundary-reflection bins are KEPT (they're the signal we hunt)."""
    keep = np.ones(len(freqs), dtype=bool)
    for i, f in enumerate(freqs):
        if label_bin(float(f), grid, tol, carrier_tol) in (
                "grid-carrier", "grid-harmonic", "grid-subharmonic"):
            keep[i] = False
    return keep


def gated_peak(freqs, psd, grid="us", band=None, tol=1.5, carrier_tol=2.5):
    """Strongest peak after exclusion. If band is given as (lo, hi),
    restrict to that acceptance window first (PLL-lite)."""
    freqs = np.asarray(freqs, dtype=float)
    psd = np.asarray(psd, dtype=float)
    keep = exclusion_mask(freqs, grid, tol)
    if band is not None:
        keep &= (freqs >= band[0]) & (freqs <= band[1])
    if not keep.any():
        return None
    idx = int(np.argmax(np.where(keep, psd, -np.inf)))
    return {"freq": float(freqs[idx]), "power": float(psd[idx]),
            "label": label_bin(float(freqs[idx]), grid, tol, carrier_tol)}


# ---------------------------------------------------------------------------
# Self-test: replay tonight's measured numbers through the gate.
# ---------------------------------------------------------------------------
def _selftest():
    print("label checks (must all pass):")
    cases = [
        (51.6, "uk", "grid-carrier"),       # the ds117 misread
        (50.8, "uk", "grid-carrier"),       # emptyroom peak
        (60.8, "us", "grid-carrier"),       # notch-skirt ghost
        (120.0, "us", "grid-harmonic"),
        (30.0, "us", "grid-subharmonic"),
        (66.2, "us", "boundary-reflection"),  # 60 + 6.2
        (53.8, "us", "boundary-reflection"),  # 60 - 6.2
        (7.83, "us", "planetary-cavity"),
        (6.2, "us", "neural"),                # measured n-back fundamental
        (10.0, "us", "neural"),
        (88.0, "us", "unknown"),
    ]
    ok = True
    for f, g, want in cases:
        got = label_bin(f, g)
        status = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"  [{status}] {f} Hz ({g}) -> {got} (want {want})")

    # exclusion must remove the grid, keep the brain
    freqs = np.arange(1, 201, 1.0)
    psd = np.random.default_rng(0).normal(1.0, 0.05, len(freqs))
    psd[freqs == 60] = 50.0     # carrier
    psd[freqs == 120] = 80.0    # harmonic (loudest thing in the room)
    psd[freqs == 10] = 5.0      # neural alpha — the actual signal
    pk = gated_peak(freqs, psd, grid="us", band=WINDOWS["neural"])
    print(f"\ngated peak in neural band: {pk}")
    assert pk and pk["label"] == "neural" and pk["freq"] == 10.0
    print("\nself-test:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    _selftest()
