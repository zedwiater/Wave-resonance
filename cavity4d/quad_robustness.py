"""RM QUADRUPOLE ROBUSTNESS: Split-half replication + cavity feedback prep.

Before claiming the (307°, +15°) quadrupole axis is real, verify it
replicates in independent data splits. Then package the tensor for
the toroidal cavity simulator as a background field boundary condition.

Test 1: Split 37,543 RMs into random halves, extract quadrupole
  principal axis from each. Stable axis = real signal.
  Also split by hemisphere (north/south Galactic) for independence.

Test 2: Export quadrupole tensor eigenvectors + eigenvalues in a
  format the cavity simulator can ingest as background B-field.
"""

import numpy as np
import math
import json

# Load and parse (reuse from hierarchical_cascade.py)
ras, decs, rms = [], [], []
with open("/tmp/nvss_rm.tsv") as f:
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        p = line.strip().split("\t")
        try:
            float(p[10])
        except (ValueError, IndexError):
            continue
        try:
            ra_parts = p[0].strip().split()
            ra_deg = (float(ra_parts[0]) + float(ra_parts[1])/60 +
                      float(ra_parts[2])/3600) * 15
            dec_parts = p[2].strip().split()
            dec_deg = float(dec_parts[0]) + math.copysign(
                float(dec_parts[1])/60 + float(dec_parts[2])/3600,
                float(dec_parts[0]))
            rm = float(p[10])
            if abs(rm) < 1000:
                ras.append(ra_deg); decs.append(dec_deg); rms.append(rm)
        except (ValueError, IndexError):
            continue

ras = np.array(ras); decs = np.array(decs); rms = np.array(rms)

def eq_to_gal(ra_deg, dec_deg):
    ra = np.radians(ra_deg); dec = np.radians(dec_deg)
    ra_ngp = np.radians(192.859508); dec_ngp = np.radians(27.128336)
    l_ncp = np.radians(122.932)
    sin_b = (np.sin(dec_ngp)*np.sin(dec) +
             np.cos(dec_ngp)*np.cos(dec)*np.cos(ra - ra_ngp))
    b = np.arcsin(np.clip(sin_b, -1, 1))
    y = np.cos(dec)*np.sin(ra - ra_ngp)
    x = (np.cos(dec_ngp)*np.sin(dec) -
         np.sin(dec_ngp)*np.cos(dec)*np.cos(ra - ra_ngp))
    l = np.mod(l_ncp - np.arctan2(y, x), 2*np.pi)
    return np.degrees(l), np.degrees(b)

l_gal, b_gal = eq_to_gal(ras, decs)

def extract_quad_axis(lh, bh, rmh):
    """Fit quadrupole, return principal axis (l, b) and eigenvalues."""
    l_rad = np.radians(lh); b_rad = np.radians(bh)
    x = np.cos(b_rad)*np.cos(l_rad)
    y = np.cos(b_rad)*np.sin(l_rad)
    z = np.sin(b_rad)
    A = np.column_stack([x*y, x*z, y*z, x*x - y*y, 3*z*z - 1])
    cq, _, _, _ = np.linalg.lstsq(A, rmh, rcond=None)
    c_xy, c_xz, c_yz, c_x2y2, c_3z2 = cq
    a = (c_x2y2 - 3*c_3z2) / 2
    Q = np.array([
        [a,        c_xy/2,     c_xz/2],
        [c_xy/2,   a - c_x2y2, c_yz/2],
        [c_xz/2,   c_yz/2,     -2*a + c_x2y2],
    ])
    eigenvals, eigenvecs = np.linalg.eigh(Q)
    idx = np.argmax(np.abs(eigenvals))
    p = eigenvecs[:, idx]
    b_p = np.degrees(np.arcsin(np.clip(p[2], -1, 1)))
    l_p = np.degrees(np.arctan2(p[1], p[0])) % 360
    quad_amp = np.sqrt(np.sum(cq**2))
    return (l_p, b_p), eigenvals, quad_amp, Q

def axial_sep_lb(l1, b1, l2, b2):
    def uv(l, b):
        l, b = np.radians(l), np.radians(b)
        return np.array([np.cos(b)*np.cos(l), np.cos(b)*np.sin(l), np.sin(b)])
    s = np.degrees(np.arccos(np.clip(np.dot(uv(l1,b1), uv(l2,b2)), -1, 1)))
    return min(s, 180 - s)

# Full sample baseline
high = np.abs(b_gal) > 20
full_axis, full_eig, full_amp, full_Q = extract_quad_axis(
    l_gal[high], b_gal[high], rms[high])
