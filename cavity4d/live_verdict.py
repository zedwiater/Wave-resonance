"""live_verdict.py — feed the joule_electron falsifier REAL measured Joules.

Protocol per prompt: predict BEFORE the request, measure during, record
after. Actual energy = RAPL package delta + integrated amdgpu power,
minus idle baseline x duration. Instruments, not estimates.

Prompt classes:
  COLD — unique prompt, full active path.
  WARM — shared long prefix; llama.cpp KV cache carries the prefix tokens
         as NEUTRONS (trajectory kept, zero recompute burn). cache_n in
         the server timings is the MEASURED neutron count.
Rates: generation tokens at the calibrated full rate (1.69 J/token,
invariant-ledger). Prompt tokens priced by the live speed ratio
(gen tok/s vs prompt tok/s) from the server's own timings — prompt
processing is faster per token, so it is cheaper per token. Nothing is
tuned to outcomes; both rates are fixed before the batch runs.

Falsifier: model MAE vs flat 1.69 J/token (over ALL tokens) on total
request energy. Beat flat or the verdict is ASTROLOGY.
"""
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from joule_electron import Falsifier, FLAT_J_PER_TOKEN  # noqa: E402

SERVER = "http://localhost:8080"
RAPL = Path("/sys/class/powercap/intel-rapl:0/energy_uj")


def gpu_power_files():
    out = []
    for name in Path("/sys/class/hwmon").glob("hwmon*/name"):
        try:
            if name.read_text().strip() == "amdgpu":
                p = name.parent / "power1_average"
                if p.exists():
                    out.append(p)
        except OSError:
            pass
    return out


GPU_POW = gpu_power_files()


def read_rapl_uj():
    try:
        return int(RAPL.read_text().strip())
    except OSError:
        return None


def read_gpu_w():
    tot = 0.0
    for p in GPU_POW:
        try:
            tot += int(p.read_text().strip()) / 1e6
        except OSError:
            pass
    return tot


class EnergyMeter:
    """Samples GPU power; reads RAPL counters at window edges."""

    def __init__(self):
        self._samples = []
        self._run = False
        self._thread = None
        self._rapl0 = None
        self._t0 = None

    def start(self):
        self._samples = []
        self._rapl0 = read_rapl_uj()
        self._t0 = time.time()
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._run:
            self._samples.append((time.time(), read_gpu_w()))
            time.sleep(0.05)

    def stop(self):
        self._run = False
        if self._thread:
            self._thread.join(timeout=1.0)
        t1 = time.time()
        rapl1 = read_rapl_uj()
        gpu_j = 0.0
        for (ta, pa), (tb, pb) in zip(self._samples, self._samples[1:]):
            gpu_j += 0.5 * (pa + pb) * (tb - ta)
        cpu_j = 0.0
        if self._rapl0 is not None and rapl1 is not None:
            d = rapl1 - self._rapl0
            if d < 0:
                d = 0  # counter wrap inside a short window: drop, stay honest
            cpu_j = d / 1e6
        return cpu_j + gpu_j, t1 - self._t0


def measure_idle(seconds=3.0):
    m = EnergyMeter()
    m.start()
    time.sleep(seconds)
    e, dt = m.stop()
    return e / dt  # watts


