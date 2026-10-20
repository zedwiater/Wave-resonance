#!/usr/bin/env python3
"""TWIN RUNG 1 — literal W + W-dagger twin for GPT-2 + cancellation fingerprint.

Zak's backend direction, tested at the smallest scale where we own the SVD map:
build per-matrix floored pseudo-inverses (the literal twin), then measure whether
cancellation (projection onto top-k input-space singular directions) leaves a
delta that SEPARATES routine from novel prompts. Falsifiers pre-stated in the
results JSON and printed at the end.

OPERATOR NAMING (deliberate): the brief writes P_k = V_k V_k^T onto top-k
right-singular directions, applied to an INPUT activation x. For y = xW with
W (in x out), the input-space directions carrying singular gains are the
columns of U in W = U diag(s) V^T (equivalently V from SVD(W^T)). Projecting x
onto output-space V would be dimensionally wrong. We use P_k = U_k U_k^T and
say so everywhere. W-dagger (out x in) = V diag(1/s_masked) U^T.

Run on PC: ~/wave-sunday/.venv/bin/python scripts/twin_rung1.py
"""
import json, math, sys, time
from pathlib import Path

import numpy as np
import torch
import tiktoken
from safetensors import safe_open

BASE = Path.home() / "wave-sunday"
WEIGHTS = BASE / "data/models/gpt2/model.safetensors"
SVD_MAP = BASE / "data/spectra/gpt2_svd.json"
PROMPTS = BASE / "data/corpora/prompts/prompts.jsonl"
TWIN_OUT = BASE / "data/twin/gpt2_twin.pt"
RESULTS = BASE / "scripts/twin_rung1_results.json"
sys.path.insert(0, str(BASE / "harness"))

LAYERS = list(range(12))
TYPES = ["attn.c_attn", "attn.c_proj", "mlp.c_fc", "mlp.c_proj"]
TAUS = [1e-3, 1e-2]
N_PROMPTS = 64
MAX_TOK = 64
FIXED_KS = [64, 256]

FALSIFIERS = {
    "P1": ("FAIL if ROUTINE vs NOVEL delta profiles do not separate: "
           "|mean gap| < 0.02 in delta ratio at k90 for EVERY layer type, "
           "or |Cohen d| < 0.2 for every layer type -> the cancellation "
           "fingerprint is decoration at this scale."),
    "COST_GATE": ("If twin overhead > 3x standard with no P1 separation "
                  "-> recommend killing the literal twin here."),
}


