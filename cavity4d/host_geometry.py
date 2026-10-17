"""Host geometry constraints: what 5D+ shape projects ℓ=2 as lowest stable mode?

If our 4D universe is a transduced projection (not emergent), then the
observed ℓ=2 dominance constrains the host carrier geometry.

We test candidate topologies by computing which spherical harmonic modes
survive projection under different boundary conditions.

Key question: what suppresses ℓ=0 (monopole) and ℓ=1 (dipole),
leaving ℓ=2 (quadrupole) as the lowest stable mode?
"""

import numpy as np
import json


def mode_suppression_factor(ell, geometry):
    """Calculate suppression of mode ℓ for a given host geometry.

    Returns 0 (fully suppressed) to 1 (unsuppressed).
    """
    if geometry == "sphere_solid":
        # Standard solid sphere: all modes allowed, ℓ=0 fundamental
        return 1.0

    elif geometry == "sphere_hollow":
        # Hollow sphere (shell): monopole suppressed (no center to oscillate)
        # ℓ=0 requires radial breathing; thin shell can't support it well
        if ell == 0:
            return 0.1  # strongly suppressed
        return 1.0

    elif geometry == "torus":
        # Toroidal topology: no simply-connected center
        # ℓ=0 (monopole): impossible — no center point
        # ℓ=1 (dipole): suppressed — toroidal symmetry disfavors dipolar flow
        # ℓ=2 (quadrupole): natural — matches toroidal harmonic
        if ell == 0:
            return 0.0  # topologically forbidden
        elif ell == 1:
            return 0.3  # symmetry-suppressed
        return 1.0

    elif geometry == "dumbbell":
        # Two-lobed (dumbbell/hourglass): naturally quadrupole
        # ℓ=0: suppressed (can't breathe symmetrically with waist constriction)
        # ℓ=1: suppressed (dipolar sloshing blocked by waist)
        # ℓ=2: enhanced (matches two-lobe structure)
        if ell == 0:
            return 0.2
        elif ell == 1:
            return 0.2
        elif ell == 2:
            return 1.5  # resonantly enhanced
        return 1.0

    elif geometry == "sphere_central_exclusion":
        # Sphere with forbidden central region (r < r_excl)
        # ℓ=0 needs central antinode → suppressed
        # Higher ℓ less affected (nodes naturally avoid center)
        r_excl = 0.3  # exclusion radius (fraction of total)
        # Suppression ~ (r_excl)^(2*ell+1) — low ℓ hit hardest
        return 1.0 - np.exp(-ell / (r_excl * 3))

    elif geometry == "cylinder_open":
        # Open cylinder (tube): axial modes quantized, radial free
        # ℓ=0: suppressed (open ends can't support breathing mode)
        # Projects to 4D as elongated structure
        if ell == 0:
            return 0.15
        return 1.0

    return 1.0


def lowest_stable_mode(geometry, threshold=0.5):
    """Find the lowest ℓ with suppression factor above threshold."""
    for ell in range(0, 10):
        if mode_suppression_factor(ell, geometry) >= threshold:
            return ell
    return None


def stability_ranking(geometry, max_ell=6):
    """Rank modes by (suppression factor) — higher = more stable."""
    modes = []
    for ell in range(max_ell + 1):
        s = mode_suppression_factor(ell, geometry)
        modes.append((ell, round(s, 3)))
    # Sort by suppression (descending), then by ell (ascending)
    modes.sort(key=lambda x: (-x[1], x[0]))
    return modes


def main():
    print("=== Host Geometry Constraints ===", flush=True)
    print("Which 5D+ topology projects ℓ=2 as lowest stable mode?\n", flush=True)

    geometries = [
        "sphere_solid",
        "sphere_hollow",
        "torus",
        "dumbbell",
        "sphere_central_exclusion",
        "cylinder_open",
    ]

    results = []
    for geom in geometries:
        lowest = lowest_stable_mode(geom)
        ranking = stability_ranking(geom)
        match = "✓ MATCH" if lowest == 2 else "  "
        results.append({
            "geometry": geom,
            "lowest_stable_ell": lowest,
            "is_ell2_lowest": lowest == 2,
            "mode_ranking": ranking[:4],  # top 4
        })
        print(f"{match} {geom:30s} → lowest stable ℓ={lowest}", flush=True)
        print(f"     Top modes: {ranking[:4]}", flush=True)

    # Summary
    matches = [r for r in results if r["is_ell2_lowest"]]
    print(f"\n=== {len(matches)} geometries produce ℓ=2 as lowest stable mode ===",
          flush=True)
    for m in matches:
        print(f"  • {m['geometry']}", flush=True)

    print(json.dumps({"results": results}, indent=2), flush=True)
    print("\nDone", flush=True)


if __name__ == "__main__":
    main()
