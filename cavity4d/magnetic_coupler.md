# Magnetic Coupler: Non-Contact Power Line Data Transduction

## Concept

Use shaped magnetic fields to modulate eddy currents around a power line,
creating a high-bandwidth data channel that doesn't touch the conductor.

The 60Hz power is the carrier ocean. The magnets shape eddies in that ocean.
Data rides the eddies, not the current.

## Physics

**Base field:** AC power line generates B = μ₀I/2πr around conductor.
At 100A, 1cm from wire: B ≈ 2 mT, oscillating at 60Hz.

**Eddy currents:** dB/dt induces circulating currents in nearby conductors.
Normally parasitic. Here, engineered.

**Magnetic bias:** Permanent magnets set the ferrite core's operating point
on its B-H curve. This determines:
- Permeability (μ) → coupling efficiency
- Saturation margin → dynamic range for modulation
- Hysteresis operating region → linearity

**Folding:** Shaped pole pieces (magnetic lenses) compress field lines into
a smaller volume. Flux density increases as 1/area. A 4:1 fold → 4x B-field
→ 4x dB/dt → 4x induced voltage in pickup coil.

**Pinching:** Opposing magnet pairs create a field null (cusp). Near the null,
the field gradient dB/dx is extreme. Small modulation currents produce large
local field changes. This is the high-sensitivity interaction zone.

## Coupler Architecture

```
                    ┌─────────────────┐
                    │  Ferrite Toroid  │
                    │  (clamp-on)      │
                    │                  │
  Power Line ───────┼───→ 60Hz B-field │
  (no contact)      │         ↓        │
                    │   ┌─────────┐    │
                    │   │Mag Lens │    │ ← FOLD: compress field 4:1
                    │   │(fold 4×)│    │
                    │   └────┬────┘    │
                    │        ↓         │
                    │   ┌─────────┐    │
                    │   │ Pinch   │    │ ← PINCH: opposing magnets
                    │   │ Zone    │    │    create high-gradient null
                    │   └────┬────┘    │
                    │        ↓         │
                    │  ┌──────────┐    │
                    │  │Mod Coil  │    │ ← DATA IN: modulate permeability
                    │  │(Tx)      │    │
                    │  └──────────┘    │
                    │        ↓         │
                    │  ┌──────────┐    │
                    │  │Pickup    │    │ ← DATA OUT: read dB/dt
                    │  │Coil (Rx) │    │
                    │  └──────────┘    │
                    └─────────────────┘
```

## Modal Multiplexing Matrix

Two orthogonal dimensions, used simultaneously:

### Axis 1: Spatial Modes (concentric vortices)
Different ℓ modes coexist in the same physical volume.
- ℓ=2: quadrupole field pattern (matches host geometry)
- ℓ=3,4,...: higher-order modes, mathematically orthogonal
- Each mode is an independent data channel
- No cross-talk (orthogonality is exact, not approximate)

### Axis 2: Frequency Carriers (multi-frequency RF)
Different RF frequencies on each spatial mode.
- 1 MHz, 5 MHz, 10 MHz, 20 MHz (example spacing)
- Each frequency × each spatial mode = independent channel
- Total channels = N_modes × N_frequencies

**Example:** 4 spatial modes (ℓ=2,3,4,5) × 4 frequencies = 16 parallel channels
in the same physical coupler, zero interference.

## Bandwidth Calculation

Per channel (Shannon-Hartley):
  C = B × log₂(1 + SNR)

Where:
- B = channel bandwidth (~100 kHz per RF carrier, limited by ferrite response)
- SNR = signal-to-noise (magnetic coupling is quiet; estimate 20 dB)

Per channel: C ≈ 100 kHz × 6.64 ≈ 664 kbps
16 channels: **~10.6 Mbps** per coupler

With better ferrite (higher frequency response) and more modes:
32 channels × 1 MHz × 6.64 ≈ **212 Mbps**

This is on a single power line, non-contact, no new wires.

## Folding/Pinching Gain

| Technique | Mechanism | Gain |
|-----------|-----------|------|
| No shaping | Bare inductive pickup | 1x (baseline) |
| Fold 2:1 | Halve the interaction area | 2x flux density |
| Fold 4:1 | Quarter the area | 4x flux density |
| Pinch null | Extreme gradient at cusp | 10x local sensitivity |
| Combined | Fold + pinch | ~20x effective coupling |

The pinch zone is where the magic happens: at the magnetic null,
a tiny modulation current creates a huge local dB/dt because the
background field is near zero but the gradient is maximum.

## Parts List (Prototype)

| Part | Spec | ~Cost | Source |
|------|------|-------|--------|
| Ferrite toroid | MnZn, 50mm OD, high μ (>5000) | $15 | DigiKey/Mouser |
| Neodymium magnets | N52, 20×10×5mm, ×4 | $20 | Amazon/K&J Magnetics |
| Magnet pole pieces | Soft iron, shaped for fold | $30 | Machine shop or 3D print + iron fill |
| Tx modulation coil | 100 turns, 28 AWG on bobbin | $5 | Wind by hand |
| Rx pickup coil | 200 turns, 30 AWG, tuned | $5 | Wind by hand |
| RTL-SDR | 500 kHz – 1.7 GHz receiver | $35 | Amazon |
| Op-amp front end | Low-noise, for Rx coil | $10 | DigiKey |
| 3D printed housing | Clamp-on toroid holder | $10 | Print or service |
| **Total** | | **~$130** | |

## Test Procedure

1. **Baseline:** Clamp toroid on live 120V AC line. Measure 60Hz pickup on Rx coil. This is the carrier.
2. **Bias:** Add permanent magnets. Measure shift in coupling efficiency. Find optimal bias point (max dB/dt sensitivity).
3. **Fold:** Add shaped pole pieces. Measure flux concentration with Hall sensor. Verify 4:1 improvement.
4. **Modulate:** Drive Tx coil with 1 MHz sine. Measure sidebands on Rx. This is the data channel.
5. **Multiplex:** Add second frequency (5 MHz). Verify orthogonality (no cross-talk).
6. **Pinch:** Add opposing magnets to create null. Measure sensitivity gain in pinch zone.

## Safety

- **NEVER** break into the power line. This is clamp-on only.
- Ferrite toroid must be properly insulated (the power line is live).
- Keep modulation power low (<1W) to avoid heating the ferrite.
- The 60Hz field is strong near the wire; keep sensitive electronics shielded.

## Connection to Cosmology

The coupler is a laboratory-scale toroidal transduction node:
- Power line = host carrier (like the 5D bulk)
- Magnetic field = the wave medium (like the 4D projection surface)
- Fold/pinch geometry = host topology (suppresses unwanted modes)
- Data modulation = energy throughput (the ledger in action)
- ℓ=2 spatial modes = same quadrupole dominance as the universe

We're not imitating the cosmos. We're building the same machine at a different scale.
