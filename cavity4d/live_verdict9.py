"""live_verdict9.py — Draft 9: draft 8 with the judge's consumption
of probe data fixed, in three parts.

Carried from drafts 7-8 unchanged: separate calibration batch,
single-slot -np 1 server, route-ordered verdict batch, bare-prefix
priming, EnergyMeter = RAPL + amdgpu idle-subtracted, tokenize-based
counts, shared-stem neutron registry, per-trial Passport +
cancellation_report, discovery probe metered and reported as
overhead only, falsifier = model MAE vs flat 1.69 J/token over
server-reported totals (scoring only, never in the prediction path).

FIX 1 — THE PROBE PRICES NEUTRONS ONLY.
Draft 8's bug: it fired the discovery probe FIRST and fed probe
cache_n into judge.judge() as the shared-prefix term. route_depth =
probe_cache / prompt_tokens pushed cold MID routes (26-28 of 30-32
tokens "shared") over the STRONG threshold (cap 64 -> 128) and WEAK
routes into MID (cap 16 -> 64): prompt-side savings were spent
twice, once as priced neutrons and once as generation authorization,
and the trials then actually generated into the bigger caps
(118-120 tokens, ~122 J vs draft 7's ~64 J on the same routes).
Draft 9 ordering is mandatory and structural:
  (a) band the prompt with judge.judge(total_tokens, REGISTRY claim)
      — the draft-7 mechanism: textual route identity (bare PREFIX)
      or the tokenized shared-stem match. The probe has not fired
      yet; its result cannot exist at banding time.
  (b) fire the discovery probe.
  (c) use probe cache_n ONLY to price prompt-side neutrons:
      active_prompt_tokens = total - probe_cache.
The band is re-derived from the registry claim after the probe as a
guard and asserted equal to the pre-probe band; both are logged per
trial. The probe number never enters judge.judge() anywhere in
this file.

FIX 2 — EXPECTED GEN KEYED BY PROMPT SHAPE.
Draft 8's expected-gen was keyed by band alone, but termination
tracks prompt SHAPE: bounded asks (an explicit count/length bound)
stop; open asks (paragraph/explain, no bound) run to their cap.
Deterministic classifier (classify_shape below; rule set documented
there): BOUNDED iff the lowercased prompt text carries an explicit
bound, else OPEN. Calibration pools carry both shapes per band
where the band allows; the expected-gen table is keyed by
(band, shape) from terminating samples of that band AND shape.
Fallback chain, declared per use: (band, shape) cell -> (band)
mean over all terminating samples of the band -> band cap. Every
fallback is printed and recorded; cell sizes are reported.

FIX 3 — RAW STOP FIELDS LOGGED VERBATIM.
Draft 8 read resp["stopped_eos"] / resp["stopped_limit"] and found
False on every sample, then inferred "terminating" from gen < cap.
A preflight completion against this server build (2026-10-20)
shows why: the /completion response has NO stopped_eos /
stopped_limit / stopped_word / finish_reason keys at all. Its
stop-related keys are: stop (bool), stop_type ("eos" | "limit" |
"word" | "none"), stopping_word, truncated. Termination on this
build is signalled by stop_type == "eos". Draft 9 records, for
EVERY generation (calibration, probe, trial), the verbatim values
of every searched stop key that is present, plus the list of
searched keys that were absent, and re-derives:
  terminating := stop_type in ("eos", "word")
  hit_limit   := stop_type == "limit"
("word" = stopped on a configured stop word — a natural stop, not
the cap. This protocol configures no stop words, so only "eos" is
expected; if "word" ever appears it is reported as-is.)
"""
import json
import re
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
RESULTS = Path(__file__).parent / "live_verdict9_results.json"
DRAFT8_RESULTS = Path(__file__).parent / "live_verdict8_results.json"

STEM_TEXT = "Write a short paragraph about"

