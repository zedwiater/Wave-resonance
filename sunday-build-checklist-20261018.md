# Sunday Build — Basement Tests (2026-10-18)

**DRAFT — updated overnight.** Two experiments now on the bench. The loop test
(magnetic coupler) is unchanged. NEW: the fuzz structure test — does toroidal
geometry imprint harmonic structure on thermal noise? Full spec in
`cavity4d/fuzz_structure_test.md`.

Safety boundary first: this touches mains-powered gear. Never open or
energize the microwave transformer (MOT). Don't drill or machine the ferrocerium
rod. Both are kill/fire hazards (details below). The motor stator is safe passive
iron — that's the one to use. The fuzz test is fully passive (no mains) — run
it first while the room thermally soaks.

## The question

Does shaping the magnetic field (fold/pinch) boost data coupling enough to climb
baud rungs? If yes → the $130 ferrite build is justified. If no → the thesis dies
at the bench, cheaply.

Full spec lives in `cavity4d/magnetic_coupler.md`.

## Parts (~$30)

- Extension cord, looped into a circle (toroidal carrier)
- Space heater, 1500W (~12.5A) as the load — strong 60Hz field
- 28 AWG magnet wire (~$8) — **50–100 turns** at two points = Tx coil and Rx coil (air-core). Wind on a 1–2" plastic form (pill bottle, marker cap). Fewer than ~20 turns buries the signal in the dongle noise floor (~0.5mV at 25 turns vs ~1.6mV at 75 turns for 50µT @ 60Hz); above ~300 turns self-capacitance rolls off the harmonics subspectra.py hunts. 50–100 is the window.
- 4× neodymium bar magnets (~$12)
- Washer/dryer motor stator (already have) — laminated iron, passive flux concentrator
- PC with line-out / line-in, minimodem (free)
- USB audio dongle (mic-in) for capture; 1–10µF series DC-blocking cap on the Rx lead (dongle puts bias voltage on mic-in). Shorted-input noise check mandatory before measuring.

## Rx coil placement & pinch protocol

**Positioning (heater cord → Rx coil):**
- Do NOT wrap the coil directly around the live cord — mains hum will clip the dongle input.
- Start 1–3" from the cord. Try both orientations: coil axis parallel to cord (axial flux) and perpendicular (radial gradient). Log which.
- Secure everything rigidly. Mechanical vibration against the wire creates microphonics that mimic harmonic structure.

**Pinch (magnets):**
- Configuration: opposing magnet pair flanking the Rx coil (N-S facing), NOT a single magnet stuffed in the core. Document exact distances.
- **Physics boundary (read this):** in an air-core coil, a static magnetic field contributes zero to dΦ/dt — classical EM predicts the pinch changes NOTHING about the induced signal. That makes this a clean null test: if harmonic structure shifts with the pinch on air-core, it is either (a) microphonics — rule out with the tap test below — or (b) the framework's actual claim (pinch retunes cavity Q/mode structure). Do not describe it as a "flux gate"; there is no classical flux-gate mechanism in linear media.
- **Keep magnets away from the stator iron.** A neodymium near laminated iron saturates it locally, collapsing its permeability and REDUCING coupling — the opposite of the intent. If testing stator+pinch combined, place magnets ≥3" from iron and note it.
- **Tap test (microphonics control):** with heater OFF, tap the bench near the coil and record 10s. Any spectral peaks that appear in both tap and pinch runs are mechanical, not electromagnetic. Discard them.

**Pinch-strength sweep:** at each ladder rung, step magnet distance (e.g. 6" → 3" → 1" → 0.5") and capture spectrum at each. Look for the threshold where harmonic content reorganizes (broadband → locked → suppressed). Log distances, don't eyeball them.

## Audio chain

- TX: `minimodem -t 1200 < msg.txt` → line-out → Tx coil
- RX: Rx coil → line-in (raise gain if needed) → `minimodem -r 1200`
- Repeat at 2400 and 4800 (minimodem baud argument)

## Measurement ladder (log BER at every rung)

1. **Baseline:** air-core coils, no iron, no magnets → 1200 baud
2. **Add stator:** cord threaded through the stator bore → re-measure 1200, climb 2400 → 4800
3. **Add pinch:** neodymium magnets in opposition near the Rx coil →
   measure each rung **magnets-off vs pinch**

Log: baud, config, characters sent, errors. BER = errors / characters.

### Spectral capture (runs in parallel — same hardware, no extra parts)

At every ladder step, ALSO record the raw Rx audio before demodulation:

```bash
arecord -f S16_LE -r 48000 -c 1 -d 30 rx_baseline_1200.wav
# then run minimodem as normal
```

FFT each capture afterward. This turns the loop test into a driven
toroidal/poloidal spectrometer for free:

- **What to look for:** harmonic structure at 60Hz multiples in the Rx
  spectrum, and how it CHANGES between baseline → stator → pinch.
  The 60Hz heater current is the poloidal drive; the Rx coil reads the
  toroidal response. The harmonic content of that coupling is the
  toroidal/poloidal flow spectrum, measured directly.
- **The pinch prediction:** if field geometry imprints on mode structure,
  the harmonic peaks shift or new ones appear when the pinch is applied.
  Watching the spectrum change with magnet configuration = watching
  geometry rewrite the mode content.
- **The baud ladder is already spectral:** which rungs succeed/fail maps
  the channel frequency response. The pattern of rungs the pinch unlocks
  is itself a spectrum measurement.

This is the DRIVEN complement to the passive fuzz test (toroid vs wire
idle noise). Driven shows the coupling; passive shows the floor. Both
matter. Neither needs new hardware.

## Win condition

A text message that traveled through a magnetically-shaped field with **no
electrical contact**. If the pinch unlocks a baud rung the baseline couldn't
reach, field shaping = bandwidth. That's the seed the $130 build grows from.

Realistic ceiling on air-core: 2400–4800 baud. The MHz stuff needs ferrite.

## Don't do this

- **Microwave transformer:** saturates at 15A mains (then it's just air), kHz eddy
  losses turn it into a heater, and its windings can induce hundreds of volts.
  People die touching MOTs.
- **Ferrocerium rod:** it's *not* ferrite — conductive metal alloy, low magnetic
  permeability. A ring of it around an AC wire is an eddy-current heater, not a
  flux concentrator. Machining it throws sparks and pyrophoric dust. Basement.
  No.

## Afternoon (gated on loop results)

PCBWay wall-plug gateway schematic — only sketch this if the loop proves the
pinch works. Order of operations: physics first, boards second.

## NEW: Fuzz structure test (run first — passive, no mains)

While the room thermally soaks for the loop test, run the fuzz test:

- **DUT A:** toroidal inductor/transformer, unpowered, room temp
- **DUT B:** straight same-wire control, matched resistance
- Preamp → USB sound card → FFT (REW/Audacity/Python)
- ABBA sequence, 60s captures, compare spectra
- **Hit:** reproducible harmonic peaks in A, absent in B, ≥3σ
- **Miss:** flat identical spectra → cascade stops at lab scale (publish it)

Full protocol: `cavity4d/fuzz_structure_test.md`. ~$40, most parts on hand.

## Honest priors

- HomePlug AV2 (2015) did 2 Gbps over power lines with DSP — the components
  aren't novel. Nobody arrived here through energy accounting; the fold/pinch
  magnetic lens for bandwidth isn't in the PLC playbook.
- Sunday's ceiling is 4800 baud ≈ 600 bytes/s. A 100 MB video would take 46 hours.
  Video transfer is the $130 ferrite build (~10 Mbps ≈ 80 s), not Sunday.
