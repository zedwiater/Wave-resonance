# Captured spectra

Full per-tick OAM spectra from the wave48 lattice expansions. Each `.npz`
holds `amps[ticks,48]` (complex128), per-mode `power`, total energy, trapped
counts, lattice positions. The matching `.json` sidecar records params,
code version, and the sha of the amps array — the sidecar summaries
reproduce the decay sweep exactly.

- `canonical_s7_e42` — 5 ticks, seed 7, E0=42 (amps sha `b27696c9b7d37e0e`)
- `decay_bh_g001` — 200 ticks, gamma=0.01, black-hole gain 1.05, seed 21
  (amps sha `4f4d9d5383ce81a9`)
- `decay_loss_g003` — 200 ticks, gamma=0.03, no gain, seed 21
  (amps sha `8670113b29dca95d`)

The two decay files are split into `.partNN` chunks (upload transport
limit): reassemble with

    cat decay_bh_g001.npz.part* > decay_bh_g001.npz
    cat decay_loss_g003.npz.part* > decay_loss_g003.npz

then verify: `python3 -c "import numpy as np,hashlib;
d=np.load('decay_bh_g001.npz'); print(hashlib.sha256(d['amps'].tobytes()).hexdigest()[:16])"`
should print the sha from the sidecar.
