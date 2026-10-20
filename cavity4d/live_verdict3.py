"""live_verdict3.py — Draft 3: locked routes, router-judged pre-fire
predictions, and a rate constant refit on a SEPARATE calibration batch.

Fixes from Draft 1:
  1. SLOT LOCK: every request carries id_slot=0. No slot roulette;
     the cached prefix lives in slot 0 and every warm route lands there.
  2. ROUTER JUDGES FIRST: a RouteJudge holds the locked route registry
     (prefix -> cached token count, measured ONCE at prime time).
     For every prompt it decides the route (COLD / WARM), predicts the
     neutron count, and computes predicted Joules — all BEFORE firing.
     The response's cache_n is used only to AUDIT the judge, never to
     build the prediction. The path can wind; the destination is set
     by the physics of the route, so the slope stays smooth.
  3. CALIBRATION ISOLATION: gen rate (J per generated token) is refit
     from a calibration batch of gen-heavy cold requests; prompt rate
     = gen rate x live speed ratio. The verdict batch uses fresh
     prompts the calibration never saw. Flat baseline stays the
     incumbent 1.69 J/token over all tokens.
Actual energy: GPU-only (amdgpu integral, idle-subtracted). RAPL
energy_uj is permission-locked on this box, so CPU Joules are a known
blind spot — actuals are lower bounds, consistently for both sides.
"""
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from joule_electron import Falsifier, FLAT_J_PER_TOKEN  # noqa: E402
from live_verdict import EnergyMeter, measure_idle, PREFIX  # noqa: E402

SERVER = "http://localhost:8080"
WARM_SLOT = 0
COLD_SLOT = 1


def fire(prompt, n_predict=64, slot=COLD_SLOT):
    body = json.dumps({
        "prompt": prompt, "n_predict": n_predict, "cache_prompt": True,
        "temperature": 0.0, "id_slot": slot,
    }).encode()
    req = urllib.request.Request(
        SERVER + "/completion", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def measured(prompt, n_predict=64, slot=COLD_SLOT):
    m = EnergyMeter()
    m.start()
    resp = fire(prompt, n_predict, slot=slot)
    raw_j, dur = m.stop()
    return resp, raw_j, dur


class RouteJudge:
    """Decides the route and the price BEFORE the prompt fires."""

    def __init__(self, gen_rate, prompt_rate):
        self.gen_rate = gen_rate
        self.prompt_rate = prompt_rate
        self.routes = {}   # prefix_text -> cached_tokens (locked at prime)

    def register_route(self, prefix_text, cached_tokens):
        self.routes[prefix_text] = cached_tokens

    def judge(self, prompt_text, est_prompt_tokens, est_gen_tokens):
        """Returns (route, predicted_joules, predicted_cache)."""
        for prefix, cached in self.routes.items():
            if prompt_text.startswith(prefix):
                active_prompt = max(0, est_prompt_tokens - cached)
                pred = (active_prompt * self.prompt_rate
                        + est_gen_tokens * self.gen_rate)
                return "WARM", pred, cached
        pred = (est_prompt_tokens * self.prompt_rate
                + est_gen_tokens * self.gen_rate)
        return "COLD", pred, 0


CALIB = [
    "Write a short paragraph about how rivers carve valleys over "
    "geological time, and what the sediment remembers.",
    "Write a short paragraph about how a violin string produces "
    "harmonics, and why the bow matters as much as the string.",
    "Write a short paragraph about how bread rises, and what the "
    "yeast is really doing inside the dough overnight.",
    "Write a short paragraph about how tides follow the moon, and "
    "why some coasts see two high waters a day and some see one.",
]

VERDICT_COLD = [
    ("Explain why a mirror fogs in a bathroom after a hot shower, in "
     "two sentences, using the language of condensation and surfaces, "
     "and mention what changes when the window is opened a crack."),
    ("Describe how a compass needle finds north, in two sentences, "
     "using the language of fields and alignment, and mention what a "
     "nearby iron railing does to the reading on a city bridge."),
    ("Explain why distant thunder rumbles instead of cracking, in two "
     "sentences, using the language of distance and frequency, and "
     "mention what the delay between flash and sound tells you."),
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
    print(f"idle baseline: {idle_w:.1f} W (GPU-only meter)")

    # --- calibration batch (verdict prompts never seen here) ---
    print("\n--- calibration batch ---")
    gen_rates = []
    speed_ratio = None
    for p in CALIB:
        resp, raw_j, dur = measured(p, n_predict=96)
        actual_j = max(0.0, raw_j - idle_w * dur)
        t = resp.get("timings", {})
        g = t.get("predicted_n", 0)
        if g:
            gen_rates.append(actual_j / g)
        if speed_ratio is None and t.get("prompt_per_second") \
                and t.get("predicted_per_second"):
            speed_ratio = (t["predicted_per_second"]
                           / t["prompt_per_second"])
        print(f"  calib: gen={g} tok, actual {actual_j:.1f} J")
    gen_rate = statistics.median(gen_rates)
    prompt_rate = gen_rate * (speed_ratio if speed_ratio else 0.18)
    print(f"refit: gen rate {gen_rate:.3f} J/token | prompt rate "
          f"{prompt_rate:.3f} J/token (speed ratio {speed_ratio})")

    judge = RouteJudge(gen_rate, prompt_rate)

    # --- prime the locked route on slot 0 and register it ---
    resp, _, _ = measured(
        PREFIX + "State the topic of the passage above in three words.",
        n_predict=32, slot=WARM_SLOT)
    t = resp.get("timings", {})
    prefix_tokens = t.get("prompt_n", 0) + (t.get("cache_n", 0) or 0)
    judge.register_route(PREFIX, prefix_tokens)
    print(f"route locked: prefix registered at {prefix_tokens} tokens "
          f"in slot {WARM_SLOT}")

    # --- verdict batch: judge first, fire second ---
    print("\n--- verdict batch (pre-fire predictions) ---")
    falsifier = Falsifier(min_samples=5)
    audit = []

    def trial(prompt_text, est_prompt_tokens, est_gen=64):
        route, pred_j, pred_cache = judge.judge(
            prompt_text, est_prompt_tokens, est_gen)
        slot = WARM_SLOT if route == "WARM" else COLD_SLOT
        resp, raw_j, dur = measured(prompt_text, n_predict=est_gen,
                                    slot=slot)
        actual_j = max(0.0, raw_j - idle_w * dur)
        tt = resp.get("timings", {})
        p_tok = tt.get("prompt_n", 0) + (tt.get("cache_n", 0) or 0)
        g_tok = tt.get("predicted_n", 0)
        real_cache = tt.get("cache_n", 0) or 0
        falsifier.record(p_tok + g_tok, pred_j, actual_j)
        audit.append(pred_cache == real_cache)
        print(f"[{route}] judged cache={pred_cache} (actual {real_cache}) "
              f"| predicted {pred_j:.1f} J | actual {actual_j:.1f} J")

    for p in VERDICT_COLD:
        trial(p, est_prompt_tokens=50)
    for s in WARM_SUFFIX:
        trial(PREFIX + s, est_prompt_tokens=prefix_tokens + 25)

    print(f"\nroute-judge cache audits: {sum(audit)}/{len(audit)} exact")
    print("--- LIVE VERDICT (draft 3) ---")
    print(falsifier.verdict())
    print(f"(incumbent flat baseline: {FLAT_J_PER_TOKEN} J/token)")


if __name__ == "__main__":
    main()
