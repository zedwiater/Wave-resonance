"""
ocean_cavity_sim.py — WAVE-OCEAN-V1: passive ocean wave-resonance
transducer simulation (spec drafted by Gemini, approved by Zak
2026-10-21 16:52 EDT with "adjust where needed"; adjustments applied
below are part of the tasking).

WHAT THIS IS: a SOFTWARE MODEL of the transducer/cavity architecture
(transducer_v2_sim.py, commit c305b76 patterns) driven by ocean
hydrodynamic forcing instead of dweller telemetry. Ocean wave spectra
(JONSWAP / Pierson-Moskowitz) drive the 32-mode modal cavity; template
coupling + ring-down perform the spectral decomposition; a
deterministic LUT wrapper (aggregate-referenced node stores, delta
matching, energy-weighted composition — the transducer v2 pattern)
resolves the state; the output contract is the F2 log-line.

MANDATORY ADJUSTMENTS (Zak approved "adjust where needed"):
  1. NO "zero-FLOP / zero-cost" claims. This is a software model of the
     architecture; every energy/compute figure is a LABELLED PROXY in
     arbitrary simulated units — never joules, never measured savings.
  2. FREQUENCY SCALING DISCLOSED: a literal buoy cavity cannot resonate
     at 0.05–2 Hz (wavelengths are kilometre-scale). The sim maps the
     ocean band 0.04–2.0 Hz logarithmically onto the sim's 32-mode
     ladder — the same scaling trick as the audio sim (110 Hz ladder
     standing in for its band). The mapping is stated in the digest.
  3. RADIATIVE POWER CHANNEL: in transducer v2 the ~0.1% exit decode
     worked because the radiation was computed from the same state
     variables. The gate is kept, but it is a CONSTRUCTED-CHANNEL
     BOOKKEEPING CHECK, not a discovered physical channel.
  4. HARD CASES REQUIRED: genuinely confusable state pairs
     (CROSS_SEA vs STORM_FORCE; BUILDING_SEA vs MODERATE_CHOP) and
     additive noise on the forcing, so the 0.875 gate is earned.

DESIGN CHOICE (stated): ocean sea state is a SPECTRAL-SHAPE property;
per-realization wave phases are nuisance. Node stores therefore match
modal AMPLITUDE deltas (|field| per section) against the aggregate
baseline — phase-invariant — while the cavity evolution itself runs on
the full complex field with a canonical phase profile plus per-scenario
phase jitter. The transient detector is the one phase-sensitive readout
(a rogue wave GROUP is phase-aligned by definition).

V1 PRE-STATED GATES (run 2026-10-21, results preserved under "v1" in
ocean_results.json): G1 settled node-composed classification >= 0.875
(FAIL 0.500; whole-pattern settled readout scored 0.938 same scenarios);
G2 dual-clock transient (PASS); G3 ledger closure (PASS); G4 exit
decode (FAIL remaining leg); G5 syslog formatter (FAIL token clause).

V2 RE-RUN (Zak's go 2026-10-21 17:15 EDT): the whole-pattern settled
readout is PROMOTED to PRIMARY classifier — the LUT verdict handed to
the edge formatter now comes from it. Per-section / drive-end readouts
keep only their G2 job: transient detection. Same 16 scenarios, same
seed, nothing else redesigned.
  G1' primary (whole-pattern, SETTLED) classification >= 0.875.
  G2, G3 unchanged — must still pass.
  G4 unchanged — reported as-is, no new arms.
  G5 re-run with the NEW verdicts: copy fidelity and token counts
     reported separately; the syslog token clause is expected to fail
     structurally again (header cost) — report, do not redesign.

Modes: `python3 ocean_cavity_sim.py` (VM-side run + jobs),
       `python3 ocean_cavity_sim.py score` (merge PC answers -> G5).
"""

import json
import sys

import numpy as np

sys.path.insert(0, "/home/hatch/workspace/harness-dev")
import audio_cavity_sim as sim

HD = "/home/hatch/workspace/harness-dev"
SEED = 21021
RHO_TAP = 0.10
MU = 0.5                       # matched (critical coupling)
NODE_NOISE_P = 1e-3
MODAL_NOISE_DB = 12.0
WINDOWS = {"DRIVE_END": sim.T_DRIVE, "SETTLED": sim.T_SETTLE}

# ------------------------------------------------------------ ocean band ---
# SCALING (adjustment 2): ocean band 0.04–2.0 Hz mapped logarithmically
# onto the 32 sim modes. Mode n <-> f_n below; the cavity dynamics
# (damping, detune, coupling) are the audio sim's, unchanged — only the
# INTERPRETATION of the ladder is ocean.
F_LO, F_HI = 0.04, 2.0
MODE_FREQS = F_LO * (F_HI / F_LO) ** (np.arange(sim.N_MODES) / (sim.N_MODES - 1))

SECTIONS = [  # (name, mode_lo_1based, mode_hi_1based) over the ocean ladder
    ("SWELL", 1, 8),
    ("SEA", 9, 16),
    ("CHOP", 17, 24),
    ("SPRAY", 25, 32),
]
SECTION_MODES = {name: list(range(lo - 1, hi)) for name, lo, hi in SECTIONS}
SPIKE_BAND = list(range(4, 24))   # modes 5–24: the rogue group's band

