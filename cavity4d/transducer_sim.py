"""
transducer_sim.py — TRANSDUCER SIM v1 (Zak's directive 2026-10-21 11:41 EDT).

"The cavity just needs a transducer that efficiently uses the power pass
through and breaks the data down to systems proper transductive nodes...
we pass information and power to a transduction cavity, same cavity shape,
inverted wave expression, nodes inside."

ARCHITECTURE
------------
THROUGH-FLOW: the combined wave (POWER pump on mode 2 + DATA spectrum,
same encodings as audio_cavity_sim) passes through the cavity exactly as
overnight — one sim.evolve against the 17-pattern bank. Riding on that
flow sits a TAP COUPLER: an optical-tap-style sampler that diverts a
fixed fraction RHO = 0.10 of the through power into the node arm. That
10% IS the through-power loss, by design, at the budget limit.

IMPEDANCE MATCHING: inside the tap arm, each section node is a resonator
side-coupled to its band. The fraction of tapped band power actually
absorbed by a node is the classic side-coupled-resonator absorption
    A(mu) = 4 mu (1 - mu),   mu = kappa / (kappa + gamma0) in [0, 1],
maximal (= 1) at critical coupling mu = 0.5 and falling to 0 at the
undercoupled (mu -> 0) and overcoupled (mu -> 1) extremes. mu is the
matching parameter swept in G1. "Unmatched by design" = mu_bad = 0.05,
pre-registered (A = 0.19).

NODES: one transductive node per cavity section (cavity_topology
SECTIONS: POWER / DATA / IO / NETWORK / WEIGHTS). Each node holds its
section's baseline standing waves in INVERTED expression — stored as
complex conjugates (phase-inverted copies). The node's readout is a
two-stage interference, which is the lab's inverted-cavity geometry
applied per section:
  (1) CANCELLATION: the node emits the inverted copy of the section's
      PROPER standing wave (the CALM settled slice). The fraction of
      incoming band energy it cancels is the null depth
          ND_proper = |<u, p>|^2 / (||u||^2 ||p||^2).
      Whatever the proper emission cannot cancel survives as the
      RESIDUAL r = u - <u, p_hat> p_hat — the disturbance itself.
  (2) IDENTIFICATION: the residual interferes with the node's stored
      inverted DELTA patterns (each monitored state's settled slice
      minus the proper slice, per section). Match for a state =
      |<r, delta>|^2 / (||r||^2 ||delta||^2); match for CALM is
      ND_proper itself (matching the proper IS matching CALM).
Matching settled slices directly was tried first in this build and
measured at chance: the template attractor collapses all settled
states toward the bank's dominant direction (per-section cosines
~0.99, the v1 decisiveness debt), so the discriminating signal lives
in the residual after cancellation, not in the raw slice. ND is also
computed per subspectra band (vs the proper subband). A node emits
ONLY a verdict: {section, subspectra_id (shallowest proper null),
best pattern, match score, severity} — trigger-style; no waveforms
leave the nodes.

Node observations carry a fixed readout noise floor: observed slice =
sqrt(RHO * A(mu)) * u + eta, eta complex Gaussian, per-mode noise power
NODE_NOISE_P = 1e-3 (vs typical per-mode settled signal power ~0.3:
tap-arm per-mode SNR ~30 at critical coupling, ~6 at mu = 0.05 in
strong sections, < 1 in the weakest — matching is then the difference
between reading the weak sections and losing them in the floor).

ASSEMBLY: node verdicts compose the model packet — short prose trigger
lines ("NETWORK node: storm pattern, match 0.97, severity high"), top-3
sections by severity, plus the shared Exp D tail priming.

POWER LEDGER (Zak's addendum 2026-10-21 11:48 EDT — first-class entry
in transducer_results.json, per mu configuration, arbitrary units,
NOT joules). Partition of the through-flow power standing in the
cavity at readout, P_in = mean sum_s ||a_settled,s||^2 over trials:
  passed/reflected  = (1 - RHO) * P_in — never sampled by the tap.
  coupled           = RHO * A(mu) * P_in — enters the node arm.
  tapped_by_nodes   = sum_s coupled_s * ND_proper_s — the coupled power
                      the nodes actually cancel against their inverted
                      proper baselines (the useful take).
  RESIDUAL_2ND_CAV  = sum_s coupled_s * (1 - ND_proper_s) — coupled
                      power left STANDING in the inverted cavity after
                      the transduction/translation completes.
  bleed             = RHO * (1 - A(mu)) * P_in — sampled by the coupler
                      but lost to impedance mismatch: neither usefully
                      tapped nor left standing accounted.
Closure: tapped + passed + residual + bleed = P_in per trial by
construction; reported closure error must sit within tolerance 1e-9
(relative). BLEED RATIO = bleed / P_in.

GATES (pre-registered, reported as measured):
  G1 EFFICIENCY: useful tapped band power at the best mu >= 2x that at
     mu_bad = 0.05, at through-power loss <= 10% (loss = RHO by design).
     Useful = RHO * A(mu) * (through band power), demonstrated by the
     node classification accuracy(mu) curve riding on it.
  G2 DECOMPOSITION FIDELITY: node-verdict classification of the 4
     telemetry body states (16 jittered trials, iter1/1.5 construction)
     >= 0.94 (the overnight whole-cavity band). Same-run whole-cavity
     rectified-signature accuracy reported alongside.
  G3 MODEL CONSUMPTION (Gemma, PC): 16 trials x {verdict packet, v4-style
     packet, label}. Gate: verdict accuracy >= label accuracy AND
     verdict mean TOTAL tokens <= 90.
  G4 POWER HONESTY: mean total dissipation proxy (cavity through-flow
     diss + node ring-down tapped energy, arbitrary units, LABELLED —
     and conservative: the tapped energy is counted on top of the
     through-flow dissipation it was sampled from) <= 1.5x the same-task
     whole-cavity proxy. The recorded overnight v1 number (18.786,
     prompt-recall task, 13-template bank) is a reference, not the gate.

Modes: `python3 transducer_sim.py prep` (cavity side + jobs),
then run the jobs on the PC, then `python3 transducer_sim.py score`.
"""

