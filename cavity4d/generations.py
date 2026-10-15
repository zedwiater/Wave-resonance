#!/usr/bin/env python3
"""
generations.py — recursive adjusters + hum bounds on a machine-balanced
timescale, run over several generations.

Each generation: a long-horizon emergence run with an ONLINE recursive
hum controller. Every K steps the controller measures the sustained
energy E and adjusts the pump (gain_G) multiplicatively to hold E inside
[hum_min, hum_max]:
    E > hum_max  ->  gain_G *= (1 - rate)   (pump down)
    E < hum_min  ->  gain_G *= (1 + rate)   (pump up)

Between generations a META-adjuster recursively tunes the controller
itself from measured performance:
    - many band violations + oscillation -> damp the rate
    - sluggish return to band           -> raise the rate
    - E pinned at a bound               -> shift the hum band
    - wall-clock drift                  -> recalibrate the timescale

Timescale is balanced to the machine: benchmark steps/sec first, then
set steps_per_generation for the target wall-clock per generation.

Usage:
  generations.py --generations 6 --target-min 28 --out generations.jsonl
Logs human-readable progress to stdout (redirect to a log file).
"""
import argparse
import json
import sys
import time
import numpy as np

sys.path.insert(0, ".")
import cavity4d as C


def benchmark(steps=200):
    psi = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    t0 = time.time()
    C.propagate(psi.copy(), 0.02, steps)
    return steps / max(time.time() - t0, 1e-9)


def calibrate(target_E=None, steps=2000, dt=0.02):
    """Measure the natural steady-state hum (fixed pump, no control)."""
    psi = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    psi = C.propagate(psi, dt, steps, gain_G=3.0, gain_Esat=2.0,
                      loss_0=0.8, aperture_a=2.0)
    return C.energy(psi)


def run_generation(gen, params, steps, dt=0.02):
    """One generation: long emergence with online hum control."""
    hum_min, hum_max = params["hum_min"], params["hum_max"]
    rate = params["rate"]
    K = params["K"]                    # controller interval (steps)
    gain_G = params["gain_G"]
    psi = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
    p0 = C.oam_spectrum(psi)
    n_chunks = max(1, steps // K)
    E_trace, gain_trace = [], []
    violations = 0
    t0 = time.time()
    for _ in range(n_chunks):
        psi = C.propagate(psi, dt, K, gain_G=gain_G, gain_Esat=2.0,
                          loss_0=0.8, aperture_a=params["aperture_a"])
        E = C.energy(psi)
        E_trace.append(E)
        gain_trace.append(gain_G)
        if E > hum_max:
            gain_G = max(0.5, gain_G * (1 - rate))
            violations += 1
        elif E < hum_min:
            gain_G = min(10.0, gain_G * (1 + rate))
            violations += 1
    wall = time.time() - t0
    p1 = C.oam_spectrum(psi)
    return {
        "gen": gen, "params": dict(params), "steps": steps,
        "wall_sec": wall, "steps_per_sec": steps / wall,
        "E_trace": [round(float(e), 4) for e in E_trace[::max(1, len(E_trace)//20)]],
        "E_end": float(E_trace[-1]), "gain_end": float(gain_G),
        "violations": violations, "violation_frac": violations / n_chunks,
        "share": float(p1.max()),
        "dominant_ell": int(C.ELLS[int(np.argmax(p1))]),
        "entropy": float(C.spectral_entropy(p1[p1 > 0])),
    }


def meta_adjust(params, res):
    """Recursively tune the controller from measured performance."""
    p = dict(params)
    vf = res["violation_frac"]
    E_end = res["E_end"]
    share = res["share"]
    # oscillating around the band -> damp the controller
    if vf > 0.30:
        p["rate"] *= 0.7
    # sluggish (few violations but E far from band center) -> push harder
    elif vf < 0.05 and abs(E_end - (p["hum_min"] + p["hum_max"]) / 2) > 0.5:
        p["rate"] = min(0.2, p["rate"] * 1.3)
    # weak condensation -> strengthen selection (differential loss)
    if share < 0.7:
        p["aperture_a"] = min(8.0, p.get("aperture_a", 2.0) * 1.25)
    # E pinned above band -> the band is too low for this pump; raise it
    if E_end > p["hum_max"] * 1.2:
        p["hum_max"] *= 1.15
        p["hum_min"] *= 1.15
    # E pinned below band -> lower the band
    if E_end < p["hum_min"] * 0.8:
        p["hum_max"] *= 0.9
        p["hum_min"] *= 0.9
    # carry the learned pump forward, then disturb it: each generation
    # starts 40% too hot so the recursive controller must earn its keep
    p["gain_G"] = min(10.0, max(0.5, res["gain_end"] * 1.4))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generations", type=int, default=6)
    ap.add_argument("--target-min", type=float, default=28,
                    help="target wall-clock minutes per generation")
    ap.add_argument("--out", default="generations.jsonl")
    args = ap.parse_args()

    sps = benchmark()
    print(f"[gen0] machine: {sps:.1f} steps/sec", flush=True)
    # calibrate the hum band to the machine's natural steady state
    E_nat = calibrate()
    hum_min, hum_max = round(0.75 * E_nat, 2), round(1.25 * E_nat, 2)
    print(f"[gen0] natural hum E={E_nat:.2f} -> band [{hum_min},{hum_max}]",
          flush=True)
    steps = int(args.target_min * 60 * sps)
    # controller adjusts every ~20 s of wall-clock (balanced timescale),
    # at least 10 adjustments per generation
    K = max(50, min(int(20 * sps), steps // 10))

    params = {"hum_min": hum_min, "hum_max": hum_max, "rate": 0.05,
              "K": K, "gain_G": 3.0, "aperture_a": 2.0}
    print(f"[gen0] steps/gen={steps} K={K}", flush=True)

    with open(args.out, "w") as f:
        for gen in range(1, args.generations + 1):
            t0 = time.time()
            res = run_generation(gen, params, steps)
            res["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                             time.gmtime())
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"[gen{gen}] share={res['share']:.3f} "
                  f"l={res['dominant_ell']} E_end={res['E_end']:.2f} "
                  f"gain={res['gain_end']:.2f} ap={res['params']['aperture_a']:.2f} "
                  f"viol={res['violation_frac']:.2f} "
                  f"wall={res['wall_sec']/60:.1f}min", flush=True)
            params = meta_adjust(params, res)
            # recalibrate timescale to the measured throughput
            sps = res["steps_per_sec"]
            steps = int(args.target_min * 60 * sps)
            params["K"] = max(50, min(int(20 * sps), steps // 10))
    print("generations complete.", flush=True)


if __name__ == "__main__":
    main()
