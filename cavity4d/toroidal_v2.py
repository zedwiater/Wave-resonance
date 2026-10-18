"""Three-field toroidal test v2: UNIFORM M_UV computation.

v1 failed: JADES catalog MUV vs my computed CEERS M_UV had ~2.2 mag
systematic offset (different pipelines). Fix: compute M_UV from apparent
magnitudes using IDENTICAL formula for all galaxies.

M_UV = m_obs - DM(z), where DM = 5*log10(D_L/10pc).
Use filter closest to rest-frame 1500A for each galaxy's redshift.
"""

from astropy.io import fits
import numpy as np
import json
import itertools

def E_inv(z, Om0=0.315, Ol0=0.685):
    return 1.0 / np.sqrt(Om0 * (1+z)**3 + Ol0)

def dist_mod(z_arr, H0=67.4):
    """Distance modulus, vectorized manual integration."""
    c_km_s = 299792.458
    DH_pc = c_km_s / H0 * 1e6
    DM = np.zeros_like(z_arr, dtype=float)
    for i, z in enumerate(z_arr):
        zs = np.linspace(0, z, 200)
        DC = DH_pc * np.trapezoid(E_inv(zs), zs)
        DL = (1 + z) * DC
        DM[i] = 5 * np.log10(DL / 10)
    return DM

# --- JADES ---
hdu_j = fits.open("/tmp/jades_z8.fits")
dj = hdu_j[1].data
ra_j = np.array(dj["RA"], dtype=float)
dec_j = np.array(dj["DEC"], dtype=float)
z_j = np.array(dj["EAZY_z_a"], dtype=float)
# Use F277W Kron mag (rest-frame ~2500-3000A at z~8-10, closest available)
m_j = np.array(dj["m_F277W_Kron"], dtype=float)
valid_j = np.isfinite(m_j) & (m_j > 15) & (m_j < 35) & np.isfinite(z_j)
ra_j, dec_j, z_j, m_j = ra_j[valid_j], dec_j[valid_j], z_j[valid_j], m_j[valid_j]
muv_j = m_j - dist_mod(z_j)
print(f"JADES valid: {len(ra_j)}")

# --- CEERS ---
hdu_c = fits.open("/tmp/ceers_cat.fits")
dc = hdu_c[1].data
ra_c = np.array(dc["RA"], dtype=float)
dec_c = np.array(dc["DEC"], dtype=float)
z_c = np.array(dc["LP_Z_BEST"], dtype=float)
m_c = np.array(dc["F277W_MAG"], dtype=float)
valid_c = (z_c > 8) & (z_c < 20) & np.isfinite(m_c) & (m_c > 15) & (m_c < 35)
ra_c, dec_c, z_c, m_c = ra_c[valid_c], dec_c[valid_c], z_c[valid_c], m_c[valid_c]
muv_c = m_c - dist_mod(z_c)
print(f"CEERS valid: {len(ra_c)}")

# Combine
ra_all = np.concatenate([ra_j, ra_c])
dec_all = np.concatenate([dec_j, dec_c])
z_all = np.concatenate([z_j, z_c])
muv_all = np.concatenate([muv_j, muv_c])

goods_s = (np.abs(ra_all - 53.1) < 2.0) & (np.abs(dec_all + 27.8) < 2.0)
goods_n = (np.abs(ra_all - 189.2) < 2.0) & (np.abs(dec_all - 62.2) < 2.0)
egs = ~goods_s & ~goods_n  # CEERS galaxies

valid = np.isfinite(muv_all) & (muv_all > -30) & (muv_all < -10)
ra_v, dec_v, z_v, muv_v = ra_all[valid], dec_all[valid], z_all[valid], muv_all[valid]
gs_v, gn_v, egs_v = goods_s[valid], goods_n[valid], egs[valid]

print(f"\nTotal valid: {np.sum(valid)}")
print(f"GOODS-S: {np.sum(gs_v)}, GOODS-N: {np.sum(gn_v)}, EGS: {np.sum(egs_v)}")

# Uniform baseline
log_z = np.log10(z_v + 1)
coeffs = np.polyfit(log_z, muv_v, 1)
resid = muv_v - np.polyval(coeffs, log_z)

print(f"\nUniform baseline: M_UV = {coeffs[0]:.2f} * log(1+z) + {coeffs[1]:.2f}")
print(f"Residual std: {np.std(resid):.3f}")

for name, mask in [("GOODS-S", gs_v), ("GOODS-N", gn_v), ("EGS", egs_v)]:
    r = resid[mask]
    n = len(r)
    if n > 0:
        print(f"{name:10s}: n={n:4d}  mean_resid={np.mean(r):+.4f} ± {np.std(r)/np.sqrt(n):.4f}")

print(f"\n=== Pairwise ===")
for (n1, m1), (n2, m2) in itertools.combinations(
    [("GOODS-S", gs_v), ("GOODS-N", gn_v), ("EGS", egs_v)], 2):
    r1, r2 = resid[m1], resid[m2]
    if len(r1) > 0 and len(r2) > 0:
        diff = np.mean(r1) - np.mean(r2)
        se = np.sqrt(np.std(r1)**2/len(r1) + np.std(r2)**2/len(r2))
        sig = abs(diff/se)
        flag = " ***" if sig > 3 else ""
        print(f"{n1} vs {n2}: diff={diff:+.4f} ± {se:.4f}  ({sig:.1f}σ){flag}")

# Cross-check: does the JADES-internal result survive uniform computation?
print(f"\n=== JADES-internal check (same pipeline as v1) ===")
rj = resid[gs_v | gn_v]
print(f"GOODS-S vs GOODS-N with uniform M_UV: "
      f"{np.mean(resid[gs_v])-np.mean(resid[gn_v]):+.4f}")

with open("/tmp/toroidal_v2.json", "w") as f:
    json.dump({
        "n_total": int(np.sum(valid)),
        "goods_s": {"n": int(np.sum(gs_v)), "mean_resid": round(float(np.mean(resid[gs_v])), 4)},
        "goods_n": {"n": int(np.sum(gn_v)), "mean_resid": round(float(np.mean(resid[gn_v])), 4)},
        "egs": {"n": int(np.sum(egs_v)), "mean_resid": round(float(np.mean(resid[egs_v])), 4)},
    }, f, indent=2)
print("\nSaved.")
