"""
transducer_v2_sim.py — TRANSDUCER SIM v2 (Zak's go 2026-10-21 12:19 EDT;
spec: transducer_v2_spec.md). Pre-registration is in ITERATION_LOG.md
(written before this run): tolerances and criteria are stated there and
in the results header.

WHAT CHANGED vs v1 (each change is a measured v1 dissection item):
  1. AGGREGATE-REFERENCED NODE STORES. v1 nodes cancelled against the
     CALM slice and matched the orthogonal residual; the attractor had
     already collapsed every state onto the CALM direction, so the
     residual carried no identity (nodes voted CALM 16/16, acc 0.250).
     v2 nodes store, per section, the LUT-style DELTA of each state
     against the AGGREGATE bank baseline (the settled / drive-end field
     of the bank-mean pattern), and match the observed delta WHOLE —
     the parallel component is kept, nothing is projected out. State
     identity lives in the rectified signature / delta direction
     (v1 law); the delta IS that direction, per section.
  2. CASCADE-TIMED SAMPLING. Every node taps at TWO windows: DRIVE_END
     (t = T_DRIVE = 0.30 s) and SETTLED (t = T_SETTLE = 0.50 s). Full
     section x window vote matrix reported (iter3/iter4 rule: localized
     events read at drive end, whole-pattern states read settled — v2
     measures which window each section actually wants for body states).
  3. LEDGER S11/S21 SPLIT. The unsampled through-flow is split into
     TRANSMITTED (component of the settled field parallel to the input
     wavefront — the forward port mode) and REFLECTED (the orthogonal,
     scattered component). Closure: in = tapped + transmitted +
     reflected + residual_second_cavity + bleed.
  4. OPEN-LOOP EXIT DECODING + RADIATIVE TEST. The far side sees only
     the RADIATIVE EXIT: an intensity spectrum (phase-blind) summed over
     two exit ports — the through port, (1-RHO)*|a_settled|^2, and the
     second cavity's radiation |r|^2, where r is the node-arm residual
     field after removing the aggregate component the stores account
     for. From that spectrum alone a least-squares decoder (fit on 24
     calibration trials) estimates USABLE power (ground truth: ledger
     tapped) and REMAINING power (ground truth: ledger residual), and a
     nearest-neighbour decode classifies the body state. Radiative
     hypothesis verdict per the pre-registered criterion.
  5. STEP-DOWN VOCABULARY + SCALE. Stage names in all logging:
     THROUGH-FLOW / TAP / NODE RING-DOWN / STEP-DOWN / RADIATIVE EXIT.
     Amplitude sweep 0.1x / 1x / 10x THROUGH-FLOW: ledger fractions
     reported per amplitude against the pre-stated 0.02 spread
     tolerance.
  6. MODEL GATE. The model receives the wrapper-LUT resolution ONLY:
     the verdict word + ONE metadata line (strongest section, its top
     subspectra tag, composed match). No deltas, no key. Gate:
     accuracy >= label arm AND mean total tokens <= 60.

All power figures are arbitrary units (simulated modal power), NOT
joules. Modes: `python3 transducer_v2_sim.py prep` then run the jobs
on the PC (expD_v3_runner.py), then `python3 transducer_v2_sim.py score`.
"""

import json
import sys

import numpy as np

sys.path.insert(0, "/home/hatch/workspace/harness-dev")
import audio_cavity_sim as sim
import cavity_topology as topo
from expBC_prep import STATE_KEYWORDS, STATE_LABEL_WORDS
from transducer_sim import kw_hit, NEAR_MISS

HD = "/home/hatch/workspace/harness-dev"
SEED = 70721
TRIALS_PER_STATE = 4
RHO_TAP = 0.10
MU = 0.5                      # matched (critical coupling), as v1 gate config
MU_BAD = 0.05
NODE_NOISE_P = 1e-3
WINDOWS = {"DRIVE_END": sim.T_DRIVE, "SETTLED": sim.T_SETTLE}
TAIL = "\nDescribe the body state in one short line.\nThe body state is:"

FRESH = json.load(open(f"{HD}/transducer_v2_baseline.json"))["baseline"]


def absorption(mu):
    return 4.0 * mu * (1.0 - mu)


SCALE = np.sqrt(RHO_TAP * absorption(MU))


def build_bank_fresh():
    prompts, cues = sim.build_templates()
    bank = {}
    for name, vec in prompts.items():
        bank[name] = vec
    for name, vec in cues.items():
        bank[name] = vec
    for s in topo.STATE_ORDER:
        bank[f"state:{s}"] = topo.encode_state(topo.state_values(s, FRESH))
    names = list(bank.keys())
    return names, np.array([bank[n] for n in names])


