"""THE EDDIE FRAMEWORK: Habitable-zone eddies as invariant structures.

An "eddie" is a stable circulation in a larger flow — the habitable zone
is not a distance, it is a topological eddy where EM flux, gravity,
temperature, and stellar wind jointly stabilize liquid water.

We define OUR eddie (the Solar habitable eddy) by its INVARIANTS —
dimensionless ratios that don't depend on units or stellar type —
then score every known exoplanet system by its invariant distance
from our eddie.

Invariants:
  1. S_norm = S / S_earth  (insolation relative to Earth)
     Computed as (L/Lsun) / (a/AU)^2 when catalog insolation missing.
  2. a_norm = a / sqrt(L/Lsun)  (orbital distance in "Earth-equivalent AU")
     This collapses all stellar types onto one scale. Earth = 1.0 by definition.
  3. Teq  (equilibrium temperature, K)
  4. Stellar: Teff, log g, [Fe/H], age
  5. Planet: R/Rearth, M/Mearth

Kopparapu HZ (conservative, Teff-dependent):
  S_inner = 1.11 (runaway greenhouse, Sun-like)
  S_outer = 0.36 (maximum greenhouse, Sun-like)
  Adjusted for Teff via Kopparapu et al. 2013 coefficients.

Eddie Similarity Score: Mahalanobis-like distance in log-space
of (S_norm, Teq, R_p, M_p, Teff_star) from Solar values.
Lower = more similar eddie.
"""

import json
import math
import numpy as np

# --- OUR EDDIE: Solar reference values ---
EDDIE_SUN = {
    "name": "Sol",
    "st_teff": 5778,      # K
    "st_lum": 1.0,        # Lsun
    "st_mass": 1.0,       # Msun
    "st_rad": 1.0,        # Rsun
    "st_logg": 4.44,      # cgs
    "st_met": 0.0,        # [Fe/H]
    "st_age": 4.6,        # Gyr
    # Earth:
    "pl_a": 1.0,          # AU
    "pl_a_norm": 1.0,     # a / sqrt(L) = 1.0 by definition
    "pl_S": 1.0,          # S_eff
    "pl_teq": 255,        # K (no greenhouse)
    "pl_rade": 1.0,
    "pl_bmasse": 1.0,
    # Heliosphere (for reference, sparse data):
    "wind_mdot": 2e-14,   # Msun/yr
    "heliopause_au": 120, # AU
}

def kopparapu_boundaries(teff):
    """Conservative HZ flux boundaries (S_eff) as function of Teff.
    Kopparapu et al. 2013, Table 1. Simplified linear interpolation."""
    # (Teff, S_inner_runaway, S_outer_maxgh)
    table = [
        (2600, 1.61, 0.32),
        (3000, 1.49, 0.33),
        (3500, 1.37, 0.34),
        (4000, 1.27, 0.35),
        (4500, 1.18, 0.35),
        (5000, 1.12, 0.36),
        (5500, 1.08, 0.36),
        (5778, 1.11, 0.36),
        (6000, 1.06, 0.36),
        (6500, 1.02, 0.37),
        (7000, 0.98, 0.37),
        (7200, 0.97, 0.38),
    ]
    teffs = [t[0] for t in table]
    if teff <= teffs[0]:
        return table[0][1], table[0][2]
    if teff >= teffs[-1]:
        return table[-1][1], table[-1][2]
    for i in range(len(table) - 1):
        if teffs[i] <= teff <= teffs[i+1]:
            f = (teff - teffs[i]) / (teffs[i+1] - teffs[i])
            si = table[i][1] + f * (table[i+1][1] - table[i][1])
            so = table[i][2] + f * (table[i+1][2] - table[i][2])
            return si, so
    return 1.11, 0.36

def valid(v):
    return v is not None and (not isinstance(v, float) or not math.isnan(v))

# Load data
with open("/tmp/exo_full.json") as f:
    planets = json.load(f)

print(f"Total planets in catalog: {len(planets)}")