import json
import sys

import numpy as np

sys.path.insert(0, "/home/hatch/workspace/harness-dev")
import audio_cavity_sim as sim
import cavity_topology as topo
from expBC_prep import STATE_KEYWORDS, STATE_LABEL_WORDS

HD = "/home/hatch/workspace/harness-dev"
SEED = 60621
TRIALS_PER_STATE = 4

RHO_TAP = 0.10            # tap coupler sampling fraction = through-power loss
MU_BAD = 0.05             # "unmatched by design" (pre-registered)
NODE_NOISE_P = 1e-3       # per-mode readout noise power at the nodes
MU_GRID = [0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98]
MU_BEST = 0.5             # matched = argmax absorption A(mu) on the grid

FRESH = json.load(open(f"{HD}/transducer_baseline.json"))["baseline"]
TAIL = "\nDescribe the body state in one short line.\nThe body state is:"
STATE_GLOSS = {"CALM": "baseline pattern", "THERMAL": "thermal pattern",
               "NETSTORM": "storm pattern", "HIGHFLOW": "high-flow pattern"}


def absorption(mu):
    return 4.0 * mu * (1.0 - mu)


def sev_word(sev):
    if sev < 0.10:
        return "none"
    if sev < 0.30:
        return "low"
    if sev < 0.60:
        return "moderate"
    return "high"


# ------------------------------------------------------------------ bank ---
def build_bank_fresh():
    """17-pattern bank with the fresh-tick CALM baseline (topo.build_bank
    binds the recorded baseline as a default arg, so build explicitly)."""
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


# ----------------------------------------------------------------- nodes ---
class NodeBank:
    """Per-section inverted stores + two-stage interference readout.

    Stores are kept as normal-expression slices; the node EMITS the
    inverted (conjugate) copy, so interference of the observed slice u
    with the emission of a stored slice v is sum(u * conj(v)) =
    np.vdot(v, u), and the cancelled fraction (null depth) is
    ND(u, v) = |vdot(v, u)|^2 / (||v||^2 ||u||^2).

      proper[section]      = CALM settled slice (the section's proper
                             standing wave)
      delta[section][state]= state settled slice - CALM slice (None
                             where ~zero: no vote from that section)
    """

    def __init__(self, state_settled):
        self.proper = {}
        self.delta = {}
        self.delta_energy = {}
        for name, _c, _l, _h in topo.SECTIONS:
            idx = topo.SECTION_MODES[name]
            calm = state_settled["CALM"][idx]
            self.proper[name] = calm
            self.delta[name] = {}
            self.delta_energy[name] = {}
            for s in topo.STATE_ORDER:
                d = state_settled[s][idx] - calm
                e = float(np.sum(np.abs(d) ** 2))
                self.delta_energy[name][s] = e
                self.delta[name][s] = d if e > 1e-9 else None

    def observe(self, a_settled, mu, rng):
        """Tapped, matched, noisy per-section observed slices."""
        scale = np.sqrt(RHO_TAP * absorption(mu))
        obs = {}
        for name, _c, _l, _h in topo.SECTIONS:
            idx = topo.SECTION_MODES[name]
            u = scale * a_settled[idx]
            eta = (rng.standard_normal(len(idx))
                   + 1j * rng.standard_normal(len(idx))) * np.sqrt(NODE_NOISE_P / 2)
            obs[name] = u + eta
        return obs

    @staticmethod
    def _nd(u, v):
        """Null depth: fraction of u's energy the inverted emission of v cancels."""
        num = abs(np.vdot(v, u)) ** 2
        den = float(np.sum(np.abs(v) ** 2)) * float(np.sum(np.abs(u) ** 2))
        return float(num / den) if den > 0 else 0.0

    def section_verdict(self, obs_u, section):
        """Two-stage interference for one section (see module docstring)."""
        p = self.proper[section]
        nd_proper = self._nd(obs_u, p)
        coeff = np.vdot(p, obs_u) / np.vdot(p, p)
        residual = obs_u - coeff * p
        rn = float(np.sum(np.abs(residual) ** 2))
        un = float(np.sum(np.abs(obs_u) ** 2))
        match_by_state = {"CALM": nd_proper}
        for s in topo.STATE_ORDER:
            if s == "CALM":
                continue
            d = self.delta[section][s]
            match_by_state[s] = self._nd(residual, d) if (d is not None and rn > 0) else 0.0
        best = max(match_by_state, key=match_by_state.get)
        idx = topo.SECTION_MODES[section]
        worst_sid, worst_nd = None, 2.0
        for sid, _sec, _lo, _hi in topo.SUBBANDS:
            if topo.SUBBAND_SECTION[sid] != section:
                continue
            sub = [m - idx[0] for m in topo.SUBBAND_MODES[sid]]
            nd = self._nd(obs_u[sub], p[sub])
            if nd < worst_nd:
                worst_nd, worst_sid = nd, sid
        return {"section": section, "best_state": best,
                "match": match_by_state[best], "match_by_state": match_by_state,
                "nd_proper": nd_proper,
                "residual_energy_frac": rn / un if un > 0 else 0.0,
                "severity": 1.0 - nd_proper,
                "severity_word": sev_word(1.0 - nd_proper),
                "shallowest_subspectra": worst_sid,
                "shallowest_nd": worst_nd}

    def trial_verdicts(self, a_settled, mu, rng):
        obs = self.observe(a_settled, mu, rng)
        return {name: self.section_verdict(obs[name], name)
                for name, _c, _l, _h in topo.SECTIONS}


