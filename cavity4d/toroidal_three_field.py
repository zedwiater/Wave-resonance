"""Three-field toroidal test: JADES GOODS-S + GOODS-N + CEERS EGS.

Adds CEERS EGS field (RA~214, Dec~+53) as third sky direction.
If brightness residuals correlate with direction across THREE fields,
survey systematics become much harder to invoke.

Method: compute M_UV from F200W apparent mag + luminosity distance,
then same residual analysis as toroidal_directional.py.
"""

from astropy.io import fits
import numpy as np
import json

# --- JADES ---
hdu_j = fits.open("/tmp/jades_z8.fits")
dj = hdu_j[1].data
ra_j = np.array(dj["RA"], dtype=float)
dec_j = np.array(dj["DEC"], dtype=float)
z_j = np.array(dj["EAZY_z_a"], dtype=float)
muv_j = np.array(dj["MUV"], dtype=float)  # already absolute

# --- CEERS ---
hdu_c = fits.open("/tmp/ceers_cat.fits")
dc = hdu_c[1].data
ra_c = np.array(dc["RA"], dtype=float)
dec_c = np.array(dc["DEC"], dtype=float)
z_c = np.array(dc["LP_Z_BEST"], dtype=float)
m_f200w = np.array(dc["F200W_MAG"], dtype=float)

# Filter CEERS to z > 8, valid mags
valid_c = (z_c > 8) & (z_c < 20) & np.isfinite(m_f200w) & (m_f200w > 15) & (m_f200w < 35)
ra_c, dec_c, z_c, m_f200w = ra_c[valid_c], dec_c[valid_c], z_c[valid_c], m_f200w[valid_c]

# Compute M_UV from apparent mag + distance modulus
# Manual luminosity distance (no scipy on target): flat LCDM numerical integration
def E_inv(z, Om0=0.315, Ol0=0.685):
    return 1.0 / np.sqrt(Om0 * (1+z)**3 + Ol0)

def luminosity_distance_pc(z_arr, H0=67.4):
    c_km_s = 299792.458
    DH_pc = c_km_s / H0 * 1e6  # Hubble distance in pc
    DL = np.zeros_like(z_arr, dtype=float)
    for i, z in enumerate(z_arr):
        zs = np.linspace(0, z, 200)
        integral = np.trapezoid(E_inv(zs), zs)
        DC = DH_pc * integral
        DL[i] = (1 + z) * DC
    return DL

DL_pc = luminosity_distance_pc(z_c)
muv_c = m_f200w - 5 * np.log10(DL_pc / 10)
# Approximate K-correction for rest-UV (small for well-chosen filter)
muv_c = muv_c + 2.5 * np.log10(1 + z_c) * 0.2  # rough

print(f"JADES: {len(ra_j)} galaxies (z>8)")
print(f"CEERS: {len(ra_c)} galaxies (z>8, valid)")

# Combine
ra_all = np.concatenate([ra_j, ra_c])
dec_all = np.concatenate([dec_j, dec_c])
z_all = np.concatenate([z_j, z_c])
muv_all = np.concatenate([muv_j, muv_c])
field = np.array(["JADES"] * len(ra_j) + ["CEERS"] * len(ra_c))

# Sub-identify JADES fields
goods_s = (np.abs(ra_all - 53.1) < 2.0) & (np.abs(dec_all + 27.8) < 2.0)
goods_n = (np.abs(ra_all - 189.2) < 2.0) & (np.abs(dec_all - 62.2) < 2.0)
egs = field == "CEERS"

print(f"\nGOODS-S: {np.sum(goods_s)}, GOODS-N: {np.sum(goods_n)}, EGS: {np.sum(egs)}")

# Valid MUV
valid = np.isfinite(muv_all) & (muv_all > -30) & (muv_all < -10)
ra_v, dec_v, z_v, muv_v = ra_all[valid], dec_all[valid], z_all[valid], muv_all[valid]
gs_v = goods_s[valid]
gn_v = goods_n[valid]
egs_v = egs[valid]

print(f"Valid: {np.sum(valid)}")

# Fit M_UV vs log(1+z) baseline
log_z = np.log10(z_v + 1)
coeffs = np.polyfit(log_z, muv_v, 1)
muv_exp = np.polyval(coeffs, log_z)
resid = muv_v - muv_exp