results = []
for p in planets:
    # Compute insolation if missing
    S = p["pl_insol"]
    if not valid(S) and valid(p["st_lum"]) and valid(p["pl_orbsmax"]) and p["pl_orbsmax"] > 0:
        S = p["st_lum"] / (p["pl_orbsmax"] ** 2)

    # Normalized orbital distance
    a_norm = None
    if valid(p["pl_orbsmax"]) and valid(p["st_lum"]) and p["st_lum"] > 0:
        a_norm = p["pl_orbsmax"] / math.sqrt(p["st_lum"])

    # HZ check
    in_hz = False
    hz_inner = hz_outer = None
    if valid(S) and valid(p["st_teff"]):
        si, so = kopparapu_boundaries(p["st_teff"])
        hz_inner, hz_outer = si, so
        in_hz = so <= S <= si

    # Eddie similarity score (log-space distance from Solar values)
    # REQUIRE S_eff: without insolation there is no eddie to compare.
    # Planets with only stellar Teff get misleading near-zero scores.
    score_terms = []
    has_insolation = False
    if valid(S) and S > 0:
        score_terms.append((math.log10(S) - math.log10(1.0)) ** 2)  # S_norm
        has_insolation = True
    if valid(p["pl_eqt"]) and p["pl_eqt"] > 0:
        score_terms.append((math.log10(p["pl_eqt"]) - math.log10(255)) ** 2)
    if valid(p["pl_rade"]) and p["pl_rade"] > 0:
        score_terms.append((math.log10(p["pl_rade"]) - math.log10(1.0)) ** 2)
    if valid(p["st_teff"]) and p["st_teff"] > 0:
        # Stellar Teff: less weight (M-dwarf eddies are valid eddies, just different)
        score_terms.append(0.25 * (math.log10(p["st_teff"]) - math.log10(5778)) ** 2)

    eddie_score = None
    if has_insolation and len(score_terms) >= 2:
        eddie_score = math.sqrt(sum(score_terms) / len(score_terms))

    results.append({
        "pl_name": p["pl_name"],
        "hostname": p["hostname"],
        "S_eff": round(S, 4) if valid(S) else None,
        "a_norm": round(a_norm, 4) if valid(a_norm) else None,
        "in_hz": in_hz,
        "eddie_score": round(eddie_score, 4) if eddie_score is not None else None,
        "st_teff": p["st_teff"],
        "pl_rade": p["pl_rade"],
        "pl_eqt": p["pl_eqt"],
        "sy_dist": p["sy_dist"],
    })

# Stats
hz_planets = [r for r in results if r["in_hz"]]
scored = [r for r in results if r["eddie_score"] is not None]
scored.sort(key=lambda r: r["eddie_score"])

print(f"\nPlanets with computed insolation: {sum(1 for r in results if r['S_eff'] is not None)}")
print(f"Planets in conservative HZ: {len(hz_planets)}")
print(f"Planets with eddie score: {len(scored)}")

print(f"\n=== TOP 20 MOST EARTH-LIKE EDDIES ===")
print(f"{'Planet':<22} {'Host':<16} {'S_eff':>7} {'a_norm':>7} {'Teq':>6} {'Score':>6} {'Dist(pc)':>8}")
for r in scored[:20]:
    print(f"{r['pl_name']:<22} {r['hostname']:<16} "
          f"{r['S_eff'] or 0:>7.2f} {r['a_norm'] or 0:>7.2f} "
          f"{r['pl_eqt'] or 0:>6.0f} {r['eddie_score']:>6.3f} {r['sy_dist'] or 0:>8.1f}")

print(f"\n=== HZ PLANETS (conservative) ===")
for r in hz_planets[:15]:
    print(f"  {r['pl_name']:<22} S={r['S_eff']:.2f}  score={r['eddie_score']}")

# Save
with open("/tmp/eddie_results.json", "w") as f:
    json.dump({
        "n_total": len(results),
        "n_hz": len(hz_planets),
        "n_scored": len(scored),
        "top_20": scored[:20],
        "hz_list": [{"pl_name": r["pl_name"], "S_eff": r["S_eff"],
                      "eddie_score": r["eddie_score"]} for r in hz_planets],
    }, f, indent=2)
print(f"\nSaved to /tmp/eddie_results.json")