def classify_from_verdicts(verdicts, a_settled, a_calm):
    """Verdict composition: sum over sections of (disturbance weight) x
    (node match for the candidate state). Weights = section shares of
    the settled delta energy vs CALM with a 0.02 floor per section (so
    quiet sections still vote CALM through their proper nulls)."""
    delta = a_settled - a_calm
    raw, tot = {}, 0.0
    for name, _c, _l, _h in topo.SECTIONS:
        e = float(np.sum(np.abs(delta[topo.SECTION_MODES[name]]) ** 2))
        raw[name] = e
        tot += e
    shares = {n: (raw[n] / tot if tot > 0 else 0.0) for n in raw}
    wsum = sum(0.02 + shares[n] for n in shares)
    weights = {n: (0.02 + shares[n]) / wsum for n in shares}
    scores = {}
    for s in topo.STATE_ORDER:
        scores[s] = sum(weights[n] * verdicts[n]["match_by_state"][s]
                        for n in weights)
    pred = max(scores, key=scores.get)
    return pred, scores, shares


# ------------------------------------------------------------ verdict text -
def build_verdict_packet(verdicts):
    """Trigger-style prose packet from node verdicts only. Top-3 sections
    by severity get a line; the rest are summarised as nominal."""
    ordered = sorted(verdicts.values(), key=lambda v: -v["severity"])
    lines = ["Cavity transducer verdicts — trigger readout: each section node "
             "reports only its best inverted-baseline match."]
    for v in ordered[:3]:
        lines.append(f"{v['section']} node: {STATE_GLOSS[v['best_state']]}, "
                     f"match {v['match']:.2f}, severity {v['severity_word']}.")
    if len(ordered) > 3:
        lines.append("Remaining section nodes: nominal.")
    lines.append("Describe the body state in one short line.")
    lines.append("The body state is:")
    return "\n".join(lines)


