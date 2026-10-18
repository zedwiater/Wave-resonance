# THE EDDIE FRAMEWORK: Habitable Zones as Invariant Eddies

## The Idea

A habitable zone is not a distance. It is a **stable eddy** — a topological
circulation where electromagnetic flux, gravitational binding, temperature,
and stellar wind jointly stabilize the conditions for liquid water.

We are an eddy in a bigger flow. The question: where are the other eddies
with the same invariant signature?

## Our Eddie: The Solar Reference

Defined by invariants (dimensionless ratios, not units):

| Axis | Solar Value | Notes |
|------|-------------|-------|
| **EM flux** | S = 1.0 S⊕ | 1361 W/m² at 1 AU |
| **Normalized orbit** | a/√L = 1.0 | Earth-equivalent AU; collapses all stellar types to one scale |
| **Equilibrium temp** | 255 K | No greenhouse; 288 K with |
| **Stellar** | G2V, 5778 K, [Fe/H]=0, 4.6 Gyr | log g = 4.44 |
| **Planet** | 1.0 R⊕, 1.0 M⊕ | Rocky |
| **Heliosphere** | Ṁ=2e-14 M☉/yr, HP~120 AU | Solar wind vs ISM balance |
| **Magnetic** | 11-yr cycle | Planetary magnetosphere shielding |

## Data: What We Have vs What We Need

Source: NASA Exoplanet Archive (TAP), 6,451 confirmed planets (Oct 2026).

| Axis | Coverage | Status |
|------|----------|--------|
| EM flux / insolation | 1,818 planets | ✅ Good (computed from L★/a² where missing) |
| Orbital / gravity | 3,955 planets | ✅ Good |
| Temperature (Teq) | 1,775 planets | ✅ Good |
| Stellar (Teff, log g, [Fe/H]) | 5,678 planets | ✅ Good |
| Planet radius | Partial | ⚠️ Missing for most RV planets |
| **Heliosphere / stellar wind** | **<20 stars** | ❌ **Critical gap** |
| **Magnetic / activity** | Sparse | ❌ Major gap |

**The heliosphere is the hole.** We can compare light, gravity, and temperature
across thousands of systems. But stellar wind ram pressure — the thing that
defines the astrospheric boundary, strips atmospheres, and modulates cosmic
rays — is measured for fewer than 20 stars (Wood et al., astrospheric Ly-α).
Without it, we cannot compare the full eddy.

## Results

- **157 planets** in optimistic HZ (0.25 < S < 1.50)
- **109 planets** in conservative HZ (Kopparapu boundaries)
- **20 rocky HZ planets** (0.5 < R < 2.0 R⊕) — the similar-eddie candidates

### Top Similar Eddies (by invariant distance from Solar)

| Planet | Host | S⊕ | R⊕ | Teq | Teff★ | Dist |
|--------|------|-----|-----|-----|-------|------|
| Kepler-1649 c | Kepler-1649 | 0.75 | 1.06 | 234K | 3240K | 92 pc |
| Kepler-438 b | Kepler-438 | 1.40 | 1.12 | — | 3748K | — |
| K2-72 e | K2-72 | 1.20 | 1.29 | — | 3360K | 66 pc |
| LP 890-9 c | LP 890-9 | 0.91 | 1.37 | 272K | 2850K | 32 pc |
| Kepler-452 b | Kepler-452 | 1.10 | 1.63 | 265K | 5757K | 552 pc |

**Kepler-452 b** is the standout: Sun-like star (5757K), 1.10 S⊕, 1.63 R⊕.
The closest true Solar-eddie analog by stellar type.

**Caveat:** Most top candidates orbit M-dwarfs. Same insolation, radically
different eddy topology — tidally locked, flare-active stars, no Solar-like
heliosphere. The invariant score captures EM/thermal similarity but cannot
capture the wind/magnetic axes where data doesn't exist.

## The Invariant Method

For each planet, compute dimensionless distance from Solar values in log-space:

  score = √[ Σ (log10(X/X☉))² / N ]

over available invariants (S, Teq, Rp, Teff★ with reduced weight).
Lower score = more similar eddy. Requires insolation as anchor.

Normalized orbital distance `a/√(L/L☉)` puts every system on the same scale:
Earth = 1.0 by definition, regardless of stellar type.

## Next: Closing the Heliosphere Gap

The framework is ready. The data gap is clear. What's needed:
1. Stellar mass-loss rates (Ṁ) for HZ planet hosts — UV spectroscopy (HST/COS)
2. Astrospheric Ly-α absorption — the only direct wind probe
3. Stellar magnetic cycle monitoring — photometric/spectroscopic time series

Without the wind axis, we're comparing eddies by light and gravity alone —
like comparing oceans by surface color without measuring currents.

## Files

- `eddie_framework.py` — full pipeline: TAP query → invariants → HZ filter → scoring
- `eddie_results.json` — top candidates and HZ lists

## Reproducibility

```bash
# Pull data from NASA Exoplanet Archive TAP
curl "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=SELECT+pl_name,hostname,pl_orbsmax,pl_rade,pl_bmasse,pl_eqt,pl_insol,st_teff,st_rad,st_mass,st_lum,st_logg,st_met,st_age,sy_dist,ra,dec+FROM+ps+WHERE+default_flag%3D1&format=json" -o exo_full.json

python3 eddie_framework.py
```
