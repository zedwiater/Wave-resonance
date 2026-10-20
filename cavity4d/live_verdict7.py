"""live_verdict7.py — Draft 7: draft-6 protocol + three pricing fixes.

Draft 6 carried the draft-5 protocol (separate calibration batch,
single-slot -np 1 server, route-ordered batch, bare-prefix priming,
urgency judge picks the exit path BEFORE firing, EnergyMeter =
RAPL + amdgpu, idle-subtracted) and added the per-trial Passport.
Its diagnosis (MAE 24.3 J, identity held 0/6, every residual an
OVERprice) named three pricing defects. Draft 7 fixes exactly
those three; everything else is unchanged:

  FIX 1 — TOKENIZE-BASED COUNTS. Draft 6 estimated prompt tokens
  as chars/4: a warm prompt was priced at ~95 active tokens when
  the server actually processed 26 uncached. Draft 7 tokenizes
  every prompt with the server's /tokenize endpoint BEFORE firing
  and prices the tokenized count (minus the route's claimed cached
  portion). The same pre-fire token ids go into the passport (no
  post-hoc tokenize in the passport path anymore).

  FIX 2 — SHARED-STEM NEUTRON PRICING FOR COLD ROUTES. Draft 6's
  single slot retained the shared opening stem, so "cold" trials
  received 26-28 cached tokens the judge priced at the full prompt
  rate. Draft 7 measures the shared stem once (tokenize the bare
  stem text), and the stem enters the judge's registry only
  because THIS run fired it — the calibration batch opens with it,
  so by verdict time the judge has itself primed it. Any route
  whose token ids begin with the stem's token ids claims those
  tokens as NEUTRON (priced, paid 0) — warm or cold. No assumed
  cache: a route that does not tokenize-match the stem claims 0,
  and the warm route claims only the bare PREFIX this run primed
  (its tokenized length, not the server-timing estimate).

  FIX 3 — EXPECTED-LENGTH GEN PRICING, NOT CAP. Draft 6 priced a
  WEAK/EARLY trial at its 16-token cap though it generated 5.
  Draft 7 prices generation at an expected length per exit path:
  the mean actual generated length of calibration prompts the
  judge placed in the same urgency band, capped by the band cap
  (a band with no calibration samples falls back to the overall
  calibration mean, likewise capped). The cap stays in the report
  as the authorization ceiling; the passport's gen hops are built
  at the expected count, so passport paid == pre-fire prediction
  by construction, exactly as in draft 6.

Falsifier unchanged: model MAE vs the flat 1.69 J/token incumbent
over all tokens (server-reported totals, used for scoring only —
never in the prediction path). Passport identity check unchanged:
gross - cancelled ~= metered delta via cancellation_report.
Oscillations stay EMPTY; interactions now fire for ANY trial that
claimed neutrons (warm -> the priming entry, cold -> the stem
entry), carrying the cancelled joules that portion contributed.
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
RESULTS = Path(__file__).parent / "live_verdict7_results.json"

# The bare shared opening stem of the cold writing routes — the same
# construction the calibration batch opens with. Measured once via
# /tokenize; claimed only by routes whose token ids start with it.
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
    """Server-side token ids; [] if unavailable."""
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
            f"FATAL: /tokenize returned no ids for {what} — draft 7 "
            "prices from tokenized counts (fix 1) and cannot run "
            "honestly without them. Nothing fired for this text.")
    return ids


def measured(prompt, n_predict):
    m = EnergyMeter()
    m.start()
    resp = fire(prompt, n_predict)
    raw_j, dur = m.stop()
    return resp, raw_j, dur


def stem_claim(token_ids, stem_ids):
    """Neutron tokens a route may claim: the registered stem's
    length iff the route's token ids begin with the stem's."""
    if stem_ids and token_ids[:len(stem_ids)] == stem_ids:
        return len(stem_ids)
    return 0


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

    # --- fix 1+2 setup: tokenize stem and prefix BEFORE firing ----
    stem_ids = tokenize_required(STEM_TEXT, "the shared stem")
    prefix_ids = tokenize_required(PREFIX, "the bare prefix")
    print(f"shared stem: {len(stem_ids)} tokens | bare prefix: "
          f"{len(prefix_ids)} tokens (tokenized)")

    print("measuring idle baseline (3 s)...")
    idle_w = measure_idle()
    print(f"idle baseline: {idle_w:.1f} W")

    judge = UrgencyJudge()
    band_cap = {}
    for b, cap in (("STRONG", judge.full_cap),
                   ("MID", judge.standard_cap),
                   ("WEAK", judge.early_cap)):
        band_cap[b] = cap

    print("\n--- calibration batch ---")
    gen_rates, speed_ratio = [], None
    calib_gens = []          # (band, actual generated tokens)
    for p in CALIB:
        ids = tokenize_required(p, "a calibration prompt")
        claim = stem_claim(ids, stem_ids)
        band = judge.judge(len(ids), claim)["band"]
        resp, raw_j, dur = measured(p, 96)
        actual_j = max(0.0, raw_j - idle_w * dur)
        t = resp.get("timings", {})
        if t.get("predicted_n"):
            gen_rates.append(actual_j / t["predicted_n"])
            calib_gens.append((band, t["predicted_n"]))
        if speed_ratio is None and t.get("prompt_per_second") \
                and t.get("predicted_per_second"):
            speed_ratio = (t["predicted_per_second"]
                           / t["prompt_per_second"])
        print(f"  calib[{band}]: prompt={len(ids)} tok (stem claim "
              f"{claim}), gen={t.get('predicted_n')} tok, actual "
              f"{actual_j:.1f} J")
    gen_rate = statistics.median(gen_rates)
    prompt_rate = gen_rate * (speed_ratio if speed_ratio else 0.24)
    print(f"refit: gen {gen_rate:.3f} J/tok | prompt {prompt_rate:.3f} "
          f"J/tok")

    # --- fix 3: expected gen length per band from calibration -----
    overall_mean = (statistics.mean(g for _, g in calib_gens)
                    if calib_gens else 0)
    expected_gen = {}
    for band, cap in band_cap.items():
        samples = [g for b, g in calib_gens if b == band]
        base = statistics.mean(samples) if samples else overall_mean
        expected_gen[band] = int(round(min(base, cap))) if base else cap
    print(f"expected gen by band (calibration-derived, cap = "
          f"ceiling): {expected_gen} | overall calib mean "
          f"{overall_mean:.1f} tok")

    # joule-electron models calibrated to this batch's two rates —
    # built once, used only to decompose each trial's prediction into
    # layer hops via the passport adapter.
    model_prompt = JouleElectronModel(total_j_per_token=prompt_rate)
    model_gen = JouleElectronModel(total_j_per_token=gen_rate)
    full_spec = model_gen.full_path(0.0)
    neutron_spec = [(role, "neutron") for role, _ in full_spec]

    # prime the single route with the BARE prefix (draft 5's rule).
    # Fix 2: the registered warm claim is the TOKENIZED prefix length
    # — this run primed exactly that text, nothing more is claimed.
    measured(PREFIX, 8)
    prefix_tokens = len(prefix_ids)
    print(f"\nroute locked: prefix = {prefix_tokens} tokens "
          f"(tokenized, primed bare, single slot)")

    falsifier = Falsifier(min_samples=5)
    results = []

    def build_passport(kind, text, response_text, token_ids,
                       claimed_tokens, claimed_against, active_pt,
                       exp_gen):
        hops = []
        if claimed_tokens > 0:
            for h in hops_from_joule_electron(
                    model_prompt, neutron_spec,
                    n_tokens=claimed_tokens):
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
        if claimed_tokens > 0:
            interactions.append({
                "other_id": kv_id(claimed_against),
                "joules": claimed_tokens * prompt_rate,
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

    def trial(kind, text):
        # FIX 1: real token counts BEFORE firing.
        token_ids = tokenize_required(text, "a verdict prompt")
        total_pt = len(token_ids)
        # FIX 2: claimed neutrons — only what this run primed /
        # registered: the bare prefix for warm routes, the shared
        # stem for any route that tokenize-matches it.
        if kind == "WARM":
            # Route identity is textual: the route IS the primed bare
            # prefix plus a suffix, and the claim is the REGISTERED
            # prefix length. (A token-id prefix check is stricter
            # than the server's own reuse — tokenizing PREFIX+suffix
            # re-pieces the junction token, so the ids of the bare
            # prefix are not an exact id-prefix of the full prompt;
            # run 1 claimed 0 this way and mis-banded the warm
            # trials. The server still reused 193-194 tokens.)
            claimed = prefix_tokens if text.startswith(PREFIX) else 0
            claimed_against = PREFIX
        else:
            claimed = stem_claim(token_ids, stem_ids)
            claimed_against = STEM_TEXT
        j = judge.judge(total_pt, claimed)
        active_pt = max(0, total_pt - claimed)
        # FIX 3: price the EXPECTED gen length for this band; the
        # band cap remains the authorization ceiling (and the
        # actual n_predict fired).
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
                                  token_ids, claimed, claimed_against,
                                  active_pt, exp_gen)
        report = passport.cancellation_report(actual_j)
        paid_drift = passport.paid_joules - pred_j
        rec = {
            "kind": kind, "band": j["band"],
            "exit_path": j["exit_path"], "urgency": j["urgency"],
            "cache_judged": claimed, "cache_actual": cache_n,
            "prompt_tokens_tokenized": total_pt,
            "active_prompt_tokens_priced": active_pt,
            "gen_expected_tokens_priced": exp_gen,
            "gen_cap_ceiling": j["gen_cap"],
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

    print("\n--- verdict batch (route-ordered) ---")
    for s in STRONG_SUFFIX:
        trial("WARM", PREFIX + s)
    for p in MID_COLD:
        trial("COLD", p)
    for p in WEAK_COLD:
        trial("COLD", p)

    n = len(results)
    mae_model = sum(r["model_err_j"] for r in results) / n
    mae_flat = sum(r["flat_err_j"] for r in results) / n
    held = sum(1 for r in results if r["identity_ok"])
    mean_resid = sum(r["identity_residual_j"] for r in results) / n

    print("\n--- LIVE VERDICT (draft 7) ---")
    print(falsifier.verdict())
    print(f"(incumbent flat baseline: {FLAT_J_PER_TOKEN} J/token)")
    print(f"passport identity: held {held}/{n} trials within "
          f"tolerance | mean identity residual {mean_resid:+.2f} J")
    print(f"metering mode: {metering}")

    RESULTS.write_text(json.dumps({
        "draft": 7,
        "metering_mode": metering,
        "idle_w": idle_w, "gen_rate_j_per_tok": gen_rate,
        "prompt_rate_j_per_tok": prompt_rate,
        "prefix_tokens": prefix_tokens,
        "stem_tokens": len(stem_ids),
        "expected_gen_by_band": expected_gen,
        "calib_gens": [{"band": b, "gen_tokens": g}
                       for b, g in calib_gens],
        "mae_model_j": mae_model, "mae_flat_j": mae_flat,
        "identity_held": held, "identity_n": n,
        "mean_identity_residual_j": mean_resid,
        "trials": results,
    }, indent=2))
    print(f"results written: {RESULTS}")


if __name__ == "__main__":
    main()
