"""HIERARCHICAL EDDY CASCADE: Magnetosphere step-down from Galactic Center.

The flat 5-axis test was the wrong geometry. Cosmic structure is nested
eddies, not weather vanes in a yard. This test builds the tier hierarchy
and measures the angular step-down between adjacent tiers.

TIERS (outermost to innermost):
  Tier 4 (cosmic):    CMB dipole — bulk flow vs cosmic rest frame
  Tier 3 (galactic):  Sgr A* / Fermi bubbles — SMBH outflow axis (poloidal)
  Tier 2 (halo):      RM quadrupole principal axis — halo magnetic topology
  Tier 1 (local ISM): LIC flow vector + local B-field — interstellar eddy
  Tier 0 (micro):     IBEX ribbon center — heliospheric boundary

MATRIX TEST:
  For each adjacent tier pair, compute angular separation.
  Null: step-down angles are random (uniform 0-90° for axes).
  Nested-eddy prediction: step-downs show systematic pattern —
    either small (aligned cascade) or harmonically related
    (e.g., ~45°/90° rotations between poloidal and toroidal components).

FERMI BUBBLE INTERSECTION:
  Do the bubbles (SMBH outflow cones) align with the RM quadrupole axis?
  If the quadrupole is halo recirculation driven by GC outflow,
  the quadrupole symmetry axis should be near the bubble axis.
"""

import numpy as np
import math
import json

def unit_vec(l_deg, b_deg):
    l, b = np.radians(l_deg), np.radians(b_deg)
    return np.array([np.cos(b)*np.cos(l), np.cos(b)*np.sin(l), np.sin(b)])

def ang_sep(v1, v2):
    return np.degrees(np.arccos(np.clip(np.dot(v1, v2), -1, 1)))

def axial_sep(v1, v2):
    s = ang_sep(v1, v2)
    return min(s, 180 - s)

# ============ TIER DEFINITIONS ============
# Tier 4: CMB dipole (our velocity relative to CMB rest frame)
cmb_dipole = (264.0, 48.0)

# Tier 3: Galactic Center / SMBH
# Sgr A* at (l,b) = (359.94°, -0.05°) ≈ (0,0)
# Fermi bubbles: bipolar outflow, axis ~perpendicular to plane
# Bubble centroids: North bubble ~(0°, +25°), South ~(0°, -25°)
# The outflow AXIS (poloidal) points along ±b through GC
# Use north bubble axis as representative
sgr_a = (0.0, 0.0)
fermi_north_axis = (0.0, 90.0)   # bubble outflow axis (north)
fermi_south_axis = (0.0, -90.0)

# Tier 2: RM quadrupole principal axis
# Extract from our NVSS fit by reconstructing the quadrupole tensor
# and finding its principal eigenvector.
# We saved coefficients; reconstruct here.
print("=== Extracting RM Quadrupole Principal Axis ===")

# Re-run the harmonic fit to get eigenvectors
# (Loading the data again for the tensor)
ras, decs, rms = [], [], []
with open("/tmp/nvss_rm.tsv") as f:
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        p = line.strip().split("\t")
        try:
            float(p[10])  # check RM is numeric
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
high = np.abs(b_gal) > 20
lh, bh, rmh = l_gal[high], b_gal[high], rms[high]

l_rad = np.radians(lh); b_rad = np.radians(bh)
x = np.cos(b_rad)*np.cos(l_rad)
y = np.cos(b_rad)*np.sin(l_rad)
z = np.sin(b_rad)

# Quadrupole basis: xy, xz, yz, x²-y², (3z²-1)/2
# Build symmetric traceless tensor Q_ij from fit coefficients
# RM_quad = Q_xx(x²-1/3) + Q_yy(y²-1/3) + Q_zz(z²-1/3) + 2Q_xy·xy + 2Q_xz·xz + 2Q_yz·yz
# Our basis: [xy, xz, yz, x²-y², 3z²-1]
# Map: c_xy → 2Q_xy = c0; c_xz → 2Q_xz = c1; c_yz → 2Q_yz = c2
#      c_x2y2 → Q_xx - Q_yy = c3
#      c_3z2m1 → Q_zz·3 - (Q_xx+Q_yy+Q_zz) ... with trace=0: Q_zz = -(Q_xx+Q_yy)
#      3z²-1 = 3(z²-1/3), so c4·(3z²-1) = 3·c4·(z²-1/3) → Q_zz = 3·c4 ... 
#      Actually: coefficient of z² is 3·c4, coefficient of x² from (x²-y²) is c3
#      Q_xx = c3/2 + t, Q_yy = -c3/2 + t, Q_zz = 3c4·(2/3)... let me just solve properly.

A_quad = np.column_stack([x*y, x*z, y*z, x*x - y*y, 3*z*z - 1])
cq, _, _, _ = np.linalg.lstsq(A_quad, rmh, rcond=None)
c_xy, c_xz, c_yz, c_x2y2, c_3z2 = cq