print(f"\nBaseline: M_UV = {coeffs[0]:.2f} * log(1+z) + {coeffs[1]:.2f}")
print(f"Residual std: {np.std(resid):.3f}")

# Three-field comparison
for name, mask in [("GOODS-S", gs_v), ("GOODS-N", gn_v), ("EGS", egs_v)]:
    r = resid[mask]
    n = len(r)
    if n > 0:
        print(f"{name:10s}: n={n:4d}  mean_resid={np.mean(r):+.4f} ± {np.std(r)/np.sqrt(n):.4f}")

# Pairwise significance
import itertools
print(f"\n=== Pairwise Tests ===")
for (n1, m1), (n2, m2) in itertools.combinations(
    [("GOODS-S", gs_v), ("GOODS-N", gn_v), ("EGS", egs_v)], 2):
    r1, r2 = resid[m1], resid[m2]
    if len(r1) > 0 and len(r2) > 0:
        diff = np.mean(r1) - np.mean(r2)
        se = np.sqrt(np.std(r1)**2/len(r1) + np.std(r2)**2/len(r2))
        print(f"{n1} vs {n2}: diff={diff:+.4f} ± {se:.4f}  ({abs(diff/se):.1f}σ)")

# Directional fit: residual as function of unit vector on sphere
# Convert RA/Dec to Cartesian
ra_rad = np.radians(ra_v)
dec_rad = np.radians(dec_v)
x = np.cos(dec_rad) * np.cos(ra_rad)
y = np.cos(dec_rad) * np.sin(ra_rad)
zhat = np.sin(dec_rad)

# Fit dipole: resid = d0 + dx*x + dy*y + dz*z
A = np.column_stack([np.ones_like(x), x, y, zhat])
coef_dip, _, _, _ = np.linalg.lstsq(A, resid, rcond=None)
dipole_amp = np.sqrt(coef_dip[1]**2 + coef_dip[2]**2 + coef_dip[3]**2)
# Dipole direction
dip_ra = np.degrees(np.arctan2(coef_dip[2], coef_dip[1])) % 360
dip_dec = np.degrees(np.arcsin(coef_dip[3] / dipole_amp)) if dipole_amp > 0 else 0

print(f"\n=== Dipole Fit ===")
print(f"Dipole amplitude: {dipole_amp:.4f} mag")
print(f"Dipole direction: RA={dip_ra:.1f}°, Dec={dip_dec:.1f}°")
print(f"Monopole (mean): {coef_dip[0]:+.4f}")

# Significance via permutation test
np.random.seed(42)
n_perm = 1000
perm_amps = []
for _ in range(n_perm):
    rp = np.random.permutation(resid)
    cp, _, _, _ = np.linalg.lstsq(A, rp, rcond=None)
    perm_amps.append(np.sqrt(cp[1]**2 + cp[2]**2 + cp[3]**2))
perm_amps = np.array(perm_amps)
p_val = np.mean(perm_amps >= dipole_amp)
print(f"Permutation p-value: {p_val:.4f} ({n_perm} trials)")
if p_val < 0.01:
    print("  → DIPOLE SIGNIFICANT at p<0.01")
elif p_val < 0.05:
    print("  → Dipole marginal at p<0.05")
else:
    print("  → No significant dipole")

output = {
    "n_total": int(np.sum(valid)),
    "fields": {
        "goods_s": {"n": int(np.sum(gs_v)), "mean_resid": round(float(np.mean(resid[gs_v])), 4)},
        "goods_n": {"n": int(np.sum(gn_v)), "mean_resid": round(float(np.mean(resid[gn_v])), 4)},
        "egs": {"n": int(np.sum(egs_v)), "mean_resid": round(float(np.mean(resid[egs_v])), 4)},
    },
    "dipole": {
        "amplitude_mag": round(float(dipole_amp), 4),
        "ra_deg": round(float(dip_ra), 1),
        "dec_deg": round(float(dip_dec), 1),
        "p_value": round(float(p_val), 4),
    },
}
with open("/tmp/toroidal_three_field.json", "w") as f:
    json.dump(output, f, indent=2)
print("\nSaved to /tmp/toroidal_three_field.json")
