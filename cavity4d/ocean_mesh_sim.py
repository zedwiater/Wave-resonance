"""
ocean_mesh_sim.py — WAVE-OCEAN-MESH: distributed buoy array as ONE
cavity (Zak's array-as-one-cavity architecture; explicit go
2026-10-21 17:54 EDT). VM-side only: no PC, no model calls, no push.

ARCHITECTURE MODELLED: a dense cluster of 12 buoys around one central
hub (the high-voltage power+data anchor). Every buoy runs the proven
ocean node from ocean_cavity_sim.py (imported, not re-implemented):
whole-pattern settled readout for sea state (the v2 PRIMARY), drive-end
tap + calibrated phase-coherence detector for transients. Buoys relay
compact readouts hop-by-hop over short induction links to the hub; the
hub fuses the 12 readouts into ONE array verdict and ONE aggregated
uplink line. The array's aperture is the cluster's extent, not one
buoy's hull.

DECLARED ASSUMPTIONS (modelling choices, NOT measurements):
  A1 INDUCTION RANGE: seawater is conductive; skin depth is ~25 m at
     100 Hz and ~8 m at 1 kHz. Links are therefore capped at 25 m per
     hop; the cluster spans 96 m across and relays multi-hop (<= 2
     hops to the hub in the ring layout used). Kilometre-
     spaced free-drifting buoys are OUT OF SCOPE for this sim — an
     induction mesh cannot span them, and this sim does not pretend
     otherwise.
  A2 RELAY EFFICIENCY: per-hop induction transfer efficiency eta is a
     DECLARED parameter, not a measured one. Sensitivity is run at
     eta = 0.90 and eta = 0.70 and both are reported.
  A3 PROPAGATION: one wave field, deep-water dispersion on the mapped
     ocean band: a buoy at projected coordinate s along the propagation
     axis (+x) sees mode n phase-shifted by exp(-i k_n s),
     k_n = (2 pi f_n)^2 / g, f_n = the parent sim's MODE_FREQS. The
     rogue group gets the same shift. Simplification: the spike's
     sim-time envelope (t0, width) is the same at every buoy — the
     sim's time axis is the scaled ladder time, not physical travel
     time across the cluster.
  A4 PER-BUOY NOISE: each buoy adds independent 12 dB modal noise (the
     parent sim's figure) from its own seeded stream. The single-buoy
     baseline carries NO extra noise and sits at s = 0 — it is the
     parent v2 run, reproduced in-process and asserted (0.9375, lone
     miss OC03) before any array number is trusted.
  A5 ENERGY: every power figure is an arbitrary simulated unit (a
     labelled proxy), never joules, never a measured saving. The
     parent S-split ledger is reused verbatim per node; the relay
     stage is downstream accounting appended to it, with relay loss
     as an explicit line item.
  A6 TOKENS (M3): counted as whitespace-delimited fields of the actual
     line strings, the same method applied to the aggregated line and
     to each individual line. (Context only: the parent sim's G5
     measured ~66 real model tokens per syslog line including prompt
     overhead — the ratio, not the absolute, is what transfers.)

PRE-STATED GATES (fixed before the run; nulls kept):
  M1  best array fusion accuracy >= 0.938 AND strictly better than the
      single-buoy baseline on CALM_SWELL scenarios. (Granularity note:
      with 16 scenarios, accuracies are multiples of 1/16, so >= 0.938
      in practice demands 16/16; the baseline CALM_SWELL accuracy is
      0.75, so "strictly better" demands 4/4 there.)
  M2  on BOTH transient scenarios: the rogue event is detected at
      array level (max per-buoy drive-end coherence >= the calibrated
      threshold) AND the first-detector buoy — argmax coherence — is
      the geometrically first buoy (minimum projected coordinate s:
      where the group physically enters the cluster). Localization is
      something a single buoy cannot provide at all.
  M3  the hub emits ONE aggregated line per scenario for the whole
      array; its token count (method A6) vs the summed count of the 12
      individual buoy lines is reported as measured counts.
  M4  per-node S-split ledger closure < 1e-9 for every buoy in every
      scenario (parent machinery), with relay losses itemized at both
      declared eta values.
  FALSIFIER (stated in advance): if the array scores <= the single
  buoy on identical scenarios, the distributed-cavity claim fails at
  this scale. Report whichever way it lands.
"""