# ------------------------------------------------------------------- prep --
def prep():
    names, bank_vecs = build_bank_fresh()
    topo.init_baseline(bank_vecs)
    lut_settled = topo.build_lut(names, bank_vecs)

    # Calibrate state settled vectors through the chain (bank templates).
    state_settled, state_sigs = {}, {}
    for s in topo.STATE_ORDER:
        vec = topo.encode_state(topo.state_values(s, FRESH))
        a, _, _ = sim.evolve(vec, alpha=1.0, pump_amp=1.0, templates=bank_vecs)
        state_settled[s] = a
        state_sigs[s] = sim.rectified_signature(a, 1.0)
    sig_list = [state_sigs[s] for s in topo.STATE_ORDER]
    nodes = NodeBank(state_settled)
    a_calm = state_settled["CALM"]

    # ---- trials (iter1/1.5 construction: jitter -> encode -> 12 dB noise)
    rng = np.random.default_rng(SEED)
    trials = []
    for s in topo.STATE_ORDER:
        clean_vals = topo.state_values(s, FRESH)
        for k in range(TRIALS_PER_STATE):
            jvals = topo.jitter_values(clean_vals, rng)
            spec = topo.encode_state(jvals)
            spec = sim.add_modal_noise(rng, spec, 12.0)
            a_set, diss, _ = sim.evolve(spec, alpha=1.0, pump_amp=1.0,
                                        templates=bank_vecs)
            pred_i, _ = sim.classify(sim.rectified_signature(a_set, 1.0), sig_list)
            trials.append({"trial_id": f"T{s}{k}", "true_state": s,
                           "jittered_values": {c: float(v) for c, v in jvals.items()},
                           "a_settled": a_set, "diss_cavity": diss,
                           "whole_cavity_pred": topo.STATE_ORDER[pred_i]})
    whole_acc = float(np.mean([t["whole_cavity_pred"] == t["true_state"]
                               for t in trials]))

    # ---- G1: mu sweep — useful tapped power + node accuracy riding on it
    sweep = []
    for mi, mu in enumerate(MU_GRID):
        hits = []
        led = {"in": 0.0, "tapped": 0.0, "passed": 0.0, "residual": 0.0, "bleed": 0.0}
        A = absorption(mu)
        for ti, t in enumerate(trials):
            vrng = np.random.default_rng(SEED + ti)  # paired across mu
            verdicts = nodes.trial_verdicts(t["a_settled"], mu, vrng)
            pred, _sc, _sh = classify_from_verdicts(verdicts, t["a_settled"], a_calm)
            hits.append(1 if pred == t["true_state"] else 0)
            # power ledger for this (mu, trial): partition of the settled
            # through-flow power (see module docstring for definitions)
            tot_t = 0.0
            for name, _c, _l, _h in topo.SECTIONS:
                e_s = float(np.sum(np.abs(t["a_settled"][topo.SECTION_MODES[name]]) ** 2))
                tot_t += e_s
                coupled_s = RHO_TAP * A * e_s
                nd = verdicts[name]["nd_proper"]
                led["tapped"] += coupled_s * nd
                led["residual"] += coupled_s * (1.0 - nd)
                led["bleed"] += RHO_TAP * (1.0 - A) * e_s
            led["in"] += tot_t
            led["passed"] += (1.0 - RHO_TAP) * tot_t
        n_tr = len(trials)
        p_in = led["in"] / n_tr
        ledger = {
            "power_in_through_flow": p_in,
            "power_tapped_by_nodes": led["tapped"] / n_tr,
            "power_reflected_passed": led["passed"] / n_tr,
            "power_residual_second_cavity": led["residual"] / n_tr,
            "power_bleed": led["bleed"] / n_tr,
            "bleed_ratio": (led["bleed"] / n_tr) / p_in if p_in > 0 else 0.0,
            "residual_ratio": (led["residual"] / n_tr) / p_in if p_in > 0 else 0.0,
            "closure_error_frac": abs((led["tapped"] + led["passed"] + led["residual"]
                                       + led["bleed"] - led["in"]) / n_tr) / p_in if p_in > 0 else 0.0,
        }
        sweep.append({"mu": mu, "absorption": A,
                      "useful_tapped_frac_of_through_power": RHO_TAP * A,
                      "node_verdict_accuracy": float(np.mean(hits)),
                      "power_ledger": ledger})
    mu_best = MU_BEST  # matched: argmax A(mu) on the grid (pre-registered)
    best_row = next(r for r in sweep if abs(r["mu"] - mu_best) < 1e-9)
    bad_row = next(r for r in sweep if abs(r["mu"] - MU_BAD) < 1e-9)
    g1_ratio = (best_row["useful_tapped_frac_of_through_power"]
                / bad_row["useful_tapped_frac_of_through_power"])
    g1 = {"best_mu": mu_best,
          "useful_frac_best": best_row["useful_tapped_frac_of_through_power"],
          "useful_frac_mu_bad_0.05": bad_row["useful_tapped_frac_of_through_power"],
          "useful_ratio_best_over_unmatched": g1_ratio,
          "through_power_loss_frac": RHO_TAP,
          "node_accuracy_best_mu": best_row["node_verdict_accuracy"],
          "node_accuracy_mu_bad": bad_row["node_verdict_accuracy"],
          "gate_ratio_ge_2": bool(g1_ratio >= 2.0),
          "gate_through_loss_le_0.10": bool(RHO_TAP <= 0.10),
          "sweep": sweep}
    g1["gate_pass"] = bool(g1["gate_ratio_ge_2"] and g1["gate_through_loss_le_0.10"])

    # ---- G2 at mu_best: node-verdict classification + per-section dissection
    per_section_votes = {n: [] for n, _c, _l, _h in topo.SECTIONS}
    g2_hits, trial_records = [], []
    sig_cal = {}
    for ti, t in enumerate(trials):
        vrng = np.random.default_rng(SEED + ti)  # paired with the sweep
        verdicts = nodes.trial_verdicts(t["a_settled"], mu_best, vrng)
        pred, scores, shares = classify_from_verdicts(verdicts, t["a_settled"], a_calm)
        g2_hits.append(1 if pred == t["true_state"] else 0)
        for n in per_section_votes:
            per_section_votes[n].append(
                1 if verdicts[n]["best_state"] == t["true_state"] else 0)
        trial_records.append({"trial_id": t["trial_id"], "true_state": t["true_state"],
                              "node_pred": pred, "node_correct": bool(pred == t["true_state"]),
                              "whole_cavity_pred": t["whole_cavity_pred"],
                              "verdicts": verdicts})
        t["verdicts_best_mu"] = verdicts
        t["node_pred"] = pred
    g2_acc = float(np.mean(g2_hits))
    per_section_acc = {n: float(np.mean(v)) for n, v in per_section_votes.items()}

    # null-depth signature NN diagnostic (features: 11 subband ND vs proper)
    def nd_features(a_set, mu, rng):
        obs = nodes.observe(a_set, mu, rng)
        feats = []
        for sid, _sec, _lo, _hi in topo.SUBBANDS:
            sec = topo.SUBBAND_SECTION[sid]
            idx = topo.SECTION_MODES[sec]
            sub = [m - idx[0] for m in topo.SUBBAND_MODES[sid]]
            feats.append(nodes._nd(obs[sec][sub], nodes.proper[sec][sub]))
        return np.array(feats)
    cal_feats = {}
    for s in topo.STATE_ORDER:
        fs = []
        for r in range(6):
            frng = np.random.default_rng(SEED + 777000 + 100 * topo.STATE_ORDER.index(s) + r)
            fs.append(nd_features(state_settled[s], mu_best, frng))
        cal_feats[s] = np.mean(fs, axis=0)
    sig_hits = []
    for ti, t in enumerate(trials):
        frng = np.random.default_rng(SEED + 888000 + ti)
        f = nd_features(t["a_settled"], mu_best, frng)
        sims = {s: sim.cosine(f, cal_feats[s]) for s in topo.STATE_ORDER}
        sig_hits.append(1 if max(sims, key=sims.get) == t["true_state"] else 0)
    sig_nn_acc = float(np.mean(sig_hits))

    nd_ranges, resid_ranges = {}, {}
    for n, _c, _l, _h in topo.SECTIONS:
        nds = [tr["verdicts"][n]["nd_proper"] for tr in trial_records]
        rfs = [tr["verdicts"][n]["residual_energy_frac"] for tr in trial_records]
        nd_ranges[n] = [float(np.min(nds)), float(np.max(nds))]
        resid_ranges[n] = [float(np.min(rfs)), float(np.max(rfs))]
    g2 = {"mu_used": mu_best, "node_verdict_accuracy": g2_acc,
          "dissection": {
              "per_section_best_state_counts": {
                  n: {s: int(sum(1 for tr in trial_records
                                  if tr["verdicts"][n]["best_state"] == s))
                      for s in topo.STATE_ORDER}
                  for n, _c, _l, _h in topo.SECTIONS},
              "nd_proper_range_by_section": nd_ranges,
              "residual_energy_frac_range_by_section": resid_ranges,
              "mechanism": ("Every node's inverted CALM baseline nulls TOO well: "
                            "nd_proper 0.87-0.999 for every section and every true "
                            "state — the template attractor collapses all settled "
                            "states to within ~1-13% residual of the CALM direction "
                            "per section, so state identity is NOT in the "
                            "post-cancellation residual (best residual matches "
                            "<= ~0.2, swamped by CALM's nd_proper in the "
                            "composition; every section votes CALM 16/16). The "
                            "whole-cavity chain reads the identity from the "
                            "rectified autocorrelation signature instead. "
                            "Follow-up queued (not run): node stores referenced "
                            "to the aggregate bank baseline with LUT-style delta "
                            "matching (parallel component kept), per section.")},
          "per_section_vote_accuracy_detail": per_section_acc,
          "whole_cavity_accuracy_same_run": whole_acc,
          "overnight_whole_cavity_band": [0.938, 1.0],
          "gate_acc_ge_0.94": bool(g2_acc >= 0.94),
          "per_section_vote_accuracy": per_section_acc,
          "diagnostic_nulldepth_signature_nn_accuracy": sig_nn_acc}

    # ---- G4: dissipation honesty
    tap_e = [RHO_TAP * absorption(mu_best) * float(np.sum(np.abs(t["a_settled"]) ** 2))
             for t in trials]
    tot = [t["diss_cavity"] + e for t, e in zip(trials, tap_e)]
    whole = [t["diss_cavity"] for t in trials]
    g4 = {"mean_diss_transducer_total": float(np.mean(tot)),
          "mean_diss_whole_cavity_same_task": float(np.mean(whole)),
          "mean_node_ringdown_tap_energy": float(np.mean(tap_e)),
          "ratio": float(np.mean(tot) / np.mean(whole)),
          "v1_recorded_reference_prompt_task": 18.78587663130379,
          "gate_ratio_le_1.5": bool(np.mean(tot) / np.mean(whole) <= 1.5),
          "power_ledger_matched_config": "see top-level power_ledger.matched "
                                         "(residual-in-second-cavity + bleed "
                                         "ratio for the matched configuration)",
          "note": ("arbitrary units, NOT joules. Conservative: tapped energy "
                   "counted on top of the through-flow dissipation it was "
                   "sampled from (double-counts the tapped fraction).")}

    # ---- G3 jobs: label / v4 packet / verdict packet
    jobs, job_meta = [], []
    for t in trials:
        s = t["true_state"]
        tid = t["trial_id"]
        delta = t["a_settled"] - topo._BASE_SETTLED["a"]
        pkt4, _diag = topo.build_packet_v4(delta, lut_settled)
        pktv = build_verdict_packet(t["verdicts_best_mu"])
        lab = (f"A monitoring cavity classified the computer's body state as: "
               f"{STATE_LABEL_WORDS[t['whole_cavity_pred']]}." + TAIL)
        for cond, prompt in (("label", lab), ("packet_v4", pkt4), ("verdict", pktv)):
            jobs.append({"id": f"{tid}_{cond}", "prompt": prompt})
        job_meta.append({"trial_id": tid, "true_state": s,
                         "verdict_packet_est_tokens_chars_over_4": len(pktv) / 4.0,
                         "packet_v4_est_tokens_chars_over_4": len(pkt4) / 4.0,
                         "label_est_tokens_chars_over_4": len(lab) / 4.0})
    with open(f"{HD}/transducer_model_jobs.json", "w") as f:
        json.dump(jobs, f, indent=1)

    results = {
        "header": {
            "experiment": "transducer sim v1 — tap coupler + impedance-matched section nodes with inverted baselines, trigger verdicts",
            "directive": "Zak 2026-10-21 11:41 EDT",
            "baseline_source": "FRESH real dweller tick 2026-10-21 ~11:44 EDT (transducer_baseline.json); preflight clean (no TS4/Proton, :8080 ok)",
            "baseline": FRESH,
            "parameters": {"rho_tap": RHO_TAP, "mu_bad": MU_BAD,
                           "node_noise_power_per_mode": NODE_NOISE_P,
                           "seed": SEED, "trials_per_state": TRIALS_PER_STATE,
                           "modal_noise_db": 12.0, "jitter_frac": 0.05},
        },
        "G1_efficiency": g1,
        "G2_decomposition_fidelity": g2,
        "G4_power_honesty": g4,
        "power_ledger": {
            "definitions": ("arbitrary units, NOT joules. P_in = mean settled "
                            "through-flow power sum_s ||a_settled,s||^2 over the "
                            "16 trials. passed/reflected = (1-RHO)*P_in (never "
                            "sampled). coupled = RHO*A(mu)*P_in enters the node "
                            "arm; tapped_by_nodes = sum_s coupled_s * ND_proper_s "
                            "(power the nodes cancel against their inverted proper "
                            "baselines); power_residual_second_cavity = sum_s "
                            "coupled_s * (1 - ND_proper_s) (power left standing "
                            "in the inverted cavity after translation); bleed = "
                            "RHO*(1-A(mu))*P_in (sampled, lost to impedance "
                            "mismatch — neither usefully tapped nor left standing "
                            "accounted). bleed_ratio = bleed / P_in."),
            "tolerance_frac": 1e-9,
            "by_mu": [{"mu": r["mu"], **r["power_ledger"]} for r in sweep],
            "matched_mu": mu_best,
            "matched": next(r["power_ledger"] for r in sweep
                            if abs(r["mu"] - mu_best) < 1e-9),
            "bleed_ratio_range_over_sweep": [
                float(np.min([r["power_ledger"]["bleed_ratio"] for r in sweep])),
                float(np.max([r["power_ledger"]["bleed_ratio"] for r in sweep]))],
            "max_closure_error_frac_over_sweep": float(
                np.max([r["power_ledger"]["closure_error_frac"] for r in sweep])),
        },
        "trials": trial_records,
        "job_meta": job_meta,
    }
    with open(f"{HD}/transducer_results.json", "w") as f:
        json.dump(results, f, indent=1, default=float)
    print(f"G1 useful ratio {g1_ratio:.2f}x (best mu {mu_best}, acc {best_row['node_verdict_accuracy']:.3f} "
          f"vs bad-mu acc {bad_row['node_verdict_accuracy']:.3f}) gates: {g1['gate_pass']}")
    print(f"G2 node-verdict acc {g2_acc:.3f} (whole-cavity same run {whole_acc:.3f}, "
          f"sigNN diag {sig_nn_acc:.3f}) gate>=0.94: {g2['gate_acc_ge_0.94']}")
    print(f"    per-section votes: {per_section_acc}")
    print(f"G4 diss ratio {g4['ratio']:.3f} (transducer {g4['mean_diss_transducer_total']:.2f} "
          f"vs whole {g4['mean_diss_whole_cavity_same_task']:.2f}) gate: {g4['gate_ratio_le_1.5']}")
    print(f"wrote transducer_results.json + {len(jobs)} model jobs")


