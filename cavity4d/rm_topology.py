"""LOCAL EDDY vs MACRO MANIFOLD: Faraday rotation as topological probe.

If we sit inside a local eddy (heliosphere/LIC) embedded in a toroidal
wave manifold (Galaxy/universe), then extragalactic Faraday rotation
measures should carry TWO signatures:

  1. LOCAL: Galactic disk dynamo — toroidal (azimuthal) B-field in the
     disk produces RM antisymmetric about the Galactic plane.
     This is standard, well-modeled.

  2. MANIFOLD: A larger-scale toroidal topology would imprint a coherent
     azimuthal pattern that does NOT follow the Galactic disk — a residual
     quadrupole/dipole in the RM sky after subtracting the disk model.

Test: Fit low-order spherical harmonics to the RM sky. The disk gives
l=1 (dipole, antisymmetric in b). A toroidal manifold signature would
appear as coherent l=2 (quadrupole) power inconsistent with disk+halo.

Data: NVSS RM catalog (Taylor et al. 2009), 37,543 sources.

LOCAL EDDY BASELINE (literature):
  - LIC: n(HI)~0.2 cm^-3, T~6300 K, v~26 km/s from (l,b)=(3°,+16°)
  - Local B-field: ~3 μG, direction (l,b)~(40°,+50°) [Frisch+]
  - Heliopause: 120 AU (V1 2012, V2 2018)
  - VLISM B-field: ~0.5 nT, draped around heliopause [Voyager]
  - IBEX ribbon: circular ENA enhancement, center (l,b)~(33°,+55°)
"""

import numpy as np
import math

# --- Parse NVSS RM catalog ---
ras, decs, rms, rm_errs = [], [], [], []
with open("/tmp/nvss_rm.tsv") as f:
    lines = [l for l in f if not l.startswith("#") and l.strip()]
    # Skip header lines (units, column names)
    data_lines = []
    for l in lines:
        parts = l.strip().split("\t")
        # RM is column 11 (0-indexed 10)
        try:
            float(parts[10])
            data_lines.append(parts)
        except (ValueError, IndexError):
            continue

    for p in data_lines:
        try:
            # RA: "00 00 02.87" (h m s, space-separated), Dec: "+09 57 06.6"
            ra_parts = p[0].strip().split()
            ra_deg = (float(ra_parts[0]) + float(ra_parts[1])/60 +
                      float(ra_parts[2])/3600) * 15
            dec_parts = p[2].strip().split()
            # First part has sign attached: "+09" or "-27"
            dec_deg = float(dec_parts[0]) + math.copysign(
                float(dec_parts[1])/60 + float(dec_parts[2])/3600,
                float(dec_parts[0]))
            rm = float(p[10])
            rm_err = float(p[11])
            if abs(rm) < 1000:  # cut outliers
                ras.append(ra_deg)
                decs.append(dec_deg)
                rms.append(rm)
                rm_errs.append(rm_err)
        except (ValueError, IndexError):
            continue

ras = np.array(ras)
decs = np.array(decs)
rms = np.array(rms)
print(f"Parsed {len(rms)} rotation measures")
print(f"RM range: {np.min(rms):.1f} to {np.max(rms):.1f} rad/m²")
print(f"RM mean: {np.mean(rms):.2f}, std: {np.std(rms):.2f}")

# --- Convert to Galactic coordinates ---
# J2000 equatorial to galactic conversion
def eq_to_gal(ra_deg, dec_deg):
    ra = np.radians(ra_deg)
    dec = np.radians(dec_deg)
    # North galactic pole (J2000): RA=192.859508°, Dec=+27.128336°
    # Zero longitude: l=0 at RA=266.405100°, Dec=-28.936175°
    ra_ngp = np.radians(192.859508)
    dec_ngp = np.radians(27.128336)
    l_ncp = np.radians(122.932)

    sin_b = (np.sin(dec_ngp) * np.sin(dec) +
             np.cos(dec_ngp) * np.cos(dec) * np.cos(ra - ra_ngp))
    b = np.arcsin(np.clip(sin_b, -1, 1))

    y = np.cos(dec) * np.sin(ra - ra_ngp)
    x = (np.cos(dec_ngp) * np.sin(dec) -
         np.sin(dec_ngp) * np.cos(dec) * np.cos(ra - ra_ngp))
    l = l_ncp - np.arctan2(y, x)
    l = np.mod(l, 2 * np.pi)
    return np.degrees(l), np.degrees(b)

l_gal, b_gal = eq_to_gal(ras, decs)

# --- Test 1: RM antisymmetry about Galactic plane (disk signature) ---
# Standard: <RM> should flip sign across b=0 for inner Galaxy
north = b_gal > 10
south = b_gal < -10
print(f"\n=== Galactic Disk Signature ===")
print(f"Mean RM (b>+10°): {np.mean(rms[north]):+.2f} (n={np.sum(north)})")
print(f"Mean RM (b<-10°): {np.mean(rms[south]):+.2f} (n={np.sum(south)})")