# Q_xy = c_xy/2, Q_xz = c_xz/2, Q_yz = c_yz/2
# Q_xx - Q_yy = c_x2y2
# From 3z²-1 term: contributes 3·c_3z2·z² - c_3z2
# In tensor form: Q_zz·z² coefficient is 3·c_3z2 (relative to x²,y² having 0 from this term)
# With traceless: Q_xx + Q_yy + Q_zz = 0
# Q_xx = a, Q_yy = a - c_x2y2, Q_zz = -2a + c_x2y2
# Coefficient of z² in RM: Q_zz = 3·c_3z2 → -2a + c_x2y2 = 3·c_3z2 → a = (c_x2y2 - 3·c_3z2)/2
a = (c_x2y2 - 3*c_3z2) / 2
Q = np.array([
    [a,            c_xy/2,       c_xz/2],
    [c_xy/2,       a - c_x2y2,   c_yz/2],
    [c_xz/2,       c_yz/2,       -2*a + c_x2y2],
])
print(f"Quadrupole tensor trace: {np.trace(Q):.6f} (should be ~0)")

eigenvals, eigenvecs = np.linalg.eigh(Q)
# Principal axis = eigenvector of largest |eigenvalue|
idx = np.argmax(np.abs(eigenvals))
principal = eigenvecs[:, idx]
# Convert back to (l, b)
b_p = np.degrees(np.arcsin(np.clip(principal[2], -1, 1)))
l_p = np.degrees(np.arctan2(principal[1], principal[0])) % 360
print(f"Quadrupole eigenvalues: {eigenvals}")
print(f"Principal axis: (l, b) = ({l_p:.1f}°, {b_p:.1f}°)")
print(f"Eigenvalue ratios: {sorted(np.abs(eigenvals))}")

rm_quad_axis = (l_p, b_p)

# Tier 1: Local ISM
lic_flow = (3.0, 16.0)      # incoming direction; outflow is antipodal
local_bfield = (40.0, 50.0)  # Frisch et al.

# Tier 0: Heliosphere
ibex_ribbon = (33.0, 55.0)

# ============ HIERARCHICAL STEP-DOWN MATRIX ============
tiers = [
    ("T4 CMB dipole",     cmb_dipole),
    ("T3 Fermi N-axis",   fermi_north_axis),
    ("T3 Sgr A* dir",     sgr_a),
    ("T2 RM quad axis",   rm_quad_axis),
    ("T1 Local B-field",  local_bfield),
    ("T1 LIC flow",       lic_flow),
    ("T0 IBEX ribbon",    ibex_ribbon),
]

print("\n=== Hierarchical Step-Down Matrix (axial separations) ===")
print(f"{'':20s}", end="")
for name, _ in tiers:
    print(f"{name[:14]:>15s}", end="")
print()
for n1, (l1, b1) in tiers:
    print(f"{n1:20s}", end="")
    v1 = unit_vec(l1, b1)
    for n2, (l2, b2) in tiers:
        v2 = unit_vec(l2, b2)
        print(f"{axial_sep(v1, v2):>15.1f}", end="")
    print()

# Adjacent-tier step-downs
print("\n=== Adjacent Tier Step-Downs ===")
cascade = [
    ("T4 CMB", cmb_dipole),
    ("T3 Fermi axis", fermi_north_axis),
    ("T2 RM quad", rm_quad_axis),
    ("T1 Local B", local_bfield),
    ("T0 IBEX", ibex_ribbon),
]
for i in range(len(cascade)-1):
    n1, (l1, b1) = cascade[i]
    n2, (l2, b2) = cascade[i+1]
    s = axial_sep(unit_vec(l1, b1), unit_vec(l2, b2))
    print(f"  {n1} → {n2}: {s:.1f}°")

# Fermi bubble / RM quadrupole intersection test
print("\n=== SMBH Outflow × RM Quadrupole ===")
s_bubble_quad = axial_sep(unit_vec(*fermi_north_axis), unit_vec(*rm_quad_axis))
print(f"Fermi N-axis vs RM quadrupole axis: {s_bubble_quad:.1f}°")
if s_bubble_quad < 20:
    print(">>> ALIGNED: quadrupole symmetry follows SMBH outflow — halo recirculation driven by GC")
elif s_bubble_quad > 70:
    print(">>> PERPENDICULAR: quadrupole orthogonal to outflow — toroidal wrap around poloidal jet")
else:
    print(">>> OBLIQUE: intermediate coupling")

s_gc_quad = axial_sep(unit_vec(*sgr_a), unit_vec(*rm_quad_axis))
print(f"Sgr A* direction vs RM quadrupole axis: {s_gc_quad:.1f}°")

# Harmonic test: are step-downs near 0°, 45°, 90° (harmonic ratios)?
print("\n=== Harmonic Resonance Check ===")
steps = []
for i in range(len(cascade)-1):
    _, (l1, b1) = cascade[i]
    _, (l2, b2) = cascade[i+1]
    steps.append(axial_sep(unit_vec(l1, b1), unit_vec(l2, b2)))
for s in steps:
    nearest = min([0, 45, 90], key=lambda h: abs(s - h))
    print(f"  Step {s:.1f}° → nearest harmonic ({nearest}°): offset {abs(s-nearest):.1f}°")

with open("/tmp/hierarchical_cascade.json", "w") as f:
    json.dump({
        "tiers": {n: {"l": l, "b": b} for n, (l, b) in tiers},
        "rm_quadrupole_axis": {"l": round(float(l_p), 1), "b": round(float(b_p), 1)},
        "rm_quadrupole_eigenvalues": [round(float(e), 2) for e in sorted(eigenvals)],
        "cascade_steps": [round(float(s), 1) for s in steps],
        "fermi_vs_quadrupole": round(float(s_bubble_quad), 1),
        "sgra_vs_quadrupole": round(float(s_gc_quad), 1),
    }, f, indent=2)
print("\nSaved to /tmp/hierarchical_cascade.json")
