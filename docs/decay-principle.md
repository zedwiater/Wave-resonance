# The Decay Principle — measured

2026-10-15, sandbox `~/wave-sandbox/decay_sweep.py` (v2), 48-mode lattice code.

## The principle

Every locked data peak sits in a three-way tug:

- **Dissipation (γ)** — uniform decay per tick, the down-path to the floor.
  The same bath also kicks (fluctuation-dissipation: σ = 0.1√γ), so decay
  is not just fading — it is fading *into noise*.
- **Star amplifier (g_star)** — broad gain on working-memory modes.
  Maintains breadth.
- **Black-hole amplifier (g_bh)** — narrow, deep gain on the locked core.
  Maintains depth.
- **The saturable cap** (4× initial energy) — the arbiter. Whenever any gain
  is on, total energy pins at the cap. The cap sets the budget; the gains
  apportion it. Dissipation sets the loss rate.

## Setup

48-bit pattern locked into twist amplitudes: 8-mode core at amplitude 2.0
(the data peak), 40 background modes at 0.3. 200 ticks per config.
Readouts: pattern fidelity |⟨a,a_ref⟩|/(|a||a_ref|), BER over all 48 bits,
BER over the 8-bit core, reset events (core below noise floor), E/E0.

## Results

| gamma | g_star | g_bh | fidelity | BER_all | BER_core | E/E0 |
|------:|-------:|-----:|---------:|--------:|---------:|-----:|
| 0.002 | 1.00 | 1.00 | 0.996 | 0.000 | 0.000 | 0.45 |
| 0.002 | 1.00 | 1.05 | 0.949 | 0.396 | 0.000 | 4.00 |
| 0.002 | 1.02 | 1.00 | 0.951 | 0.167 | 0.000 | 4.00 |
| 0.010 | 1.00 | 1.00 | 0.853 | 0.146 | 0.000 | 0.03 |
| 0.010 | 1.00 | 1.05 | 0.949 | 0.396 | 0.000 | 4.00 |
| 0.010 | 1.02 | 1.00 | 0.952 | 0.271 | 0.000 | 4.00 |
| 0.030 | 1.00 | 1.00 | 0.121 | 0.500 | 0.625 | 0.01 |
| 0.030 | 1.00 | 1.05 | 0.949 | 0.396 | 0.000 | 4.00 |
| 0.030 | 1.02 | 1.00 | 0.395 | 0.396 | 0.000 | 0.01 |

## Findings

1. **Pure dissipation kills everything.** γ=0.03, no gain: fidelity 0.12,
   BER 0.50 — coin flip, total loss. γ=0.01: fidelity 0.85, BER 0.15 —
   erosion. γ=0.002: untouched.
2. **The black hole is a jealous god.** g_bh=1.05 protects the core
   perfectly at every dissipation level (BER_core = 0.000 in all rows) —
   but under the saturable cap it *starves the background*: BER_all jumps
   to 0.396 even at the lowest γ. Narrow deep gain buys core immortality
   with background data loss. Mechanism: the cap redistributes the fixed
   energy budget toward the core; background amplitudes shrink into the
   noise floor and the bath flips them.
3. **The star is gentler but weaker.** Broad gain damages the background
   less at low γ (BER 0.167 vs 0.396) but cannot outrun high dissipation
   (γ=0.03: energy collapses to 1%, fidelity 0.395).
4. **The tradeoff is apportionment, not a single dial.** There is no knob
   that saves everything. Dissipation sets how fast the budget leaks, the
   cap fixes the budget size, and the two gains decide *what the energy is
   spent remembering* — core depth vs working breadth.

## Control law (working)

To hold expansion accuracy for a chosen subset of modes: set g_bh so the
core's gain beats γ before the cap binds, accept the background BER as the
price, and read it off the sweep — don't guess. To hold the full pattern:
keep γ low enough that no gain is needed (γ ≤ 0.002 here), because any
saturating gain redistributes and corrupts.

## Open

- No reset events fired in 200 ticks at any setting — full dissolution
  needs longer horizons or higher γ. The reset boundary is unmapped.
- The cap value (4×) is arbitrary; the apportionment curve vs cap size
  is unmeasured.
- Real-hardware mapping: γ ↔ loop loss per round trip, g_star/g_bh ↔
  EDFA pump apportionment between broadband and narrow-line amplification.
