"""live_verdict6.py — Draft 6: draft-5 protocol + per-trial Passport.

Everything from draft 5 is unchanged: separate calibration batch,
single-slot (-np 1) server, route-ordered batch (prime -> warm ->
cold), bare-prefix priming (the server reuses KV only on exact-prefix
match), urgency judge picks the exit path BEFORE firing, prediction =
active prompt tokens x prompt rate + gen cap x gen rate, rates refit
on the calibration batch. Falsifier unchanged: model MAE vs the flat
1.69 J/token incumbent over all tokens.

NEW in draft 6 — every trial also builds a Passport (passport.py,
inverted-cavity delta spec §4-§5):

  token_ids      from the server (/completion "tokens" field if the
                 server returns it, else the /tokenize endpoint;
                 empty list + a printed wart if neither works)
  embedding_point  the route name (draft 5's judge assigns no orbit)
  prompt_kv_id   kv_cube.kv_id(prompt text)
  response_kv_id kv_cube.kv_id(response text)
  path           hops built with passport.hops_from_joule_electron
                 from two JouleElectronModel instances calibrated to
                 THIS batch's refit rates (prompt model at prompt_rate,
                 gen model at gen_rate — the same two rates the judge
                 prediction uses, fixed before the batch fires):
                   - prompt-cached hops: full layer path, ALL neutron,
                     n_tokens = judged shared tokens, priced at the
                     prompt rate, paid 0 (the cancelled portion)
                   - prompt hops: full layer path, active,
                     n_tokens = active prompt tokens at prompt rate
                   - gen hops: full layer path, active,
                     n_tokens = gen cap at gen rate
                 Because the adapter's per-pass rating sum equals the
                 model's calibrated total, passport paid_joules equals
                 the pre-fire prediction by construction; gross adds
                 back the cancelled prefix value. The identity check
                 (gross - cancelled ~= metered delta, via
                 cancellation_report) therefore tests the prediction
                 against the meter with the cancellation bookkeeping
                 made explicit — it does not manufacture agreement.
  interactions   WARM trials only: one event against the priming
                 entry (kv_id of the bare prefix) carrying the
                 cancelled joules the shared stem contributed.
                 COLD trials interacted with nothing: empty.
  oscillations   EMPTY. The cube is not touched by a verdict run;
                 no oscillation joules are invented.

Metering: EnergyMeter (live_verdict.py) = RAPL package delta +
integrated amdgpu power, idle-subtracted. Metering mode is detected
at startup: if the RAPL counter is unreadable the run proceeds
GPU-only and every absolute figure is a lower bound (comparisons
stay fair — both predictors share the same blind meter).
"""
import json
import statistics
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from joule_electron import (Falsifier, FLAT_J_PER_TOKEN,  # noqa: E402
                            JouleElectronModel)
from kv_cube import kv_id  # noqa: E402
from live_verdict import EnergyMeter, measure_idle, PREFIX, read_rapl_uj  # noqa: E402
from passport import Passport, hops_from_joule_electron  # noqa: E402
from urgency import UrgencyJudge  # noqa: E402

SERVER = "http://localhost:8080"
RESULTS = Path(__file__).parent / "live_verdict6_results.json"


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