def cohen_d(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return 0.0
    sp = math.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return float((a.mean() - b.mean()) / sp) if sp > 0 else 0.0


def main():
    t_start = time.time()
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    env = {"device": str(dev),
           "gpu": torch.cuda.get_device_name(0) if dev.type == "cuda" else None,
           "torch": torch.__version__}
    print("ENV", env, flush=True)

    svd_map = json.loads(SVD_MAP.read_text())

    # ---------- load weights ----------
    raw = {}
    with safe_open(str(WEIGHTS), framework="pt") as f:
        for k in f.keys():
            raw[k] = f.get_tensor(k).float()
    names = [f"h.{i}.{t}.weight" for i in LAYERS for t in TYPES]
    mats = {n: raw[n] for n in names}
    print(f"loaded {len(mats)} matrices", flush=True)

    # ---------- SVD + twins ----------
    twin_store = {}
    svd_info = {}          # name -> dict(cond, floored fracs, k90, crosscheck)
    U_store = {}           # name -> U on device (input-space directions)
    s_store = {}
    for n in names:
        W = mats[n]
        # SVD on CPU via numpy: GPU rocSOLVER hits 'invalid device function'
        # on this RDNA2 (gfx1032) and the async error poisons later GPU ops.
        # Same route map_svd.py used. Results moved to device for projection.
        Un, sn, Vhn = np.linalg.svd(W.numpy().astype(np.float64),
                                    full_matrices=False)
        U = torch.from_numpy(Un.astype(np.float32)).to(dev)
        s = torch.from_numpy(sn.astype(np.float32)).to(dev)
        Vh = torch.from_numpy(Vhn.astype(np.float32)).to(dev)
        U_store[n], s_store[n] = U, s
        r = len(s)
        cond = float(s[0] / s[-1]) if s[-1] > 0 else float("inf")
        e = s.double() ** 2
        cum = torch.cumsum(e, 0) / e.sum()
        k90 = int(torch.searchsorted(cum, 0.90).item()) + 1
        entry = {"shape": list(W.shape), "rank": r, "cond": cond, "k90": k90,
                 "sigma_max": float(s[0]), "sigma_min": float(s[-1]),
                 "map_sigma_max": svd_map[n].get("spec_norm"),
                 "map_k90": svd_map[n].get("k90"),
                 "sigma_max_err": abs(float(s[0]) - svd_map[n].get("spec_norm", -1)),
                 "k90_match": bool(k90 == svd_map[n].get("k90"))}
        pinvs = {}
        for tau in TAUS:
            keep = s >= tau * s[0]
            entry[f"floored_frac_tau{tau:g}"] = float(1.0 - keep.float().mean())
            inv_s = torch.where(keep, 1.0 / s, torch.zeros_like(s))
            pinvs[tau] = (Vh.T * inv_s.unsqueeze(0)) @ U.T   # (out, in)
        twin_store[n] = {
            "Wpinv_tau1e-3": pinvs[1e-3].cpu(),
            "Wpinv_tau1e-2": pinvs[1e-2].cpu(),
            "V": Vh.T.cpu(), "U": U.cpu(), "s": s.cpu(),
        }
        svd_info[n] = entry
        print(f"  svd {n} cond={cond:.3g} k90={k90} "
              f"floored@1e-3={entry['floored_frac_tau0.001']:.3f}", flush=True)

    TWIN_OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.save(twin_store, TWIN_OUT)
    twin_bytes = TWIN_OUT.stat().st_size
    base_bytes = WEIGHTS.stat().st_size
    print(f"twin saved {twin_bytes/1e6:.1f} MB vs base {base_bytes/1e6:.1f} MB", flush=True)

    # ---------- model ----------
    from transformers import GPT2Config, GPT2LMHeadModel
    cfg = GPT2Config.from_pretrained(str(WEIGHTS.parent))
    model = GPT2LMHeadModel(cfg)
    sd = {}
    for k, v in raw.items():
        if k.endswith(".attn.bias"):
            continue  # legacy causal-mask buffer in the checkpoint, not a parameter
        if k.startswith("h.") or k in ("wte.weight", "wpe.weight") or k.startswith("ln_f."):
            sd["transformer." + k] = v
    missing, unexpected = model.load_state_dict(sd, strict=False)
    model.tie_weights()
    real_missing = [m for m in missing if "lm_head" not in m]
    assert not real_missing, f"missing keys: {real_missing[:5]}"
    assert not unexpected, f"unexpected keys: {unexpected[:5]}"
    chk = model.transformer.h[0].mlp.c_fc.weight.detach()
    assert torch.allclose(chk, raw["h.0.mlp.c_fc.weight"]), "weight load mismatch"
    model.to(dev).eval()
    print("model loaded + verified against safetensors", flush=True)

    modules = {}
    for i in LAYERS:
        blk = model.transformer.h[i]
        modules[f"h.{i}.attn.c_attn.weight"] = blk.attn.c_attn
        modules[f"h.{i}.attn.c_proj.weight"] = blk.attn.c_proj
        modules[f"h.{i}.mlp.c_fc.weight"] = blk.mlp.c_fc
        modules[f"h.{i}.mlp.c_proj.weight"] = blk.mlp.c_proj

    # ---------- prompts ----------
    enc = tiktoken.get_encoding("gpt2")
    prompts = []
    for line in PROMPTS.read_text().splitlines():
        if len(prompts) >= N_PROMPTS:
            break
        try:
            txt = json.loads(line)["text"].strip()
        except Exception:
            continue
        if not txt:
            continue
        ids = enc.encode(txt)[:MAX_TOK]
        if len(ids) >= 16:
            prompts.append(ids)
    print(f"{len(prompts)} prompts", flush=True)

    # ---------- fingerprint: hooks + teacher-forced logprob ----------
    captured = {}
    handles = []

    def mk_hook(name):
        def hook(mod, inp):
            captured[name] = inp[0].detach()
        return hook

    for n, m in modules.items():
        handles.append(m.register_forward_pre_hook(mk_hook(n)))

    ks_for = {}
    for n in names:
        ks = {"k90": svd_info[n]["k90"], "k64": 64, "k256": 256}
        ks_for[n] = {kk: min(v, U_store[n].shape[1]) for kk, v in ks.items()}

    per_prompt = []   # dict(name -> dict(k -> delta ratio)), plus logprob
    with torch.no_grad():
        for pi, ids in enumerate(prompts):
            captured.clear()
            x = torch.tensor([ids], device=dev)
            out = model(x)
            logits = out.logits[0].float()
            lp = torch.log_softmax(logits[:-1], dim=-1)
            tgt = x[0, 1:]
            mean_lp = float(lp.gather(1, tgt.unsqueeze(1)).mean())
            rec = {"logprob": mean_lp, "n_tok": len(ids), "delta": {}}
            for n in names:
                xin = captured[n][0].float()          # (T, in)
                U = U_store[n]
                xn = xin.norm(dim=-1) + 1e-12
                d = {}
                for kk, kval in ks_for[n].items():
                    Uk = U[:, :kval]
                    resid = xin - (xin @ Uk) @ Uk.T
                    d[kk] = float((resid.norm(dim=-1) / xn).mean())
                rec["delta"][n] = d
            per_prompt.append(rec)
            if (pi + 1) % 16 == 0:
                print(f"  fingerprint {pi+1}/{len(prompts)}", flush=True)
    for h in handles:
        h.remove()

    # ---------- classify ROUTINE / NOVEL ----------
    lps = np.array([r["logprob"] for r in per_prompt])
    med = float(np.median(lps))
    for r in per_prompt:
        r["class"] = "ROUTINE" if r["logprob"] >= med else "NOVEL"
    n_r = sum(1 for r in per_prompt if r["class"] == "ROUTINE")
    print(f"logprob median {med:.3f}; ROUTINE {n_r} / NOVEL {len(per_prompt)-n_r}", flush=True)

    # ---------- aggregate ----------
    def prompt_type_val(r, t, kk):
        vals = [r["delta"][f"h.{i}.{t}.weight"][kk] for i in LAYERS]
        return float(np.mean(vals))

    delta_tables = {}
    for t in TYPES:
        delta_tables[t] = {}
        for kk in ["k90", "k64", "k256"]:
            rv = [prompt_type_val(r, t, kk) for r in per_prompt if r["class"] == "ROUTINE"]
            nv = [prompt_type_val(r, t, kk) for r in per_prompt if r["class"] == "NOVEL"]
            delta_tables[t][kk] = {
                "routine_mean": float(np.mean(rv)), "novel_mean": float(np.mean(nv)),
                "gap_novel_minus_routine": float(np.mean(nv) - np.mean(rv)),
                "cohen_d": cohen_d(nv, rv)}

    # depth trend at k90: gap per layer (types averaged)
    layer_gap = []
    for i in LAYERS:
        rv = [float(np.mean([r["delta"][f"h.{i}.{t}.weight"]["k90"] for t in TYPES]))
              for r in per_prompt if r["class"] == "ROUTINE"]
        nv = [float(np.mean([r["delta"][f"h.{i}.{t}.weight"]["k90"] for t in TYPES]))
              for r in per_prompt if r["class"] == "NOVEL"]
        layer_gap.append(float(np.mean(nv) - np.mean(rv)))
    xs = np.arange(12)
    depth_corr = float(np.corrcoef(xs, layer_gap)[0, 1]) if np.std(layer_gap) > 0 else 0.0
    depth_slope = float(np.polyfit(xs, layer_gap, 1)[0])

    # ---------- gates ----------
    k90 = {t: delta_tables[t]["k90"] for t in TYPES}
    separated = [t for t in TYPES if abs(k90[t]["gap_novel_minus_routine"]) >= 0.02
                 and abs(k90[t]["cohen_d"]) >= 0.2]
    p1_pass = len(separated) > 0
    direction = ("NOVEL>ROUTINE (novel excites tail more)"
                 if np.mean([k90[t]["gap_novel_minus_routine"] for t in TYPES]) > 0
                 else "ROUTINE>=NOVEL (inverted vs expectation)")

    # ---------- cost: standard vs twin-inline ----------
    from live_verdict import EnergyMeter, measure_idle
    gen_prompts = prompts[:8]

    def run_gens():
        tot_tok = 0
        for ids in gen_prompts:
            seed = torch.tensor([ids[:16]], device=dev)
            out = model.generate(seed, max_new_tokens=32, do_sample=False,
                                 pad_token_id=50256)
            tot_tok += out.shape[1] - seed.shape[1]
        return tot_tok

    proj_handles = []

    def mk_proj_hook(name):
        Uk = U_store[name][:, :ks_for[name]["k90"]]

        def hook(mod, inp):
            xin = inp[0].float()
            _ = (xin @ Uk) @ Uk.T
            return None
        return hook

    cost = {}
    for label, twin in [("standard", False), ("twin_inline", True)]:
        if twin:
            for n, m in modules.items():
                proj_handles.append(m.register_forward_pre_hook(mk_proj_hook(n)))
        idle_w = measure_idle(3.0)
        j_per_tok, rounds = [], 2
        for _ in range(rounds):
            meter = EnergyMeter()
            meter.start()
            toks = run_gens()
            raw_j, dt = meter.stop()
            net = max(raw_j - idle_w * dt, 0.0)
            j_per_tok.append(net / toks)
        for h in proj_handles:
            h.remove()
        proj_handles = []
        cost[label] = {"j_per_token_mean": float(np.mean(j_per_tok)),
                       "j_per_token_rounds": j_per_tok, "idle_w": idle_w,
                       "tokens_per_round": 8 * 32}
        print(f"cost {label}: {cost[label]['j_per_token_mean']:.3f} J/tok "
              f"(idle {idle_w:.1f} W)", flush=True)
    overhead = cost["twin_inline"]["j_per_token_mean"] / max(
        cost["standard"]["j_per_token_mean"], 1e-9)
    cost["overhead_factor"] = overhead
    cost_gate_kill = bool(overhead > 3.0 and not p1_pass)

    # ---------- condition summaries by type ----------
    cond_by_type, floored_by_type = {}, {}
    for t in TYPES:
        cs = [svd_info[f"h.{i}.{t}.weight"]["cond"] for i in LAYERS]
        cond_by_type[t] = {"mean": float(np.mean(cs)), "min": float(np.min(cs)),
                           "max": float(np.max(cs))}
        floored_by_type[t] = {
            f"tau{tau:g}": float(np.mean(
                [svd_info[f"h.{i}.{t}.weight"][f"floored_frac_tau{tau:g}"]
                 for i in LAYERS])) for tau in TAUS}

    results = {
        "rung": "twin_rung1",
        "environment": env,
        "falsifiers_prestated": FALSIFIERS,
        "operator_note": ("P_k = U_k U_k^T with U = input-space singular "
                          "directions of W (in x out, y = xW); equivalently "
                          "V of SVD(W^T). W-dagger = V diag(1/s) U^T, "
                          "singulars inverted only where s >= tau * s_max."),
        "svd_crosscheck": {
            "max_sigma_max_err": max(svd_info[n]["sigma_max_err"] for n in names),
            "k90_matches": sum(1 for n in names if svd_info[n]["k90_match"]),
            "of": len(names)},
        "condition_by_type": cond_by_type,
        "floored_frac_by_type": floored_by_type,
        "svd_per_matrix": svd_info,
        "classification": {"median_logprob": med, "n_routine": n_r,
                           "n_novel": len(per_prompt) - n_r,
                           "logprob_min": float(lps.min()),
                           "logprob_max": float(lps.max())},
        "delta_tables": delta_tables,
        "depth_trend_k90": {"layer_gap_novel_minus_routine": layer_gap,
                            "pearson_r_layer_vs_gap": depth_corr,
                            "slope_per_layer": depth_slope},
        "gates": {
            "P1_separation": "PASS" if p1_pass else "FAIL",
            "P1_separated_types": separated,
            "P1_direction": direction,
            "twin_overhead_factor": overhead,
            "COST_GATE_kill_recommendation": cost_gate_kill,
        },
        "cost": cost,
        "twin_size_bytes": twin_bytes,
        "base_model_bytes": base_bytes,
        "twin_vs_base_ratio": twin_bytes / base_bytes,
        "wall_seconds": time.time() - t_start,
    }
    RESULTS.write_text(json.dumps(results, indent=1))
    print(json.dumps({"gates": results["gates"],
                      "delta_k90": {t: delta_tables[t]["k90"] for t in TYPES},
                      "cost": {k: cost[k] for k in ("standard", "twin_inline")},
                      "overhead": overhead}, indent=1), flush=True)
    print("WROTE", RESULTS, flush=True)


if __name__ == "__main__":
    main()