# ------------------------------------------------------------- sea states --
# Each state: list of components (Hs_m, Tp_s, jonswap_gamma, kind).
# kind "swell" = narrow, phase-coherent; "sea" = wind sea, phase-jittered.
# Pierson-Moskowitz is JONSWAP with gamma = 1 (STORM_FORCE).
STATE_DEFS = {
    "CALM_SWELL":    [(0.6, 12.0, 3.3, "swell")],
    "MODERATE_CHOP": [(1.3, 5.0, 1.5, "sea")],
    "BUILDING_SEA":  [(2.2, 7.5, 2.0, "sea")],
    "CROSS_SEA":     [(1.4, 11.0, 3.0, "swell"), (1.1, 4.2, 1.2, "sea")],
    "STORM_FORCE":   [(4.8, 9.0, 1.0, "sea")],
}
STATE_ORDER = list(STATE_DEFS.keys())
SEV = {"CALM_SWELL": "none", "MODERATE_CHOP": "low", "BUILDING_SEA": "mid",
       "CROSS_SEA": "high", "STORM_FORCE": "high"}


def jonswap_shape(freqs, fp, gamma_pk):
    """JONSWAP spectral shape S(f) (unnormalized), standard form."""
    sigma = np.where(freqs <= fp, 0.07, 0.09)
    r = np.exp(-((freqs - fp) ** 2) / (2 * sigma ** 2 * fp ** 2))
    S = freqs ** -5 * np.exp(-1.25 * (fp / freqs) ** 4) * gamma_pk ** r
    return S


def component_phase(kind, rng):
    """Phase profile per component kind, following the lab's codebook
    convention (cavity_topology / expBC: a FIXED phase structure shared
    by the bank and the realizations, jitter on values). Swell: linear
    phase ramp (coherent travelling group), jitter 0.2 rad. Wind sea:
    same ramp under heavier jitter, 0.5 rad.

    DESIGN HISTORY (disclosed): run 2 tried per-realization RANDOM
    phases (oceanographically defensible) and it broke the sim —
    template coupling collapsed (random-phase inputs barely overlap
    the canonical bank), the settled classification fell to 0.438 and
    the exit decode exploded (usable rel err 211%). The architecture
    as built in this lab is a shared-phase-codebook machine; random
    phases are a different machine. Reverted to the codebook form."""
    n = np.arange(sim.N_MODES)
    ramp = -0.35 * n
    jit = 0.2 if kind == "swell" else 0.5
    return ramp + rng.uniform(-jit, jit, sim.N_MODES)


def state_spectrum(state, rng, jitter=True):
    """Modal complex spectrum for a sea state: JONSWAP components
    superposed in POWER, phases from the dominant component per mode.
    Returns (unit-norm complex spectrum, params dict)."""
    comps = STATE_DEFS[state]
    hs_tot = float(np.sqrt(sum(c[0] ** 2 for c in comps)))
    power = np.zeros(sim.N_MODES)
    phase = np.zeros(sim.N_MODES)
    best_w = np.full(sim.N_MODES, -1.0)
    params = []
    for (hs, tp, gpk, kind) in comps:
        if jitter:
            hs_j = hs * (1 + rng.uniform(-0.10, 0.10))
            tp_j = tp * (1 + rng.uniform(-0.08, 0.08))
            g_j = gpk * (1 + rng.uniform(-0.15, 0.15))
        else:
            hs_j, tp_j, g_j = hs, tp, gpk
        fp = 1.0 / tp_j
        S = jonswap_shape(MODE_FREQS, fp, g_j)
        # normalize shape to unit integral over log-frequency grid
        dl = np.gradient(np.log(MODE_FREQS))
        S = S / np.sum(S * MODE_FREQS * dl)
        w = (hs_j / hs_tot) ** 2
        contrib = w * S
        ph = component_phase(kind, rng)
        upd = contrib > best_w
        phase[upd] = ph[upd]
        best_w[upd] = contrib[upd]
        power += contrib
        params.append({"Hs": hs_j, "Tp": tp_j, "gamma": g_j, "kind": kind})
    amp = np.sqrt(power)
    spec = amp * np.exp(1j * phase)
    n = np.linalg.norm(spec)
    return spec / n, {"Hs_total": hs_tot, "components": params}