print(f"Full sample quadrupole axis: ({full_axis[0]:.1f}°, {full_axis[1]:.1f}°)")
print(f"  Eigenvalues: {sorted(full_eig, key=abs)}")

# Test 1a: Random split-half
print("\n=== Split-Half Replication ===")
np.random.seed(123)
for trial in range(3):
    idx = np.random.permutation(len(rms))
    h1 = idx[:len(idx)//2]
    h2 = idx[len(idx)//2:]
    # Apply high-lat cut to each half
    m1 = np.abs(b_gal[h1]) > 20
    m2 = np.abs(b_gal[h2]) > 20
    ax1, _, amp1, _ = extract_quad_axis(l_gal[h1][m1], b_gal[h1][m1], rms[h1][m1])
    ax2, _, amp2, _ = extract_quad_axis(l_gal[h2][m2], b_gal[h2][m2], rms[h2][m2])
    sep = axial_sep_lb(ax1[0], ax1[1], ax2[0], ax2[1])
    sep1f = axial_sep_lb(ax1[0], ax1[1], full_axis[0], full_axis[1])
    sep2f = axial_sep_lb(ax2[0], ax2[1], full_axis[0], full_axis[1])
    print(f"  Trial {trial+1}: half1=({ax1[0]:.1f}°,{ax1[1]:.1f}°) "
          f"half2=({ax2[0]:.1f}°,{ax2[1]:.1f}°)")
    print(f"    half1↔half2: {sep:.1f}°  |  half1↔full: {sep1f:.1f}°  |  half2↔full: {sep2f:.1f}°")

# Test 1b: North/South Galactic hemisphere split
print("\n=== Hemisphere Split ===")
north_m = (b_gal > 20)
south_m = (b_gal < -20)
ax_n, _, _, _ = extract_quad_axis(l_gal[north_m], b_gal[north_m], rms[north_m])
ax_s, _, _, _ = extract_quad_axis(l_gal[south_m], b_gal[south_m], rms[south_m])
print(f"  North (b>+20°): ({ax_n[0]:.1f}°, {ax_n[1]:.1f}°)")
print(f"  South (b<-20°): ({ax_s[0]:.1f}°, {ax_s[1]:.1f}°)")
print(f"  N↔S separation: {axial_sep_lb(ax_n[0],ax_n[1],ax_s[0],ax_s[1]):.1f}°")
print(f"  N↔full: {axial_sep_lb(ax_n[0],ax_n[1],full_axis[0],full_axis[1]):.1f}°")
print(f"  S↔full: {axial_sep_lb(ax_s[0],ax_s[1],full_axis[0],full_axis[1]):.1f}°")

# Test 2: Export tensor for cavity simulator
print("\n=== Cavity Simulator Input ===")
# Eigenvectors in Galactic Cartesian, sorted by |eigenvalue| descending
order = np.argsort(np.abs(full_eig))[::-1]
print("Principal axes (eigenvector, eigenvalue):")
for i, o in enumerate(order):
    ev = np.linalg.eigh(full_Q)[1][:, o]
    # Recompute properly
eigvals_sorted, eigvecs_sorted = np.linalg.eigh(full_Q)
idx_sort = np.argsort(np.abs(eigvals_sorted))[::-1]
for rank, oi in enumerate(idx_sort):
    ev = eigvecs_sorted[:, oi]
    e_val = eigvals_sorted[oi]
    bl = np.degrees(np.arcsin(np.clip(ev[2], -1, 1)))
    ll = np.degrees(np.arctan2(ev[1], ev[0])) % 360
    print(f"  Axis {rank+1}: (l,b)=({ll:.1f}°,{bl:.1f}°), λ={e_val:.2f}")

cavity_input = {
    "description": "RM quadrupole tensor from 37,543 NVSS sources, |b|>20°",
    "tensor_galactic_cartesian": full_Q.tolist(),
    "eigenvalues": [round(float(eigvals_sorted[oi]), 3) for oi in idx_sort],
    "eigenvectors_lb": [
        [round(float(np.degrees(np.arctan2(eigvecs_sorted[:,oi][1],
                                           eigvecs_sorted[:,oi][0])) % 360), 1),
         round(float(np.degrees(np.arcsin(np.clip(eigvecs_sorted[:,oi][2],-1,1)))), 1)]
        for oi in idx_sort
    ],
    "usage": ("Use principal axis as background B-field orientation in toroidal "
              "cavity sim. Test whether l=2 cavity modes align with measured axis."),
}
with open("/tmp/quadrupole_cavity_input.json", "w") as f:
    json.dump(cavity_input, f, indent=2)
print("\nTensor exported to /tmp/quadrupole_cavity_input.json")
