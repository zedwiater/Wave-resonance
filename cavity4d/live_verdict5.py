"""live_verdict5.py — Draft 5: locked single route + the two-step
transform (urgency rating -> exit path) as the pre-fire judge.

Server state: llama-server restarted with -np 1 (single slot; original
command line saved in server_cmdline_original.txt). One conduit, no
slot roulette. Batch is ROUTE-ORDERED: prime -> warm (STRONG) trials
while the route is hot -> cold trials. No id_slot anywhere: pinning
was draft 3's negative result.

Judge flow per prompt (ALL before firing):
  1. RouteJudge: shared-prefix tokens from the locked registry.
  2. UrgencyJudge: urgency from route depth + complexity ->
     exit path (FULL / STANDARD / EARLY) -> generation cap.
  3. Price: predicted J = active prompt tokens x prompt rate
     + gen cap x gen rate (the AUTHORIZED burn of the chosen path).
Rates refit on a separate calibration batch, as in draft 2/3.
Falsifier: model vs incumbent flat 1.69 J/token over all tokens.
Actuals: GPU-only Joules, idle-subtracted (RAPL still locked).
"""
import json
import statistics
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from joule_electron import Falsifier, FLAT_J_PER_TOKEN  # noqa: E402
from live_verdict import EnergyMeter, measure_idle, PREFIX  # noqa: E402
from urgency import UrgencyJudge  # noqa: E402

SERVER = "http://localhost:8080"


def est_tokens(text):
    return max(1, round(len(text) / 4))


def fire(prompt, n_predict):
    body = json.dumps({
        "prompt": prompt, "n_predict": n_predict,
        "cache_prompt": True, "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(
        SERVER + "/completion", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def measured(prompt, n_predict):
    m = EnergyMeter()
    m.start()
    resp = fire(prompt, n_predict)
    raw_j, dur = m.stop()
    return resp, raw_j, dur


CALIB = [
    "Write a short paragraph about how rivers carve valleys over "
    "geological time, and what the sediment remembers.",
    "Write a short paragraph about how a violin string produces "
    "harmonics, and why the bow matters as much as the string.",
    "Write a short paragraph about how bread rises, and what the "
    "yeast is really doing inside the dough overnight.",
]

STRONG_SUFFIX = [
    "Given all of the above, write a short paragraph explaining what "
    "the boundary contributes that the carrier alone cannot provide.",
    "Given all of the above, write a short paragraph explaining why "
    "an empty room and a living subject produce different harmonic "
    "ratios against the same carrier.",
]

MID_COLD = [
    "Write a short paragraph about why a mirror fogs in a bathroom "
    "after a hot shower, using the language of condensation, surfaces "
    "and temperature differences throughout.",
    "Write a short paragraph about why distant thunder rumbles "
    "instead of cracking, using the language of distance, frequency "
    "and the time between the flash and the sound arriving.",
]

WEAK_COLD = [
    "Say hello in one short sentence.",
    "Answer in a few words: what color is the sky on a clear day?",
]


def main():
    print("measuring idle baseline (3 s)...")
    idle_w = measure_idle()
    print(f"idle baseline: {idle_w:.1f} W (GPU-only meter)")

    print("\n--- calibration batch ---")
    gen_rates, speed_ratio = [], None
    for p in CALIB:
        resp, raw_j, dur = measured(p, 96)
        actual_j = max(0.0, raw_j - idle_w * dur)
        t = resp.get("timings", {})
        if t.get("predicted_n"):
            gen_rates.append(actual_j / t["predicted_n"])
        if speed_ratio is None and t.get("prompt_per_second") \
                and t.get("predicted_per_second"):
            speed_ratio = (t["predicted_per_second"]
                           / t["prompt_per_second"])
        print(f"  calib: gen={t.get('predicted_n')} tok, "
              f"actual {actual_j:.1f} J")
    gen_rate = statistics.median(gen_rates)
    prompt_rate = gen_rate * (speed_ratio if speed_ratio else 0.24)
    print(f"refit: gen {gen_rate:.3f} J/tok | prompt {prompt_rate:.3f} "
          f"J/tok")

    # prime the single route with the BARE prefix and register its
    # measured token count — the server reuses KV only when the cached
    # prompt is an exact prefix of the request (proven 2026-10-20:
    # bare prime -> 194-208 neutron tokens on divergent warm prompts;
    # prefix+suffix prime -> 0). Never prime with a suffix again.
    resp, _, _ = measured(PREFIX, 8)
    t = resp.get("timings", {})
    prefix_tokens = t.get("prompt_n", 0) + (t.get("cache_n", 0) or 0)
    print(f"\nroute locked: prefix = {prefix_tokens} tokens (single "
          f"slot, no pinning)")

    judge = UrgencyJudge()
    falsifier = Falsifier(min_samples=5)

    def trial(kind, text, shared_tokens):
        est_pt = est_tokens(text)
        j = judge.judge(est_pt, shared_tokens)
        active_pt = max(0, est_pt - shared_tokens)
        pred_j = (active_pt * prompt_rate
                  + j["gen_cap"] * gen_rate)
        resp, raw_j, dur = measured(text, j["gen_cap"])
        actual_j = max(0.0, raw_j - idle_w * dur)
        tt = resp.get("timings", {})
        p_tok = tt.get("prompt_n", 0) + (tt.get("cache_n", 0) or 0)
        g_tok = tt.get("predicted_n", 0)
        cache_n = tt.get("cache_n", 0) or 0
        falsifier.record(p_tok + g_tok, pred_j, actual_j)
        print(f"[{kind}/{j['band']}/{j['exit_path']}] urgency "
              f"{j['urgency']:.2f} | cache judged {shared_tokens} "
              f"actual {cache_n} | predicted {pred_j:.1f} J | "
              f"actual {actual_j:.1f} J")

    print("\n--- verdict batch (route-ordered) ---")
    for s in STRONG_SUFFIX:
        trial("WARM", PREFIX + s, prefix_tokens)
    for p in MID_COLD:
        trial("COLD", p, 0)
    for p in WEAK_COLD:
        trial("COLD", p, 0)

    print("\n--- LIVE VERDICT (draft 5) ---")
    print(falsifier.verdict())
    print(f"(incumbent flat baseline: {FLAT_J_PER_TOKEN} J/token)")


if __name__ == "__main__":
    main()
