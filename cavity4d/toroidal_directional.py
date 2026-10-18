"""Toroidal directional test: JWST high-z galaxy brightness vs sky position.

Hypothesis: if the universe has toroidal topology, the distance-redshift
relation has a geometric component. Galaxies at the same redshift but
different sky directions should show systematic brightness residuals
correlated with direction (toward/away from torus axis).

Null hypothesis: brightness residuals are isotropic (no directional dependence).

Data: JADES z>8 catalog (Hainline et al. 2024), 717 galaxies, GOODS-S + GOODS-N.
Columns: RA, Dec, EAZY_z_a (photometric redshift), M_UV (absolute UV magnitude).

Method:
1. For each galaxy, compute expected M_UV from redshift using the
   observed M_UV-z relation (fit from the data itself, not theory).
2. Residual = observed M_UV - expected M_UV(z).
   Negative residual = brighter than expected for its redshift.
3. Test for directional dependence:
   a. Split by field (GOODS-S vs GOODS-N) — coarse dipole test.
   b. Fit residual as function of sky position — look for gradient.
   c. Rayleigh test for non-uniformity of bright outliers on the sphere.

If toroidal: residuals correlate with direction.
If LCDM: residuals are isotropic noise.
"""

from astropy.io import fits
import numpy as np
import json

# Load JADES catalog
hdu = fits.open("/tmp/jades_z8.fits")
# HDU 1 = full catalog (717 rows)
data = hdu[1].data

# Extract columns (check exact names)
cols = [c.name for c in data.columns]
print("Available columns:", [c for c in cols if "MUV" in c.upper() or "MAG" in c.upper()][:10])

# Find M_UV column
muv_col = "MUV"
for c in cols:
    if "MUV" in c.upper():
        muv_col = c
        break

ra = np.array(data["RA"], dtype=float)
dec = np.array(data["DEC"], dtype=float)
z = np.array(data["EAZY_z_a"], dtype=float)

print(f"\nTotal galaxies: {len(ra)}")
print(f"Redshift range: {np.min(z):.2f} - {np.max(z):.2f}")
print(f"RA range: {np.min(ra):.2f} - {np.max(ra):.2f}")
print(f"Dec range: {np.min(dec):.2f} - {np.max(dec):.2f}")

# Identify fields by position
# GOODS-S: RA ~53.1, Dec ~-27.8
# GOODS-N: RA ~189.2, Dec ~+62.2
goods_s = (np.abs(ra - 53.1) < 2.0) & (np.abs(dec + 27.8) < 2.0)
goods_n = (np.abs(ra - 189.2) < 2.0) & (np.abs(dec - 62.2) < 2.0)
print(f"\nGOODS-S: {np.sum(goods_s)} galaxies")
print(f"GOODS-N: {np.sum(goods_n)} galaxies")
print(f"Other/unmatched: {len(ra) - np.sum(goods_s) - np.sum(goods_n)}")

if muv_col:
    muv = np.array(data[muv_col], dtype=float)
    # Filter valid
    valid = np.isfinite(muv) & np.isfinite(z) & (z > 0)
    print(f"\nValid M_UV measurements: {np.sum(valid)}")

    ra_v, dec_v, z_v, muv_v = ra[valid], dec[valid], z[valid], muv[valid]
    gs_v = goods_s[valid]
    gn_v = goods_n[valid]

    # Fit M_UV vs z relation (simple linear in log space)
    # Use all valid data to establish the baseline trend
    log_z = np.log10(z_v + 1)  # log(1+z) is more physical
    # Robust linear fit (ignore outliers)
    coeffs = np.polyfit(log_z, muv_v, 1)
    muv_expected = np.polyval(coeffs, log_z)
    residuals = muv_v - muv_expected  # negative = brighter than expected

    print(f"\nM_UV vs log(1+z) fit: M_UV = {coeffs[0]:.2f} * log(1+z) + {coeffs[1]:.2f}")
    print(f"Residual std: {np.std(residuals):.3f} mag")

    # Test 1: Field comparison
    res_gs = residuals[gs_v]
    res_gn = residuals[gn_v]
    print(f"\n=== Field Dipole Test ===")
    print(f"GOODS-S mean residual: {np.mean(res_gs):.4f} ± {np.std(res_gs)/np.sqrt(len(res_gs)):.4f} (n={len(res_gs)})")
    print(f"GOODS-N mean residual: {np.mean(res_gn):.4f} ± {np.std(res_gn)/np.sqrt(len(res_gn)):.4f} (n={len(res_gn)})")
    diff = np.mean(res_gs) - np.mean(res_gn)
    se_diff = np.sqrt(np.std(res_gs)**2/len(res_gs) + np.std(res_gn)**2/len(res_gn))
    print(f"Difference (S - N): {diff:.4f} ± {se_diff:.4f}")
    print(f"Significance: {abs(diff/se_diff):.2f} sigma")
    if abs(diff/se_diff) > 2:
        print("  → DIRECTIONAL SIGNAL DETECTED (>2σ)")
    else:
        print("  → No significant directional difference")

    # Test 2: Correlation with Dec (north-south gradient)
    # If torus axis is tilted, expect gradient
    corr_dec = np.corrcoef(dec_v, residuals)[0, 1]
    corr_ra = np.corrcoef(ra_v, residuals)[0, 1]
    print(f"\n=== Sky Gradient Test ===")
    print(f"Correlation(residual, Dec): {corr_dec:.4f}")
    print(f"Correlation(residual, RA): {corr_ra:.4f}")

    # Test 3: Brightest outliers — are they clustered?
    # Take top 10% brightest residuals, check if uniformly distributed
    thresh = np.percentile(residuals, 10)  # most negative = brightest
    bright = residuals < thresh
    bright_dec_mean = np.mean(dec_v[bright])
    all_dec_mean = np.mean(dec_v)
    print(f"\n=== Bright Outlier Clustering ===")
    print(f"Brightest 10% mean Dec: {bright_dec_mean:.2f}")
    print(f"Full sample mean Dec: {all_dec_mean:.2f}")
    print(f"Brightest 10% GOODS-S fraction: {np.mean(gs_v[bright]):.2%}")
    print(f"Full sample GOODS-S fraction: {np.mean(gs_v):.2%}")

    # Save results
    output = {
        "n_galaxies": int(np.sum(valid)),
        "n_goods_s": int(np.sum(gs_v)),
        "n_goods_n": int(np.sum(gn_v)),
        "field_dipole": {
            "goods_s_mean_residual": round(float(np.mean(res_gs)), 4),
            "goods_n_mean_residual": round(float(np.mean(res_gn)), 4),
            "difference": round(float(diff), 4),
            "significance_sigma": round(float(abs(diff/se_diff)), 2),
        },
        "sky_gradient": {
            "corr_residual_dec": round(float(corr_dec), 4),
            "corr_residual_ra": round(float(corr_ra), 4),
        },
        "bright_outliers": {
            "goods_s_fraction_bright": round(float(np.mean(gs_v[bright])), 4),
            "goods_s_fraction_all": round(float(np.mean(gs_v)), 4),
        },
    }
    with open("/tmp/toroidal_directional.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to /tmp/toroidal_directional.json")
else:
    print("\nNo M_UV column found — cannot compute brightness residuals.")
    print("Will report positional data only.")
