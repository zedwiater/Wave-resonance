"""live_verdict11.py — Draft 11: draft 10 protocol, ONE change.

THE CORRECTED CLAIM RULE (Phase A reuse sweep, 2026-10-20):
draft 10's neutron claim (tokenized length of the prime prompt,
prime-textual) overshot the server's actual reuse by exactly 4
tokens on 6/6 trials. The sweep (reuse_sweep_results.json) found
the transferable rule in server-token space: on a trial that
follows its own prime, the server evaluates exactly prompt_n=5
server tokens (measured on every draft-10 trial, every sweep pair
with a 2-token divergent ending, and every state-controlled exact
repeat >=34 text tokens); server total = text tokens + 1 (BOS),
so cache_n = claim + 1 - 5 = claim - 4 for an exact prime-textual
claim. Chunk quantization (claim mod 8/16/32/64) was REJECTED
(mean abs residuals 1.9-17.0 vs 0.0). Draft 11 therefore prices
claim_corrected = max(0, claim - 4). The raw claim is still
logged on every record. Everything else is draft 10, unchanged:

Draft 10: draft 9 plus three rules that draft 9's own data wrote.

Carried from draft 9 unchanged: separate calibration batch,
single-slot -np 1 server, route-ordered verdict batch, bare-prefix
priming, EnergyMeter = RAPL + amdgpu idle-subtracted, tokenize-based
counts, shared-stem neutron registry, per-trial Passport +
cancellation_report, the discovery firing metered and reported as
overhead only, the BAND GUARD (band from the registry claim BEFORE
any prime/probe data exists, re-derived after and asserted equal —
prime data never enters judge.judge() anywhere in this file),
stop_type-based termination (stop_type in (eos, word) =
terminating; the raw stop fields are logged verbatim again), and
the falsifier = model MAE vs flat 1.69 J/token over server-reported
totals (scoring only, never in the prediction path).

RULE 1 — PRICE OPEN AT CAP WHEN THE (band, OPEN) CELL IS EMPTY.
Draft 9: every OPEN cell was empty (no terminating OPEN sample in
any band), so OPEN generations fell back to the band mean — which
is the BOUNDED mean. 10 of 11 open generations across the drafts
hit their cap; the warm trials priced 59 expected gen tokens
against an actual 128 and underpriced by ~51 J each. Draft 10
expected-gen chain, declared per trial:
  (band, shape) cell with n>=2 terminating samples -> cell mean;
  else if shape == OPEN -> the band cap;
  else -> band mean over terminating samples; else band cap.

RULE 2 — PROBE-AS-PRIME.
Draft 9's paradox: on cold routes the probe REPORTED cache_n=0,
yet the trial that followed reused 26/28 tokens — the probe's
firing had primed the single slot, and the reuse came from what
the prime ESTABLISHED, not from what it reported. Draft 10 renames
the discovery firing to what it is: a PRIME (exact route prompt,
max_tokens=1, metered as overhead, as before). The trial's neutron
claim = tokenized length of the longest common TEXTUAL prefix
between the prime prompt and the trial prompt (textual route
identity, the draft-7 logic — never token-id prefix comparison;
tokenizing prefix+suffix re-pieces the junction token), capped by
the trial's prompt length. The prime's reported cache_n is logged
for the record and is NOT the claim. If the trial prompt does not
start with the prime prompt textually, the claim falls back to
the registry stem claim only.

RULE 3 — PRIME ONLY ROUTES EXPECTED TO REPEAT.
In this protocol every route is fired twice (prime + trial), so
all routes are primed — but the run must prove priming pays. Per
route the results carry: prime overhead, claimed neutrons,
savings per repeat (= claim x prompt rate), realized repeats (1 —
the trial the prime served), realized savings, net, and the
break-even repeat count (prime cost / savings per repeat). A route
whose savings do not cover its prime within the run is flagged,
and the aggregate verdict states whether priming paid for itself
this run, route by route and in total.
"""
import json
import math
import os
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
RESULTS = Path(__file__).parent / "live_verdict11_results.json"
DRAFT7_RESULTS = Path(__file__).parent / "live_verdict7_results.json"
DRAFT8_RESULTS = Path(__file__).parent / "live_verdict8_results.json"
DRAFT9_RESULTS = Path(__file__).parent / "live_verdict9_results.json"
DRAFT10_RESULTS = Path(__file__).parent / "live_verdict10_results.json"

# Phase A corrected claim rule: constant 4-token shortfall for
# prime-textual (exact prime prompt) claims. See module docstring.
SHORTFALL_TOKENS = 4