import json
import sys

import numpy as np

sys.path.insert(0, "/home/hatch/workspace/harness-dev")
import audio_cavity_sim as sim
import ocean_cavity_sim as oc

HD = "/home/hatch/workspace/harness-dev"
SEED = oc.SEED
N_BUOYS = 12
LINK_RANGE_M = 25.0          # A1: max induction hop (skin-depth bound)
LATTICE_A_M = 24.0           # hex-lattice spacing (< link range)
MAX_RADIUS_M = 140.0
ETA_VALUES = (0.90, 0.70)    # A2: declared per-hop efficiencies
G_EARTH = 9.81
K_MODES = (2.0 * np.pi * oc.MODE_FREQS) ** 2 / G_EARTH   # A3 dispersion


# ------------------------------------------------------------- geometry ---
def build_layout():
    """12 buoys on a hexagonal lattice AROUND the hub: the 6 ring-1
    points (24 m) plus the 6 ring-2 corner points (48 m). Every buoy
    is <= 2 hops from the hub over <= 25 m links; cluster diameter
    96 m. Deterministic (axial coordinates, fixed order).

    DESIGN HISTORY (disclosed): run 1 grew the layout by repeatedly
    adding the largest-radius frontier point (ties by polar angle).
    The tie-break walked the growth into one angular sector and
    produced a one-sided 10-hop CHAIN (all buoys at negative x, hops
    1..10, max radius 134 m) — connected, but not the specified
    architecture (a cluster around a central hub), and it made the
    farthest relay the geometric first detector. Run 1 outcomes with
    that layout: M1 FAIL (vote 0.875, field 0.6875), M2 FAIL (no
    detection; max coherences 0.462 / 0.612 vs threshold 0.793),
    M4 PASS. Replaced by the ring layout below; gates unchanged."""
    u = np.array([LATTICE_A_M, 0.0])
    v = np.array([LATTICE_A_M / 2.0, LATTICE_A_M * np.sqrt(3.0) / 2.0])
    axial = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1),      # ring 1
             (2, 0), (0, 2), (-2, 2), (-2, 0), (0, -2), (2, -2)]      # ring 2 corners
    positions = np.array([i * u + j * v for (i, j) in axial], dtype=float)
    # hop counts: BFS over {hub} + buoys with edges <= LINK_RANGE_M
    nodes = [np.zeros(2)] + list(positions)
    hops = [None] * (N_BUOYS + 1)
    hops[0] = 0
    queue = [0]
    while queue:
        cur = queue.pop(0)
        for nxt in range(N_BUOYS + 1):
            if hops[nxt] is None and float(np.linalg.norm(nodes[cur] - nodes[nxt])) <= LINK_RANGE_M + 1e-9:
                hops[nxt] = hops[cur] + 1
                queue.append(nxt)
    buoy_hops = hops[1:]
    assert all(h is not None for h in buoy_hops), "layout disconnected"
    return positions, buoy_hops


POSITIONS, HOPS = build_layout()
S_PROJ = POSITIONS[:, 0]                       # projected coordinate s
PHASE = np.exp(-1j * np.outer(S_PROJ, K_MODES))  # per-buoy mode phases
FIRST_BUOY = int(np.argmin(S_PROJ))            # where the group enters
FIRST_SET = [b for b in range(N_BUOYS) if S_PROJ[b] == S_PROJ[FIRST_BUOY]]


def shift(vec, b):
    return vec * PHASE[b]


def compensated_coherence(a_de, agg_de, b):
    """DIAGNOSTIC D2 statistic: spike-band phase coherence of the
    drive-end delta AFTER dispersion compensation — the delta is
    derotated by the conjugate propagation factor, undoing (in this
    linear-propagation model) the dephasing the packet accumulated
    travelling to s_b. The shipped detector (parent pattern) has no
    such compensation; D2 tests whether that is the M2 mechanism."""
    d = oc.SCALE * (a_de - agg_de) * np.conj(PHASE[b])
    band = d[oc.SPIKE_BAND]
    tot = float(np.sum(np.abs(band)))
    return float(abs(np.sum(band)) / tot) if tot > 0 else 0.0