def evolve_window(spec, bank_vecs, t_total):
    a, diss, _ = sim.evolve(spec, alpha=1.0, pump_amp=1.0,
                            templates=bank_vecs, t_total=t_total)
    return a, diss


# ------------------------------------------------------------- node core ---
class V2Nodes:
    """Aggregate-referenced LUT delta stores, per section, per window.

    ref_delta[state][window] = settled/drive-end field of the clean
    state minus the aggregate bank baseline field at the SAME window.
    Observed delta = (tapped observation) - (tapped aggregate field).
    Match per section = |cosine| between observed delta slice and the
    stored state delta slice — the whole delta, parallel component
    kept (v1 law: identity lives in the delta direction itself).
    """

    def __init__(self, agg, ref_fields):
        # agg[window] = aggregate field; ref_fields[state][window]
        self.ref_delta = {s: {} for s in topo.STATE_ORDER}
        for s in topo.STATE_ORDER:
            for w in WINDOWS:
                self.ref_delta[s][w] = ref_fields[s][w] - agg[w]
        self.agg = agg

    def observe(self, a_window, eta):
        return SCALE * a_window + eta

    def delta_obs(self, a_window, window, eta):
        return self.observe(a_window, eta) - SCALE * self.agg[window]

    def section_matches(self, d_obs, window):
        """{section: {state: cosine}} for one observed delta."""
        out = {}
        for name, _c, _l, _h in topo.SECTIONS:
            idx = topo.SECTION_MODES[name]
            out[name] = {s: sim.cosine(d_obs[idx], self.ref_delta[s][window][idx])
                         for s in topo.STATE_ORDER}
        return out

    def classify(self, d_obs, window):
        """Energy-weighted composition (v1 weighting: observed delta
        energy shares per section, 0.02 floor). Returns (pred, scores,
        per-section votes, shares)."""
        matches = self.section_matches(d_obs, window)
        shares, tot = {}, 0.0
        for name, _c, _l, _h in topo.SECTIONS:
            e = float(np.sum(np.abs(d_obs[topo.SECTION_MODES[name]]) ** 2))
            shares[name] = e
            tot += e
        shares = {n: (e / tot if tot > 0 else 0.0) for n, e in shares.items()}
        wsum = sum(0.02 + shares[n] for n in shares)
        weights = {n: (0.02 + shares[n]) / wsum for n in shares}
        scores = {s: sum(weights[n] * matches[n][s] for n in weights)
                  for s in topo.STATE_ORDER}
        votes = {n: max(matches[n], key=matches[n].get) for n in matches}
        return max(scores, key=scores.get), scores, votes, shares


# ---------------------------------------------------------------- ledger ---
def ledger_for(a_set, spec, nd_by_section):
    """S11/S21-split ledger for one settled field (matched mu).
    nd_by_section: null depth of the settled slice vs the aggregate
    slice (noiseless, through the tap scale — scale cancels)."""
    p_in = float(np.sum(np.abs(a_set) ** 2))
    tapped = residual = 0.0
    A = absorption(MU)
    for name, _c, _l, _h in topo.SECTIONS:
        e_s = float(np.sum(np.abs(a_set[topo.SECTION_MODES[name]]) ** 2))
        coupled_s = RHO_TAP * A * e_s
        tapped += coupled_s * nd_by_section[name]
        residual += coupled_s * (1.0 - nd_by_section[name])
    bleed = RHO_TAP * (1.0 - A) * p_in
    d = spec / np.linalg.norm(spec)
    transmitted = (1.0 - RHO_TAP) * float(abs(np.vdot(d, a_set)) ** 2)
    reflected = (1.0 - RHO_TAP) * p_in - transmitted
    tot = tapped + transmitted + reflected + residual + bleed
    return {"power_in_through_flow": p_in,
            "power_tapped_by_nodes": tapped,
            "power_transmitted_S21": transmitted,
            "power_reflected_S11": reflected,
            "power_residual_second_cavity": residual,
            "power_bleed": bleed,
            "bleed_ratio": bleed / p_in if p_in > 0 else 0.0,
            "tapped_ratio": tapped / p_in if p_in > 0 else 0.0,
            "residual_ratio": residual / p_in if p_in > 0 else 0.0,
            "transmitted_ratio": transmitted / p_in if p_in > 0 else 0.0,
            "reflected_ratio": reflected / p_in if p_in > 0 else 0.0,
            "closure_error_frac": abs(tot - p_in) / p_in if p_in > 0 else 0.0}