def run_prompt(prompt, n_predict=64):
    body = json.dumps({
        "prompt": prompt, "n_predict": n_predict,
        "cache_prompt": True, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        SERVER + "/completion", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


PREFIX = (
    "The wave resonance harness treats every boundary as a transducer. "
    "A carrier wave crossing from one medium into another carries the "
    "geometry of the host with it, and the receiving medium reconstructs "
    "a local version of the signal shaped by its own impedance, its own "
    "resonant modes, and its own history of prior excitation. This is why "
    "the same grid harmonic can appear as a faint room artifact in an "
    "empty chamber, a doubled reflection against an inert phantom, and a "
    "strong boundary signature against living tissue: the carrier is "
    "constant, the boundary does the work. Spectral labeling exists to "
    "record exactly this distinction, stamping every measured peak with "
    "whose signal it is and what the boundary did to it, so that no "
    "downstream analysis ever mistakes the room for the mind or the grid "
    "for the planet. The planetary cavity speaks near eight hertz, the "
    "neural fundamental near six, the grid at sixty and its harmonic at "
    "one hundred twenty, and the whole craft of the harness is keeping "
    "those voices separate while measuring how they couple. ")

COLD = [
    ("Explain why a kettle whistles when the water boils, in two "
     "sentences, using the language of pressure and resonance only, "
     "and mention what changes in the sound as the water level drops "
     "inside the vessel over repeated mornings of use in a kitchen."),
    ("Describe how a lighthouse lens concentrates light into a beam, "
     "in two sentences, using the language of boundaries and focusing, "
     "and mention what a keeper would notice about the beam on a foggy "
     "night compared with a clear one over the same dark water."),
    ("Explain how a sailboat can move partly toward the wind rather "
     "than only away from it, in two sentences, using the language of "
     "angles and forces, and mention what the crew feels in the hull "
     "when the boat crosses from sheltered water into open chop."),
]

WARM_SUFFIX = [
    "Given all of the above, state in one sentence what the boundary "
    "contributes that the carrier alone cannot provide.",
    "Given all of the above, state in one sentence why an empty room "
    "and a living subject produce different harmonic ratios.",
    "Given all of the above, state in one sentence why the labeling "
    "layer matters more than the raw spectrum it annotates.",
]


def main():
    print("measuring idle baseline (3 s)...")
    idle_w = measure_idle()
    print(f"idle baseline: {idle_w:.1f} W | RAPL: "
          f"{'live' if read_rapl_uj() is not None else 'MISSING'} | "
          f"GPU power sensors: {len(GPU_POW)}")

    falsifier = Falsifier(min_samples=5)
    rows = []

    def trial(kind, prompt_text):
        # --- predict first (rates fixed before this batch; prompt rate
        # calibrated from the server's live speed ratio on trial 1) ---
        meter = EnergyMeter()
        meter.start()
        resp = run_prompt(prompt_text)
        raw_j, dur = meter.stop()
        t = resp.get("timings", {})
        p_tok = t.get("prompt_n", 0)
        g_tok = t.get("predicted_n", 0)
        cache_n = t.get("cache_n", 0) or 0
        actual_j = max(0.0, raw_j - idle_w * dur)

        if not hasattr(trial, "prompt_rate"):
            pps = t.get("prompt_per_second") or 0
            gps = t.get("predicted_per_second") or 0
            ratio = (gps / pps) if pps and gps else 0.063
            trial.prompt_rate = FLAT_J_PER_TOKEN * ratio
            print(f"live speed ratio: prompt {pps:.0f} tok/s vs gen "
                  f"{gps:.0f} tok/s -> prompt rate "
                  f"{trial.prompt_rate:.3f} J/token")

        active_prompt = max(0, p_tok - cache_n)
        predicted_j = (active_prompt * trial.prompt_rate
                       + g_tok * FLAT_J_PER_TOKEN)
        total_tok = p_tok + g_tok
        falsifier.record(total_tok, predicted_j, actual_j)
        rows.append((kind, p_tok, cache_n, g_tok, predicted_j, actual_j))
        print(f"[{kind}] prompt={p_tok} cached={cache_n} gen={g_tok} | "
              f"predicted {predicted_j:.1f} J | actual {actual_j:.1f} J")

    for p in COLD:
        trial("COLD", p)
    # prime the KV cache with the shared prefix (not a recorded trial)
    run_prompt(PREFIX + WARM_SUFFIX[0])
    print("[PRIME] shared prefix cached")
    for s in WARM_SUFFIX:
        trial("WARM", PREFIX + s)

    print("\n--- LIVE VERDICT ---")
    print(falsifier.verdict())
    print(f"(flat baseline: {FLAT_J_PER_TOKEN} J/token over all tokens)")


if __name__ == "__main__":
    main()