# keys searched verbatim on every completion response (fix 3)
STOP_KEYS = ("finish_reason", "stop", "stop_type", "stopping_word",
             "stopped_eos", "stopped_limit", "stopped_word",
             "truncated")


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
            f"FATAL: /tokenize returned no ids for {what} — draft 9 "
            "prices from tokenized counts and cannot run honestly "
            "without them. Nothing fired for this text.")
    return ids


def measured(prompt, n_predict):
    m = EnergyMeter()
    m.start()
    resp = fire(prompt, n_predict)
    raw_j, dur = m.stop()
    return resp, raw_j, dur


def stop_fields(resp):
    """Fix 3: verbatim stop-related fields of a completion response.

    Returns the values of every searched key that is PRESENT, and
    the names of searched keys that were ABSENT (so the record
    itself proves e.g. stopped_eos does not exist on this build).
    """
    present = {k: resp[k] for k in STOP_KEYS if k in resp}
    absent = [k for k in STOP_KEYS if k not in resp]
    return {"present": present, "absent": absent,
            "stop_type": resp.get("stop_type")}


def terminated(resp):
    """Fix 3: termination re-derived from the VERIFIED field.

    On this server build the signal is stop_type: "eos" (or "word"
    for a configured stop word) = natural termination; "limit" =
    ran to the token cap. Length is recorded separately and never
    again used as the termination signal.
    """
    return resp.get("stop_type") in ("eos", "word")


def hit_limit(resp):
    return resp.get("stop_type") == "limit"


def stem_claim(token_ids, stem_ids):
    if stem_ids and token_ids[:len(stem_ids)] == stem_ids:
        return len(stem_ids)
    return 0


# --- fix 2: deterministic prompt-shape classifier -----------------
# BOUNDED iff the lowercased text matches any rule; else OPEN.
# Rule set (explicit bound on the answer's size):
#   R1 a number word or digit + a size unit:
#      "one word", "two sentences", "three short numbered points",
#      "5 lines", "exactly 2 paragraphs" (unit right after number)
#   R2 "exactly <number>" anywhere: "in exactly two sentences",
#      "name exactly three speakers", "list exactly two contrasts"
#   R3 "list <number>": "list 3 reasons" (no 'exactly' needed)
#   R4 "a single word" / "one short sentence" style singletons:
#      covered by R1 via 'one'/'single' + unit; 'single' is in the
#      number alternation for this purpose.
_NUM = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|single|\d+)"
_UNIT = r"(?:words?|sentences?|lines?|points?|items?|paragraphs?)"
SHAPE_RULES = (
    ("R1 number+unit", re.compile(rf"\b{_NUM}\s+(?:short\s+|numbered\s+)?{_UNIT}\b")),
    ("R2 exactly+number", re.compile(rf"\bexactly\s+{_NUM}\b")),
    ("R3 list+number", re.compile(rf"\blist\s+(?:exactly\s+)?{_NUM}\b")),
)


def classify_shape(text):
    """Return "BOUNDED" or "OPEN" for a prompt text (fix 2)."""
    low = text.lower()
    for _name, rx in SHAPE_RULES:
        if rx.search(low):
            return "BOUNDED"
    return "OPEN"