# ----------------------------------------------------------------- main ---
def run():
    bank, bank_vecs, agg_hub, ref_hub = oc.build_references()
    base = np.mean(bank_vecs, axis=0)
    base = base / np.linalg.norm(base)
    whole_sigs_hub = {s: np.abs(ref_hub[s]["SETTLED"]) ** 2 for s in oc.STATE_ORDER}

    # ---- scenario inputs: EXACT parent rng consumption order (A4) ----
    rng = np.random.default_rng(SEED)
    scen_inputs = []
    for (state, is_tr) in oc.SCENARIO_PLAN:
        spec, _params = oc.state_spectrum(state, rng, jitter=True)
        spec_n = sim.add_modal_noise(rng, spec, oc.MODAL_NOISE_DB)
        spike = None
        if is_tr:
            spike = {"vec": oc.rogue_vec(rng), "amp": 3.0, "t0": 0.21, "width": 0.03}
        scen_inputs.append((state, bool(is_tr), spec_n, spike))

    # ---- A4 baseline check: parent v2, in-process ----------------------
    base_preds = []
    for (state, is_tr, spec_n, spike) in scen_inputs:
        _de, a_st, _d = oc.ocean_evolve(spec_n, bank_vecs, spike=spike)
        ps = np.abs(a_st) ** 2
        sc_ = {s: float(sim.cosine(ps, whole_sigs_hub[s])) for s in oc.STATE_ORDER}
        base_preds.append(max(oc.STATE_ORDER, key=lambda s: sc_[s]))
    base_acc = float(np.mean([p == st for p, (st, *_r) in zip(base_preds, scen_inputs)]))
    calm_idx = [i for i, (st, *_r) in enumerate(scen_inputs) if st == "CALM_SWELL"]
    base_calm = float(np.mean([base_preds[i] == "CALM_SWELL" for i in calm_idx]))
    assert abs(base_acc - 0.9375) < 1e-12, f"baseline drift: {base_acc}"
    print(f"baseline (single buoy, parent v2 reproduced): {base_acc:.4f}, "
          f"CALM_SWELL {base_calm:.2f}, miss = OC03 only")

    # ---- per-buoy references (position-matched, A3) -------------------
    agg_b, sig_b = [], []
    for b in range(N_BUOYS):
        a_de, a_st, _ = oc.ocean_evolve(shift(base, b), bank_vecs)
        agg_b.append({"DRIVE_END": a_de, "SETTLED": a_st})
        sigs = {}
        for s in oc.STATE_ORDER:
            _d, a_s, _x = oc.ocean_evolve(shift(bank[s], b), bank_vecs)
            sigs[s] = np.abs(a_s) ** 2
        sig_b.append(sigs)

    # ---- detector calibration: 30 disjoint trials (parent seeds),
    #      evaluated at EVERY buoy position; one global threshold.
    crng = np.random.default_rng(SEED + 500000)
    cal_inputs = []
    for s in oc.STATE_ORDER:
        for _rep in range(6):
            spec_c, _ = oc.state_spectrum(s, crng, jitter=True)
            spec_c = sim.add_modal_noise(crng, spec_c, oc.MODAL_NOISE_DB)
            cal_inputs.append(spec_c)
    coh_bg_max = 0.0
    coh_bg_max_comp = 0.0
    cal_fields_de = []          # kept for the D2 compensated threshold
    for ci, spec_c in enumerate(cal_inputs):
        row = []
        for b in range(N_BUOYS):
            inp = sim.add_modal_noise(
                np.random.default_rng(SEED + 880000 + 1000 * ci + b),
                shift(spec_c, b), oc.MODAL_NOISE_DB)
            a_de, _st, _d = oc.ocean_evolve(inp, bank_vecs)
            row.append(a_de)
            coh = oc.transient_metrics(a_de, agg_b[b]["DRIVE_END"])["phase_coherence"]
            coh_bg_max = max(coh_bg_max, coh)
            coh_bg_max_comp = max(coh_bg_max_comp,
                                  compensated_coherence(a_de, agg_b[b]["DRIVE_END"], b))
        cal_fields_de.append(row)
    THR = float(coh_bg_max + 0.02)
    THR_COMP = float(coh_bg_max_comp + 0.02)
    print(f"array detector threshold: background max {coh_bg_max:.3f} "
          f"(30 trials x {N_BUOYS} buoys) + 0.02 -> {THR:.3f} "
          f"(parent single-buoy threshold was 0.796); "
          f"D2 compensated background max {coh_bg_max_comp:.3f} -> {THR_COMP:.3f}")

    # ---- scenarios x buoys --------------------------------------------
    scenarios_out = []
    for i, (state, is_tr, spec_n, spike) in enumerate(scen_inputs):
        sid = f"OC{i + 1:02d}"
        per_buoy = []
        fields_st = []
        fields_de = []
        for b in range(N_BUOYS):
            inp = sim.add_modal_noise(
                np.random.default_rng(SEED + 770000 + 100 * i + b),
                shift(spec_n, b), oc.MODAL_NOISE_DB)
            spike_b = None
            if spike is not None:
                spike_b = {"vec": shift(spike["vec"], b), "amp": spike["amp"],
                           "t0": spike["t0"], "width": spike["width"]}
            a_de, a_st, _d = oc.ocean_evolve(inp, bank_vecs, spike=spike_b)
            fields_st.append(a_st)
            fields_de.append(a_de)
            ps = np.abs(a_st) ** 2
            scores = {s: float(sim.cosine(ps, sig_b[b][s])) for s in oc.STATE_ORDER}
            pred = max(oc.STATE_ORDER, key=lambda s: scores[s])
            ranked = sorted(scores.values(), reverse=True)
            coh = oc.transient_metrics(a_de, agg_b[b]["DRIVE_END"])["phase_coherence"]
            nd = oc.nd_vs_agg(a_st, agg_b[b]["SETTLED"])
            led = oc.ledger_for(a_st, inp, nd)
            per_buoy.append({"buoy": b, "pred": pred, "scores": scores,
                             "margin": ranked[0] - ranked[1],
                             "coherence_drive_end": coh, "ledger": led})
        # fusion (a): margin-weighted vote (+ majority diagnostic)
        vote_w, vote_n = {}, {}
        for pb in per_buoy:
            vote_w[pb["pred"]] = vote_w.get(pb["pred"], 0.0) + pb["margin"]
            vote_n[pb["pred"]] = vote_n.get(pb["pred"], 0) + 1
        pred_vote = max(vote_w, key=vote_w.get)
        pred_majority = max(vote_n, key=lambda s: (vote_n[s], vote_w.get(s, 0.0)))
        conf_vote = vote_w[pred_vote] / sum(vote_w.values())
        # fusion (b): phase-aligned (derotated) complex field mean
        joint = np.mean([fields_st[b] * np.conj(PHASE[b]) for b in range(N_BUOYS)], axis=0)
        ps_j = np.abs(joint) ** 2
        scores_j = {s: float(sim.cosine(ps_j, whole_sigs_hub[s])) for s in oc.STATE_ORDER}
        pred_field = max(oc.STATE_ORDER, key=lambda s: scores_j[s])
        conf_field = scores_j[pred_field]
        # diagnostic (c): incoherent power-spectrum mean
        ps_m = np.mean([np.abs(fields_st[b]) ** 2 for b in range(N_BUOYS)], axis=0)
        scores_m = {s: float(sim.cosine(ps_m, whole_sigs_hub[s])) for s in oc.STATE_ORDER}
        pred_powermean = max(oc.STATE_ORDER, key=lambda s: scores_m[s])
        # transient / localization
        cohs = [pb["coherence_drive_end"] for pb in per_buoy]
        first_hat = int(np.argmax(cohs))
        detected = bool(max(cohs) >= THR)
        # D2 diagnostic: dispersion-compensated detector (not the gate)
        cohs_comp = [compensated_coherence(fields_de[b], agg_b[b]["DRIVE_END"], b)
                     for b in range(N_BUOYS)]
        first_hat_comp = int(np.argmax(cohs_comp))
        detected_comp = bool(max(cohs_comp) >= THR_COMP)
        # ---- M3 lines --------------------------------------------------
        ts = f"2026-10-21T{18 + (5 + i) // 60:02d}:{(5 + i) % 60:02d}Z"
        indiv_lines = []
        for b, pb in enumerate(per_buoy):
            led = pb["ledger"]
            power_est = f"{100.0 * (1.0 - led['bleed_ratio']):.1f}%"
            indiv_lines.append(
                f'<134>1 {ts} BUOY_{b + 1:02d} WAVE_CAVITY - - [state@41021 '
                f'classification="{pb["pred"]}" power_est="{power_est}" '
                f'confidence="{pb["scores"][pb["pred"]]:.3f}"]')
        # production rule for the hub line: better of (a)/(b) is chosen
        # after scoring (below); provisional here = field fusion, and
        # the line is rebuilt once the M1 winner is known.
        scenarios_out.append({
            "scenario_id": sid, "true_state": state, "transient": is_tr,
            "per_buoy": [{k: v for k, v in pb.items() if k != "ledger"}
                         for pb in per_buoy],
            "per_buoy_ledger_closure": [pb["ledger"]["closure_error_frac"]
                                        for pb in per_buoy],
            "per_buoy_tapped": [pb["ledger"]["power_tapped_by_nodes"] for pb in per_buoy],
            "per_buoy_p_in": [pb["ledger"]["power_in_through_flow"] for pb in per_buoy],
            "pred_vote_weighted": pred_vote, "pred_majority": pred_majority,
            "pred_field_fusion": pred_field, "pred_powermean_diag": pred_powermean,
            "conf_vote_weighted": conf_vote, "conf_field_fusion": conf_field,
            "coherences": cohs, "array_detected": detected,
            "first_detector_hat": first_hat, "first_detector_expected": FIRST_BUOY,
            "first_detector_expected_set": FIRST_SET,
            "localization_correct": bool(first_hat in FIRST_SET),
            "coherences_compensated_diag": cohs_comp,
            "array_detected_compensated_diag": detected_comp,
            "first_detector_hat_compensated_diag": first_hat_comp,
            "localization_correct_compensated_diag": bool(first_hat_comp in FIRST_SET),
            "_ts": ts, "_indiv_lines": indiv_lines,
        })

    # ---- M1 scoring -----------------------------------------------------
    def acc_of(key):
        return float(np.mean([sc[key] == sc["true_state"] for sc in scenarios_out]))

    def calm_of(key):
        rows = [sc for sc in scenarios_out if sc["true_state"] == "CALM_SWELL"]
        return float(np.mean([sc[key] == "CALM_SWELL" for sc in rows]))

    acc_vote, acc_field = acc_of("pred_vote_weighted"), acc_of("pred_field_fusion")
    acc_majority, acc_pm = acc_of("pred_majority"), acc_of("pred_powermean_diag")
    per_buoy_acc = float(np.mean([pb["pred"] == sc["true_state"]
                                  for sc in scenarios_out for pb in sc["per_buoy"]]))
    fusions = {"vote_weighted": acc_vote, "field_fusion": acc_field}
    best_name = max(fusions, key=fusions.get)
    best_acc = fusions[best_name]
    best_key = "pred_vote_weighted" if best_name == "vote_weighted" else "pred_field_fusion"
    best_calm = calm_of(best_key)
    m1_pass = bool(best_acc >= 0.938 and best_calm > base_calm)
    print(f"M1 fusions: vote {acc_vote:.4f} (CALM {calm_of('pred_vote_weighted'):.2f}), "
          f"field {acc_field:.4f} (CALM {calm_of('pred_field_fusion'):.2f}); "
          f"diagnostics: majority {acc_majority:.4f}, power-mean {acc_pm:.4f}, "
          f"mean per-buoy {per_buoy_acc:.4f} vs baseline {base_acc:.4f} — "
          f"M1 {'PASS' if m1_pass else 'FAIL'}")

    # ---- M2 -------------------------------------------------------------
    trans = [sc for sc in scenarios_out if sc["transient"]]
    m2_rows = [{"scenario": sc["scenario_id"], "true_state": sc["true_state"],
                "detected": sc["array_detected"],
                "first_hat": sc["first_detector_hat"],
                "first_expected": sc["first_detector_expected"],
                "localization_correct": sc["localization_correct"],
                "max_coherence": max(sc["coherences"])} for sc in trans]
    m2_pass = bool(all(r["detected"] and r["localization_correct"] for r in m2_rows))
    print(f"M2 transients: {[(r['scenario'], r['detected'], r['first_hat'], r['localization_correct']) for r in m2_rows]} "
          f"— {'PASS' if m2_pass else 'FAIL'}")

    # ---- DIAGNOSTIC D1: noise ablation --------------------------------
    # Same scenarios, same phase shifts, position-matched references —
    # but NO extra per-buoy noise draw. Separates the A4 double-noise
    # cost from the phase-mixing cost. Diagnostic only; M1 stands as run.
    d1_rows = []
    for i, (state, is_tr, spec_n, spike) in enumerate(scen_inputs):
        preds_b, vote_w, fields = [], {}, []
        for b in range(N_BUOYS):
            inp = shift(spec_n, b)
            spike_b = None
            if spike is not None:
                spike_b = {"vec": shift(spike["vec"], b), "amp": spike["amp"],
                           "t0": spike["t0"], "width": spike["width"]}
            _de, a_st, _d = oc.ocean_evolve(inp, bank_vecs, spike=spike_b)
            fields.append(a_st)
            ps = np.abs(a_st) ** 2
            scores = {s: float(sim.cosine(ps, sig_b[b][s])) for s in oc.STATE_ORDER}
            pred = max(oc.STATE_ORDER, key=lambda s: scores[s])
            ranked = sorted(scores.values(), reverse=True)
            preds_b.append(pred)
            vote_w[pred] = vote_w.get(pred, 0.0) + (ranked[0] - ranked[1])
        joint = np.mean([fields[b] * np.conj(PHASE[b]) for b in range(N_BUOYS)], axis=0)
        ps_j = np.abs(joint) ** 2
        scores_j = {s: float(sim.cosine(ps_j, whole_sigs_hub[s])) for s in oc.STATE_ORDER}
        d1_rows.append({"scenario": scenarios_out[i]["scenario_id"], "true_state": state,
                        "per_buoy_correct": int(sum(p == state for p in preds_b)),
                        "vote_pred": max(vote_w, key=vote_w.get),
                        "field_pred": max(oc.STATE_ORDER, key=lambda s: scores_j[s])})
    d1 = {"per_buoy_accuracy_no_extra_noise":
          float(np.mean([r["per_buoy_correct"] for r in d1_rows])) / N_BUOYS,
          "vote_accuracy_no_extra_noise":
          float(np.mean([r["vote_pred"] == r["true_state"] for r in d1_rows])),
          "field_accuracy_no_extra_noise":
          float(np.mean([r["field_pred"] == r["true_state"] for r in d1_rows])),
          "rows": d1_rows}
    print(f"D1 noise ablation: per-buoy {d1['per_buoy_accuracy_no_extra_noise']:.4f} "
          f"(with noise {per_buoy_acc:.4f}), vote {d1['vote_accuracy_no_extra_noise']:.4f}, "
          f"field {d1['field_accuracy_no_extra_noise']:.4f}")

    # ---- DIAGNOSTIC D2 summary (compensated detector, transients) -----
    d2 = {"threshold_compensated": THR_COMP,
          "background_max_compensated": coh_bg_max_comp,
          "rows": [{"scenario": sc["scenario_id"],
                    "detected_compensated": sc["array_detected_compensated_diag"],
                    "first_hat_compensated": sc["first_detector_hat_compensated_diag"],
                    "localization_correct_compensated":
                    sc["localization_correct_compensated_diag"],
                    "max_coherence_compensated": max(sc["coherences_compensated_diag"])}
                   for sc in trans]}
    print(f"D2 compensated detector: {[(r['scenario'], r['detected_compensated'], r['localization_correct_compensated']) for r in d2['rows']]} "
          f"(threshold {THR_COMP:.3f})")

    # ---- M3: aggregated line uses the M1-winning fusion ----------------
    conf_key = "conf_vote_weighted" if best_name == "vote_weighted" else "conf_field_fusion"
    tok_indiv_total, tok_agg_total, m3_rows = 0, 0, []
    for sc in scenarios_out:
        verdict = sc[best_key]
        conf = sc[conf_key]
        tid = "none"
        first_s = "none"
        if sc["transient"] and sc["array_detected"]:
            tid = sc["scenario_id"]
            first_s = f"B{sc['first_detector_hat'] + 1:02d}"
        agg_line = (f'<134>1 {sc["_ts"]} HUB ARRAY{N_BUOYS} WAVE_CAVITY - - '
                    f'[array@41021 classification="{verdict}" '
                    f'confidence="{conf:.3f}" transient="{tid}" '
                    f'first="{first_s}"]')
        tok_i = sum(len(l.split()) for l in sc["_indiv_lines"])
        tok_a = len(agg_line.split())
        tok_indiv_total += tok_i
        tok_agg_total += tok_a
        m3_rows.append({"scenario": sc["scenario_id"], "aggregated_line": agg_line,
                        "tokens_aggregated": tok_a, "tokens_individual_total": tok_i})
    saving = 1.0 - tok_agg_total / tok_indiv_total
    print(f"M3 uplink tokens (whitespace fields, 16 scenarios): aggregated "
          f"{tok_agg_total} vs individual {tok_indiv_total} -> saving {saving:.1%}")

    # ---- M4 -------------------------------------------------------------
    max_closure = float(np.max([c for sc in scenarios_out
                                for c in sc["per_buoy_ledger_closure"]]))
    relay = {}
    for eta in ETA_VALUES:
        rows = []
        for sc in scenarios_out:
            tapped = np.array(sc["per_buoy_tapped"])
            p_in = float(np.sum(sc["per_buoy_p_in"]))
            received = float(np.sum([tapped[b] * eta ** HOPS[b] for b in range(N_BUOYS)]))
            loss = float(np.sum(tapped) - received)
            rows.append({"scenario": sc["scenario_id"],
                         "tapped_total_proxy": float(np.sum(tapped)),
                         "hub_received_tapped_proxy": received,
                         "relay_loss_proxy": loss,
                         "relay_loss_frac_of_tapped": loss / float(np.sum(tapped)),
                         "relay_loss_frac_of_p_in": loss / p_in})
        relay[str(eta)] = {
            "mean_relay_loss_frac_of_tapped": float(np.mean([r["relay_loss_frac_of_tapped"] for r in rows])),
            "mean_relay_loss_frac_of_p_in": float(np.mean([r["relay_loss_frac_of_p_in"] for r in rows])),
            "rows": rows}
    m4_pass = bool(max_closure < 1e-9)
    print(f"M4 per-node ledger max closure {max_closure:.2e} (tol 1e-9) — "
          f"{'PASS' if m4_pass else 'FAIL'}; relay loss frac of tapped: "
          f"eta 0.90 -> {relay['0.9']['mean_relay_loss_frac_of_tapped']:.3f}, "
          f"eta 0.70 -> {relay['0.7']['mean_relay_loss_frac_of_tapped']:.3f}")

    gates = {
        "M1_array_fusion": {
            "best_fusion": best_name, "best_accuracy": best_acc,
            "threshold": 0.938, "baseline_accuracy": base_acc,
            "best_calm_swell_accuracy": best_calm, "baseline_calm_swell_accuracy": base_calm,
            "vote_weighted_accuracy": acc_vote, "field_fusion_accuracy": acc_field,
            "diagnostics": {"majority_vote_accuracy": acc_majority,
                            "powermean_accuracy": acc_pm,
                            "mean_per_buoy_accuracy": per_buoy_acc},
            "confusions_best": [{"scenario": sc["scenario_id"], "true": sc["true_state"],
                                 "pred": sc[best_key]}
                                for sc in scenarios_out if sc[best_key] != sc["true_state"]],
            "pass": m1_pass},
        "M2_transient_localization": {"threshold": THR, "rows": m2_rows, "pass": m2_pass,
                                      "note": "single buoy baseline detects the event "
                                              "(parent G2) but has no localization to give"},
        "M3_uplink_aggregation": {
            "counting_method": "whitespace-delimited fields of the actual line strings (A6)",
            "tokens_aggregated_total_16_scenarios": tok_agg_total,
            "tokens_individual_total_16_scenarios": tok_indiv_total,
            "mean_tokens_aggregated_per_scenario": tok_agg_total / 16.0,
            "mean_tokens_individual_per_scenario": tok_indiv_total / 16.0,
            "saving_frac": saving, "rows": m3_rows,
            "pass": bool(tok_agg_total < tok_indiv_total)},
        "M4_ledger_and_relay": {"max_closure_error_frac": max_closure, "tolerance": 1e-9,
                                "pass": m4_pass, "relay_by_eta": relay},
        "falsifier": {"statement": "array <= single buoy on identical scenarios -> "
                                   "distributed-cavity claim fails at this scale",
                      "array_best_accuracy": best_acc, "baseline_accuracy": base_acc,
                      "claim_survives": bool(best_acc > base_acc)},
    }

    results = {
        "header": {
            "experiment": "wave-ocean-mesh — distributed buoy array as one cavity",
            "directive": "Zak 2026-10-21 17:54 EDT (explicit go for the mesh sim)",
            "parent": "ocean_cavity_sim.py v2 (whole-pattern primary, drive-end transient tap)",
            "declared_assumptions": {
                "A1_induction_range_m_per_hop": LINK_RANGE_M,
                "A2_eta_values": list(ETA_VALUES),
                "A3_propagation": "deep-water dispersion k_n=(2 pi f_n)^2/g on the parent sim's mapped ocean band; phase shift exp(-i k_n s_b); spike envelope timing identical at all buoys (declared simplification)",
                "A4_per_buoy_noise_db": oc.MODAL_NOISE_DB,
                "A5_energy_label": "all power figures arbitrary simulated units (proxies), never joules",
                "A6_token_method": "whitespace-delimited field count of the actual line strings",
                "frequency_scaling": "inherited from parent: ocean band 0.04-2.0 Hz mapped logarithmically onto the 32-mode ladder",
            },
            "geometry": {
                "n_buoys": N_BUOYS, "lattice_spacing_m": LATTICE_A_M,
                "link_range_m": LINK_RANGE_M,
                "positions_m": [[round(float(x), 2), round(float(y), 2)] for x, y in POSITIONS],
                "projected_s_m": [round(float(s), 2) for s in S_PROJ],
                "hops_to_hub": HOPS,
                "max_radius_m": round(float(np.max(np.linalg.norm(POSITIONS, axis=1))), 2),
                "first_buoy_geometric": FIRST_BUOY,
                "first_buoy_set": FIRST_SET,
            },
            "design_history": {
                "run_1_chain_layout": {
                    "layout": "growth algorithm (largest radius, angle tie-break) -> one-sided chain, hops 1..10, max radius 134 m",
                    "gates": {"M1": "FAIL (vote 0.875, field 0.6875)", "M2": "FAIL (0/2 detected; max coherences 0.462/0.612 vs thr 0.793)",
                              "M3": "192 vs 1920 tokens (90.0% saving)", "M4": "PASS (closure 2.93e-16)"},
                    "disposition": "layout contradicted the specified architecture (cluster around a central hub); replaced by ring layout, gates unchanged, re-run as run 2 (the results in this file)"},
            },
            "parameters": {"seed": SEED, "detector_threshold": THR,
                           "calibration_background_max": coh_bg_max},
        },
        "baseline_single_buoy": {"accuracy": base_acc, "calm_swell_accuracy": base_calm,
                                 "preds": base_preds},
        "diagnostics": {"D1_noise_ablation": d1, "D2_compensated_detector": d2},
        "gates": gates,
        "scenarios": [{k: v for k, v in sc.items() if not k.startswith("_")}
                      for sc in scenarios_out],
    }
    with open(f"{HD}/ocean_mesh_results.json", "w") as f:
        json.dump(results, f, indent=1, default=float)
    print(f"wrote ocean_mesh_results.json — gates: "
          f"M1 {'PASS' if m1_pass else 'FAIL'}, M2 {'PASS' if m2_pass else 'FAIL'}, "
          f"M3 counts reported, M4 {'PASS' if m4_pass else 'FAIL'}")


if __name__ == "__main__":
    run()
