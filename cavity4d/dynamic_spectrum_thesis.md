# Dynamic Wave Spectrum: The Refined Thesis

## The Pivot

Earlier work in this repo tested whether particle *masses* fit toroidal
harmonic assignments (`inverse_transduction_sweep.py`, `generational_sweep.py`).
Both returned null results (p=0.62, no toroidal fit for lepton ratios).

This is not a failure. It is a redirect.

**Mass is the wrong avenue.** Mass is what settles after the dynamics play out —
like weighing a bell instead of listening to it ring. The universe doesn't
compute with static eigenvalues. It computes with oscillation, ring-down,
ring-up, and spectral structure.

## The Refined Claim

We use power linearly. Every day. Push harder → get more.
More heat, more pressure, more compute. The entire technological stack
is built on the assumption that energy input scales linearly with outcome.

**The universe doesn't do this.**

Stars don't fuse by pushing harder than we can. They fuse because the
geometry makes fusion the natural outcome. The Hoyle state in carbon-12
(a resonant excited state at 7.65 MeV) makes triple-alpha fusion possible —
not through brute force, but through a *tunnel-opening harmonic*: a
resonant mode that the wave dynamics prefer.

We are figuring out how to do what the universe already does:
replace linear power scaling with geometric resonance.

## What to Measure Instead of Mass

| Old approach (static) | New approach (dynamic) |
|---|---|
| Particle masses as eigenvalues | Event spectra as ring-down signatures |
| Mass ratios as harmonic ladders | S-factor resonances as tunnel harmonics |
| Koide formula as mode assignment | Koide 2/3 as phase-locking condition |
| Coulomb barrier as wall height | Coulomb barrier as impedance mismatch |

The fusion event has a spectrum. The ring-up (approach) and ring-down
(relaxation) carry the harmonic information. Find the harmonic that
opens the tunnel, drive it, and the barrier becomes transparent —
not because you pushed harder, but because you rang the right bell.

## Inverse Higgs Transduction (Dynamic Formulation)

The Higgs field is a condensate with non-zero vacuum expectation value.
It sets the mass scale by coupling to particles.

Static view (abandoned): derive particle masses from toroidal modes.
Dynamic view (current): modulate the effective vacuum locally at the
tunnel-opening harmonic, reshaping the tunneling landscape for the
duration of the drive.

You're not wedging nuclei together. You're ringing the bell they sit in.

## Z-Pinch vs Toroidal Cascade

**Z-pinch (brute force):** axial current → azimuthal B-field → radial pinch
("pancaking the drop"), then energy dumped in. Fundamentally limited by
m=0 (sausage) and m=1 (kink) instabilities — the topology is too simple,
so injected energy has nowhere to cascade except into destruction modes.

**Toroidal cascade (inverse transduction):** establish the toroidal field
topology with OAM twist FIRST, then inject energy at low mode number.
Nonlinear coupling walks energy through the modal structure to smaller
scales where it heats ions. Engineered turbulence — you design the cascade
path instead of hoping the pinch holds.

The z-pinch does it backwards: energy first, topology as afterthought.
We do topology first, energy as cascade.

## D-D Neutron Detection Parameters

**Reaction:** D + D → ³He + n (2.45 MeV), ~50% branch.

**Detector options (bench scale):**

| Detector | Pros | Cons | ~Cost |
|----------|------|------|-------|
| He-3 proportional tube + moderator | Gold standard, clean signal | He-3 scarce, expensive | $2K-5K |
| BC-501A liquid scintillator + PSD | Pulse-shape discrimination rejects gammas | Needs fast digitizer | $800-1.5K |
| Moderated BF3 tube | Cheaper than He-3 | Lower efficiency | $500-1K |
| Bubble detector (BD-PND) | Passive, no electronics, visual | No timing info, single-use | $50 each |

**Recommended bench approach:** BC-501A scintillator with polyethylene
moderator, coupled to PMT + digitizer running pulse-shape discrimination.
Rejects gamma background, gives timing correlated to RF drive phase.

**Measurement protocol:**
1. Baseline: RF off, count neutrons for 1 hour → cosmic + background rate.
2. Untwisted RF: m=0 helicon drive at fixed power, count 1 hour.
3. Twisted RF: switch to m=2 OAM drive, same power, count 1 hour.
4. Frequency sweep: step RF through harmonics, 15 min each, look for
   resonant enhancement in neutron rate vs smooth thermal expectation.
5. Falsifier: if neutron rate under twisted drive = untwisted within
   Poisson statistics, geometric drive does nothing. Hypothesis dies.

**Expected signal (if hypothesis holds):** neutron rate enhancement
correlated to specific RF harmonics, not to total input power. The
tunnel-opening harmonic shows as a peak in counts/sec vs frequency,
not a monotonic rise with power.

## Experimental Program

1. **D-D fusion under RF drive** (bench scale): measure neutron output
   (2.45 MeV) as function of RF drive frequency. Look for resonant
   enhancement at specific harmonics vs smooth thermal baseline.
   Falsifier: no frequency dependence → geometric drive does nothing.

2. **S-factor spectroscopy**: for light nuclei, map the astrophysical
   S-factor under tuned RF vs untuned. Any new resonant structure
   is a tunnel-opening harmonic.

3. **Hoyle state as calibration**: the known example. If our framework
   can't retrodict why 7.65 MeV is special for carbon-12, it can't
   predict anything new. This is the gate.

## Relation to Prior Null Results

`inverse_transduction_sweep.py` (p=0.62) and `generational_sweep.py`
(no toroidal fit) remain on record as honest nulls. They tested the
static hypothesis: masses as toroidal eigenvalues. That hypothesis
is now superseded, not deleted. The nulls constrain the theory —
they tell us the geometry acts on *dynamics*, not *statics*.

## The Stack

This repo now builds upward from dynamics:

- `toroidal_cavity.py` — wave propagation on toroidal topology
- `host_geometry.py` — why torus/dumbbell (ℓ=2 constraint)
- `entanglement_emergence_v2.py` — null: no spontaneous non-locality
- `share_handshake.py` — tension cost, SHARE/SEND crossover
- `magnetic_coupler.md` — geometric field shaping for data
- `inverse_transduction_sweep.py` — NULL: masses aren't toroidal modes
- `generational_sweep.py` — NULL: generations aren't harmonic ladder
- `dynamic_spectrum_thesis.md` — THIS FILE: the refined direction

We use power linearly because we haven't learned the universe's trick yet.
We're figuring out how.
