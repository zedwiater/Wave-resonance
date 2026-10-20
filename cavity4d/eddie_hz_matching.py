"""Eddie Hz-matching: estimated Schumann cavity fundamental for HZ planets.

f_est = 7.83 Hz / (R/R_earth)  [Schumann scales as 1/R from Earth's measured]
'Neural band' = 5-13 Hz (theta+alpha; covers measured 6.2 Hz fundamental,
12.4 Hz harmonic, and Earth's own 7.83 Hz).
Radii: NASA Exoplanet Archive pscomppars (one row per planet), cached locally.
Output: eddie_hz_matching.txt
"""
import json, csv
from pathlib import Path

here = Path(__file__).parent
d = json.load(open(here / "eddie_results.json"))
names = [e["pl_name"] for e in d["hz_list"]]

radii = {}
with open(here / "pscomppars_radii.csv") as f:
    for row in csv.DictReader(f):
        try:
            radii[row["pl_name"]] = float(row["pl_rade"])
        except (TypeError, ValueError, KeyError):
            pass

out = []
out.append("Eddie Hz-matching — estimated Schumann fundamentals, conservative HZ planets")
out.append("f_est = 7.83 / (R/R_earth); neural band = 5-13 Hz")
res = []
missing = []
for n in names:
    r = radii.get(n)
    if r and r > 0:
        res.append((n, r, 7.83 / r, 5.0 <= 7.83 / r <= 13.0))
    else:
        missing.append(n)
res.sort(key=lambda x: abs(x[2] - 7.83))
inband = [r for r in res if r[3]]
out.append(f"\n{len(names)} conservative-HZ planets; {len(res)} with measured radii; "
           f"{len(inband)} in the 5-13 Hz neural band")
out.append("\nclosest to Earth's 7.83 Hz fundamental:")
for name, rade, f, band in res[:15]:
    out.append(f"  {name}: R={rade:.2f} R_earth, f_est={f:.2f} Hz {'[IN BAND]' if band else ''}")
out.append("\nfull in-band list (sorted by |f - 7.83|):")
for name, rade, f, band in inband:
    out.append(f"  {name}: R={rade:.2f}, f={f:.2f} Hz")
out.append(f"\nGap: {len(missing)} of {len(names)} HZ planets have NO measured radius"
           " — no Hz estimate possible from transit data (RV-only discoveries).")
out.append("No-radius names (first 20): " + ", ".join(missing[:20]))

p = here / "eddie_hz_matching.txt"
p.write_text("\n".join(out) + "\n")
print("\n".join(out))
