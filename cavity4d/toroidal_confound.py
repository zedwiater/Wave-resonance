"""Toroidal test v4: KILLING THE REMAINING CONFOUNDS.

Confound 1: Survey depth asymmetry.
  GOODS-S has ultradeep pointings (~650 hrs) vs GOODS-N (~150 hrs).
  If GOODS-S goes deeper, it picks up fainter galaxies, weighting the mean down.
  KILL: Apply strict luminosity cut above the completeness limit of BOTH fields.
  If the directional delta survives on the bright-end flux-matched sample,
  survey depth is eliminated.

Confound 2: Galactic foreground dust.
  Claim: dust maps underestimated E(B-V) toward GOODS-S by ~0.5 mag.
  KILL: Check known E(B-V) for both fields. Both are high-galactic-latitude
  deep fields with E(B-V) < 0.015. A 0.53-mag UV offset would require
  dE(B-V) ~ 0.06-0.08, wildly inconsistent with measured values.
"""

from astropy.io import fits
import numpy as np
import json

def load_dr4(path):
    hdu = fits.open(path)
    d = hdu[1].data
    return {
        "ra": np.array(d["RA_TARG"], dtype=float),
        "dec": np.array(d["DEC_TARG"], dtype=float),
        "z_spec": np.array(d["z_Spec"], dtype=float),
        "muv": np.array(d["MUV"], dtype=float),
        "tier": np.array(d["TIER"]),
    }

gs = load_dr4("/tmp/dr4_goods_s.fits")
gn = load_dr4("/tmp/dr4_goods_n.fits")

ra = np.concatenate([gs["ra"], gn["ra"]])
dec = np.concatenate([gs["dec"], gn["dec"]])
z_spec = np.concatenate([gs["z_spec"], gn["z_spec"]])
muv = np.concatenate([gs["muv"], gn["muv"]])
field = np.array(["GS"] * len(gs["ra"]) + ["GN"] * len(gn["ra"]))

# Base sample: spec-z > 5, valid MUV
base = (np.isfinite(z_spec) & (z_spec > 5) & (z_spec < 20) &
        np.isfinite(muv) & (muv > -30) & (muv < -10))

print("=== CONFOUND 1: Survey Depth ===")
print("Testing luminosity-complete subsamples.\n")

results = {}
for mcut in [-18.0, -18.5, -19.0, -19.5, -20.0]:
    # Bright-end cut: M_UV <= mcut (more negative = brighter)
    sel = base & (muv <= mcut)
    n_gs = np.sum(sel & (field == "GS"))
    n_gn = np.sum(sel & (field == "GN"))

    if n_gs < 10 or n_gn < 10:
        print(f"M_UV <= {mcut}: n_gs={n_gs}, n_gn={n_gn} — too few, skipping")
        continue

    # Recompute baseline on this subsample
    zs = z_spec[sel]
    m = muv[sel]
    f = field[sel]
    log_z = np.log10(zs + 1)
    coeffs = np.polyfit(log_z, m, 1)
    resid = m - np.polyval(coeffs, log_z)

    r_gs = resid[f == "GS"]
    r_gn = resid[f == "GN"]
    diff = np.mean(r_gs) - np.mean(r_gn)
    se = np.sqrt(np.std(r_gs)**2/len(r_gs) + np.std(r_gn)**2/len(r_gn))
    sig = abs(diff / se)

    status = "SURVIVES" if sig > 3 else ("MARGINAL" if sig > 2 else "DEAD")
    print(f"M_UV <= {mcut}: n={np.sum(sel)} (GS={n_gs}, GN={n_gn})  "
          f"diff={diff:+.4f} ± {se:.4f}  ({sig:.1f}σ)  [{status}]")
    results[str(mcut)] = {
        "n_gs": int(n_gs), "n_gn": int(n_gn),
        "diff": round(float(diff), 4), "sigma": round(float(sig), 2),
        "status": status,
    }

print("\n=== CONFOUND 2: Galactic Dust ===")
# Known E(B-V) from Schlafly & Finkbeiner (2011) for deep field centers:
# GOODS-S (CDF-S, l=223.6, b=-54.4): E(B-V) = 0.0088
# GOODS-N (HDF-N, l=125.9, b=+54.8): E(B-V) = 0.0123
# Both from the SFD maps recalibrated.
ebv_gs = 0.0088
ebv_gn = 0.0123
d_ebv = abs(ebv_gs - ebv_gn)

# UV extinction: A_1500 ~ 8.0 * E(B-V) (Calzetti-like, roughly)
# Even using extreme R_V variations, A_UV/E(B-V) is 6-10
for R in [6.0, 8.0, 10.0]:
    d_Auv = R * d_ebv
    print(f"  A_UV/E(B-V)={R}: differential extinction = {d_Auv:.4f} mag")

print(f"\n  Observed directional offset: 0.53 mag")
print(f"  Max dust can explain: ~{10.0 * d_ebv:.3f} mag (extreme assumptions)")
print(f"  Shortfall factor: {0.53 / (10.0 * d_ebv):.1f}x")
print(f"  >>> DUST CANNOT EXPLAIN THE SIGNAL")

# What E(B-V) difference WOULD be needed?
needed_d_ebv = 0.53 / 8.0
print(f"\n  E(B-V) difference needed for dust explanation: {needed_d_ebv:.4f}")
print(f"  Actual measured difference: {d_ebv:.4f}")
print(f"  Required/actual ratio: {needed_d_ebv / d_ebv:.1f}x")

with open("/tmp/toroidal_confound.json", "w") as f:
    json.dump({
        "luminosity_cuts": results,
        "dust": {
            "ebv_goods_s": ebv_gs,
            "ebv_goods_n": ebv_gn,
            "differential_ebv": round(d_ebv, 4),
            "max_dust_mag": round(10.0 * d_ebv, 4),
            "observed_offset_mag": 0.53,
            "verdict": "DUST_ELIMINATED",
        },
    }, f, indent=2)
print("\nSaved to /tmp/toroidal_confound.json")
