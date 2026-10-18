"""Toroidal test v3: SPECTROSCOPIC redshifts (JADES DR4).

The falsification gate. If the directional brightness offset survives
the transition from photo-z to spec-z, the photo-z template confound dies.

Data: JADES DR4 NIRSpec catalogs (GOODS-S + GOODS-N), same pipeline.
Columns: RA_TARG, DEC_TARG, z_Spec, z_Spec_flag, MUV, MUV_err.
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
        "z_flag": np.array(d["z_Spec_flag"]),
        "z_phot": np.array(d["z_phot"], dtype=float),
        "muv": np.array(d["MUV"], dtype=float),
        "muv_err_u": np.array(d["MUV_err_u"], dtype=float),
        "muv_err_l": np.array(d["MUV_err_l"], dtype=float),
    }

gs = load_dr4("/tmp/dr4_goods_s.fits")
gn = load_dr4("/tmp/dr4_goods_n.fits")

print(f"GOODS-S targets: {len(gs['ra'])}")
print(f"GOODS-N targets: {len(gn['ra'])}")
print(f"Unique z_spec flags in GS: {np.unique(gs['z_flag'])}")
print(f"Unique z_spec flags in GN: {np.unique(gn['z_flag'])}")

# Combine
ra = np.concatenate([gs["ra"], gn["ra"]])
dec = np.concatenate([gs["dec"], gn["dec"]])
z_spec = np.concatenate([gs["z_spec"], gn["z_spec"]])
z_flag = np.concatenate([gs["z_flag"], gn["z_flag"]])
z_phot = np.concatenate([gs["z_phot"], gn["z_phot"]])
muv = np.concatenate([gs["muv"], gn["muv"]])
field = np.array(["GS"] * len(gs["ra"]) + ["GN"] * len(gn["ra"]))

# Filter: valid spec-z, valid MUV, high-z
# z_Spec_flag: check what values mean — assume non-empty/positive = good
print(f"\nz_spec valid: {np.sum(np.isfinite(z_spec) & (z_spec > 0))}")
print(f"muv valid: {np.sum(np.isfinite(muv) & (muv < 0))}")

# Use spec-z > 5 for the high-z test (DR4 has ~400 at z>5.7)
valid = (np.isfinite(z_spec) & (z_spec > 5) & (z_spec < 20) &
         np.isfinite(muv) & (muv > -30) & (muv < -10))
print(f"High-z spec-z sample (z>5): {np.sum(valid)}")

ra_v, dec_v = ra[valid], dec[valid]
zs_v, zp_v = z_spec[valid], z_phot[valid]
muv_v = muv[valid]
f_v = field[valid]

gs_v = f_v == "GS"
gn_v = f_v == "GN"
print(f"  GOODS-S: {np.sum(gs_v)}, GOODS-N: {np.sum(gn_v)}")

# Baseline: M_UV vs log(1+z_spec)
log_z = np.log10(zs_v + 1)
coeffs = np.polyfit(log_z, muv_v, 1)
resid = muv_v - np.polyval(coeffs, log_z)

print(f"\nSpec-z baseline: M_UV = {coeffs[0]:.2f} * log(1+z) + {coeffs[1]:.2f}")
print(f"Residual std: {np.std(resid):.3f}")

r_gs = resid[gs_v]
r_gn = resid[gn_v]
n_gs, n_gn = len(r_gs), len(r_gn)

print(f"\n=== SPEC-Z DIRECTIONAL TEST ===")
print(f"GOODS-S: n={n_gs:4d}  mean_resid={np.mean(r_gs):+.4f} ± {np.std(r_gs)/np.sqrt(n_gs):.4f}")
print(f"GOODS-N: n={n_gn:4d}  mean_resid={np.mean(r_gn):+.4f} ± {np.std(r_gn)/np.sqrt(n_gn):.4f}")

diff = np.mean(r_gs) - np.mean(r_gn)
se = np.sqrt(np.std(r_gs)**2/n_gs + np.std(r_gn)**2/n_gn)
sig = abs(diff / se)
print(f"\nDifference (S - N): {diff:+.4f} ± {se:.4f}")
print(f"Significance: {sig:.2f}σ")

if sig > 3:
    print(">>> DIRECTIONAL OFFSET SURVIVES SPEC-Z — photo-z confound DEAD")
elif sig > 2:
    print(">>> Marginal — weakened but not dead")
else:
    print(">>> OFFSET GONE — photo-z was the confound, toroidal test fails this gate")

# Also check: does spec-z agree with photo-z? (sanity)
dz = np.abs(zs_v - zp_v) / (1 + zs_v)
print(f"\nPhoto-z vs spec-z NMAD: {1.48 * np.median(dz):.4f}")
print(f"Catastrophic outliers (|dz|>0.15): {np.mean(dz > 0.15):.1%}")

# Per-redshift-bin check: is the offset consistent across z?
print(f"\n=== Redshift Bins ===")
for zlo, zhi in [(5, 7), (7, 9), (9, 12), (12, 20)]:
    m = (zs_v >= zlo) & (zs_v < zhi)
    if np.sum(m & gs_v) >= 5 and np.sum(m & gn_v) >= 5:
        d = np.mean(resid[m & gs_v]) - np.mean(resid[m & gn_v])
        print(f"  z=[{zlo},{zhi}): n_gs={np.sum(m & gs_v)}, n_gn={np.sum(m & gn_v)}, diff={d:+.3f}")

with open("/tmp/toroidal_specz.json", "w") as f:
    json.dump({
        "n_total": int(np.sum(valid)),
        "n_goods_s": int(n_gs),
        "n_goods_n": int(n_gn),
        "goods_s_mean_resid": round(float(np.mean(r_gs)), 4),
        "goods_n_mean_resid": round(float(np.mean(r_gn)), 4),
        "difference": round(float(diff), 4),
        "significance_sigma": round(float(sig), 2),
        "verdict": "SURVIVES" if sig > 3 else ("MARGINAL" if sig > 2 else "FAILS"),
    }, f, indent=2)
print("\nSaved to /tmp/toroidal_specz.json")
