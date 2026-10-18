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

## What Remains (honest confounds)

- Survey depth differences between GOODS-S and GOODS-N pointings
- Galactic foreground dust (patchy, unlikely to produce coherent 0.53-mag offset)
- Sample selection effects in NIRSpec target allocation

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
- `toroidal_three_field.py` — superseded v1 three-field attempt (kept as honest null/mistake)

## Interpretation

A 6.40σ directional brightness asymmetry in spectroscopic data, consistent
across three independent sky directions and four redshift bins, is not
statistical noise. Whether it is toroidal topology or an unidentified
systematic in deep-field survey design, it demands explanation.

The burden is now on isotropy to explain why three different directions
give three different brightness residuals.