def nd_vs_agg(a_set, a_agg):
    out = {}
    for name, _c, _l, _h in topo.SECTIONS:
        idx = topo.SECTION_MODES[name]
        u, v = a_set[idx], a_agg[idx]
        den = float(np.sum(np.abs(v) ** 2)) * float(np.sum(np.abs(u) ** 2))
        out[name] = float(abs(np.vdot(v, u)) ** 2 / den) if den > 0 else 0.0
    return out


# ------------------------------------------------------------ exit channel -
def residual_field(obs_set, a_agg_set):
    """Node-arm residual field r: observed tapped field minus its
    component along the tapped aggregate field, per section (the part
    the stores do NOT account for — what the second cavity radiates)."""
    r = np.zeros(sim.N_MODES, dtype=np.complex128)
    for name, _c, _l, _h in topo.SECTIONS:
        idx = topo.SECTION_MODES[name]
        ref = SCALE * a_agg_set[idx]
        u = obs_set[idx]
        den = float(np.vdot(ref, ref).real)
        coeff = np.vdot(ref, u) / den if den > 0 else 0.0
        r[idx] = u - coeff * ref
    return r


def exit_intensity(a_set, r):
    """RADIATIVE EXIT spectrum: two exit ports, intensities summed.
    Through port: (1-RHO)*|a_settled|^2. Second-cavity radiation: |r|^2.
    Phase-blind by construction (intensities only)."""
    return (1.0 - RHO_TAP) * np.abs(a_set) ** 2 + np.abs(r) ** 2


def exit_features(I):
    tot = float(np.sum(I))
    feats = [1.0, tot]
    for name, _c, _l, _h in topo.SECTIONS:
        e = float(np.sum(I[topo.SECTION_MODES[name]]))
        feats.append(e / tot if tot > 0 else 0.0)
    return np.array(feats)


# ------------------------------------------------------------------- prep --
def make_spec(state, rng):
    jvals = topo.jitter_values(topo.state_values(state, FRESH), rng)
    spec = topo.encode_state(jvals)
    spec = sim.add_modal_noise(rng, spec, 12.0)
    return spec, jvals


