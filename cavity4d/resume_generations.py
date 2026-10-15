#!/usr/bin/env python3
"""
resume_generations.py — continue a cavity4d generational run from an
existing generations JSONL.

Reads the last record of --resume, applies the meta-adjuster once to
get generation N+1's starting params, then continues the generational
loop (same machinery as generations.py), appending rows to --out.

Pre-committed falsifier for the aperture lever (the open question from
the gen 1-6 report): if the aperture is pinned at its cap (8.0) and
|d(share)| < 0.01 for three consecutive generations, the run halts
early with the verdict "aperture lever exhausted — share plateaued
under the cap". Otherwise the run answers the other branch: share
keeps climbing or crosses 0.7.

Assumes the working directory holds cavity4d.py, generations.py and
spectra/ (same assumption generations.py makes).

Usage:
  resume_generations.py --resume generations.jsonl --generations 5 \
      --target-min 28 --out generations-7-11.jsonl
Logs human-readable progress to stdout (redirect to a log file).
"""
import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# generations.py does sys.path.insert(0, ".") and `import cavity4d as C`;
# make sure the real cwd (which holds cavity4d.py) resolves first.
sys.path.insert(0, os.getcwd())
sys.path.insert(0, HERE)

_spec = importlib.util.spec_from_file_location(
    "gen_mod", os.path.join(HERE, "generations.py"))
gen_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_mod)

APERTURE_CAP = 8.0
SHARE_PLATEAU_TOL = 0.01
PLATEAU_GENS = 3


def load_last(path):
    with open(path) as f:
        rows = [json.loads(ln) for ln in f if ln.strip()]
    if not rows:
        raise SystemExit(f"{path}: no records to resume from")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", required=True,
                    help="generations JSONL to continue from")
    ap.add_argument("--generations", type=int, default=5,
                    help="generations to run from the resume point")
    ap.add_argument("--target-min", type=float, default=28,
                    help="target wall-clock minutes per generation")
    ap.add_argument("--out", required=True,
                    help="JSONL to append continued generations to")
    ap.add_argument("--no-plateau-stop", action="store_true",
                    help="disable the aperture-plateau falsifier stop rule")
    args = ap.parse_args()

    rows = load_last(args.resume)
    last = rows[-1]
    start_gen = last["gen"] + 1

    # gen N+1's starting params = meta-adjuster applied to gen N
    params = gen_mod.meta_adjust(dict(last["params"]), last)
    sps = last["steps_per_sec"]
    steps = int(args.target_min * 60 * sps)
    params["K"] = max(50, min(int(20 * sps), steps // 10))
    print(f"[resume] gen{last['gen']} -> gen{start_gen}: "
          f"share={last['share']:.3f} l={last['dominant_ell']} "
          f"ap={params['aperture_a']:.2f} rate={params['rate']:.3f} "
          f"gain_G={params['gain_G']:.2f} band=[{params['hum_min']},"
          f"{params['hum_max']}] sps~{sps:.0f}", flush=True)

    shares = [r["share"] for r in rows]
    apertures = [r["params"]["aperture_a"] for r in rows]

    with open(args.out, "a") as f:
        for gen in range(start_gen, start_gen + args.generations):
            t0 = time.time()
            res = gen_mod.run_generation(gen, params, steps)
            res["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                             time.gmtime())
            res["resumed_from"] = args.resume
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(f"[gen{gen}] share={res['share']:.3f} "
                  f"l={res['dominant_ell']} E_end={res['E_end']:.2f} "
                  f"gain={res['gain_end']:.2f} "
                  f"ap={res['params']['aperture_a']:.2f} "
                  f"viol={res['violation_frac']:.2f} "
                  f"wall={res['wall_sec']/60:.1f}min", flush=True)
            shares.append(res["share"])
            apertures.append(res["params"]["aperture_a"])

            if res["share"] >= 0.7:
                print("[verdict] share >= 0.7 — aperture lever CONFIRMED "
                      "as the condensation mechanism.", flush=True)
                break

            if (not args.no_plateau_stop and len(shares) >= PLATEAU_GENS + 1
                    and all(a >= APERTURE_CAP for a in
                            apertures[-PLATEAU_GENS:])):
                diffs = [abs(shares[-i] - shares[-i - 1])
                         for i in range(1, PLATEAU_GENS + 1)]
                if all(d < SHARE_PLATEAU_TOL for d in diffs):
                    print(f"[verdict] aperture pinned at cap {APERTURE_CAP} "
                          f"and |d(share)| < {SHARE_PLATEAU_TOL} for "
                          f"{PLATEAU_GENS} consecutive gens — aperture lever "
                          f"EXHAUSTED, share plateaued. Different lever "
                          f"needed.", flush=True)
                    break

            params = gen_mod.meta_adjust(params, res)
            sps = res["steps_per_sec"]
            steps = int(args.target_min * 60 * sps)
            params["K"] = max(50, min(int(20 * sps), steps // 10))
    print("resume complete.", flush=True)


if __name__ == "__main__":
    main()