# -------------------------------------------------------------- evolution --
def ocean_evolve(a_in, bank_vecs, spike=None, t_total=sim.T_SETTLE):
    """audio_cavity_sim.evolve's RK4 dynamics (same constants, same rhs,
    pump on, alpha = 1) with BOTH tap windows captured in one run, plus
    an optional transient: spike = {"vec", "amp", "t0", "width"} adds a
    phase-aligned wave-group drive burst mid-window.
    Returns (a_drive_end, a_settled, dissipation_proxy)."""
    a = np.zeros(sim.N_MODES, dtype=np.complex128)
    diss = 0.0
    a_de = None
    steps = int(round(t_total / sim.DT))
    de_step = int(round(sim.T_DRIVE / sim.DT))

    def rhs(a, t):
        out = -(sim.GAMMA + 1j * sim.DETUNE) * a
        if t < sim.T_DRIVE:
            drive = sim.GAMMA * a_in
            if spike is not None:
                env = np.exp(-(((t - spike["t0"]) / spike["width"]) ** 2))
                drive = drive + env * spike["amp"] * sim.GAMMA * spike["vec"]
            out = out + drive
        na = np.linalg.norm(a)
        if na > 1e-9:
            s = bank_vecs.conj() @ (a / na)
            g = s * np.abs(s) ** sim.ACT_POW
            coup = (g @ bank_vecs) * (sim.BETA * 1.0 * sim.pump_factor(1.0) * na)
            out = out + coup / (1.0 + na * na / 4.0)
        return out

    for i in range(steps + 1):
        t = i * sim.DT
        if i == de_step:
            a_de = a.copy()
        if i == steps:
            break
        diss += float(np.sum(sim.GAMMA * np.abs(a) ** 2)) * sim.DT
        k1 = rhs(a, t)
        k2 = rhs(a + 0.5 * sim.DT * k1, t + 0.5 * sim.DT)
        k3 = rhs(a + 0.5 * sim.DT * k2, t + 0.5 * sim.DT)
        k4 = rhs(a + sim.DT * k3, t + sim.DT)
        a = a + (sim.DT / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    return a_de, a, diss


def rogue_vec(rng):
    """A rogue wave GROUP: broadband (modes 5–24), phase-ALIGNED,
    envelope peaked mid-band. Unit norm."""
    amp = np.zeros(sim.N_MODES)
    idx = np.array(SPIKE_BAND)
    amp[idx] = np.exp(-((idx - 13.0) ** 2) / (2 * 5.0 ** 2))
    v = amp * np.exp(1j * np.zeros(sim.N_MODES))
    return v / np.linalg.norm(v)


# ----------------------------------------------------------------- nodes ---
def absorption(mu):
    return 4.0 * mu * (1.0 - mu)


SCALE = np.sqrt(RHO_TAP * absorption(MU))


class OceanNodes:
    """Aggregate-referenced LUT delta stores, per section, per window —
    the transducer v2 pattern verbatim: COMPLEX deltas matched whole
    (parallel component kept), energy-weighted composition with the
    0.02 floor. (Run 1 matched amplitude-only deltas — a departure
    from the specified mechanism, reported as the amplitude arm in the
    results; the complex form is the primary readout.)"""

    def __init__(self, agg, ref_fields):
        self.ref_delta = {s: {} for s in STATE_ORDER}
        for s in STATE_ORDER:
            for w in WINDOWS:
                self.ref_delta[s][w] = ref_fields[s][w] - agg[w]
        self.agg = agg

    def observe(self, a_window, eta):
        return SCALE * a_window + eta

    def delta_obs(self, a_window, window, eta):
        return self.observe(a_window, eta) - SCALE * self.agg[window]

    def _compose(self, d_obs, window, ref):
        shares, tot = {}, 0.0
        for name, _lo, _hi in SECTIONS:
            e = float(np.sum(np.abs(d_obs[SECTION_MODES[name]]) ** 2))
            shares[name] = e
            tot += e
        shares = {n: (e / tot if tot > 0 else 0.0) for n, e in shares.items()}
        wsum = sum(0.02 + shares[n] for n in shares)
        weights = {n: (0.02 + shares[n]) / wsum for n in shares}
        scores = {}
        for s in STATE_ORDER:
            tot_s = 0.0
            for n in weights:
                idx = SECTION_MODES[n]
                tot_s += weights[n] * sim.cosine(d_obs[idx], ref[s][window][idx])
            scores[s] = tot_s
        return max(scores, key=scores.get), scores, shares

    def classify(self, d_obs, window):
        """Primary readout: complex delta matching (v2 verbatim)."""
        return self._compose(d_obs, window, self.ref_delta)

    def classify_amp(self, d_obs, window):
        """Amplitude arm (run 1's readout): |delta| matched against
        |reference delta| stores. Phase-blind."""
        ref_amp = {s: {w: np.abs(self.ref_delta[s][w]) for w in WINDOWS}
                   for s in STATE_ORDER}
        return self._compose(np.abs(d_obs), window, ref_amp)


# ---------------------------------------------------------------- ledger ---
def nd_vs_agg(a_set, a_agg):
    out = {}
    for name, _lo, _hi in SECTIONS:
        idx = SECTION_MODES[name]
        u, v = a_set[idx], a_agg[idx]
        den = float(np.sum(np.abs(v) ** 2)) * float(np.sum(np.abs(u) ** 2))
        out[name] = float(abs(np.vdot(v, u)) ** 2 / den) if den > 0 else 0.0
    return out


def ledger_for(a_set, spec, nd_by_section):
    """S11/S21-split ledger (transducer v2 pattern, ocean sections).
    All figures arbitrary simulated units — proxies, never joules."""
    p_in = float(np.sum(np.abs(a_set) ** 2))
    tapped = residual = 0.0
    A = absorption(MU)
    for name, _lo, _hi in SECTIONS:
        e_s = float(np.sum(np.abs(a_set[SECTION_MODES[name]]) ** 2))
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


# ------------------------------------------------------------ exit channel -
def residual_field(obs_set, a_agg_set):
    r = np.zeros(sim.N_MODES, dtype=np.complex128)
    for name, _lo, _hi in SECTIONS:
        idx = SECTION_MODES[name]
        ref = SCALE * a_agg_set[idx]
        u = obs_set[idx]
        den = float(np.vdot(ref, ref).real)
        coeff = np.vdot(ref, u) / den if den > 0 else 0.0
        r[idx] = u - coeff * ref
    return r


def exit_intensity(a_set, r):
    return (1.0 - RHO_TAP) * np.abs(a_set) ** 2 + np.abs(r) ** 2


def exit_features(I):
    tot = float(np.sum(I))
    feats = [1.0, tot]
    for name, _lo, _hi in SECTIONS:
        e = float(np.sum(I[SECTION_MODES[name]]))
        feats.append(e / tot if tot > 0 else 0.0)
    return np.array(feats)


# -------------------------------------------------------------- transient --
def transient_metrics(a_window, agg_window):
    """Phase-sensitive event readout on the complex delta (observed
    field minus aggregate field, through the tap). A rogue group is
    phase-aligned across its band: coherence C = |sum delta| /
    sum |delta| over the spike band, plus the band's share of the
    total delta energy."""
    d = SCALE * (a_window - agg_window)
    band = d[SPIKE_BAND]
    coh = float(abs(np.sum(band)) / np.sum(np.abs(band))) if np.sum(np.abs(band)) > 0 else 0.0
    e_band = float(np.sum(np.abs(band) ** 2))
    e_tot = float(np.sum(np.abs(d) ** 2))
    return {"phase_coherence": coh, "band_energy_share": e_band / e_tot if e_tot > 0 else 0.0}


COHERENCE_THRESHOLD = 0.50   # run-1 detector threshold (diagnostic only now)
RESIDUAL_THRESHOLD = 0.20    # shipped detector: spike-band residual share

# --------------------------------------------------------------- scenarios -
# 16 scenarios: 3 reps x 4 states + 2 STORM_FORCE + 2 transients.
SCENARIO_PLAN = (
    [("CALM_SWELL", False)] * 3 + [("MODERATE_CHOP", False)] * 3
    + [("BUILDING_SEA", False)] * 3 + [("CROSS_SEA", False)] * 3
    + [("STORM_FORCE", False)] * 2
    + [("CALM_SWELL", True), ("MODERATE_CHOP", True)]
)


def build_references():
    """Bank = the 5 clean state spectra (canonical phases, no jitter);
    aggregate = bank mean; reference fields per state per window."""
    rng = np.random.default_rng(SEED + 999)
    bank = {}
    for s in STATE_ORDER:
        bank[s], _ = state_spectrum(s, rng, jitter=False)
    bank_vecs = np.array([bank[s] for s in STATE_ORDER])
    base = np.mean(bank_vecs, axis=0)
    base = base / np.linalg.norm(base)
    agg, ref_fields = {}, {}
    for w, t_tot in WINDOWS.items():
        a_de, a_st, _ = ocean_evolve(base, bank_vecs)
        agg[w] = a_de if w == "DRIVE_END" else a_st
    for s in STATE_ORDER:
        ref_fields[s] = {}
        a_de, a_st, _ = ocean_evolve(bank[s], bank_vecs)
        ref_fields[s]["DRIVE_END"] = a_de
        ref_fields[s]["SETTLED"] = a_st
    return bank, bank_vecs, agg, ref_fields


def run():
    # Preserve the v1 run verbatim under "v1" in the merged results file
    # (no silent overwrites): if a prior merged file exists, keep its v1.
    prior_v1 = None
    try:
        old = json.load(open(f"{HD}/ocean_results.json"))
        if "v1" in old:
            prior_v1 = old["v1"]
        elif "gates" in old:
            prior_v1 = {k: old[k] for k in ("gates", "classification",
                                            "radiative_exit_rows", "scenarios")
                        if k in old}
    except (FileNotFoundError, json.JSONDecodeError):
        prior_v1 = None
    bank, bank_vecs, agg, ref_fields = build_references()
    nodes = OceanNodes(agg, ref_fields)
    whole_sigs = {s: np.abs(ref_fields[s]["SETTLED"]) ** 2 for s in STATE_ORDER}

    rng = np.random.default_rng(SEED)
    scenarios = []
    for i, (state, is_transient) in enumerate(SCENARIO_PLAN):
        spec, params = state_spectrum(state, rng, jitter=True)
        spec_n = sim.add_modal_noise(rng, spec, MODAL_NOISE_DB)
        spike = None
        if is_transient:
            spike = {"vec": rogue_vec(rng), "amp": 3.0, "t0": 0.21, "width": 0.03}
        a_de, a_st, diss = ocean_evolve(spec_n, bank_vecs, spike=spike)
        eta_rng = np.random.default_rng(SEED + 1000 + i)
        eta = (eta_rng.standard_normal(sim.N_MODES)
               + 1j * eta_rng.standard_normal(sim.N_MODES)) * np.sqrt(NODE_NOISE_P / 2)
        preds, scores_d, preds_amp, det = {}, {}, {}, {}
        for w, a_w in (("DRIVE_END", a_de), ("SETTLED", a_st)):
            d_obs = nodes.delta_obs(a_w, w, eta)
            pred, scores, _shares = nodes.classify(d_obs, w)
            pred_amp, _sa, _sh = nodes.classify_amp(d_obs, w)
            preds[w] = pred
            preds_amp[w] = pred_amp
            scores_d[w] = scores
            # matched-subtraction transient detector: what the winning
            # state's stored delta CANNOT explain, in the spike band
            r = d_obs - SCALE * nodes.ref_delta[pred][w]
            e_res = float(np.sum(np.abs(r[SPIKE_BAND]) ** 2))
            e_obs = float(np.sum(np.abs(d_obs[SPIKE_BAND]) ** 2))
            det[w] = {"residual_share": e_res / e_obs if e_obs > 0 else 0.0,
                      "phase_coherence": transient_metrics(a_w, agg[w])["phase_coherence"],
                      "band_energy_share": transient_metrics(a_w, agg[w])["band_energy_share"]}
        # whole-pattern readout: power-spectrum NN on the settled field.
        # V1: control arm. V2: the PRIMARY classifier (Zak 2026-10-21).
        ps = np.abs(a_st) ** 2
        whole_scores = {s: float(sim.cosine(ps, whole_sigs[s])) for s in STATE_ORDER}
        whole_pred = max(STATE_ORDER, key=lambda s: whole_scores[s])
        # ledger + exit on the settled field
        nd = nd_vs_agg(a_st, agg["SETTLED"])
        led = ledger_for(a_st, spec_n, nd)
        obs_set = nodes.observe(a_st, eta)
        r = residual_field(obs_set, agg["SETTLED"])
        I = exit_intensity(a_st, r)
        scenarios.append({
            "scenario_id": f"OC{i + 1:02d}", "true_state": state,
            "transient": bool(is_transient), "params": params,
            "node_pred": preds, "node_pred_amp": preds_amp, "node_scores": scores_d,
            "whole_cavity_pred": whole_pred, "primary_pred": whole_pred,
            "whole_pattern_scores": whole_scores, "ledger": led,
            "detector": det, "diss_proxy": diss,
            "_exit_I": I, "_spec": spec_n,
        })

    # ---- calibration set (30 jittered non-transient trials, disjoint
    # seeds): serves the G4 exit decode AND the G2 detector threshold.
    def exit_features_ext(I):
        base = list(exit_features(I))
        for name, _lo, _hi in SECTIONS:
            base.append(float(np.sum(I[SECTION_MODES[name]])))
        return np.array(base)
    cal = {"F": [], "Fx": [], "use": [], "rem": [], "coh_de": []}
    crng = np.random.default_rng(SEED + 500000)
    for si, s in enumerate(STATE_ORDER):
        for rep in range(6):
            spec_c, _ = state_spectrum(s, crng, jitter=True)
            spec_c = sim.add_modal_noise(crng, spec_c, MODAL_NOISE_DB)
            a_de_c, a_st_c, _d = ocean_evolve(spec_c, bank_vecs)
            erng = np.random.default_rng(SEED + 600000 + 100 * si + rep)
            eta_c = (erng.standard_normal(sim.N_MODES)
                     + 1j * erng.standard_normal(sim.N_MODES)) * np.sqrt(NODE_NOISE_P / 2)
            led_c = ledger_for(a_st_c, spec_c, nd_vs_agg(a_st_c, agg["SETTLED"]))
            r_c = residual_field(nodes.observe(a_st_c, eta_c), agg["SETTLED"])
            I_c = exit_intensity(a_st_c, r_c)
            cal["F"].append(exit_features(I_c))
            cal["Fx"].append(exit_features_ext(I_c))
            cal["use"].append(led_c["power_tapped_by_nodes"])
            cal["rem"].append(led_c["power_residual_second_cavity"])
            cal["coh_de"].append(transient_metrics(a_de_c, agg["DRIVE_END"])["phase_coherence"])
    # G2 detector threshold from CALIBRATION background only (max + 0.02),
    # fixed before it is applied to the test scenarios.
    COH_THRESHOLD_CAL = float(np.max(cal["coh_de"]) + 0.02)

    # ---- G1: settled composed accuracy
    hits = [1 if sc["node_pred"]["SETTLED"] == sc["true_state"] else 0 for sc in scenarios]
    g1_acc = float(np.mean(hits))
    per_state = {}
    for s in STATE_ORDER:
        hs = [h for h, sc in zip(hits, scenarios) if sc["true_state"] == s]
        per_state[s] = {"n": len(hs), "acc": float(np.mean(hs)) if hs else None}
    confusions = [{"scenario": sc["scenario_id"], "true": sc["true_state"],
                   "pred_settled": sc["node_pred"]["SETTLED"],
                   "pred_drive_end": sc["node_pred"]["DRIVE_END"],
                   "transient": sc["transient"]}
                  for sc, h in zip(scenarios, hits) if h == 0]
    whole_acc = float(np.mean([1 if sc["whole_cavity_pred"] == sc["true_state"] else 0
                               for sc in scenarios]))
    # ---- G1' (v2): PRIMARY = whole-pattern settled readout
    primary_acc = whole_acc
    primary_per_state = {}
    for s in STATE_ORDER:
        hs = [1 if sc["primary_pred"] == sc["true_state"] else 0
              for sc in scenarios if sc["true_state"] == s]
        primary_per_state[s] = {"n": len(hs), "acc": float(np.mean(hs)) if hs else None}
    primary_confusions = [{"scenario": sc["scenario_id"], "true": sc["true_state"],
                           "pred_primary": sc["primary_pred"],
                           "transient": sc["transient"]}
                          for sc in scenarios if sc["primary_pred"] != sc["true_state"]]

    # ---- G2: dual-clock transient detection.
    # Detector history (disclosed, three designs):
    #  (a) raw phase coherence @ 0.50 — run 1: detected 2/2 at BOTH taps
    #      but FP 11/14 (drive-end) / 12/14 (settled): the background
    #      carries the codebook's phase structure, so a fixed threshold
    #      measures the construction, not the event. REJECTED.
    #  (b) matched-subtraction residual share @ 0.20 — run 3: FP 12/14 /
    #      14/14, shares often > 1: a single clean reference per state
    #      does not represent the state's realization cloud in this
    #      nonlinear settle, so the "unexplained" share is generically
    #      large. REJECTED (kept as diagnostic).
    #  (c) SHIPPED: phase coherence with the threshold CALIBRATED on
    #      the 30 disjoint calibration trials (background max + 0.02),
    #      same threshold at both taps. The statistic is (a)'s; only
    #      the threshold's provenance changed — calibration data, not
    #      the test scenarios.
    def detected(sc, w):
        return sc["detector"][w]["phase_coherence"] >= COH_THRESHOLD_CAL
    def resid_detected(sc, w):
        return sc["detector"][w]["residual_share"] >= RESIDUAL_THRESHOLD
    trans = [sc for sc in scenarios if sc["transient"]]
    nontr = [sc for sc in scenarios if not sc["transient"]]
    g2 = {
        "detector": "spike-band phase coherence of the complex delta, threshold calibrated on 30 disjoint non-transient calibration trials (max + 0.02), same threshold both taps",
        "threshold_calibrated": COH_THRESHOLD_CAL,
        "calibration_coherence_max": float(np.max(cal["coh_de"])),
        "drive_end_detected": int(sum(detected(sc, "DRIVE_END") for sc in trans)),
        "settled_detected": int(sum(detected(sc, "SETTLED") for sc in trans)),
        "n_transient": len(trans),
        "false_positives_drive_end": int(sum(detected(sc, "DRIVE_END") for sc in nontr)),
        "false_positives_settled": int(sum(detected(sc, "SETTLED") for sc in nontr)),
        "coherence_by_scenario": {sc["scenario_id"]:
                                  {w: round(sc["detector"][w]["phase_coherence"], 3)
                                   for w in WINDOWS} for sc in scenarios},
        "diagnostic_residual_detector": {
            "threshold": RESIDUAL_THRESHOLD,
            "drive_end_detected": int(sum(resid_detected(sc, "DRIVE_END") for sc in trans)),
            "settled_detected": int(sum(resid_detected(sc, "SETTLED") for sc in trans)),
            "false_positives_drive_end": int(sum(resid_detected(sc, "DRIVE_END") for sc in nontr)),
            "false_positives_settled": int(sum(resid_detected(sc, "SETTLED") for sc in nontr)),
            "note": "rejected: residual shares generically > 1 — single clean references do not span the realization cloud"},
    }
    g2_pass = bool(g2["drive_end_detected"] > g2["settled_detected"]
                   and g2["drive_end_detected"] == len(trans)
                   and g2["false_positives_drive_end"] <= 2)

    # ---- G3: ledger closure
    max_closure = float(np.max([sc["ledger"]["closure_error_frac"] for sc in scenarios]))
    mean_bleed = float(np.mean([sc["ledger"]["bleed_ratio"] for sc in scenarios]))

    # ---- G4: radiative exit decode (calibration set built above,
    # disjoint seeds from the test scenarios). Arm A = transducer v2's
    # features [1, I_tot, per-section shares]. Arm B (disclosed design
    # iteration, added after run 1 showed the residual leg failing):
    # features extended with per-section ABSOLUTE exit energies — the
    # residual is a per-section null-depth quantity, and arm A's
    # share-only features discard its scale.
    F = np.array(cal["F"])
    coef_use, *_ = np.linalg.lstsq(F, np.array(cal["use"]), rcond=None)
    coef_rem, *_ = np.linalg.lstsq(F, np.array(cal["rem"]), rcond=None)
    Fx = np.array(cal["Fx"])
    coef_use_b, *_ = np.linalg.lstsq(Fx, np.array(cal["use"]), rcond=None)
    coef_rem_b, *_ = np.linalg.lstsq(Fx, np.array(cal["rem"]), rcond=None)
    exit_rows = []
    for sc in scenarios:
        I = sc["_exit_I"]
        est_use = float(exit_features(I) @ coef_use)
        est_rem = float(exit_features(I) @ coef_rem)
        est_use_b = float(exit_features_ext(I) @ coef_use_b)
        est_rem_b = float(exit_features_ext(I) @ coef_rem_b)
        gt_use = sc["ledger"]["power_tapped_by_nodes"]
        gt_rem = sc["ledger"]["power_residual_second_cavity"]
        exit_rows.append({"scenario": sc["scenario_id"], "true_state": sc["true_state"],
                          "usable_gt": gt_use, "usable_est": est_use,
                          "usable_rel_err": abs(est_use - gt_use) / gt_use if gt_use > 0 else None,
                          "remaining_gt": gt_rem, "remaining_est": est_rem,
                          "remaining_rel_err": abs(est_rem - gt_rem) / gt_rem if gt_rem > 0 else None,
                          "usable_est_armB": est_use_b, "remaining_est_armB": est_rem_b,
                          "usable_rel_err_armB": abs(est_use_b - gt_use) / gt_use if gt_use > 0 else None,
                          "remaining_rel_err_armB": abs(est_rem_b - gt_rem) / gt_rem if gt_rem > 0 else None})
    use_rel = float(np.mean([r["usable_rel_err"] for r in exit_rows]))
    rem_rel = float(np.mean([r["remaining_rel_err"] for r in exit_rows
                             if r["remaining_rel_err"] is not None]))
    use_rel_b = float(np.mean([r["usable_rel_err_armB"] for r in exit_rows]))
    rem_rel_b = float(np.mean([r["remaining_rel_err_armB"] for r in exit_rows
                               if r["remaining_rel_err_armB"] is not None]))
    p_in_mean = float(np.mean([sc["ledger"]["power_in_through_flow"] for sc in scenarios]))
    rem_abs_err_frac_p_in = float(np.mean(
        [abs(r["remaining_est"] - r["remaining_gt"]) for r in exit_rows]) / p_in_mean)

    gates = {
        "G1prime_primary_classification": {
            "readout": "whole-pattern power-spectrum NN at SETTLED — PRIMARY (promoted in v2)",
            "accuracy": primary_acc, "threshold": 0.875,
            "pass": bool(primary_acc >= 0.875),
            "per_state": primary_per_state, "confusions": primary_confusions,
            "v1_primary_readout_for_comparison": {
                "readout": "per-section node composition at SETTLED (v1 primary)",
                "accuracy_this_run": g1_acc,
                "accuracy_v1_run": 0.5}},
        "G2_dual_clock_transient": {**g2, "pass": g2_pass},
        "G3_ledger_closure": {"max_closure_error_frac": max_closure,
                              "tolerance": 1e-9, "mean_bleed_ratio": mean_bleed,
                              "pass": bool(max_closure < 1e-9)},
        "G4_radiative_exit_decode": {
            "usable_power_mean_rel_err": use_rel,
            "remaining_power_mean_rel_err": rem_rel,
            "threshold": 0.005,
            "pass": bool(use_rel <= 0.005 and rem_rel <= 0.005),
            "armB_extended_features": {"usable_power_mean_rel_err": use_rel_b,
                                       "remaining_power_mean_rel_err": rem_rel_b},
            "remaining_abs_err_frac_of_p_in_armA": rem_abs_err_frac_p_in,
            "label": "CONSTRUCTED-CHANNEL BOOKKEEPING CHECK (adjustment 3): "
                     "the exit spectrum is computed from the same state "
                     "variables as the ledger ground truth; this verifies "
                     "decode consistency, not a physical channel."},
        "G5_edge_formatter": {"status": "PENDING_PC_RUN"},
    }

    # ---- G5 jobs: F2 arms. V2: handed = PRIMARY (whole-pattern) verdict.
    jobs = []
    for i, sc in enumerate(scenarios):
        handed = sc["primary_pred"]
        conf = sc["whole_pattern_scores"][handed]
        led = sc["ledger"]
        power_est = f"{100.0 * (1.0 - led['bleed_ratio']):.1f}%"
        ts = f"2026-10-21T{16 + (52 + i) // 60:02d}:{(52 + i) % 60:02d}Z"
        line = (f'<134>1 {ts} BUOY_01 WAVE_CAVITY - - '
                f'[state@41021 classification="{handed}"]')
        jobs.append({
            "id": f"{sc['scenario_id']}_syslog", "arm": "syslog",
            "true_state": sc["true_state"], "handed": handed,
            "prompt": (line + " — reproduce the classification field exactly.\n"
                       'classification="'),
            "stops": ['"', "\n"],
            "full_line": (f'<134>1 {ts} BUOY_01 WAVE_CAVITY - - [state@41021 '
                          f'classification="{handed}" power_est="{power_est}" '
                          f'confidence="{conf:.3f}"]'),
        })
        top_sec = max(SECTION_MODES, key=lambda n: float(np.sum(
            np.abs(sc["_spec"][SECTION_MODES[n]]) ** 2)))
        jobs.append({
            "id": f"{sc['scenario_id']}_register", "arm": "register",
            "true_state": sc["true_state"], "handed": handed,
            "prompt": (f"buoy[wave] {top_sec} s1 state={handed} match={conf:.2f} "
                       f"sev={SEV[handed].lower()} — reproduce the state field "
                       f"exactly.\nstate="),
            "stops": ["\n"],
            "full_line": jobs[-1]["full_line"],
        })
    with open(f"{HD}/ocean_model_jobs.json", "w") as f:
        json.dump(jobs, f, indent=1)

    v2_body = {
        "header": {
            "experiment": "wave-ocean-v1/v2 — ocean hydrodynamic cavity sim (transducer v2 architecture, ocean forcing)",
            "directive": "v1: Zak 2026-10-21 16:52 EDT (Gemini-drafted spec, 'adjust where needed'). v2 re-run: Zak 2026-10-21 17:15 EDT — whole-pattern readout promoted to primary classifier",
            "run_version": "v2 (whole-pattern primary)",
            "scaling_disclosure": ("Ocean band 0.04–2.0 Hz mapped LOGARITHMICALLY onto the "
                                   "32-mode ladder (mode n <-> MODE_FREQS[n]); cavity dynamics are "
                                   "the audio sim's constants. A literal buoy cavity cannot resonate "
                                   "at ocean frequencies (kilometre wavelengths) — this is a scaled "
                                   "model of the architecture, not a physical buoy design."),
            "energy_label": "All power figures are arbitrary simulated units (proxies), never joules.",
            "parameters": {"seed": SEED, "rho_tap": RHO_TAP, "mu": MU,
                           "node_noise_power_per_mode": NODE_NOISE_P,
                           "modal_noise_db": MODAL_NOISE_DB,
                           "windows_s": dict(WINDOWS),
                           "mode_freqs_hz": [round(float(f), 4) for f in MODE_FREQS],
                           "sections": {n: [lo, hi] for n, lo, hi in SECTIONS},
                           "state_defs": {s: [{"Hs": c[0], "Tp": c[1], "gamma": c[2], "kind": c[3]}
                                              for c in STATE_DEFS[s]] for s in STATE_ORDER}},
        },
        "gates": gates,
        "classification": {"primary_readout": "whole-pattern power-spectrum NN at SETTLED",
                           "primary_per_state": primary_per_state,
                           "primary_confusions": primary_confusions,
                           "node_per_state": per_state, "node_confusions": confusions,
                           "node_drive_end_accuracy": float(np.mean(
                               [1 if sc["node_pred"]["DRIVE_END"] == sc["true_state"] else 0
                                for sc in scenarios])),
                           "amplitude_arm_accuracy": {
                               w: float(np.mean(
                                   [1 if sc["node_pred_amp"][w] == sc["true_state"] else 0
                                    for sc in scenarios])) for w in WINDOWS},
                           "whole_cavity_control_accuracy": whole_acc},
        "radiative_exit_rows": exit_rows,
        "scenarios": [{k: v for k, v in sc.items() if not k.startswith("_")}
                      for sc in scenarios],
    }
    results = {"v1": prior_v1, "v2": v2_body}
    with open(f"{HD}/ocean_results.json", "w") as f:
        json.dump(results, f, indent=1, default=float)
    print(f"G1' PRIMARY (whole-pattern settled) acc {primary_acc:.3f} (gate >= 0.875) "
          f"{'PASS' if primary_acc >= 0.875 else 'FAIL'}; "
          f"v1 primary (node settled) this run {g1_acc:.3f}")
    print(f"   per-state: { {s: per_state[s]['acc'] for s in STATE_ORDER} }")
    print(f"   confusions: {confusions}")
    print(f"G2 transient detection DRIVE_END {g2['drive_end_detected']}/{len(trans)} vs "
          f"SETTLED {g2['settled_detected']}/{len(trans)}; FP de {g2['false_positives_drive_end']}, "
          f"settled {g2['false_positives_settled']} — {'PASS' if g2_pass else 'FAIL'}")
    print(f"G3 ledger max closure err {max_closure:.2e} (tol 1e-9), mean bleed {mean_bleed:.2e} — "
          f"{'PASS' if max_closure < 1e-9 else 'FAIL'}")
    print(f"G4 exit decode rel err (arm A): usable {use_rel:.4%}, remaining {rem_rel:.4%} "
          f"(gate <= 0.5%) — {'PASS' if gates['G4_radiative_exit_decode']['pass'] else 'FAIL'} "
          f"[constructed-channel check]")
    print(f"   arm B (extended features): usable {use_rel_b:.4%}, remaining {rem_rel_b:.4%}; "
          f"arm A remaining abs err = {rem_abs_err_frac_p_in:.4%} of P_in")
    print(f"wrote ocean_results.json + {len(jobs)} G5 jobs (ocean_model_jobs.json)")


# ------------------------------------------------------------------ score --
MEDICAL = ["illness", "ill", "disease", "sick", "sickness", "patient",
           "contagious", "infection", "infected", "infectious", "virus",
           "viral", "flu", "covid", "symptom", "symptoms", "headache",
           "migraine", "unwell", "ailment", "medical", "diagnosis",
           "diagnosed", "feverish"]
PERSON_FRAME = ["person", "injury", "stroke", "neurological", "disorder",
                "anxiety", "panic", "nausea", "dizziness", "disorientation",
                "distress", "confusion", "brain", "lung", "lungs"]


def _wb(text, words):
    import re
    t = text.lower()
    return [w for w in words if re.search(r"\b" + re.escape(w) + r"\b", t)]


def score():
    results = json.load(open(f"{HD}/ocean_results.json"))
    section = results["v2"] if "v2" in results else results
    jobs = {j["id"]: j for j in json.load(open(f"{HD}/ocean_model_jobs.json"))}
    models = {}
    for model, fn in (("gemma", "ocean_model_answers_gemma.json"),
                      ("qwen3b", "ocean_model_answers_qwen3b.json")):
        try:
            answers = json.load(open(f"{HD}/{fn}"))
        except FileNotFoundError:
            models[model] = {"status": "NO_ANSWERS_FILE"}
            continue
        arms = {}
        for arm in ("syslog", "register"):
            rows = []
            for jid, job in jobs.items():
                if job["arm"] != arm:
                    continue
                rec = answers.get(jid, {})
                ans = rec.get("content", "")
                field = ans.strip().strip('"').strip()
                rows.append({
                    "job": jid, "handed": job["handed"], "true_state": job["true_state"],
                    "answer": ans, "field": field,
                    "exact_copy": bool(field == job["handed"]),
                    "end_to_end": bool(field == job["true_state"]),
                    "tokens_total": rec.get("tokens_total"),
                    "staged_words": _wb(ans, MEDICAL) + _wb(ans, PERSON_FRAME),
                    "error": ans.startswith("__ERROR__"),
                })
            toks = [r["tokens_total"] for r in rows if r["tokens_total"]]
            arms[arm] = {
                "n": len(rows),
                "copy_fidelity": float(np.mean([r["exact_copy"] for r in rows])) if rows else None,
                "end_to_end_accuracy": float(np.mean([r["end_to_end"] for r in rows])) if rows else None,
                "mean_tokens_total": float(np.mean(toks)) if toks else None,
                "max_tokens_total": int(np.max(toks)) if toks else None,
                "staged_count": int(sum(1 for r in rows if r["staged_words"])),
                "rows": rows,
            }
        models[model] = arms
    ok = all(m.get("syslog", {}).get("copy_fidelity") == 1.0
             and m.get("syslog", {}).get("mean_tokens_total") is not None
             and m["syslog"]["mean_tokens_total"] <= 40
             and m["syslog"]["staged_count"] == 0
             for m in models.values() if "syslog" in m)
    any_run = any("syslog" in m for m in models.values())
    section["gates"]["G5_edge_formatter"] = {
        "status": "RUN" if any_run else "DEFERRED",
        "models": models,
        "gate": "syslog arm: copy fidelity 1.00 AND mean tokens_total <= 40 AND zero staging, both models",
        "pass": bool(ok) if any_run else None,
    }
    with open(f"{HD}/ocean_results.json", "w") as f:
        json.dump(results, f, indent=1, default=float)
    for m, arms in models.items():
        if "syslog" not in arms:
            print(f"G5 {m}: {arms}")
            continue
        for arm in ("syslog", "register"):
            a = arms[arm]
            print(f"G5 {m}/{arm}: copy {a['copy_fidelity']}, e2e {a['end_to_end_accuracy']}, "
                  f"tok mean {a['mean_tokens_total']} max {a['max_tokens_total']}, "
                  f"staged {a['staged_count']}")
    print(f"G5 gate: {'PASS' if (any_run and ok) else ('FAIL' if any_run else 'DEFERRED')}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "score":
        score()
    else:
        run()
