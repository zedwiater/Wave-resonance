# LOCAL EDDY vs MACRO MANIFOLD: Faraday Rotation Topology

## The Question

If we sit inside a local eddy (heliosphere + Local Interstellar Cloud)
embedded in a larger toroidal manifold, then extragalactic Faraday rotation
should carry two signatures: the local Galactic disk dynamo (known) and
any larger-scale coherent topology (unknown).

## Local Eddy Baseline (literature)

| Parameter | Value | Source |
|-----------|-------|--------|
| LIC density | n(HI) ~0.2 cm⁻³ | Redfield & Linsky 2008 |
| LIC temperature | ~6300 K | Redfield & Linsky 2008 |
| LIC velocity | 26 km/s from (l,b)=(3°,+16°) | IBEX / Ulysses |
| Local B-field | ~3 μG toward (l,b)~(40°,+50°) | Frisch et al. |
| Heliopause | 120 AU | Voyager 1 (2012), Voyager 2 (2018) |
| VLISM B-field | ~0.5 nT, draped | Voyager magnetometer |
| IBEX ribbon | Circular, center (l,b)~(33°,+55°) | IBEX ENA maps |

The IBEX ribbon center and local B-field direction are roughly aligned —
the local eddy has a coherent magnetic orientation.

## Macro: NVSS Rotation Measures (37,543 sources)

### Test 1: Galactic disk confirmed
Mean RM flips across the plane: +6.2 rad/m² (north) vs −12.8 rad/m² (south).
Inner Galaxy shows stronger antisymmetry (+7.5 / −21.8). This is the standard
toroidal disk field. No surprise.

### Test 2: High-latitude quadrupole — UNEXPECTED
At |b| > 20° (away from disk contamination), spherical harmonic fit gives:

- Monopole: 3.7 rad/m²
- Dipole: 9.6 rad/m²
- **Quadrupole: 68.0 rad/m²** (p < 0.0001, permutation test)

The quadrupole is **7× stronger than the dipole** at high latitude.
Standard halo models predict dipole-dominated smooth fields. A dominant
quadrupole means coherent large-scale structure that is NOT the disk.

Possible explanations:
1. Galactic halo X-shaped field (known, but usually weaker than this)
2. Local magnetized structures (Loop I, Local Bubble wall)
3. Extragalactic / intergalactic coherent field
4. Larger-scale toroidal manifold topology

We cannot distinguish these with RM alone. But the signal is real and
demands explanation beyond "disk + turbulent halo."

### Test 3: JWST anisotropy directions
- GOODS-S (l=223.6°, b=−54.5°): mean RM = +20.2 rad/m²
- GOODS-N (l=125.9°, b=+54.8°): mean RM = +13.6 rad/m²

Both positive, small difference. No smoking gun linking RM to the
brightness anisotropy — but also no contradiction. Different physics
(magnetic vs geometric), different scales.

## Interpretation

The Faraday sky is not just "disk + noise." There is a highly significant
quadrupole at high Galactic latitude that standard models underpredict.

Whether this is Galactic halo complexity or something larger, it shows the
same lesson as the JWST work: **the sky has directions, and isotropic
baselines miss them.**

## Files
- `rm_topology.py` — full pipeline: Vizier download → parse → Galactic conversion → harmonic fit
- `rm_analysis.json` — numerical results

## Reproducibility
```bash
# NVSS RM catalog (Taylor et al. 2009) from Vizier
curl "https://vizier.cds.unistra.fr/viz-bin/asu-tsv?-source=J/ApJ/702/1230/catalog&-out.max=40000" -o nvss_rm.tsv
python3 rm_topology.py
```