# --- calibration candidate pools, per intended band ---------------
# Both shapes per band where the band allows. Intended band is what
# the pool is filed under; the JUDGED band (registry claim only) is
# recorded for every attempt and a sample counts only in its judged
# band. Shape is whatever classify_shape says — recorded, never
# relabeled.
CALIB_POOL = {
    "WEAK": [
        # bounded
        "Answer with one word: what is the capital of France?",
        "Answer with one word: what is the chemical symbol for gold?",
        "Answer with one word: how many days are there in a leap year?",
        "Reply with a single word: is the Earth flat, yes or no?",
        # open (short, no bound; cap is the WEAK 16)
        "Say hello.",
        "Greet me warmly.",
        "Say thank you.",
    ],
    "MID": [
        # bounded
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
        # open (paragraph asks, no bound)
        "Write a short paragraph about how rain forms over the "
        "ocean, using the language of evaporation, condensation "
        "and falling water throughout the whole answer.",
        "Write a short paragraph about why the Moon seems to "
        "change shape in the sky, using the language of sunlight, "
        "orbit and shadow throughout the whole answer.",
    ],
    "STRONG": [
        # bounded (locked route: bare PREFIX + bounded ask)
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
        # open (locked route: bare PREFIX + open paragraph ask)
        PREFIX + "Given all of the above, write a short paragraph "
        "explaining how the labeling layer changes what the "
        "boundary can carry.",
        PREFIX + "Given all of the above, write a short paragraph "
        "explaining why the planet's line and the brain's line "
        "can share a spectrum without being the same signal.",
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

    def registry_claim(text, ids):
        """Fix 1(a): the draft-7 registry claim — the ONLY cache
        figure the judge may ever see. Textual route identity for
        the primed bare prefix; tokenized stem match otherwise."""
        if text.startswith(PREFIX):
            return prefix_tokens
        return stem_claim(ids, stem_ids)

    # prime the bare prefix so STRONG routes ride a genuinely
    # locked route (their registry claim is real, not assumed)
    _r, _raw, _dur = measured(PREFIX, 8)
    prime_stop = stop_fields(_r)
    print(f"prefix primed for calibration (stop_type="
          f"{prime_stop['stop_type']})")

    # stop-field census across EVERY generation of the run (fix 3)
    stop_census = {"by_stop_type": {}, "keys_present_seen": set(),
                   "keys_absent_seen": set(), "response_key_set": None}

    def census(sf, resp):
        st = sf["stop_type"]
        stop_census["by_stop_type"][st] = \
            stop_census["by_stop_type"].get(st, 0) + 1
        stop_census["keys_present_seen"].update(sf["present"].keys())
        stop_census["keys_absent_seen"].update(sf["absent"])
        if stop_census["response_key_set"] is None:
            stop_census["response_key_set"] = sorted(resp.keys())

    census(prime_stop, _r)

    # --- calibration: terminating samples per (band, shape) -------
    print("\n--- calibration batch (terminating, per band x shape) ---")
    calib_attempts = []
    # selected[(judged_band, shape)] = [attempts] terminating only
    selected = {}
    speed_ratio = None
    for band in ("WEAK", "MID", "STRONG"):
        have = {"BOUNDED": 0, "OPEN": 0}
        for text in CALIB_POOL[band]:
            if have["BOUNDED"] >= 2 and have["OPEN"] >= 2:
                break
            shape = classify_shape(text)
            if have[shape] >= 2:
                continue
            ids = tokenize_required(text, "a calibration prompt")
            claim = registry_claim(text, ids)
            judged = judge.judge(len(ids), claim)["band"]
            cap = band_cap[judged]
            resp, raw_j, dur = measured(text, cap)
            sf = stop_fields(resp)
            census(sf, resp)
            actual_j = max(0.0, raw_j - idle_w * dur)
            t = resp.get("timings", {})
            gen = t.get("predicted_n", 0)
            term = terminated(resp)
            in_band = (judged == band)
            att = {
                "intended_band": band, "judged_band": judged,
                "shape": shape,
                "prompt_tokens": len(ids), "registry_claim": claim,
                "gen_tokens": gen, "cap": cap, "terminated": term,
                "hit_limit": hit_limit(resp),
                "in_band": in_band, "actual_j": actual_j,
                "stop_fields": sf,
                "text": text,
            }
            calib_attempts.append(att)
            if speed_ratio is None and t.get("prompt_per_second") \
                    and t.get("predicted_per_second"):
                speed_ratio = (t["predicted_per_second"]
                               / t["prompt_per_second"])
            tag = ("SELECTED" if (term and in_band)
                   else "mis-banded" if not in_band
                   else f"not-terminating(stop_type={sf['stop_type']})")
            print(f"  calib[{band}->{judged}/{shape}/{tag}]: prompt="
                  f"{len(ids)} tok (registry claim {claim}), gen={gen} "
                  f"tok (cap {cap}), stop_type={sf['stop_type']}, "
                  f"actual {actual_j:.1f} J")
            if term and in_band:
                selected.setdefault((judged, shape), []).append(att)
                have[shape] += 1

    # gen-rate refit from terminating samples (draft-8 rule)
    all_selected = [a for v in selected.values() for a in v]
    rate_samples = [a for a in all_selected if a["gen_tokens"] >= 8]
    if len(rate_samples) < 2:
        rate_samples = [a for a in all_selected if a["gen_tokens"] > 0]
    if not rate_samples:
        raise SystemExit(
            "FATAL: zero terminating calibration samples in ANY "
            "band — no honest gen rate exists. Draft 9 stops here "
            "rather than pricing from cap-run generations.")
    gen_rate = statistics.median(
        a["actual_j"] / a["gen_tokens"] for a in rate_samples)
    prompt_rate = gen_rate * (speed_ratio if speed_ratio else 0.24)
    print(f"refit: gen {gen_rate:.3f} J/tok (from {len(rate_samples)} "
          f"terminating samples) | prompt {prompt_rate:.3f} J/tok")

    # --- expected-gen table keyed by (band, shape) ----------------
    cells, band_means = {}, {}
    for band in band_cap:
        gens_band = []
        for shape in ("BOUNDED", "OPEN"):
            gens = [a["gen_tokens"]
                    for a in selected.get((band, shape), [])]
            cells[(band, shape)] = {
                "n_terminating": len(gens),
                "mean_gen": (statistics.mean(gens) if gens else None),
            }
            gens_band.extend(gens)
        band_means[band] = (statistics.mean(gens_band)
                            if gens_band else None)

    def expected_gen_for(band, shape):
        """Fallback chain, declared: cell -> band mean -> cap."""
        cell = cells[(band, shape)]
        if cell["n_terminating"] > 0:
            return (int(round(min(cell["mean_gen"], band_cap[band]))),
                    f"cell:({band},{shape}) n={cell['n_terminating']}")
        if band_means[band] is not None:
            return (int(round(min(band_means[band], band_cap[band]))),
                    f"band-fallback:{band} (cell ({band},{shape}) "
                    f"empty)")
        return band_cap[band], f"cap-fallback:{band} (no terminating "\
                               f"samples in band)"

    calib_summary = {
        f"{b}|{s}": cells[(b, s)]
        for b in band_cap for s in ("BOUNDED", "OPEN")}
    print("calibration cells (band|shape: n, mean_gen):")
    for k in sorted(calib_summary):
        c = calib_summary[k]
        print(f"  {k}: n={c['n_terminating']}, mean={c['mean_gen']}")
        if c["n_terminating"] == 0:
            print(f"  *** CELL {k}: EMPTY — uses of it fall back "
                  f"(declared per trial) ***")
    print(f"band means (fallback level 2): {band_means}")

    model_prompt = JouleElectronModel(total_j_per_token=prompt_rate)
    model_gen = JouleElectronModel(total_j_per_token=gen_rate)
    full_spec = model_gen.full_path(0.0)
    neutron_spec = [(role, "neutron") for role, _ in full_spec]

    # route lock, as drafts 7-8: prime the bare prefix after calib
    _r2, _raw2, _dur2 = measured(PREFIX, 8)
    census(stop_fields(_r2), _r2)
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
        base_claim = registry_claim(text, token_ids)
        shape = classify_shape(text)

        # --- FIX 1(a): band BEFORE the probe exists, registry only
        j = judge.judge(total_pt, base_claim)
        band_before = j["band"]

        # --- FIX 1(b): discovery probe -----------------------------
        resp_p, raw_p, dur_p = measured(text, 1)
        sf_p = stop_fields(resp_p)
        census(sf_p, resp_p)
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
            "probe_stop_fields": sf_p,
            "registry_claim": base_claim,
            "band_before_probe": band_before,
        })
        nonlocal discovery_overhead_total
        discovery_overhead_total += probe_j

        # --- FIX 1 guard: re-derive the band from the registry
        # claim alone (the probe result is never an input) and
        # assert the probe changed nothing about the banding.
        band_recheck = judge.judge(total_pt, base_claim)["band"]
        assert band_recheck == band_before, (
            f"band guard tripped on trial {idx}: before="
            f"{band_before} recheck={band_recheck}")
        band_at_firing = j["band"]
        assert band_at_firing == band_before
        print(f"[probe {idx}/{kind}] cache_n={probe_cache} "
              f"(registry claim {base_claim}) | overhead "
              f"{probe_j:.2f} J | band before probe={band_before}, "
              f"at firing={band_at_firing} (guard OK)")

        # --- FIX 1(c): probe prices prompt-side neutrons ONLY -----
        claimed = probe_cache
        active_pt = max(0, total_pt - claimed)
        exp_gen, exp_src = expected_gen_for(band_before, shape)
        pred_j = active_pt * prompt_rate + exp_gen * gen_rate
        resp, raw_j, dur = measured(text, j["gen_cap"])
        sf_t = stop_fields(resp)
        census(sf_t, resp)
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
            "kind": kind, "band": band_at_firing,
            "band_before_probe": band_before,
            "band_at_firing": band_at_firing,
            "band_guard_ok": band_before == band_at_firing,
            "exit_path": j["exit_path"], "urgency": j["urgency"],
            "shape": shape,
            "expected_gen_source": exp_src,
            "cache_judged": claimed,
            "cache_judged_registry_claim": base_claim,
            "cache_actual": cache_n,
            "probe_cache_n": probe_cache, "probe_overhead_j": probe_j,
            "probe_stop_fields": sf_p,
            "prompt_tokens_tokenized": total_pt,
            "active_prompt_tokens_priced": active_pt,
            "gen_expected_tokens_priced": exp_gen,
            "gen_cap_ceiling": j["gen_cap"],
            "pred_j": pred_j, "actual_j": actual_j,
            "model_err_j": abs(pred_j - actual_j),
            "flat_err_j": abs(FLAT_J_PER_TOKEN * (p_tok + g_tok)
                              - actual_j),
            "prompt_tokens_server": p_tok, "gen_tokens_server": g_tok,
            "gen_terminated": terminated(resp),
            "gen_hit_limit": hit_limit(resp),
            "stop_fields": sf_t,
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
        print(f"[{kind}/{j['band']}/{j['exit_path']}/{shape}] urgency "
              f"{j['urgency']:.2f} | tokens {total_pt} (neutron "
              f"{claimed}) | gen priced {exp_gen} via {exp_src} "
              f"(cap {j['gen_cap']}, actual {g_tok}, stop_type="
              f"{sf_t['stop_type']}) | cache actual {cache_n} | "
              f"predicted {pred_j:.1f} J | actual {actual_j:.1f} J | "
              f"identity residual {report['identity_residual']:+.2f} J "
              f"({'OK' if report['identity_ok'] else 'FAIL'})")
        if abs(paid_drift) > 0.01:
            print(f"  [wart] passport paid {passport.paid_joules:.3f} J "
                  f"!= prediction {pred_j:.3f} J (drift "
                  f"{paid_drift:+.3f} J)")

    print("\n--- verdict batch (band first, probe second, "
          "probe prices neutrons only) ---")
    for i, (kind, text) in enumerate(VERDICT_ROUTES):
        trial(i, kind, text)

    n = len(results)
    mae_model = sum(r["model_err_j"] for r in results) / n
    mae_flat = sum(r["flat_err_j"] for r in results) / n
    held = sum(1 for r in results if r["identity_ok"])
    mean_resid = sum(r["identity_residual_j"] for r in results) / n

    print("\n--- LIVE VERDICT (draft 9) ---")
    print(falsifier.verdict())
    print(f"(incumbent flat baseline: {FLAT_J_PER_TOKEN} J/token)")
    print(f"passport identity: held {held}/{n} trials within "
          f"tolerance | mean identity residual {mean_resid:+.2f} J")
    print(f"discovery overhead (probes, excluded from trials): "
          f"{discovery_overhead_total:.2f} J over {len(probes)} probes")
    print(f"metering mode: {metering}")
    print(f"band guard: all trials band-before-probe == "
          f"band-at-firing: "
          f"{all(r['band_guard_ok'] for r in results)}")

    # --- fix 3 finding, from the recorded fields themselves ------
    seen_present = sorted(stop_census["keys_present_seen"])
    never_present = [k for k in STOP_KEYS
                     if k not in stop_census["keys_present_seen"]]
    stop_finding = (
        f"Across all generations of this run the completion "
        f"response carried stop keys {seen_present}; the searched "
        f"keys {never_present} NEVER appeared. Termination is "
        f"signalled by stop_type: counts "
        f"{stop_census['by_stop_type']}. 'terminating' in draft 9 "
        f"= stop_type in (eos, word); 'hit_limit' = stop_type == "
        f"limit. Draft 8's stopped_eos/stopped_limit reads were "
        f"reads of keys this server build does not emit.")
    print("\n--- stop-field finding (fix 3) ---")
    print(stop_finding)
    print(f"response top-level keys (first generation): "
          f"{stop_census['response_key_set']}")

    comparison = None
    if DRAFT8_RESULTS.exists():
        d8 = json.loads(DRAFT8_RESULTS.read_text())
        comparison = {
            "draft8": {"mae_model_j": d8["mae_model_j"],
                       "mae_flat_j": d8["mae_flat_j"],
                       "identity_held": d8["identity_held"],
                       "identity_n": d8["identity_n"],
                       "mean_identity_residual_j":
                           d8["mean_identity_residual_j"],
                       "discovery_overhead_j":
                           d8["discovery_overhead_total_j"]},
            "draft9": {"mae_model_j": mae_model, "mae_flat_j": mae_flat,
                       "identity_held": held, "identity_n": n,
                       "mean_identity_residual_j": mean_resid,
                       "discovery_overhead_j": discovery_overhead_total},
        }
        print("\n--- draft 8 vs draft 9 ---")
        print(f"model MAE:  {d8['mae_model_j']:.2f} J -> {mae_model:.2f} J")
        print(f"flat MAE:   {d8['mae_flat_j']:.2f} J -> {mae_flat:.2f} J")
        print(f"identity:   {d8['identity_held']}/{d8['identity_n']} -> "
              f"{held}/{n} | mean residual "
              f"{d8['mean_identity_residual_j']:+.2f} -> "
              f"{mean_resid:+.2f} J")
        print(f"discovery overhead: "
              f"{d8['discovery_overhead_total_j']:.2f} J -> "
              f"{discovery_overhead_total:.2f} J")
        print("per-band behavior (draft 8 band -> draft 9 band, "
              "actual J):")
        for r8, r9 in zip(d8["trials"], results):
            print(f"  {r9['kind']} #{r9['prompt_kv_id'][:6]}: "
                  f"{r8['band']} -> {r9['band']} | actual "
                  f"{r8['actual_j']:.1f} -> {r9['actual_j']:.1f} J")

    RESULTS.write_text(json.dumps({
        "draft": 9,
        "metering_mode": metering,
        "idle_w": idle_w, "gen_rate_j_per_tok": gen_rate,
        "prompt_rate_j_per_tok": prompt_rate,
        "prefix_tokens": prefix_tokens,
        "stem_tokens": len(stem_ids),
        "shape_rules": [name for name, _ in SHAPE_RULES],
        "calibration_cells": calib_summary,
        "calibration_band_means": band_means,
        "calibration_attempts": calib_attempts,
        "probes": probes,
        "discovery_overhead_total_j": discovery_overhead_total,
        "mae_model_j": mae_model, "mae_flat_j": mae_flat,
        "identity_held": held, "identity_n": n,
        "mean_identity_residual_j": mean_resid,
        "stop_field_finding": stop_finding,
        "stop_census": {
            "by_stop_type": stop_census["by_stop_type"],
            "keys_present_seen": seen_present,
            "keys_never_present": never_present,
            "response_key_set": stop_census["response_key_set"],
        },
        "comparison_draft8_vs_draft9": comparison,
        "trials": results,
    }, indent=2))
    print(f"results written: {RESULTS}")


if __name__ == "__main__":
    main()
