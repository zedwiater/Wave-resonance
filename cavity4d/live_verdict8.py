"""live_verdict8.py — Draft 8: draft-7 protocol + two upgrades.

Carried from draft 7 unchanged: separate calibration batch,
single-slot -np 1 server, route-ordered verdict batch, bare-prefix
priming, urgency judge picks the exit path BEFORE firing,
EnergyMeter = RAPL + amdgpu idle-subtracted, tokenize-based counts
(fix 1), shared-stem neutron registry (fix 2), expected-length gen
pricing (fix 3), per-trial Passport + cancellation_report,
falsifier = model MAE vs flat 1.69 J/token over server-reported
totals (scoring only, never in the prediction path).

UPGRADE 1 — TERMINATING CALIBRATION PER BAND.
Draft 7's calibration prompts all ran to the 96-token cap (no EOS)
and all judged MID, so expected-gen degenerated to the caps and the
WEAK band had zero samples. Draft 8's calibration set is at least
two prompts PER BAND, each designed to terminate naturally (EOS
before its band cap):
  WEAK   one-word-answer questions (short enough that the judge's
         complexity term really bands them WEAK — verified, and the
         judged band is recorded for every attempt);
  MID    two-sentence prompts with an explicit stopping bound;
  STRONG PREFIX + a bounded structured ask (numbered points, then
         stop).
A candidate pool is fired per band until two EOS-terminated samples
are collected or the pool is exhausted. A sample counts toward a
band ONLY if (a) it terminated (server stopped_eos / stopped before
the cap, not stopped_limit) AND (b) its judged band equals its
intended band — a prompt that lands in the wrong band is recorded
as mis-banded, never relabeled. The expected-gen table is built
ONLY from those terminating samples (n and mean reported per band).
A band with zero terminating samples falls back to its cap and the
report SAYS SO. Gen-rate refit uses terminating samples with >= 8
generated tokens when available (a 2-token gen prices prompt
overhead, not generation), else all terminating samples.

UPGRADE 2 — REUSE-DISCOVERY PROBE.
Draft 7 found the server reusing 26-28 tokens on cold MID trials
(chunk-level prompt-cache reuse beyond the 5-token literal stem)
that the judge could not claim under the no-assumed-cache rule.
Draft 8 earns the claim: before pricing each verdict prompt, fire
ONE discovery probe — the route's exact full prompt with
n_predict=1, metered — and read cache_n from its timings. The
judge then claims neutrons = the probe's measured cache_n for that
prompt (never more; the draft-7 registry claim is recorded beside
it for comparison). If the probe reports cache_n=0, the judge
claims 0 — the mechanism can learn "nothing reusable here." Probe
joules are metered and reported per route as discovery overhead;
they are NOT folded into any trial's prediction or actuals, and
never enter the falsifier.
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
RESULTS = Path(__file__).parent / "live_verdict8_results.json"
DRAFT7_RESULTS = Path(__file__).parent / "live_verdict7_results.json"

STEM_TEXT = "Write a short paragraph about"


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
    body = json.dumps({"content": text}).encode()
    req = urllib.request.Request(
        SERVER + "/tokenize", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("tokens", [])


def tokenize_required(text, what):
    ids = tokenize(text)
    if not ids:
        raise SystemExit(
            f"FATAL: /tokenize returned no ids for {what} — draft 8 "
            "prices from tokenized counts and cannot run honestly "
            "without them. Nothing fired for this text.")
    return ids


def measured(prompt, n_predict):
    m = EnergyMeter()
    m.start()
    resp = fire(prompt, n_predict)
    raw_j, dur = m.stop()
    return resp, raw_j, dur


def stem_claim(token_ids, stem_ids):
    if stem_ids and token_ids[:len(stem_ids)] == stem_ids:
        return len(stem_ids)
    return 0


def terminated(resp, gen_tokens, cap):
    """Natural termination = EOS/stop BEFORE the cap, not the cap."""
    if resp.get("stopped_limit"):
        return False
    if resp.get("stopped_eos"):
        return True
    if resp.get("stop") and gen_tokens < cap:
        return True
    return gen_tokens < cap


# --- upgrade 1: calibration candidate pools, per intended band ----
# claim mode resolved at runtime: "prefix" (text starts with PREFIX),
# "stem" (tokenize-matches STEM_TEXT), else 0.
CALIB_POOL = {
    "WEAK": [
        "Answer with one word: what is the capital of France?",
        "Answer with one word: what is the chemical symbol for gold?",
        "Answer with one word: how many days are there in a leap year?",
        "Reply with a single word: is the Earth flat, yes or no?",
    ],
    "MID": [
        "Write a short paragraph about how a kettle heats water. "
        "In exactly two sentences, cover the heating element and the "
        "steam, and nothing else.",
        "In exactly two sentences, explain why a bicycle stays "
        "upright while it is moving, using the language of balance "
        "and momentum throughout the whole answer, and do not add a "
        "third sentence or any extra remark after the second "
        "sentence ends.",
        "Write a short paragraph about how tides rise and fall. In "
        "exactly two sentences, cover the Moon's pull and the "
        "ocean's answer, and nothing else.",
        "Explain in exactly two sentences why leaves change color "
        "in autumn, mentioning chlorophyll, daylight and temperature "
        "as the days shorten, using plain language throughout, and "
        "stop when the second sentence is complete without adding "
        "any summary or closing remark afterwards.",
    ],
    "STRONG": [
        PREFIX + "Given all of the above, answer in exactly three "
        "short numbered points: first what the carrier contributes, "
        "second what the boundary contributes, third what the "
        "labeling layer contributes. One point per line, then stop.",
        PREFIX + "Given all of the above, list exactly two numbered "
        "contrasts between an empty room and a living subject "
        "facing the same carrier. Keep each contrast to one short "
        "line, then stop.",
        PREFIX + "Given all of the above, name exactly three "
        "speakers in the spectrum described — the planet, the "
        "brain, and the grid — with their frequencies, as a "
        "numbered list of three lines, then stop.",
    ],
}

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

VERDICT_ROUTES = ([("WARM", PREFIX + s) for s in STRONG_SUFFIX]
                  + [("COLD", p) for p in MID_COLD]
                  + [("COLD", p) for p in WEAK_COLD])


def main():
    metering = ("RAPL+GPU (full system)" if read_rapl_uj() is not None
                else "GPU-ONLY — RAPL unreadable, absolute figures "
                     "are LOWER BOUNDS")
    print(f"metering mode: {metering}")
    if "GPU-ONLY" in metering:
        print("*** WARNING: RAPL UNREADABLE — GPU-ONLY MODE, all "
              "absolute joule figures are LOWER BOUNDS ***")

    stem_ids = tokenize_required(STEM_TEXT, "the shared stem")
    prefix_ids = tokenize_required(PREFIX, "the bare prefix")
    prefix_tokens = len(prefix_ids)
    print(f"shared stem: {len(stem_ids)} tokens | bare prefix: "
          f"{prefix_tokens} tokens (tokenized)")

    print("measuring idle baseline (3 s)...")
    idle_w = measure_idle()
    print(f"idle baseline: {idle_w:.1f} W")

    judge = UrgencyJudge()
    band_cap = {"STRONG": judge.full_cap, "MID": judge.standard_cap,
                "WEAK": judge.early_cap}

    def claim_for(text, ids):
        """Draft-7 registry claim: what this run has primed/registered."""
        if text.startswith(PREFIX):
            return prefix_tokens
        return stem_claim(ids, stem_ids)

    # prime the bare prefix so STRONG calibration candidates ride a
    # genuinely locked route (their judged claim is real, not assumed)
    measured(PREFIX, 8)
    print("prefix primed for calibration")

    # --- upgrade 1: terminating calibration per band -------------
    print("\n--- calibration batch (terminating, per band) ---")
    calib_attempts = []
    selected = {"STRONG": [], "MID": [], "WEAK": []}  # terminating, in-band
    speed_ratio = None
    for band in ("WEAK", "MID", "STRONG"):
        for text in CALIB_POOL[band]:
            if len(selected[band]) >= 2:
                break
            ids = tokenize_required(text, "a calibration prompt")
            claim = claim_for(text, ids)
            judged = judge.judge(len(ids), claim)["band"]
            cap = band_cap[judged]
            resp, raw_j, dur = measured(text, cap)
            actual_j = max(0.0, raw_j - idle_w * dur)
            t = resp.get("timings", {})
            gen = t.get("predicted_n", 0)
            term = terminated(resp, gen, cap)
            in_band = (judged == band)
            att = {
                "intended_band": band, "judged_band": judged,
                "prompt_tokens": len(ids), "registry_claim": claim,
                "gen_tokens": gen, "cap": cap, "terminated": term,
                "in_band": in_band, "actual_j": actual_j,
                "stopped_eos": bool(resp.get("stopped_eos")),
                "stopped_limit": bool(resp.get("stopped_limit")),
                "text": text,
            }
            calib_attempts.append(att)
            if speed_ratio is None and t.get("prompt_per_second") \
                    and t.get("predicted_per_second"):
                speed_ratio = (t["predicted_per_second"]
                               / t["prompt_per_second"])
            tag = ("SELECTED" if (term and in_band)
                   else "mis-banded" if not in_band
                   else "no-EOS")
            print(f"  calib[{band}->{judged}/{tag}]: prompt="
                  f"{len(ids)} tok (claim {claim}), gen={gen} tok "
                  f"(cap {cap}), actual {actual_j:.1f} J")
            if term and in_band:
                selected[band].append(att)

    # gen-rate refit from terminating samples (see docstring)
    rate_samples = [a for b in selected.values() for a in b
                    if a["gen_tokens"] >= 8]
    if len(rate_samples) < 2:
        rate_samples = [a for b in selected.values() for a in b
                        if a["gen_tokens"] > 0]
    if not rate_samples:
        raise SystemExit(
            "FATAL: zero terminating calibration samples in ANY "
            "band — no honest gen rate exists. Draft 8 stops here "
            "rather than pricing from cap-run generations.")
    gen_rate = statistics.median(
        a["actual_j"] / a["gen_tokens"] for a in rate_samples)
    prompt_rate = gen_rate * (speed_ratio if speed_ratio else 0.24)
    print(f"refit: gen {gen_rate:.3f} J/tok (from {len(rate_samples)} "
          f"terminating samples) | prompt {prompt_rate:.3f} J/tok")

    # expected-gen table: terminating samples ONLY; cap fallback said out loud
    expected_gen, band_fallback, calib_summary = {}, [], {}
    for band, cap in band_cap.items():
        gens = [a["gen_tokens"] for a in selected[band]]
        if gens:
            expected_gen[band] = int(round(min(statistics.mean(gens), cap)))
            calib_summary[band] = {"n_terminating": len(gens),
                                   "mean_gen": statistics.mean(gens),
                                   "fallback_to_cap": False}
        else:
            expected_gen[band] = cap
            band_fallback.append(band)
            calib_summary[band] = {"n_terminating": 0, "mean_gen": None,
                                   "fallback_to_cap": True}
            print(f"  *** BAND {band}: ZERO terminating samples — "
                  f"expected gen FALLS BACK TO CAP ({cap}) ***")
    print(f"calibration per band: " + " | ".join(
        f"{b}: n={calib_summary[b]['n_terminating']}, mean="
        f"{calib_summary[b]['mean_gen']}" for b in band_cap))
    print(f"expected gen by band: {expected_gen}")

    model_prompt = JouleElectronModel(total_j_per_token=prompt_rate)
    model_gen = JouleElectronModel(total_j_per_token=gen_rate)
    full_spec = model_gen.full_path(0.0)
    neutron_spec = [(role, "neutron") for role, _ in full_spec]

    # route lock, as draft 7: prime the bare prefix after calibration
    measured(PREFIX, 8)
    print(f"\nroute locked: prefix = {prefix_tokens} tokens "
          f"(tokenized, primed bare, single slot)")

    falsifier = Falsifier(min_samples=5)
    results, probes = [], []
    discovery_overhead_total = 0.0

    def build_passport(kind, text, response_text, token_ids, claimed,
                       base_claim, active_pt, exp_gen):
        hops = []
        if claimed > 0:
            for h in hops_from_joule_electron(
                    model_prompt, neutron_spec, n_tokens=claimed):
                h.name = "prompt-cached:" + h.name
                hops.append(h)
        if active_pt > 0:
            for h in hops_from_joule_electron(
                    model_prompt, full_spec, n_tokens=active_pt):
                h.name = "prompt:" + h.name
                hops.append(h)
        if exp_gen > 0:
            for h in hops_from_joule_electron(
                    model_gen, full_spec, n_tokens=exp_gen):
                h.name = "gen:" + h.name
                hops.append(h)
        interactions = []
        base = min(base_claim, claimed)
        if base > 0:
            interactions.append({
                "other_id": kv_id(PREFIX if kind == "WARM" else STEM_TEXT),
                "joules": base * prompt_rate,
            })
        extra = claimed - base
        if extra > 0:
            # the portion the discovery probe earned beyond the
            # draft-7 registry: it interacted with this run's own
            # probe firing of the same prompt
            interactions.append({
                "other_id": kv_id("probe:" + text),
                "joules": extra * prompt_rate,
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

    def trial(idx, kind, text):
        token_ids = tokenize_required(text, "a verdict prompt")
        total_pt = len(token_ids)
        base_claim = claim_for(text, token_ids)

        # --- upgrade 2: discovery probe BEFORE pricing -----------
        resp_p, raw_p, dur_p = measured(text, 1)
        probe_j = max(0.0, raw_p - idle_w * dur_p)
        probe_cache = (resp_p.get("timings", {}).get("cache_n", 0) or 0)
        probe_cache = max(0, min(probe_cache, total_pt))
        probes.append({
            "route_index": idx, "kind": kind,
            "prompt_kv_id": kv_id(text),
            "probe_cache_n": probe_cache,
            "probe_overhead_j": probe_j,
            "probe_gen_tokens":
                resp_p.get("timings", {}).get("predicted_n", 0),
            "registry_claim_draft7_rule": base_claim,
        })
        nonlocal discovery_overhead_total
        discovery_overhead_total += probe_j
        print(f"[probe {idx}/{kind}] cache_n={probe_cache} "
              f"(draft-7 registry claim would be {base_claim}) | "
              f"overhead {probe_j:.2f} J")

        claimed = probe_cache  # earned by measurement, never more
        j = judge.judge(total_pt, claimed)
        active_pt = max(0, total_pt - claimed)
        exp_gen = expected_gen[j["band"]]
        pred_j = active_pt * prompt_rate + exp_gen * gen_rate
        resp, raw_j, dur = measured(text, j["gen_cap"])
        actual_j = max(0.0, raw_j - idle_w * dur)
        tt = resp.get("timings", {})
        p_tok = tt.get("prompt_n", 0) + (tt.get("cache_n", 0) or 0)
        g_tok = tt.get("predicted_n", 0)
        cache_n = tt.get("cache_n", 0) or 0
        falsifier.record(p_tok + g_tok, pred_j, actual_j)

        passport = build_passport(kind, text, resp.get("content", ""),
                                  token_ids, claimed, base_claim,
                                  active_pt, exp_gen)
        report = passport.cancellation_report(actual_j)
        paid_drift = passport.paid_joules - pred_j
        rec = {
            "kind": kind, "band": j["band"],
            "exit_path": j["exit_path"], "urgency": j["urgency"],
            "cache_judged": claimed,
            "cache_judged_registry_draft7_rule": base_claim,
            "cache_actual": cache_n,
            "probe_cache_n": probe_cache, "probe_overhead_j": probe_j,
            "prompt_tokens_tokenized": total_pt,
            "active_prompt_tokens_priced": active_pt,
            "gen_expected_tokens_priced": exp_gen,
            "gen_cap_ceiling": j["gen_cap"],
            "pred_j": pred_j, "actual_j": actual_j,
            "model_err_j": abs(pred_j - actual_j),
            "flat_err_j": abs(FLAT_J_PER_TOKEN * (p_tok + g_tok)
                              - actual_j),
            "prompt_tokens_server": p_tok, "gen_tokens_server": g_tok,
            "gen_terminated": terminated(resp, g_tok, j["gen_cap"]),
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
              f"{j['urgency']:.2f} | tokens {total_pt} (neutron "
              f"{claimed}) | gen priced {exp_gen} (cap "
              f"{j['gen_cap']}, actual {g_tok}) | cache actual "
              f"{cache_n} | predicted {pred_j:.1f} J | actual "
              f"{actual_j:.1f} J | identity residual "
              f"{report['identity_residual']:+.2f} J "
              f"({'OK' if report['identity_ok'] else 'FAIL'})")
        if abs(paid_drift) > 0.01:
            print(f"  [wart] passport paid {passport.paid_joules:.3f} J "
                  f"!= prediction {pred_j:.3f} J (drift "
                  f"{paid_drift:+.3f} J)")

    print("\n--- verdict batch (route-ordered, probe before pricing) ---")
    for i, (kind, text) in enumerate(VERDICT_ROUTES):
        trial(i, kind, text)

    n = len(results)
    mae_model = sum(r["model_err_j"] for r in results) / n
    mae_flat = sum(r["flat_err_j"] for r in results) / n
    held = sum(1 for r in results if r["identity_ok"])
    mean_resid = sum(r["identity_residual_j"] for r in results) / n

    print("\n--- LIVE VERDICT (draft 8) ---")
    print(falsifier.verdict())
    print(f"(incumbent flat baseline: {FLAT_J_PER_TOKEN} J/token)")
    print(f"passport identity: held {held}/{n} trials within "
          f"tolerance | mean identity residual {mean_resid:+.2f} J")
    print(f"discovery overhead (probes, excluded from trials): "
          f"{discovery_overhead_total:.2f} J over {len(probes)} probes")
    print(f"metering mode: {metering}")

    comparison = None
    if DRAFT7_RESULTS.exists():
        d7 = json.loads(DRAFT7_RESULTS.read_text())
        comparison = {
            "draft7": {"mae_model_j": d7["mae_model_j"],
                       "mae_flat_j": d7["mae_flat_j"],
                       "identity_held": d7["identity_held"],
                       "identity_n": d7["identity_n"],
                       "mean_identity_residual_j":
                           d7["mean_identity_residual_j"]},
            "draft8": {"mae_model_j": mae_model, "mae_flat_j": mae_flat,
                       "identity_held": held, "identity_n": n,
                       "mean_identity_residual_j": mean_resid},
            "discovery_overhead_j": discovery_overhead_total,
        }
        print("\n--- draft 7 vs draft 8 ---")
        print(f"model MAE:  {d7['mae_model_j']:.2f} J -> {mae_model:.2f} J")
        print(f"flat MAE:   {d7['mae_flat_j']:.2f} J -> {mae_flat:.2f} J")
        print(f"identity:   {d7['identity_held']}/{d7['identity_n']} -> "
              f"{held}/{n} | mean residual "
              f"{d7['mean_identity_residual_j']:+.2f} -> "
              f"{mean_resid:+.2f} J")
        print(f"discovery overhead (new cost): "
              f"{discovery_overhead_total:.2f} J")

    RESULTS.write_text(json.dumps({
        "draft": 8,
        "metering_mode": metering,
        "idle_w": idle_w, "gen_rate_j_per_tok": gen_rate,
        "prompt_rate_j_per_tok": prompt_rate,
        "prefix_tokens": prefix_tokens,
        "stem_tokens": len(stem_ids),
        "expected_gen_by_band": expected_gen,
        "calibration_summary": calib_summary,
        "calibration_band_fallback": band_fallback,
        "calibration_attempts": calib_attempts,
        "probes": probes,
        "discovery_overhead_total_j": discovery_overhead_total,
        "mae_model_j": mae_model, "mae_flat_j": mae_flat,
        "identity_held": held, "identity_n": n,
        "mean_identity_residual_j": mean_resid,
        "comparison_draft7_vs_draft8": comparison,
        "trials": results,
    }, indent=2))
    print(f"results written: {RESULTS}")


if __name__ == "__main__":
    main()