def prep():
    names, bank_vecs = build_bank_fresh()
    topo.init_baseline(bank_vecs)
    base_pattern = topo.baseline_pattern(bank_vecs)

    # THROUGH-FLOW references: aggregate field + clean state fields, per window
    agg, ref_fields = {}, {}
    for w, t_tot in WINDOWS.items():
        agg[w], _ = evolve_window(base_pattern, bank_vecs, t_tot)
    for s in topo.STATE_ORDER:
        ref_fields[s] = {}
        clean = topo.encode_state(topo.state_values(s, FRESH))
        for w, t_tot in WINDOWS.items():
            ref_fields[s][w], _ = evolve_window(clean, bank_vecs, t_tot)
    nodes = V2Nodes(agg, ref_fields)
    sig_list = [sim.rectified_signature(ref_fields[s]["SETTLED"], 1.0)
                for s in topo.STATE_ORDER]

    # ---- test trials: NODE RING-DOWN at both tap windows
    rng = np.random.default_rng(SEED)
    trials = []
    vote_hits = {w: {n: [] for n, _c, _l, _h in topo.SECTIONS} for w in WINDOWS}
    comp_hits = {w: [] for w in WINDOWS}
    whole_hits = []
    for s in topo.STATE_ORDER:
        for k in range(TRIALS_PER_STATE):
            spec, jvals = make_spec(s, rng)
            fields = {}
            diss = None
            for w, t_tot in WINDOWS.items():
                fields[w], d = evolve_window(spec, bank_vecs, t_tot)
                if w == "SETTLED":
                    diss = d
            eta_rng = np.random.default_rng(SEED + len(trials))
            eta = (eta_rng.standard_normal(sim.N_MODES)
                   + 1j * eta_rng.standard_normal(sim.N_MODES)) * np.sqrt(NODE_NOISE_P / 2)
            pred_w, scores_w, votes_w = {}, {}, {}
            for w in WINDOWS:
                d_obs = nodes.delta_obs(fields[w], w, eta)
                pred, scores, votes, shares = nodes.classify(d_obs, w)
                pred_w[w], scores_w[w], votes_w[w] = pred, scores, votes
                comp_hits[w].append(1 if pred == s else 0)
                for n in votes:
                    vote_hits[w][n].append(1 if votes[n] == s else 0)
            wpred_i, _ = sim.classify(sim.rectified_signature(fields["SETTLED"], 1.0), sig_list)
            whole_pred = topo.STATE_ORDER[wpred_i]
            whole_hits.append(1 if whole_pred == s else 0)
            nd = nd_vs_agg(fields["SETTLED"], agg["SETTLED"])
            led = ledger_for(fields["SETTLED"], spec, nd)
            obs_set = nodes.observe(fields["SETTLED"], eta)
            r = residual_field(obs_set, agg["SETTLED"])
            I = exit_intensity(fields["SETTLED"], r)
            d_obs_set = nodes.delta_obs(fields["SETTLED"], "SETTLED", eta)
            tags = topo.ranked_tags(d_obs_set)
            top_sec = max(topo.section_energies(d_obs_set),
                          key=topo.section_energies(d_obs_set).get)
            trials.append({
                "trial_id": f"V{s}{k}", "true_state": s,
                "jittered_values": {c: float(v) for c, v in jvals.items()},
                "node_pred": pred_w, "node_scores": scores_w,
                "whole_cavity_pred": whole_pred,
                "ledger": led, "exit_I": I,
                "top_section_settled": top_sec,
                "top_tag_settled": tags[0]["subspectra_id"],
                "diss_cavity": diss,
                "_spec": spec, "_fields": fields, "_eta": eta,
            })
    node_acc = {w: float(np.mean(comp_hits[w])) for w in WINDOWS}
    best_window = max(node_acc, key=node_acc.get)
    whole_acc = float(np.mean(whole_hits))
    vote_matrix = {w: {n: float(np.mean(v)) for n, v in vote_hits[w].items()}
                   for w in WINDOWS}

    # ---- RADIATIVE EXIT decode: calibration (24) -> test (16)
    cal_F, cal_use, cal_rem, cal_I = [], [], [], []
    cal_I_by_state = {s: [] for s in topo.STATE_ORDER}
    crng = np.random.default_rng(SEED + 500000)
    for si, s in enumerate(topo.STATE_ORDER):
        for rep in range(6):
            spec_c, _jv = make_spec(s, crng)
            a_st, _d = evolve_window(spec_c, bank_vecs, sim.T_SETTLE)
            erng = np.random.default_rng(SEED + 600000 + 100 * si + rep)
            eta_c = (erng.standard_normal(sim.N_MODES)
                     + 1j * erng.standard_normal(sim.N_MODES)) * np.sqrt(NODE_NOISE_P / 2)
            led_c = ledger_for(a_st, spec_c, nd_vs_agg(a_st, agg["SETTLED"]))
            r_c = residual_field(nodes.observe(a_st, eta_c), agg["SETTLED"])
            I_c = exit_intensity(a_st, r_c)
            cal_F.append(exit_features(I_c))
            cal_use.append(led_c["power_tapped_by_nodes"])
            cal_rem.append(led_c["power_residual_second_cavity"])
            cal_I.append(I_c)
            cal_I_by_state[s].append(I_c)
    F = np.array(cal_F)
    coef_use, *_ = np.linalg.lstsq(F, np.array(cal_use), rcond=None)
    coef_rem, *_ = np.linalg.lstsq(F, np.array(cal_rem), rcond=None)
    mean_I = {s: np.mean(cal_I_by_state[s], axis=0) for s in topo.STATE_ORDER}
    exit_rows, exit_hits = [], []
    for t in trials:
        I = t["exit_I"]
        est_use = float(exit_features(I) @ coef_use)
        est_rem = float(exit_features(I) @ coef_rem)
        gt_use = t["ledger"]["power_tapped_by_nodes"]
        gt_rem = t["ledger"]["power_residual_second_cavity"]
        sims = {s: sim.cosine(I, mean_I[s]) for s in topo.STATE_ORDER}
        epred = max(sims, key=sims.get)
        exit_hits.append(1 if epred == t["true_state"] else 0)
        exit_rows.append({"trial_id": t["trial_id"], "true_state": t["true_state"],
                          "exit_pred": epred,
                          "usable_gt": gt_use, "usable_est": est_use,
                          "usable_abs_err": abs(est_use - gt_use),
                          "remaining_gt": gt_rem, "remaining_est": est_rem,
                          "remaining_abs_err": abs(est_rem - gt_rem),
                          "p_in": t["ledger"]["power_in_through_flow"]})
    exit_acc = float(np.mean(exit_hits))
    p_in_mean = float(np.mean([r["p_in"] for r in exit_rows]))
    exit_decode = {
        "exit_only_classification_accuracy": exit_acc,
        "internal_whole_cavity_accuracy_same_trials": whole_acc,
        "radiative_criterion_prestated": "exit acc >= 0.75 AND >= internal - 0.10",
        "radiative_hypothesis_supported": bool(exit_acc >= 0.75 and exit_acc >= whole_acc - 0.10),
        "usable_power_decode": {
            "mean_abs_err": float(np.mean([r["usable_abs_err"] for r in exit_rows])),
            "mean_abs_err_frac_of_p_in": float(np.mean([r["usable_abs_err"] for r in exit_rows]) / p_in_mean),
            "gt_mean": float(np.mean([r["usable_gt"] for r in exit_rows]))},
        "remaining_power_decode": {
            "mean_abs_err": float(np.mean([r["remaining_abs_err"] for r in exit_rows])),
            "mean_abs_err_frac_of_p_in": float(np.mean([r["remaining_abs_err"] for r in exit_rows]) / p_in_mean),
            "gt_mean": float(np.mean([r["remaining_gt"] for r in exit_rows]))},
        "estimator": "least squares on [1, I_tot, per-section shares of I], fit on 24 calibration trials (4 clean states x 6 jittered replicates, disjoint seeds)",
        "rows": exit_rows,
    }

    # ---- ledger summary over test trials (matched mu)
    ledgers = [t["ledger"] for t in trials]
    ledger_summary = {
        "mean": {k: float(np.mean([l[k] for l in ledgers])) for k in ledgers[0]},
        "max_closure_error_frac": float(np.max([l["closure_error_frac"] for l in ledgers])),
        "closure_tolerance_prestated": 1e-9,
        "split_note": ("TRANSMITTED (S21) = unsampled through-flow power in the "
                       "component of the settled field parallel to the input "
                       "wavefront; REFLECTED (S11) = the orthogonal (scattered) "
                       "component of the unsampled through-flow. Modal proxy "
                       "for port powers, stated as such."),
    }

    # ---- SCALE: amplitude sweep (STEP-DOWN fractions vs THROUGH-FLOW size)
    sweep = {}
    for amp in (0.1, 1.0, 10.0):
        fr = {"tapped_ratio": [], "residual_ratio": [], "bleed_ratio": [],
              "transmitted_ratio": [], "reflected_ratio": []}
        srng = np.random.default_rng(SEED + int(1000 * amp) + 7)
        for s in topo.STATE_ORDER:
            for rep in range(2):
                spec_s, _jv = make_spec(s, srng)
                a_st, _d = evolve_window(amp * spec_s, bank_vecs, sim.T_SETTLE)
                led_s = ledger_for(a_st, spec_s, nd_vs_agg(a_st, agg["SETTLED"]))
                for key in fr:
                    fr[key].append(led_s[key])
        sweep[str(amp)] = {k: float(np.mean(v)) for k, v in fr.items()}
    spreads = {k: float(max(sweep[a][k] for a in sweep) - min(sweep[a][k] for a in sweep))
               for k in ("tapped_ratio", "residual_ratio", "transmitted_ratio", "reflected_ratio")}
    scale_block = {"amplitudes": sweep, "spreads": spreads,
                   "tolerance_prestated": 0.02,
                   "stable_tapped_residual": bool(spreads["tapped_ratio"] <= 0.02
                                                  and spreads["residual_ratio"] <= 0.02),
                   "bleed_note": ("bleed ratio at matched mu = RHO*(1-A(0.5)) = 0 by "
                                  "construction at every amplitude (definitional, "
                                  "not a stability finding); at mu_bad it is "
                                  "RHO*(1-A(0.05)) = 0.081 by definition.")}

    # ---- model jobs: verdict (wrapper-LUT) / label / raw, same trials
    jobs, job_meta = [], []
    for t in trials:
        s = t["true_state"]
        pred = t["node_pred"][best_window]
        sc = t["node_scores"][best_window][pred]
        verdict = (f"Cavity verdict: {STATE_LABEL_WORDS[pred]}. "
                   f"Strongest node: {t['top_section_settled']} "
                   f"({t['top_tag_settled']}), match {sc:.2f}." + TAIL)
        label = (f"A monitoring cavity classified the computer's body state as: "
                 f"{STATE_LABEL_WORDS[t['whole_cavity_pred']]}." + TAIL)
        v = t["jittered_values"]
        raw = (f"Computer telemetry: maximum temperature {v['temp_max']:.1f} C, "
               f"memory temperature {v['temp_mem']:.1f} C, network receive drops "
               f"{int(round(v['rx_drop']))} per interval, receive errors "
               f"{int(round(v['rx_errs']))}, transduction flow index {v['tp_flow']:.4f}, "
               f"data rate {int(round(v['data_bps']))} bits per second, VRAM use "
               f"{v['vram']:.3f}, load average {v['loadavg']:.2f}." + TAIL)
        for cond, prompt in (("verdict", verdict), ("label", label), ("raw", raw)):
            jobs.append({"id": f"{t['trial_id']}_{cond}", "prompt": prompt})
        job_meta.append({"trial_id": t["trial_id"], "true_state": s,
                         "node_pred_best_window": pred})
    with open(f"{HD}/transducer_v2_model_jobs.json", "w") as f:
        json.dump(jobs, f, indent=1)

    results = {
        "header": {
            "experiment": "transducer sim v2 — aggregate-referenced node stores, cascade-timed taps, S11/S21 ledger, radiative exit decode",
            "directive": "Zak 2026-10-21 12:19 EDT (run the v2 spec)",
            "spec": "transducer_v2_spec.md; pre-registration in ITERATION_LOG.md (tolerances stated before the run)",
            "baseline_source": "FRESH real dweller tick 2026-10-21 ~12:21 EDT (transducer_v2_baseline.json); preflight clean (no [T]S4/[P]roton hits, :8080 ok)",
            "baseline": FRESH,
            "parameters": {"rho_tap": RHO_TAP, "mu_matched": MU, "mu_bad": MU_BAD,
                           "node_noise_power_per_mode": NODE_NOISE_P,
                           "seed": SEED, "trials_per_state": TRIALS_PER_STATE,
                           "modal_noise_db": 12.0, "jitter_frac": 0.05,
                           "windows": {w: t for w, t in WINDOWS.items()}},
            "lexicon": ["THROUGH-FLOW", "TAP", "NODE RING-DOWN", "STEP-DOWN", "RADIATIVE EXIT"],
        },
        "node_classification": {
            "composed_accuracy_by_window": node_acc,
            "best_window": best_window,
            "section_x_window_vote_accuracy": vote_matrix,
            "whole_cavity_accuracy_same_run": whole_acc,
            "gate_best_window_ge_whole_cavity": bool(node_acc[best_window] >= whole_acc),
        },
        "ledger_matched_mu": ledger_summary,
        "radiative_exit": exit_decode,
        "scale_amplitude_sweep": scale_block,
        "trials": [{k: v for k, v in t.items() if not k.startswith("_")
                    and k != "exit_I"} for t in trials],
        "job_meta": job_meta,
    }
    with open(f"{HD}/transducer_v2_results.json", "w") as f:
        json.dump(results, f, indent=1, default=float)
    print(f"NODE composed acc: {node_acc} (best {best_window}) vs whole-cavity {whole_acc:.3f} "
          f"gate: {results['node_classification']['gate_best_window_ge_whole_cavity']}")
    print(f"section x window votes: {vote_matrix}")
    print(f"LEDGER max closure err {ledger_summary['max_closure_error_frac']:.2e}; "
          f"mean tapped ratio {ledger_summary['mean']['tapped_ratio']:.4f}, "
          f"residual {ledger_summary['mean']['residual_ratio']:.4f}, "
          f"T {ledger_summary['mean']['transmitted_ratio']:.4f}, R {ledger_summary['mean']['reflected_ratio']:.4f}")
    print(f"RADIATIVE EXIT acc {exit_acc:.3f} vs internal {whole_acc:.3f} -> "
          f"hypothesis supported: {exit_decode['radiative_hypothesis_supported']}")
    print(f"  usable decode MAE {exit_decode['usable_power_decode']['mean_abs_err']:.4f} "
          f"({exit_decode['usable_power_decode']['mean_abs_err_frac_of_p_in']:.3f} of P_in); "
          f"remaining MAE {exit_decode['remaining_power_decode']['mean_abs_err']:.4f} "
          f"({exit_decode['remaining_power_decode']['mean_abs_err_frac_of_p_in']:.3f} of P_in)")
    print(f"SCALE spreads: {spreads}; stable(tapped+residual): {scale_block['stable_tapped_residual']}")
    print(f"wrote transducer_v2_results.json + {len(jobs)} model jobs")


