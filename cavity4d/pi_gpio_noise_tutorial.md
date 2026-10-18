# Tutorial: Pi GPIO Noise Capture for the Fuzz Test

**What:** Turn a Raspberry Pi into a precision noise spectrum analyzer using
the GPIO pins and a $5 I2S ADC board. This is the measurement chain for
the fuzz structure test — but it works as a standalone trick for anyone
who wants to see what "random" noise actually looks like.

**Why I2S, not the obvious options:**
- The Pi has no analog inputs. GPIO pins are digital only.
- MCP3008 (SPI ADC) is the classic tutorial part, but it's 10-bit and tops
  out around 200k samples/sec shared across channels. For microvolt noise
  work, you want more bits.
- A PCM1808 I2S ADC board (~$5) gives 24-bit samples at up to 96 kHz over
  three GPIO pins. That's 16 million times finer voltage resolution than
  the MCP3008. For noise spectra, bits matter more than speed.

---

## Parts

- Raspberry Pi (3/4/5, any with the 40-pin header)
- PCM1808 I2S ADC module (blue board, ~$5 — search "PCM1808 Raspberry Pi")
- Low-noise preamp between your DUT and the ADC (the ADC wants line-level;
  raw Johnson noise is microvolts — you need 40–60 dB of gain first)
- Jumper wires, breadboard or solder

## Wiring (Pi GPIO → PCM1808)

| Pi pin | GPIO   | → PCM1808 pin |
|--------|--------|---------------|
| 12     | GPIO18 | BCK (bit clock) |
| 35     | GPIO19 | DIN (data in — yes, *in* to the Pi) |
| 40     | GPIO21 | LCK (word clock / LRCK) |
| any 3V3| —      | VCC |
| any GND| —      | GND |

That's it. Three signal wires. I2S is a beautiful protocol — the ADC is
the clock master, the Pi just listens.

**The trick most tutorials skip:** the PCM1808 board usually needs its
format pin pulled high/low to select I2S mode (vs left-justified). Check
your board's silkscreen — tie FMT to 3V3 for I2S. If `arecord` gives you
garbage, this pin is the first suspect.

## Software

```bash
# Enable I2S in /boot/config.txt (or via raspi-config → Interface Options → I2S):
dtoverlay=hifiberry-dac
# (Yes, the DAC overlay — it enables the I2S peripheral. The ADC rides the same bus.)

sudo reboot

# Verify the card shows up:
arecord -l
# You want to see something like: card 1: sndrpihifiberry

# Capture 60 seconds of noise at 96 kHz, 24-bit, stereo:
arecord -D hw:1 -f S24_LE -r 96000 -c 2 -d 60 noise_run_A1.wav
```

## The FFT (the part that makes it a spectrum analyzer)

```python
import numpy as np, wave

with wave.open("noise_run_A1.wav", "rb") as w:
    n = w.getnframes()
    raw = w.readframes(n)
# S24_LE packed in 32-bit — unpack accordingly
samples = np.frombuffer(raw, dtype=np.int32) >> 8  # 24-bit in 32-bit container
samples = samples.astype(np.float64) / 2**23        # normalize to ±1

# Welch's method: averaged PSD, 1 Hz resolution at 96 kHz needs care —
# use 2^17-point segments (~1.4 s each, ~0.7 Hz bins), 50% overlap
from numpy.lib.stride_tricks import sliding_window_view
seg = 2**17
window = np.hanning(seg)
views = sliding_window_view(samples, seg)[::seg//2]
psd = np.mean([np.abs(np.fft.rfft(v * window))**2 for v in views], axis=0)
freqs = np.fft.rfftfreq(seg, 1/96000)

# Plot log-log. White noise = flat line. Structure = peaks.
import matplotlib.pyplot as plt
plt.loglog(freqs[1:], psd[1:])
plt.xlabel("Hz"); plt.ylabel("Power"); plt.savefig("spectrum.png")
```

## Sanity checks (do these before trusting any result)

1. **Shorted input:** short the preamp input, capture. This is your
   measurement floor — preamp + ADC noise. Your DUT signal must sit
   clearly above this.
2. **Known resistor:** a plain metal-film resistor of known value should
   give flat Johnson noise at 4kTR per Hz. If the computed level matches
   theory within 3 dB, your gain calibration is right.
3. **60 Hz hunt:** mains hum *will* show up. Note where it is so you don't
   mistake it for a discovery. (A discovery at exactly 60/120/180 Hz is
   a power supply, not physics.)

## Gotchas

- **Ground loops** between the Pi's USB power and your preamp will inject
  noise that isn't from the DUT. Power the Pi and preamp from the same
  strip, or better, run the Pi off a battery bank during captures.
- **The Pi is noisy.** WiFi, CPU throttling, and the switching regulator
  all leak into measurements. Turn off WiFi/Bluetooth during captures
  (`rfkill block wifi`), and don't touch the Pi mid-run.
- **Thermal drift** changes Johnson noise slowly. That's why the fuzz test
  uses ABBA sequencing — don't skip it.

---

*Once this chain is validated (flat resistor spectrum matching 4kTR),
you're ready for the actual experiment: toroid vs straight wire.
Spec: `cavity4d/fuzz_structure_test.md`.*