# Inner galaxy (|l|<90 or >270) vs outer
inner = (l_gal < 90) | (l_gal > 270)
print(f"\nInner Galaxy mean RM (b>+10): {np.mean(rms[north & inner]):+.2f}")
print(f"Inner Galaxy mean RM (b<-10): {np.mean(rms[south & inner]):+.2f}")
print(f"Outer Galaxy mean RM (b>+10): {np.mean(rms[north & ~inner]):+.2f}")
print(f"Outer Galaxy mean RM (b<-10): {np.mean(rms[south & ~inner]):+.2f}")

# --- Test 2: Spherical harmonic power spectrum ---
# Fit RM(l,b) = Σ a_lm Y_lm, look at l=1 vs l=2 power
# Use high-latitude only (|b|>20°) to reduce disk contamination
high_lat = np.abs(b_gal) > 20
lh, bh, rmh = l_gal[high_lat], b_gal[high_lat], rms[high_lat]
print(f"\n=== High-Latitude Spherical Harmonics (|b|>20°, n={len(rmh)}) ===")

# Convert to unit vectors
l_rad = np.radians(lh)
b_rad = np.radians(bh)
x = np.cos(b_rad) * np.cos(l_rad)
y = np.cos(b_rad) * np.sin(l_rad)
z = np.sin(b_rad)

# l=0 (monopole)
# l=1 (dipole): x, y, z
# l=2 (quadrupole): xy, xz, yz, x²-y², 3z²-1
A = np.column_stack([
    np.ones_like(x),           # monopole
    x, y, z,                   # dipole
    x*y, x*z, y*z,             # quadrupole (off-diagonal)
    x*x - y*y, 3*z*z - 1,      # quadrupole (diagonal)
])
coeffs, residuals, rank, sv = np.linalg.lstsq(A, rmh, rcond=None)

monopole = abs(coeffs[0])
dipole = np.sqrt(sum(c**2 for c in coeffs[1:4]))
quad = np.sqrt(sum(c**2 for c in coeffs[4:9]))

print(f"Monopole:  {monopole:.3f} rad/m²")
print(f"Dipole:    {dipole:.3f} rad/m²")
print(f"Quadrupole:{quad:.3f} rad/m²")
print(f"Dipole/Quad ratio: {dipole/quad:.2f}" if quad > 0 else "")

# Significance: permutation test on quadrupole
np.random.seed(42)
n_perm = 500
perm_quads = []
for _ in range(n_perm):
    rp = np.random.permutation(rmh)
    cp, _, _, _ = np.linalg.lstsq(A, rp, rcond=None)
    perm_quads.append(np.sqrt(sum(c**2 for c in cp[4:9])))
perm_quads = np.array(perm_quads)
p_quad = np.mean(perm_quads >= quad)
print(f"\nQuadrupole permutation p-value: {p_quad:.4f}")
if p_quad < 0.01:
    print(">>> SIGNIFICANT QUADRUPOLE — coherent large-scale structure beyond disk")
elif p_quad < 0.05:
    print(">>> Marginal quadrupole")
else:
    print(">>> No significant quadrupole — consistent with disk + noise")

# --- Test 3: Correlation with JWST anisotropy direction ---
# JWST: GOODS-S (RA~53°, Dec~-28°) dimmer, GOODS-N (RA~189°, Dec~+62°) brighter
# Convert to galactic and check RM in those directions
for name, ra_c, dec_c in [("GOODS-S", 53.1, -27.8), ("GOODS-N", 189.2, 62.2)]:
    lg, bg = eq_to_gal(np.array([ra_c]), np.array([dec_c]))
    # Find RMs within 10° of this direction
    ang_sep = np.degrees(np.arccos(np.clip(
        np.cos(np.radians(bg[0])) * np.cos(b_rad) *
        np.cos(np.radians(lg[0]) - l_rad) +
        np.sin(np.radians(bg[0])) * np.sin(b_rad), -1, 1)))
    nearby = ang_sep < 10
    if np.sum(nearby) > 5:
        print(f"\n{name} (l={lg[0]:.1f}°, b={bg[0]:.1f}°): "
              f"mean RM = {np.mean(rmh[nearby]):+.2f} (n={np.sum(nearby)})")

import json
with open("/tmp/rm_analysis.json", "w") as f:
    json.dump({
        "n_sources": int(len(rms)),
        "disk_north_mean": round(float(np.mean(rms[north])), 3),
        "disk_south_mean": round(float(np.mean(rms[south])), 3),
        "monopole": round(float(monopole), 3),
        "dipole": round(float(dipole), 3),
        "quadrupole": round(float(quad), 3),
        "quadrupole_p": round(float(p_quad), 4),
    }, f, indent=2)
print("\nSaved to /tmp/rm_analysis.json")