# ------------------------------------------------------------------ score --
def score():
    answers = json.load(open(f"{HD}/transducer_v2_model_answers.json"))
    results = json.load(open(f"{HD}/transducer_v2_results.json"))
    conds = ("verdict", "label", "raw")
    agg = {c: {"hit": [], "near": [], "tok_t": [], "empty": []} for c in conds}
    rows = []
    for tr in results["trials"]:
        s = tr["true_state"]
        for c in conds:
            rec = answers.get(f"{tr['trial_id']}_{c}", {})
            ans = rec.get("content", "")
            hit = kw_hit(ans, STATE_KEYWORDS[s]) if ans else False
            near = (not hit) and (kw_hit(ans, NEAR_MISS[s]) if ans else False)
            rows.append({"trial": tr["trial_id"], "true_state": s, "condition": c,
                         "answer": ans, "names_true_state": bool(hit),
                         "near_miss": bool(near),
                         "tokens_prompt": rec.get("tokens_prompt"),
                         "tokens_completion": rec.get("tokens_completion"),
                         "tokens_total": rec.get("tokens_total")})
            agg[c]["hit"].append(1 if hit else 0)
            agg[c]["near"].append(1 if near else 0)
            agg[c]["empty"].append(1 if not ans or ans.startswith("__ERROR__") else 0)
            if rec.get("tokens_total") is not None:
                agg[c]["tok_t"].append(rec["tokens_total"])
    summary = {}
    for c in conds:
        summary[c] = {"accuracy": float(np.mean(agg[c]["hit"])),
                      "near_miss_rate": float(np.mean(agg[c]["near"])),
                      "empty_rate": float(np.mean(agg[c]["empty"])),
                      "mean_tokens_total": float(np.mean(agg[c]["tok_t"])) if agg[c]["tok_t"] else None,
                      "n": len(agg[c]["hit"])}
    mg = {"conditions": summary,
          "gate_acc_verdict_ge_label": bool(summary["verdict"]["accuracy"] >= summary["label"]["accuracy"]),
          "gate_tokens_verdict_le_60": bool(summary["verdict"]["mean_tokens_total"] is not None
                                            and summary["verdict"]["mean_tokens_total"] <= 60),
          "rows": rows}
    mg["gate_pass"] = bool(mg["gate_acc_verdict_ge_label"] and mg["gate_tokens_verdict_le_60"])
    results["model_gate"] = mg
    nc = results["node_classification"]
    results["gates"] = {
        "node_best_window_ge_whole_cavity": nc["gate_best_window_ge_whole_cavity"],
        "ledger_closes_S_split": bool(results["ledger_matched_mu"]["max_closure_error_frac"] <= 1e-9),
        "radiative_hypothesis_supported": results["radiative_exit"]["radiative_hypothesis_supported"],
        "scale_stable_tapped_residual": results["scale_amplitude_sweep"]["stable_tapped_residual"],
        "model_gate": mg["gate_pass"],
    }
    with open(f"{HD}/transducer_v2_results.json", "w") as f:
        json.dump(results, f, indent=1, default=float)
    for c in conds:
        print(f"MODEL {c}: acc {summary[c]['accuracy']:.3f} tokens {summary[c]['mean_tokens_total']} "
              f"empty {summary[c]['empty_rate']:.3f}")
    print(f"GATES: {results['gates']}")

    # ---- bookkeeping (once)
    import datetime
    state = json.load(open(f"{HD}/cavity_iter_state.json"))
    if any(e.get("id") == "transducer_v2" for e in state["experiments_done"]):
        print("bookkeeping already present — skipped")
        return
    ts = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M-04:00")
    rx = results["radiative_exit"]
    sc = results["scale_amplitude_sweep"]
    entry = {
        "id": "transducer_v2", "ts": ts,
        "directive": "Zak 2026-10-21 12:19 EDT (run transducer_v2_spec.md)",
        "node_classification": {"composed_accuracy_by_window": nc["composed_accuracy_by_window"],
                                "best_window": nc["best_window"],
                                "whole_cavity_same_run": nc["whole_cavity_accuracy_same_run"],
                                "gate_pass": nc["gate_best_window_ge_whole_cavity"],
                                "section_x_window_vote_accuracy": nc["section_x_window_vote_accuracy"]},
        "ledger_matched_mu": {"tapped_ratio": results["ledger_matched_mu"]["mean"]["tapped_ratio"],
                              "residual_ratio": results["ledger_matched_mu"]["mean"]["residual_ratio"],
                              "transmitted_ratio_S21": results["ledger_matched_mu"]["mean"]["transmitted_ratio"],
                              "reflected_ratio_S11": results["ledger_matched_mu"]["mean"]["reflected_ratio"],
                              "bleed_ratio": results["ledger_matched_mu"]["mean"]["bleed_ratio"],
                              "max_closure_error_frac": results["ledger_matched_mu"]["max_closure_error_frac"]},
        "radiative_exit": {"exit_only_accuracy": rx["exit_only_classification_accuracy"],
                           "internal_accuracy": rx["internal_whole_cavity_accuracy_same_trials"],
                           "hypothesis_supported": rx["radiative_hypothesis_supported"],
                           "usable_decode_mae_frac_p_in": rx["usable_power_decode"]["mean_abs_err_frac_of_p_in"],
                           "remaining_decode_mae_frac_p_in": rx["remaining_power_decode"]["mean_abs_err_frac_of_p_in"]},
        "scale_amplitude_sweep": {"spreads": sc["spreads"],
                                  "stable_tapped_residual": sc["stable_tapped_residual"]},
        "model_gate": {"accuracy": {c: summary[c]["accuracy"] for c in conds},
                       "mean_tokens_total": {c: summary[c]["mean_tokens_total"] for c in conds},
                       "gate_pass": mg["gate_pass"]},
        "gates": results["gates"],
        "results_file": "transducer_v2_results.json",
        "code": ["transducer_v2_sim.py"],
    }
    state["experiments_done"].append(entry)
    state["queue"] = [q for q in state["queue"] if not q.startswith("TRANSDUCER V2")]
    state["last_updated"] = ts
    json.dump(state, open(f"{HD}/cavity_iter_state.json", "w"), indent=1)
    with open(f"{HD}/ITERATION_LOG.md", "a") as f:
        f.write(f"\n\n## {ts} — transducer_v2 (Zak 12:19 go)\n\n")
        f.write("Stages: THROUGH-FLOW -> TAP -> NODE RING-DOWN -> STEP-DOWN -> RADIATIVE EXIT. "
                "Nodes aggregate-referenced (LUT delta stores per section, parallel component kept); "
                "taps at DRIVE_END (0.30 s) and SETTLED (0.50 s); ledger with S11/S21 split; "
                "exit decode from the radiative intensity spectrum alone. Baseline: FRESH tick "
                "~12:21 EDT (transducer_v2_baseline.json), preflight clean.\n\n")
        f.write(f"NODE RING-DOWN: composed accuracy by window "
                f"{ {w: round(a, 3) for w, a in nc['composed_accuracy_by_window'].items()} } "
                f"(best {nc['best_window']}) vs whole-cavity same-run "
                f"{nc['whole_cavity_accuracy_same_run']:.3f} — gate "
                f"{'PASS' if nc['gate_best_window_ge_whole_cavity'] else 'FAIL'}. "
                f"Section x window vote accuracy: {nc['section_x_window_vote_accuracy']}.\n\n")
        lm = results["ledger_matched_mu"]["mean"]
        f.write(f"LEDGER (matched mu, S-split; arbitrary units, NOT joules): in 1.000 = "
                f"tapped {lm['tapped_ratio']:.4f} + transmitted(S21) {lm['transmitted_ratio']:.4f} + "
                f"reflected(S11) {lm['reflected_ratio']:.4f} + residual_second_cavity "
                f"{lm['residual_ratio']:.4f} + bleed {lm['bleed_ratio']:.4f}; max closure error "
                f"{results['ledger_matched_mu']['max_closure_error_frac']:.2e} (tolerance 1e-9).\n\n")
        f.write(f"RADIATIVE EXIT: exit-only classification {rx['exit_only_classification_accuracy']:.3f} "
                f"vs internal {rx['internal_whole_cavity_accuracy_same_trials']:.3f} — radiative "
                f"hypothesis {'SUPPORTED' if rx['radiative_hypothesis_supported'] else 'NOT SUPPORTED'} "
                f"(criterion: >= 0.75 and >= internal - 0.10). Power decode from exit alone: usable "
                f"MAE {rx['usable_power_decode']['mean_abs_err_frac_of_p_in']:.3f} of P_in, remaining "
                f"MAE {rx['remaining_power_decode']['mean_abs_err_frac_of_p_in']:.3f} of P_in.\n\n")
        f.write(f"STEP-DOWN / SCALE: fraction spreads over 0.1x/1x/10x THROUGH-FLOW "
                f"{ {k: round(v, 4) for k, v in sc['spreads'].items()} } (tolerance 0.02) — "
                f"tapped+residual {'STABLE' if sc['stable_tapped_residual'] else 'NOT STABLE'}.\n\n")
        f.write(f"MODEL GATE: verdict acc {summary['verdict']['accuracy']:.3f} / "
                f"{summary['verdict']['mean_tokens_total']} tok; label {summary['label']['accuracy']:.3f} / "
                f"{summary['label']['mean_tokens_total']} tok; raw {summary['raw']['accuracy']:.3f} / "
                f"{summary['raw']['mean_tokens_total']} tok — gate "
                f"{'PASS' if mg['gate_pass'] else 'FAIL'} (acc >= label AND verdict tokens <= 60).\n")
    print("bookkeeping appended (log + state); TRANSDUCER V2 queue item pruned")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "score":
        score()
    else:
        prep()