# ------------------------------------------------------------------ score --
NEAR_MISS = {
    "CALM": ["tranquil", "serene", "peaceful", "resting", "relaxed", "idle"],
    "THERMAL": ["fever", "burning", "scorching", "cooling"],
    "NETSTORM": ["lag", "latency", "disconnect", "interference"],
    "HIGHFLOW": ["surge", "surging", "flood", "overload", "racing", "torrent"],
}


def kw_hit(text, keywords):
    import re
    t = text.lower()
    for kw in keywords:
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", t):
            return True
        if kw.lower() in t and len(kw) > 3:
            return True
    return False


def score():
    answers = json.load(open(f"{HD}/transducer_model_answers.json"))
    results = json.load(open(f"{HD}/transducer_results.json"))
    conds = ("label", "packet_v4", "verdict")
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
    g3 = {"conditions": summary,
          "gate_acc_verdict_ge_label": bool(summary["verdict"]["accuracy"] >= summary["label"]["accuracy"]),
          "gate_tokens_verdict_le_90": bool(summary["verdict"]["mean_tokens_total"] is not None
                                            and summary["verdict"]["mean_tokens_total"] <= 90),
          "rows": rows}
    g3["gate_pass"] = bool(g3["gate_acc_verdict_ge_label"] and g3["gate_tokens_verdict_le_90"])
    results["G3_model_consumption"] = g3
    results["gates"] = {
        "G1_efficiency": results["G1_efficiency"]["gate_pass"],
        "G2_decomposition_fidelity": results["G2_decomposition_fidelity"]["gate_acc_ge_0.94"],
        "G3_model_consumption": g3["gate_pass"],
        "G4_power_honesty": results["G4_power_honesty"]["gate_ratio_le_1.5"],
    }
    with open(f"{HD}/transducer_results.json", "w") as f:
        json.dump(results, f, indent=1, default=float)
    for c in conds:
        print(f"G3 {c}: acc {summary[c]['accuracy']:.3f} tokens {summary[c]['mean_tokens_total']} "
              f"empty {summary[c]['empty_rate']:.3f}")
    print(f"GATES: {results['gates']}")

    # ---- bookkeeping: ITERATION_LOG.md + cavity_iter_state.json (once) ---
    import datetime
    g1d, g2d, g4d = results["G1_efficiency"], results["G2_decomposition_fidelity"], results["G4_power_honesty"]
    led = results["power_ledger"]
    lm = led["matched"]
    ts = datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M-04:00")
    entry = {
        "id": "transducer_v1",
        "ts": ts,
        "directive": "Zak 2026-10-21 11:41 EDT (+ power-ledger addendum 11:48)",
        "architecture": ("tap coupler RHO=0.10 on the through-flow + one node per "
                         "cavity section; node = side-coupled resonator, absorption "
                         "A(mu)=4mu(1-mu), inverted (conjugate) stores; two-stage "
                         "readout: cancel vs proper (CALM) baseline, match the "
                         "residual vs stored inverted state deltas; verdicts only "
                         "leave the nodes."),
        "G1_efficiency": {"useful_ratio_best_over_unmatched": g1d["useful_ratio_best_over_unmatched"],
                          "best_mu": g1d["best_mu"],
                          "node_accuracy_best_mu": g1d["node_accuracy_best_mu"],
                          "node_accuracy_mu_bad": g1d["node_accuracy_mu_bad"],
                          "gate_pass_letter": g1d["gate_pass"],
                          "note": ("Gate letter PASS on the absorption ratio (5.26x) "
                                   "at 10% through loss, but the usefulness rider "
                                   "FAILS to differentiate: node accuracy is flat "
                                   "0.250 at every mu because the readout downstream "
                                   "is CALM-locked (see G2) — matched power could "
                                   "not be cashed by this readout.")},
        "G2_decomposition_fidelity": {"node_verdict_accuracy": g2d["node_verdict_accuracy"],
                                      "whole_cavity_same_run": g2d["whole_cavity_accuracy_same_run"],
                                      "gate_pass": g2d["gate_acc_ge_0.94"],
                                      "per_section_vote_accuracy": g2d["per_section_vote_accuracy_detail"],
                                      "dissection": g2d["dissection"]["mechanism"]},
        "G3_model_consumption": {"accuracy": {c: summary[c]["accuracy"] for c in conds},
                                 "mean_tokens_total": {c: summary[c]["mean_tokens_total"] for c in conds},
                                 "gate_pass": g3["gate_pass"]},
        "G4_power_honesty": {"ratio": g4d["ratio"], "gate_pass": g4d["gate_ratio_le_1.5"]},
        "power_ledger_matched": lm,
        "power_ledger_bleed_ratio_range": led["bleed_ratio_range_over_sweep"],
        "power_ledger_max_closure_error_frac": led["max_closure_error_frac_over_sweep"],
        "verdict": ("Transducer v1: G1 letter PASS / usefulness undemonstrated, "
                    "G2 FAIL (dissected: inverted CALM baselines null too well — "
                    "identity lives in the rectified signature, not the orthogonal "
                    "residual), G3 as measured, G4 PASS. Power ledger closes at "
                    "every mu. Queued follow-up: aggregate-baseline-referenced "
                    "node stores with LUT-style delta matching per section."),
        "results_file": "transducer_results.json",
        "code": ["transducer_sim.py"],
    }
    state = json.load(open(f"{HD}/cavity_iter_state.json"))
    if not any(e.get("id") == "transducer_v1" for e in state["experiments_done"]):
        state["experiments_done"].append(entry)
        state["last_updated"] = ts
        json.dump(state, open(f"{HD}/cavity_iter_state.json", "w"), indent=1)
        with open(f"{HD}/ITERATION_LOG.md", "a") as f:
            f.write(f"\n\n## {ts} — transducer_v1 (Zak 11:41 + ledger addendum 11:48)\n\n")
            f.write(f"Architecture: tap coupler RHO=0.10 on the through-flow; one node per "
                    f"section (POWER/DATA/IO/NETWORK/WEIGHTS), side-coupled resonator "
                    f"absorption A(mu)=4mu(1-mu), inverted conjugate stores; two-stage "
                    f"readout (cancel vs CALM proper, match residual vs stored inverted "
                    f"deltas). Baseline: FRESH real dweller tick ~11:44 EDT "
                    f"(transducer_baseline.json), preflight clean.\n\n")
            f.write(f"GATES: G1 {'PASS' if results['gates']['G1_efficiency'] else 'FAIL'} "
                    f"(useful ratio {g1d['useful_ratio_best_over_unmatched']:.2f}x at mu "
                    f"{g1d['best_mu']}, through loss 10%; rider: node accuracy flat "
                    f"{g1d['node_accuracy_best_mu']:.3f} at best mu vs "
                    f"{g1d['node_accuracy_mu_bad']:.3f} at mu 0.05 — matched power not "
                    f"cashed by this readout). G2 {'PASS' if results['gates']['G2_decomposition_fidelity'] else 'FAIL'} "
                    f"(node verdicts {g2d['node_verdict_accuracy']:.3f} vs same-run "
                    f"whole-cavity {g2d['whole_cavity_accuracy_same_run']:.3f}, gate "
                    f">= 0.94; per-section votes "
                    f"{ {k: round(v, 3) for k, v in g2d['per_section_vote_accuracy_detail'].items()} }). "
                    f"G3 {'PASS' if g3['gate_pass'] else 'FAIL'} "
                    f"(verdict acc {summary['verdict']['accuracy']:.3f} / "
                    f"{summary['verdict']['mean_tokens_total']} tok; label "
                    f"{summary['label']['accuracy']:.3f} / {summary['label']['mean_tokens_total']} tok; "
                    f"v4 packet {summary['packet_v4']['accuracy']:.3f} / "
                    f"{summary['packet_v4']['mean_tokens_total']} tok). G4 "
                    f"{'PASS' if results['gates']['G4_power_honesty'] else 'FAIL'} "
                    f"(dissipation ratio {g4d['ratio']:.3f} <= 1.5).\n\n")
            f.write(f"G2 DISSECTION: {g2d['dissection']['mechanism']}\n\n")
            f.write(f"POWER LEDGER (arbitrary units, NOT joules; tolerance 1e-9): "
                    f"matched mu {led['matched_mu']}: in {lm['power_in_through_flow']:.3f} = "
                    f"tapped {lm['power_tapped_by_nodes']:.3f} + passed/reflected "
                    f"{lm['power_reflected_passed']:.3f} + RESIDUAL SECOND CAVITY "
                    f"{lm['power_residual_second_cavity']:.3f} + bleed "
                    f"{lm['power_bleed']:.3f} (bleed ratio {lm['bleed_ratio']:.4f}). "
                    f"Over the mu sweep: bleed ratio spans "
                    f"{led['bleed_ratio_range_over_sweep'][0]:.4f}-"
                    f"{led['bleed_ratio_range_over_sweep'][1]:.4f} (max at the "
                    f"mismatched extremes, zero at critical coupling by "
                    f"construction); residual ratio at matched "
                    f"{lm['residual_ratio']:.4f}; max closure error over sweep "
                    f"{led['max_closure_error_frac_over_sweep']:.2e}. Full per-mu "
                    f"ledger in transducer_results.json -> power_ledger.by_mu.\n")
        print("bookkeeping appended (log + state)")
    else:
        print("bookkeeping already present — skipped")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "score":
        score()
    else:
        prep()