def tokenize(text):
    """Server-side token ids for the passport; [] if unavailable."""
    body = json.dumps({"content": text}).encode()
    req = urllib.request.Request(
        SERVER + "/tokenize", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("tokens", [])


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
    metering = ("RAPL+GPU (full system)" if read_rapl_uj() is not None
                else "GPU-ONLY — RAPL unreadable, absolute figures "
                     "are LOWER BOUNDS")
    print(f"metering mode: {metering}")

    print("measuring idle baseline (3 s)...")
    idle_w = measure_idle()
    print(f"idle baseline: {idle_w:.1f} W")

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

    # joule-electron models calibrated to this batch's two rates —
    # built once, used only to decompose each trial's prediction into
    # layer hops via the passport adapter (see header).
    model_prompt = JouleElectronModel(total_j_per_token=prompt_rate)
    model_gen = JouleElectronModel(total_j_per_token=gen_rate)
    full_spec = model_gen.full_path(0.0)
    neutron_spec = [(role, "neutron") for role, _ in full_spec]

    # prime the single route with the BARE prefix (draft 5's rule:
    # exact-prefix match or no reuse; never prime with a suffix).
    resp, _, _ = measured(PREFIX, 8)
    t = resp.get("timings", {})
    prefix_tokens = t.get("prompt_n", 0) + (t.get("cache_n", 0) or 0)
    print(f"\nroute locked: prefix = {prefix_tokens} tokens (single "
          f"slot, no pinning)")

    judge = UrgencyJudge()
    falsifier = Falsifier(min_samples=5)
    results = []
    tokenize_wart = False

    def build_passport(kind, text, response_text, token_ids,
                       shared_tokens, active_pt, gen_cap):
        hops = []
        if shared_tokens > 0:
            for h in hops_from_joule_electron(
                    model_prompt, neutron_spec, n_tokens=shared_tokens):
                h.name = "prompt-cached:" + h.name
                hops.append(h)
        if active_pt > 0:
            for h in hops_from_joule_electron(
                    model_prompt, full_spec, n_tokens=active_pt):
                h.name = "prompt:" + h.name
                hops.append(h)
        if gen_cap > 0:
            for h in hops_from_joule_electron(
                    model_gen, full_spec, n_tokens=gen_cap):
                h.name = "gen:" + h.name
                hops.append(h)
        interactions = []
        if kind == "WARM" and shared_tokens > 0:
            interactions.append({
                "other_id": kv_id(PREFIX),
                "joules": shared_tokens * prompt_rate,
            })
        return Passport(
            token_ids=token_ids,
            embedding_point=("warm:locked-prefix-route" if kind == "WARM"
                             else "cold:unique-route"),
            prompt_kv_id=kv_id(text),
            path=hops,
            response_kv_id=kv_id(response_text),
            interactions=interactions,
            oscillations=[],  # cube untouched by a verdict run
        )

    def trial(kind, text, shared_tokens):
        nonlocal tokenize_wart
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

        # --- draft 6: passport + cancellation identity ---------------
        token_ids = resp.get("tokens") or []
        if not token_ids:
            try:
                token_ids = tokenize(text)
            except Exception:
                token_ids = []
                if not tokenize_wart:
                    tokenize_wart = True
                    print("  [wart] server returned no token ids and "
                          "/tokenize failed — token_ids empty")
        passport = build_passport(kind, text, resp.get("content", ""),
                                  token_ids, shared_tokens, active_pt,
                                  j["gen_cap"])
        report = passport.cancellation_report(actual_j)
        paid_drift = passport.paid_joules - pred_j
        rec = {
            "kind": kind, "band": j["band"],
            "exit_path": j["exit_path"], "urgency": j["urgency"],
            "cache_judged": shared_tokens, "cache_actual": cache_n,
            "pred_j": pred_j, "actual_j": actual_j,
            "model_err_j": abs(pred_j - actual_j),
            "flat_err_j": abs(FLAT_J_PER_TOKEN * (p_tok + g_tok)
                              - actual_j),
            "prompt_tokens_server": p_tok, "gen_tokens_server": g_tok,
            "gross_j": report["gross"], "cancelled_j": report["cancelled"],
            "passport_paid_j": passport.paid_joules,
            "paid_vs_pred_drift_j": paid_drift,
            "identity_residual_j": report["identity_residual"],
            "identity_ok": report["identity_ok"],
            "identity_tolerance_j": report["tolerance_j"],
            "prompt_kv_id": passport.prompt_kv_id,
            "response_kv_id": passport.response_kv_id,
            "n_token_ids": len(token_ids),
            "passport": passport.to_dict(),
        }
        results.append(rec)
        print(f"[{kind}/{j['band']}/{j['exit_path']}] urgency "
              f"{j['urgency']:.2f} | cache judged {shared_tokens} "
              f"actual {cache_n} | predicted {pred_j:.1f} J | "
              f"actual {actual_j:.1f} J | identity residual "
              f"{report['identity_residual']:+.2f} J "
              f"({'OK' if report['identity_ok'] else 'FAIL'})")
        if abs(paid_drift) > 0.01:
            print(f"  [wart] passport paid {passport.paid_joules:.3f} J "
                  f"!= prediction {pred_j:.3f} J (drift "
                  f"{paid_drift:+.3f} J)")

    print("\n--- verdict batch (route-ordered) ---")
    for s in STRONG_SUFFIX:
        trial("WARM", PREFIX + s, prefix_tokens)
    for p in MID_COLD:
        trial("COLD", p, 0)
    for p in WEAK_COLD:
        trial("COLD", p, 0)

    n = len(results)
    mae_model = sum(r["model_err_j"] for r in results) / n
    mae_flat = sum(r["flat_err_j"] for r in results) / n
    held = sum(1 for r in results if r["identity_ok"])
    mean_resid = sum(r["identity_residual_j"] for r in results) / n

    print("\n--- LIVE VERDICT (draft 6) ---")
    print(falsifier.verdict())
    print(f"(incumbent flat baseline: {FLAT_J_PER_TOKEN} J/token)")
    print(f"passport identity: held {held}/{n} trials within "
          f"tolerance | mean identity residual {mean_resid:+.2f} J")
    print(f"metering mode: {metering}")

    RESULTS.write_text(json.dumps({
        "draft": 6,
        "metering_mode": metering,
        "idle_w": idle_w, "gen_rate_j_per_tok": gen_rate,
        "prompt_rate_j_per_tok": prompt_rate,
        "prefix_tokens": prefix_tokens,
        "mae_model_j": mae_model, "mae_flat_j": mae_flat,
        "identity_held": held, "identity_n": n,
        "mean_identity_residual_j": mean_resid,
        "trials": results,
    }, indent=2))
    print(f"results written: {RESULTS}")


if __name__ == "__main__":
    main()
