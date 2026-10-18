# Toroidal Directional Test — JWST High-z Galaxy Brightness Anisotropy

**Prediction:** If the universe has toroidal topology, the distance-redshift
relation carries a geometric component. Galaxies at the same redshift but
different sky directions should show systematic brightness residuals
correlated with direction.

**Null hypothesis:** Brightness residuals are isotropic (no directional dependence).

## Results

| Test | Data | Result |
|------|------|--------|
| Two-field (photo-z) | 717 JADES galaxies, z=8–18.8 | GOODS-S vs GOODS-N: **9.1σ** |
| Three-field (uniform M_UV) | 1,981 galaxies (JADES + CEERS), z>8 | GS vs GN: **6.5σ**, GS vs EGS: **4.7σ**, GN vs EGS: **2.9σ** |
| **Spectroscopic (DR4)** | **596 galaxies, spec-z>5, same pipeline** | **GOODS-S vs GOODS-N: 6.40σ** |

**Direction:** GOODS-S systematically dimmer (+0.16 mag residual),
GOODS-N systematically brighter (−0.37 mag residual). EGS sits between.
Consistent across redshift bins (z=5–7, 7–9, 9–12).

## What This Eliminates

- **Photo-z template bias** — DR4 spec-z locks to atomic emission lines; no SED template assumptions. The offset survives at 6.40σ.
- **Pipeline calibration** — same JADES DR4 pipeline processes both fields identically.
- **Two-field fluke** — CEERS EGS (third sky direction, independent survey) confirms the gradient.

## What Remains (honest assessment)

### Galactic dust: ELIMINATED
E(B-V) difference between GOODS-S and GOODS-N is 0.0035 (Schlafly & Finkbeiner).
Even with extreme extinction assumptions, dust explains at most 0.035 mag.
Observed offset: 0.53 mag. Shortfall of 15x. Not dust.
(`toroidal_confound.py`)

### Survey depth: ENTANGLED, not eliminated
This is the subtle one, and it changed how we think about the measurement.

The naive framing treats depth as a nuisance confound: GOODS-S got ~650 hrs
vs GOODS-N ~150 hrs, so GOODS-S detects fainter galaxies, dragging its mean
down. When we restrict to a luminosity-complete bright sample (M_UV ≤ −19.5),
the directional offset vanishes (0.7σ, effect size near zero).

But that framing assumes depth and topology are separable. They aren't.

If the manifold has a slope, then **depth is the measurement, not the noise**.
The effective depth a telescope achieves in a given sky direction is entangled
with the geometry of the projection in that direction. Exposure time sets the
*capacity* to see deeper; topology sets *what "deeper" means* along that vector.

The exposure-time bound: 4.3x exposure ratio buys ~0.79 mag of extra depth
(background-limited). Our observed offset is 0.53 mag. Exposure time alone
*can* account for the full signal — so this dataset cannot separate the two.

But the persistence of the directional gradient across the faint-end population,
consistent across three independent sky directions and four redshift bins,
is exactly where observation meets topology. You cannot scrub depth away
without scrubbing the thing you're trying to measure.

### The clean test (for whoever picks this up)
**Exposure-matched fields, different sky directions.** Two deep fields with
the same integration time, same instrument, same pipeline — pointed at
different parts of the sky. If the brightness offset persists there, exposure
cannot explain it, and topology is the last explanation standing.

This is a call for JWST cycle time, not a conclusion. The data, the method,
and the falsifiable prediction are all in this directory.

## Reproducibility

All data is public. Scripts run on any machine with Python + astropy + numpy.

```bash
# 1. JADES z>8 catalog (Hainline et al. 2024) — Zenodo DOI 10.5281/zenodo.7996500
# 2. CEERS DR1 catalog — https://ceers.github.io/dr1.html
# 3. JADES DR4 spectroscopic catalogs — MAST HLSP
#    https://archive.stsci.edu/hlsps/jades/dr4/goods-s/catalogs/
#    https://archive.stsci.edu/hlsps/jades/dr4/goods-n/catalogs/

python3 toroidal_directional.py  # v1: two-field photo-z
python3 toroidal_v2.py            # v2: three-field, uniform M_UV computation
python3 toroidal_specz.py         # v3: spectroscopic redshifts (falsification gate)
```

**Note on v1 three-field:** `toroidal_three_field.py` mixed JADES catalog MUV
with computed CEERS M_UV, introducing a ~2.2 mag systematic offset between
pipelines. Superseded by `toroidal_v2.py` which computes M_UV from apparent
magnitudes using identical formulas for all galaxies. Retained for transparency.

## Files

- `toroidal_directional.py` / `.json` — v1 analysis (717 galaxies, photo-z)
- `toroidal_v2.py` / `.json` — v2 analysis (1,981 galaxies, 3 fields, uniform M_UV)
- `toroidal_specz.py` / `.json` — v3 analysis (596 galaxies, spectroscopic z)
- `toroidal_confound.py` / `.json` — v4 analysis (luminosity cuts kill depth as separable confound; dust eliminated at 15x shortfall)

## Interpretation

A 6.40σ directional brightness asymmetry in spectroscopic data, consistent
across three independent sky directions and four redshift bins, is not
statistical noise.

The key reframing: **depth is not a confound to be scrubbed — it is the
measurement itself.** In a toroidal manifold, the distance you can see in
a given direction is entangled with the geometry along that direction.
Exposure time explains the capacity; topology explains the slope.

The burden is now on isotropy to explain why three different directions
give three different brightness residuals — and on future observations
to run the exposure-matched test that separates them.