def shortfall_model(claim):
    return SHORTFALL_TOKENS if claim > 0 else 0

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
            f"FATAL: /tokenize returned no ids for {what} — draft 11 "
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
            "band — no honest gen rate exists. Draft 11 stops here "
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
        """RULE 1 chain, declared per use: (band, shape) cell with
        n>=2 terminating -> cell mean; else shape==OPEN -> band cap
        (draft 9 priced open gens at the bounded band mean, 59 vs
        an actual 128, ~51 J of warm underpricing); else band mean
        over terminating samples of the band; else band cap."""
        cell = cells[(band, shape)]
        if cell["n_terminating"] >= 2:
            return (int(round(min(cell["mean_gen"], band_cap[band]))),
                    f"cell:({band},{shape}) n={cell['n_terminating']}")
        if shape == "OPEN":
            return (band_cap[band],
                    f"open-cap:{band} (cell ({band},{shape}) "
                    f"n={cell['n_terminating']} < 2 — rule 1)")
        if band_means[band] is not None:
            return (int(round(min(band_means[band], band_cap[band]))),
                    f"band-fallback:{band} (cell ({band},{shape}) "
                    f"n={cell['n_terminating']} < 2)")
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
    results, primes, prime_cb = [], [], []
    prime_overhead_total = 0.0

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
                "other_id": kv_id("prime:" + text),
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

        # --- BAND GUARD (carried): band BEFORE the prime exists,
        # registry claim only. The prime has not fired yet; nothing
        # it will report can exist at banding time.
        j = judge.judge(total_pt, base_claim)
        band_before = j["band"]

        # --- RULE 2: the prime (draft 9's probe, re-read) --------
        # Exact route prompt, max_tokens=1, metered as overhead.
        prime_text = text
        resp_p, raw_p, dur_p = measured(prime_text, 1)
        sf_p = stop_fields(resp_p)
        census(sf_p, resp_p)
        prime_j = max(0.0, raw_p - idle_w * dur_p)
        prime_reported_cache = (resp_p.get("timings", {})
                                .get("cache_n", 0) or 0)
        prime_reported_cache = max(0, min(prime_reported_cache,
                                          total_pt))
        primes.append({
            "route_index": idx, "kind": kind,
            "prompt_kv_id": kv_id(text),
            "prime_reported_cache_n": prime_reported_cache,
            "prime_overhead_j": prime_j,
            "prime_gen_tokens":
                resp_p.get("timings", {}).get("predicted_n", 0),
            "prime_stop_fields": sf_p,
            "registry_claim": base_claim,
            "band_before_prime": band_before,
        })
        nonlocal prime_overhead_total
        prime_overhead_total += prime_j

        # --- BAND GUARD assertion: re-derive the band from the
        # registry claim alone (prime data is never an input) and
        # assert the prime changed nothing about the banding.
        band_recheck = judge.judge(total_pt, base_claim)["band"]
        assert band_recheck == band_before, (
            f"band guard tripped on trial {idx}: before="
            f"{band_before} recheck={band_recheck}")
        band_at_firing = j["band"]
        assert band_at_firing == band_before

        # --- RULE 2 claim: what the prime ESTABLISHED, not what
        # it reported. Longest common TEXTUAL prefix between the
        # prime prompt and the trial prompt, tokenized; never a
        # token-id prefix comparison (junction re-piecing). If the
        # trial prompt does not start with the prime prompt
        # textually, the claim is the registry stem claim only.
        lcp_chars = len(os.path.commonprefix([prime_text, text]))
        if text.startswith(prime_text):
            prime_ids = tokenize_required(prime_text,
                                          "the prime prompt")
            claimed_raw = min(len(prime_ids), total_pt)
            claim_source = "prime-textual"
        else:
            claimed_raw = stem_claim(token_ids, stem_ids)
            claim_source = "registry-stem(prime-not-textual-prefix)"
        # --- DRAFT 11: corrected claim. The Phase A sweep's rule
        # (constant 4 for prime-textual claims) is applied ONCE,
        # here; every downstream consumer (pricing, passport,
        # cost-benefit) sees the corrected claim, and the raw
        # claim is carried on the records for audit.
        sf_model = shortfall_model(claimed_raw)
        claimed = max(0, claimed_raw - sf_model)
        print(f"[prime {idx}/{kind}] reported cache_n="
              f"{prime_reported_cache} (logged, NOT the claim; "
              f"registry claim {base_claim}) | overhead "
              f"{prime_j:.2f} J | claim {claimed} via {claim_source} "
              f"(raw {claimed_raw}, corrected -{sf_model} per "
              f"Phase A) (textual prefix {lcp_chars} chars) | band "
              f"before prime={band_before}, at firing="
              f"{band_at_firing} (guard OK)")

        # --- RULE 3 bookkeeping: did this prime pay for itself? --
        savings_per_repeat = claimed * prompt_rate
        realized_repeats = 1  # the one trial this prime serves
        realized_savings = savings_per_repeat * realized_repeats
        break_even = (math.ceil(prime_j / savings_per_repeat)
                      if savings_per_repeat > 0 else None)
        cb = {
            "route_index": idx, "kind": kind,
            "prompt_kv_id": kv_id(text),
            "prime_overhead_j": prime_j,
            "claim_tokens": claimed,
            "claim_tokens_raw": claimed_raw,
            "shortfall_model_tokens": sf_model,
            "claim_source": claim_source,
            "savings_per_repeat_j": savings_per_repeat,
            "realized_repeats": realized_repeats,
            "realized_savings_j": realized_savings,
            "net_j": realized_savings - prime_j,
            "break_even_repeats": break_even,
            "paid_for_itself": realized_savings >= prime_j,
        }
        prime_cb.append(cb)

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
            "band_before_prime": band_before,
            "band_at_firing": band_at_firing,
            "band_guard_ok": band_before == band_at_firing,
            "exit_path": j["exit_path"], "urgency": j["urgency"],
            "shape": shape,
            "expected_gen_source": exp_src,
            "cache_judged": claimed,
            "cache_judged_raw_claim": claimed_raw,
            "shortfall_model_tokens": sf_model,
            "claim_corrected_vs_actual_tokens": claimed - cache_n,
            "cache_judged_registry_claim": base_claim,
            "claim_source": claim_source,
            "textual_prefix_chars": lcp_chars,
            "cache_actual": cache_n,
            "prime_reported_cache_n": prime_reported_cache,
            "prime_overhead_j": prime_j,
            "prime_stop_fields": sf_p,
            "prime_cost_benefit": cb,
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
              f"{claimed} via {claim_source}) | gen priced {exp_gen} "
              f"via {exp_src} "
              f"(cap {j['gen_cap']}, actual {g_tok}, stop_type="
              f"{sf_t['stop_type']}) | cache actual {cache_n} | "
              f"predicted {pred_j:.1f} J | actual {actual_j:.1f} J | "
              f"identity residual {report['identity_residual']:+.2f} J "
              f"({'OK' if report['identity_ok'] else 'FAIL'})")
        if abs(paid_drift) > 0.01:
            print(f"  [wart] passport paid {passport.paid_joules:.3f} J "
                  f"!= prediction {pred_j:.3f} J (drift "
                  f"{paid_drift:+.3f} J)")

    print("\n--- verdict batch (band first, prime second, "
          "claim from what the prime established) ---")
    for i, (kind, text) in enumerate(VERDICT_ROUTES):
        trial(i, kind, text)

    n = len(results)
    mae_model = sum(r["model_err_j"] for r in results) / n
    mae_flat = sum(r["flat_err_j"] for r in results) / n
    held = sum(1 for r in results if r["identity_ok"])
    mean_resid = sum(r["identity_residual_j"] for r in results) / n

    # --- RULE 3 aggregate: did priming pay for itself? -----------
    savings_total = sum(c["realized_savings_j"] for c in prime_cb)
    priming_paid = savings_total >= prime_overhead_total

    print("\n--- LIVE VERDICT (draft 11) ---")
    print(falsifier.verdict())
    print(f"(incumbent flat baseline: {FLAT_J_PER_TOKEN} J/token)")
    print(f"passport identity: held {held}/{n} trials within "
          f"tolerance | mean identity residual {mean_resid:+.2f} J")
    print(f"prime overhead (primes, excluded from trials): "
          f"{prime_overhead_total:.2f} J over {len(primes)} primes")
    print(f"metering mode: {metering}")
    print(f"band guard: all trials band-before-prime == "
          f"band-at-firing: "
          f"{all(r['band_guard_ok'] for r in results)}")

    print("\n--- prime cost-benefit (rule 3) ---")
    for c in prime_cb:
        flag = ("PAID" if c["paid_for_itself"] else
                "*** DID NOT PAY within this run ***")
        be = (c["break_even_repeats"] if c["break_even_repeats"]
              is not None else "never (zero savings)")
        print(f"  route {c['route_index']}/{c['kind']} "
              f"#{c['prompt_kv_id'][:6]}: prime {c['prime_overhead_j']:.2f} J "
              f"| claim {c['claim_tokens']} tok via {c['claim_source']} "
              f"| savings/repeat {c['savings_per_repeat_j']:.2f} J "
              f"| realized x{c['realized_repeats']} = "
              f"{c['realized_savings_j']:.2f} J | net {c['net_j']:+.2f} J "
              f"| break-even repeats {be} | {flag}")
    print(f"  TOTAL: overhead {prime_overhead_total:.2f} J vs "
          f"neutron savings {savings_total:.2f} J -> priming "
          f"{'PAID FOR ITSELF' if priming_paid else 'DID NOT PAY'} "
          f"this run")

    # --- fix 3 finding, from the recorded fields themselves ------
    seen_present = sorted(stop_census["keys_present_seen"])
    never_present = [k for k in STOP_KEYS
                     if k not in stop_census["keys_present_seen"]]
    stop_finding = (
        f"Across all generations of this run the completion "
        f"response carried stop keys {seen_present}; the searched "
        f"keys {never_present} NEVER appeared. Termination is "
        f"signalled by stop_type: counts "
        f"{stop_census['by_stop_type']}. 'terminating' in draft 11 "
        f"= stop_type in (eos, word); 'hit_limit' = stop_type == "
        f"limit. Draft 8's stopped_eos/stopped_limit reads were "
        f"reads of keys this server build does not emit.")
    print("\n--- stop-field finding (carried, re-verified) ---")
    print(stop_finding)
    print(f"response top-level keys (first generation): "
          f"{stop_census['response_key_set']}")

    def _agg(path, overhead_key):
        if not path.exists():
            return None
        d = json.loads(path.read_text())
        return {"mae_model_j": d["mae_model_j"],
                "mae_flat_j": d["mae_flat_j"],
                "identity_held": d["identity_held"],
                "identity_n": d["identity_n"],
                "mean_identity_residual_j":
                    d["mean_identity_residual_j"],
                "overhead_j": d.get(overhead_key)}

    comparison = {
        "draft7": _agg(DRAFT7_RESULTS, "discovery_overhead_total_j"),
        "draft8": _agg(DRAFT8_RESULTS, "discovery_overhead_total_j"),
        "draft9": _agg(DRAFT9_RESULTS, "discovery_overhead_total_j"),
        "draft10": _agg(DRAFT10_RESULTS, "prime_overhead_total_j"),
        "draft11": {"mae_model_j": mae_model, "mae_flat_j": mae_flat,
                    "identity_held": held, "identity_n": n,
                    "mean_identity_residual_j": mean_resid,
                    "overhead_j": prime_overhead_total},
    }
    print("\n--- drafts 7 / 8 / 9 / 10 / 11 ---")
    print(f"{'draft':<8} {'model MAE':>10} {'flat MAE':>10} "
          f"{'identity':>9} {'mean resid':>11} {'overhead':>9}")
    for name in ("draft7", "draft8", "draft9", "draft10", "draft11"):
        a = comparison[name]
        if a is None:
            print(f"{name:<8} (results file missing)")
            continue
        oh = (f"{a['overhead_j']:.2f}" if a["overhead_j"] is not None
              else "—")
        print(f"{name:<8} {a['mae_model_j']:>10.2f} "
              f"{a['mae_flat_j']:>10.2f} "
              f"{a['identity_held']}/{a['identity_n']:<7} "
              f"{a['mean_identity_residual_j']:>+11.2f} {oh:>9}")

    RESULTS.write_text(json.dumps({
        "draft": 11,
        "shortfall_model": {
            "rule": "claim_corrected = max(0, claim - 4) for "
                    "prime-textual claims",
            "basis": "Phase A reuse sweep: server evaluates "
                     "exactly prompt_n=5 server tokens on a trial "
                     "following its own prime; server total = text "
                     "tokens + 1 (BOS); cache_n = claim - 4. "
                     "Chunk quantization rejected.",
            "source_file": "reuse_sweep_results.json",
        },
        "metering_mode": metering,
        "idle_w": idle_w, "gen_rate_j_per_tok": gen_rate,
        "prompt_rate_j_per_tok": prompt_rate,
        "prefix_tokens": prefix_tokens,
        "stem_tokens": len(stem_ids),
        "shape_rules": [name for name, _ in SHAPE_RULES],
        "calibration_cells": calib_summary,
        "calibration_band_means": band_means,
        "calibration_attempts": calib_attempts,
        "primes": primes,
        "prime_overhead_total_j": prime_overhead_total,
        # draft-9 key name kept as an alias so cross-draft tooling
        # that reads discovery_overhead_total_j still works
        "discovery_overhead_total_j": prime_overhead_total,
        "prime_cost_benefit": prime_cb,
        "prime_savings_total_j": savings_total,
        "priming_paid_for_itself": priming_paid,
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
        "comparison_drafts_7_8_9_10_11": comparison,
        "trials": results,
    }, indent=2))
    print(f"results written: {RESULTS}")


if __name__ == "__main__":
    main()
