"""reuse_sweep.py — Phase A diagnostic for the draft-10 -4 reuse wart.

Builds prime/trial prompt pairs whose shared TEXT prefix has an exact
/tokenize-measured token length, fires prime (max_tokens=1) then trial
(same textual prefix, different ending), and records the trial's
timings.cache_n (server-reported tokens_cached/reuse).

Claim definition matches draft 10: claim = len(/tokenize(shared text
prefix)). Shortfall = claim - actual.

This is a diagnostic: no energy metering, no verdict pricing.
"""
import json
import statistics
import sys
import urllib.request
from pathlib import Path

SERVER = "http://localhost:8080"
OUT = Path(__file__).parent / "reuse_sweep_results.json"
TARGETS = [4, 8, 12, 16, 20, 24, 28, 32, 33, 48, 64, 65, 96, 128,
           192, 224]
REPEAT_TARGETS = {16, 24, 28, 32, 48, 64, 96, 128}

# Candidate increments, in preference order. Each is appended only if
# tokenizing the extended text grows the token count by EXACTLY the
# number wanted for a clean one-token step; otherwise the next
# candidate is tried. This makes the prefixes token-boundary-exact by
# construction rather than by assumption about the tokenizer.
INCREMENTS = [" alpha", " beta", " gamma", " delta", " omega",
              " sigma", " theta", " lambda", " vector", " scalar",
              " copper", " silver", " marble", " velvet", " harbor",
              " meadow", " cinder", " falcon", " quartz", " timber"]

ENDINGS = [" red.", " blue."]


def post(path, payload, timeout=300):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        SERVER + path, data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def tokenize(text):
    return post("/tokenize", {"content": text}, timeout=30).get(
        "tokens", [])


def fire(prompt, n_predict=1):
    resp = post("/completion", {
        "prompt": prompt, "n_predict": n_predict,
        "cache_prompt": True, "temperature": 0.0,
    })
    return resp


def build_prefix(target):
    """Greedy one-token-at-a-time construction of a text whose
    /tokenize length is EXACTLY target tokens."""
    text = "Alpha"
    ids = tokenize(text)
    if len(ids) > target:
        raise RuntimeError("seed already longer than target")
    k = 0
    while len(ids) < target:
        advanced = False
        for j in range(len(INCREMENTS)):
            cand = INCREMENTS[(k + j) % len(INCREMENTS)]
            trial_text = text + cand
            trial_ids = tokenize(trial_text)
            if len(trial_ids) == len(ids) + 1:
                text, ids = trial_text, trial_ids
                k += (j + 1)
                advanced = True
                break
        if not advanced:
            raise RuntimeError(
                f"could not advance prefix at {len(ids)} tokens "
                f"(target {target})")
    return text, ids


def head_check(prefix_ids, full_ids):
    return full_ids[:len(prefix_ids)] == prefix_ids


def run_pair(target, rep):
    prefix_text, prefix_ids = build_prefix(target)
    claim = len(prefix_ids)
    prompts = [prefix_text + e for e in ENDINGS]
    full_ids = [tokenize(p) for p in prompts]
    heads = [head_check(prefix_ids, ids) for ids in full_ids]
    prime_resp = fire(prompts[0], 1)
    trial_resp = fire(prompts[1], 1)
    tt = trial_resp.get("timings", {})
    actual = tt.get("cache_n", 0) or 0
    row = {
        "target_tokens": target,
        "repetition": rep,
        "claim": claim,
        "actual_cache_n": actual,
        "shortfall": claim - actual,
        "prefix_end": "word-boundary",
        "prefix_token_head_of_prime": heads[0],
        "prefix_token_head_of_trial": heads[1],
        "prime_prompt_tokens_server": (
            prime_resp.get("timings", {}).get("prompt_n", 0)
            + (prime_resp.get("timings", {}).get("cache_n", 0) or 0)),
        "trial_prompt_tokens_server": (
            tt.get("prompt_n", 0) + actual),
        "trial_prompt_n_evaluated": tt.get("prompt_n", 0),
        "trial_tokens_cached_field": trial_resp.get("tokens_cached"),
        "prefix_text_tail": prefix_text[-40:],
    }
    print(f"  len={target} rep={rep}: claim={claim} actual={actual} "
          f"shortfall={claim - actual} heads={heads} "
          f"trial_eval={tt.get('prompt_n', 0)}", flush=True)
    return row


def fit(rows):
    """Try the candidate rules and report residuals for each.

    Rules: constant c; quantized claim mod C (C in 8/16/32/64) with
    the discarded tail = claim mod C (special case: mod 0 -> 0 or C,
    both tried implicitly via the fitted offset); offset + mod:
    shortfall = a + (claim mod C), a fitted as the rounded mean of
    shortfall - (claim mod C); proportional round(k*claim).
    The reported best rule is by mean absolute residual on the
    primary (rep=1) rows, with rep=2 rows as stability check.
    """
    primary = [r for r in rows if r["repetition"] == 1]
    claims = [r["claim"] for r in primary]
    shorts = [r["shortfall"] for r in primary]

    def score(fn):
        res = [abs(fn(c) - s) for c, s in zip(claims, shorts)]
        return (statistics.mean(res), max(res), res)

    cands = {}
    c_const = round(statistics.mean(shorts))
    cands[f"constant {c_const}"] = (lambda c, v=c_const: v, score(
        lambda c, v=c_const: v))
    for C in (8, 16, 32, 64):
        cands[f"claim mod {C}"] = (None, score(
            lambda c, C=C: c % C))
        offs = [s - (c % C) for c, s in zip(claims, shorts)]
        a = round(statistics.mean(offs))
        cands[f"{a} + claim mod {C}"] = (None, score(
            lambda c, C=C, a=a: a + (c % C)))
        # variant: a full chunk is also discarded when claim % C == 0
        offs2 = [s - ((c % C) or C) for c, s in zip(claims, shorts)]
        a2 = round(statistics.mean(offs2))
        cands[f"{a2} + ((claim mod {C}) or {C})"] = (None, score(
            lambda c, C=C, a2=a2: a2 + ((c % C) or C)))
    # proportional
    if sum(claims):
        k = sum(shorts) / sum(claims)
        cands[f"proportional {k:.4f}*claim"] = (None, score(
            lambda c, k=k: round(k * c)))
    ranked = sorted(cands.items(), key=lambda kv: kv[1][1][0])
    out = []
    for name, (_fn, (ma, mx, _res)) in ranked:
        out.append({"rule": name, "mean_abs_residual": ma,
                    "max_abs_residual": mx})
    return out


def main():
    health = post("/health", {}, timeout=10) if False else None
    rows = []
    for t in TARGETS:
        rows.append(run_pair(t, 1))
        if t in REPEAT_TARGETS:
            rows.append(run_pair(t, 2))
    ranked = fit(rows)
    print("\n--- candidate rules (by mean abs residual) ---")
    for r in ranked:
        print(f"  {r['rule']}: mean|r|={r['mean_abs_residual']:.3f} "
              f"max|r|={r['max_abs_residual']:.1f}")
    result = {
        "diagnostic": "draft-10 -4 reuse shortfall sweep",
        "claim_definition": "len(/tokenize(shared text prefix))",
        "actual_definition": "trial timings.cache_n",
        "targets": TARGETS,
        "rows": rows,
        "candidate_rules_ranked": ranked,
        "best_rule": ranked[0]["rule"] if ranked else None,
    }
    OUT.write_text(json.dumps(result, indent=2))
    print(f"results written: {OUT}")


if __name__ == "__main__":
    main()
