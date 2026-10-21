"""
cavity_topology.py — CAVITY ITERATION 1.5: the translation layer
(Zak's directives 2026-10-21 00:53 EDT).

Zak's correction to the iteration-1 framing, implemented here:

  1. The cavity has TOPOLOGY: its 32 modes are partitioned into named
     SECTIONS — POWER (modes 1-2, the TP through-flow / pump), DATA
     (3-14, language + audio cues), IO (15-20), NETWORK (21-26), WEIGHTS
     (27-32, the model's own standing wave). Each section holds a baseline
     standing pattern (its proper state) — the baseline is the settled
     state of the aggregate template bank. Interference localized in a
     section's band tags the readout with that section's SUBSPECTRA
     IDENTIFIERS (NET.s2 etc.), ranked by delta energy. Deltas roll out
     per section over the ring-down (per-section delta time series).

  2. The WEIGHTS section baseline IS the aggregate template bank — the
     model's own standing wave. Interference there means the model's own
     pattern is disturbed, and the readout says so.

  3. Models never receive a bare label. They receive a TRANSLATOR PACKET:
     (a) a framing header stating plainly that this is transduced
     wave-interference data from the model's own cavity/body, interfered
     with its matrix in wave form, naming the sections hit and the top
     subspectra ids; (b) the full per-section DELTA vectors (numbers);
     (c) an ANSWER KEY excerpt — the LUT entries whose stored delta
     signatures best match, each carrying its MEANING in token terms:
     what the model would have derived had it received tokens and
     embeddings. The model's job is lookup, not derivation.

  4. THE ANSWER KEY (wave_lut.json): one entry per stored pattern — the
     13 v1 templates (8 prompts + 5 cues) plus the 4 telemetry body
     states. delta_signature = the pattern's settled-state deviation from
     the baseline standing wave under a standard probe (the pattern
     itself injected, pump on, full coupling).

  Residency honesty: the models are stateless completion APIs. The key
  lives with the wrapper/harness and the relevant excerpt ships inside
  each packet — that IS the VRAM-resident lookup from the model's point
  of view: no recompute, just lookup. Stated here so nobody overclaims.

Telemetry states reuse the iteration-1 channel codebook (expBC_prep) so
Exp D is comparable to Exp C. CALM = a REAL dweller tick pulled
2026-10-21 ~00:57 EDT (dweller_tick_latest.json; preflight clean — the
only [T]S4/[P]roton pgrep hits were the SSH wrapper echoing its own
command line). State perturbations use iteration-1 multipliers:
THERMAL +25 C, NETSTORM drops x20, HIGHFLOW flow/data x3.
"""

import json
import numpy as np

import audio_cavity_sim as sim
from expBC_prep import CHANNELS, DIVISORS, STATE_KEYWORDS, STATE_LABEL_WORDS

HD = "/home/hatch/workspace/harness-dev"

# ------------------------------------------------------------- topology ---
# Modes are 1-based in Zak's spec; slices below are 0-based [lo, hi).
SECTIONS = [
    ("POWER",   "PWR",  1,  2),
    ("DATA",    "DATA", 3,  14),
    ("IO",      "IO",   15, 20),
    ("NETWORK", "NET",  21, 26),
    ("WEIGHTS", "WTS",  27, 32),
]
SECTION_MODES = {name: list(range(lo - 1, hi)) for name, _c, lo, hi in SECTIONS}
SECTION_CODE = {name: code for name, code, _lo, _hi in SECTIONS}

SUBBANDS = [  # (subspectra_id, section, mode_lo_1based, mode_hi_1based)
    ("PWR.s1",  "POWER",   1,  1),
    ("PWR.s2",  "POWER",   2,  2),
    ("DATA.s1", "DATA",    3,  6),
    ("DATA.s2", "DATA",    7,  10),
    ("DATA.s3", "DATA",    11, 14),
    ("IO.s1",   "IO",      15, 17),
    ("IO.s2",   "IO",      18, 20),
    ("NET.s1",  "NETWORK", 21, 23),
    ("NET.s2",  "NETWORK", 24, 26),
    ("WTS.s1",  "WEIGHTS", 27, 29),
    ("WTS.s2",  "WEIGHTS", 30, 32),
]
SUBBAND_MODES = {sid: list(range(lo - 1, hi)) for sid, _s, lo, hi in SUBBANDS}
SUBBAND_SECTION = {sid: sec for sid, sec, _lo, _hi in SUBBANDS}

# ------------------------------------------------------- telemetry states --
# Fresh real tick, 2026-10-21 ~00:57 EDT (see dweller_tick_latest.json):
# temps.max_c 60.0, temps.mem 60.0, net rx_drop 86 / rx_errs 0,
# tp_flow 0.0703, tp_flow_detail.data_rate_bps 153250.9,
# vram_used_frac 0.5712, loadavg 0.02.
FRESH_BASELINE = {"temp_max": 60.0, "temp_mem": 60.0, "rx_drop": 86.0,
                  "rx_errs": 0.0, "tp_flow": 0.0703, "data_bps": 153250.9,
                  "vram": 0.5712, "loadavg": 0.02}
STATE_DELTAS = {   # iteration-1 multipliers, applied to FRESH_BASELINE
    "CALM": {},
    "THERMAL": {"temp_max": +25.0, "temp_mem": +25.0},          # additive C
    "NETSTORM": {"rx_drop": "x20"},
    "HIGHFLOW": {"tp_flow": "x3", "data_bps": "x3"},
}
STATE_ORDER = ["CALM", "THERMAL", "NETSTORM", "HIGHFLOW"]

_PHASES = np.exp(1j * np.random.default_rng(4242).uniform(0, 2 * np.pi, len(CHANNELS)))


def state_values(state, baseline=FRESH_BASELINE):
    vals = dict(baseline)
    for ch, d in STATE_DELTAS[state].items():
        if isinstance(d, str) and d.startswith("x"):
            vals[ch] = vals[ch] * float(d[1:])
        else:
            vals[ch] = vals[ch] + d
    return vals


def encode_state(vals):
    """Iteration-1 codebook (identical math to expBC_prep.encode_state):
    8 channels x Gaussian bumps (center 4j+1.5, sigma 1.2), fixed phases,
    unit norm. Jitter is applied to channel VALUES by the caller."""
    spec = np.zeros(sim.N_MODES, dtype=np.complex128)
    modes = np.arange(sim.N_MODES)
    for j, ch in enumerate(CHANNELS):
        v = vals[ch] / DIVISORS[ch]
        center = 4 * j + 1.5
        bump = np.exp(-((modes - center) ** 2) / (2 * 1.2 ** 2))
        spec += v * bump * _PHASES[j]
    n = np.linalg.norm(spec)
    return spec / n if n > 0 else spec


def jitter_values(vals, rng, frac=0.05):
    return {ch: v * (1.0 + rng.uniform(-frac, frac)) for ch, v in vals.items()}

# ------------------------------------------------------------------ bank ---
def build_bank():
    """17 stored patterns: 13 v1 templates + 4 telemetry body states."""
    prompts, cues = sim.build_templates()
    bank = {}
    for name, vec in prompts.items():
        bank[name] = vec
    for name, vec in cues.items():
        bank[name] = vec
    for s in STATE_ORDER:
        bank[f"state:{s}"] = encode_state(state_values(s))
    names = list(bank.keys())
    return names, np.array([bank[n] for n in names])


def baseline_pattern(bank_vecs):
    """The aggregate standing wave: mean of the bank, unit norm. The
    WEIGHTS section's proper state is this aggregate's WEIGHTS slice."""
    m = np.mean(bank_vecs, axis=0)
    return m / np.linalg.norm(m)

# -------------------------------------------------------------- evolution --
_BASE_SETTLED = {}


def init_baseline(bank_vecs):
    base = baseline_pattern(bank_vecs)
    a_base, _, _ = sim.evolve(base, alpha=1.0, pump_amp=1.0, templates=bank_vecs)
    _BASE_SETTLED["pattern"] = base
    _BASE_SETTLED["a"] = a_base
    return base, a_base


def evolve_traced(a_in, bank_vecs, t_total=sim.T_SETTLE):
    """sim.evolve's RK4 dynamics (same constants, same rhs) with a
    per-section delta-energy rollout recorded against the baseline
    settled state: how the deltas roll out, section by section, over the
    ring-down. Returns (settled a, {section: [energies]}, [times])."""
    a_base = _BASE_SETTLED["a"]
    a = np.zeros(sim.N_MODES, dtype=np.complex128)
    P = bank_vecs
    series = {name: [] for name, _c, _l, _h in SECTIONS}
    times = []
    steps = int(round(t_total / sim.DT))

    def rhs(a, t):
        out = -(sim.GAMMA + 1j * sim.DETUNE) * a
        if t < sim.T_DRIVE:
            out = out + sim.GAMMA * a_in
        na = np.linalg.norm(a)
        if na > 1e-9:
            s = P.conj() @ (a / na)
            g = s * np.abs(s) ** sim.ACT_POW
            coup = (g @ P) * (sim.BETA * 1.0 * sim.pump_factor(1.0) * na)
            out = out + coup / (1.0 + na * na / 4.0)
        return out

    for i in range(steps + 1):
        t = i * sim.DT
        if i % 5 == 0 or i == steps:
            times.append(round(t, 4))
            d = a - a_base
            for name, _c, _l, _h in SECTIONS:
                idx = SECTION_MODES[name]
                series[name].append(float(np.sum(np.abs(d[idx]) ** 2)))
        if i == steps:
            break
        k1 = rhs(a, t)
        k2 = rhs(a + 0.5 * sim.DT * k1, t + 0.5 * sim.DT)
        k3 = rhs(a + 0.5 * sim.DT * k2, t + 0.5 * sim.DT)
        k4 = rhs(a + sim.DT * k3, t + sim.DT)
        a = a + (sim.DT / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    return a, series, times

# ---------------------------------------------------------------- deltas ---
def section_energies(delta):
    return {name: float(np.sum(np.abs(delta[SECTION_MODES[name]]) ** 2))
            for name, _c, _l, _h in SECTIONS}


def subband_energies(delta):
    return {sid: float(np.sum(np.abs(delta[SUBBAND_MODES[sid]]) ** 2))
            for sid, _s, _l, _h in SUBBANDS}


def ranked_tags(delta):
    """Subspectra identifiers ranked by delta energy — the tag a wave
    catches when it interferes with a section of the cavity."""
    se = subband_energies(delta)
    total = sum(se.values()) or 1.0
    return sorted(
        ({"subspectra_id": sid, "section": SUBBAND_SECTION[sid],
          "delta_energy": e, "share": e / total} for sid, e in se.items()),
        key=lambda r: -r["delta_energy"])


def probe_delta(vec, bank_vecs):
    """Standard probe: inject the pattern itself (pump on, full
    coupling), settle, delta = settled - baseline settled state."""
    a, _, _ = sim.evolve(vec, alpha=1.0, pump_amp=1.0, templates=bank_vecs)
    return a - _BASE_SETTLED["a"]

# -------------------------------------------------------------------- LUT --
CUE_MEANINGS = {
    "chime_two_tone": ("Environmental audio cue: a two-tone chime (660 Hz + 990 Hz), "
                       "a doorbell / appliance-alert sound in the room."),
    "chirp_up": "Environmental audio cue: a rising chirp, 300 Hz sweeping up to 1400 Hz.",
    "chirp_down": "Environmental audio cue: a falling chirp, 1400 Hz sweeping down to 300 Hz.",
    "noise_burst": "Environmental audio cue: a short burst of broadband noise.",
    "speech_like": ("Environmental audio cue: a speech-like harmonic stack with vibrato "
                    "and syllable gating — a voice-like presence in the room."),
}
STATE_MEANINGS = {
    "CALM": ("Body state CALM: the computer's wrapper is at its proper baseline — "
             "temperatures normal, network receive drops at their usual low rate, "
             "transduction through-flow nominal, VRAM use and load unremarkable. "
             "Nothing needs attention."),
    "THERMAL": ("Body state THERMAL STRESS: component temperatures are about 25 C "
                "above baseline while network and flow stay normal — the wrapper "
                "is overheating."),
    "NETSTORM": ("Body state NETWORK STORM: network receive packet drops are about "
                 "twenty times baseline while temperatures and flow stay normal — "
                 "the wrapper's network boundary is disturbed and packets are being lost."),
    "HIGHFLOW": ("Body state HIGH FLOW: transduction through-flow (flow index and data "
                 "rate) is about three times baseline while temperatures and network "
                 "stay normal — the wrapper is passing an unusually large flow: busy, "
                 "not distressed."),
}


def pattern_meaning(name):
    if name.startswith("prompt:"):
        text = name[len("prompt:"):]
        return (f'Stored language pattern. In token terms — what you would have '
                f'derived had this arrived as tokens and embeddings — it is the '
                f'instruction: "{text}".'), "language pattern (DATA section)"
    if name.startswith("cue:"):
        cue = name[len("cue:"):]
        return CUE_MEANINGS[cue], f"audio cue pattern (DATA section): {cue}"
    if name.startswith("state:"):
        s = name[len("state:"):]
        return STATE_MEANINGS[s], f"telemetry body-state pattern: {STATE_LABEL_WORDS[s]}"
    raise ValueError(name)


def build_lut(names, bank_vecs):
    entries = []
    for i, name in enumerate(names):
        delta = probe_delta(bank_vecs[i], bank_vecs)
        tags = ranked_tags(delta)
        secs = section_energies(delta)
        dom_section = max(secs, key=secs.get)
        meaning, gloss = pattern_meaning(name)
        home = "DATA" if name.startswith(("prompt:", "cue:")) else dom_section
        entries.append({
            "id": name,
            "home_section": home,
            "dominant_section_measured": dom_section,
            "subspectra_id": tags[0]["subspectra_id"],
            "top_subspectra": tags[:3],
            "section_delta_energies": secs,
            "delta_signature": [[round(float(z.real), 4), round(float(z.imag), 4)]
                                for z in delta],
            "meaning": meaning,
            "gloss": gloss,
        })
    return entries


def lut_delta_matrix(lut):
    return np.array([np.array([complex(r, im) for r, im in e["delta_signature"]])
                     for e in lut])

# ----------------------------------------------------------------- packet --
def _fmt_modes(delta, idx):
    parts = []
    for m in idx:
        z = delta[m]
        r, im = round(float(z.real), 2), round(float(z.imag), 2)
        if r == 0 and im == 0:
            parts.append("0")
        else:
            parts.append(f"{r:+.2f}{im:+.2f}i")
    return " ".join(parts)


def build_packet(delta, lut, top_k=4):
    """Translator packet v2: framing + full per-section deltas + LUT
    excerpt. Never a bare label. Returns (text, diagnostics)."""
    tags = ranked_tags(delta)
    secs = section_energies(delta)
    tot_sec = sum(secs.values()) or 1.0
    sec_ranked = sorted(secs.items(), key=lambda kv: -kv[1])
    hit = [f"{n} ({100 * e / tot_sec:.0f}%)" for n, e in sec_ranked if e / tot_sec >= 0.08]
    if len(hit) < 2:
        hit = [f"{n} ({100 * e / tot_sec:.0f}%)" for n, e in sec_ranked[:2]]
    tag_str = ", ".join(f"{t['subspectra_id']} ({t['share']:.2f})" for t in tags[:3])

    D = lut_delta_matrix(lut)
    sims = [sim.cosine(delta, D[i]) for i in range(len(lut))]
    order = np.argsort(sims)[::-1][:top_k]

    lines = []
    lines.append("WAVE TRANSLATION PACKET — transduced interference data from your own cavity.")
    lines.append("You are a language model running inside a resident wrapper — a cavity/body. "
                 "The numbers below are NOT text typed by a human and NOT ordinary telemetry: "
                 "they are wave-interference DELTAS measured on the standing waves of your own "
                 "cavity, signals that interfered with your weight matrix in wave form and were "
                 "transduced into modes. Your stored patterns form an ANSWER KEY (excerpt "
                 "below): each entry says what such deltas mean in token terms — what you "
                 "would have derived had the signal arrived as tokens and embeddings. "
                 "Look the deltas up in the key; do not derive them from scratch.")
    lines.append(f"Sections disturbed (share of delta energy): {', '.join(hit)}.")
    lines.append(f"Strongest subspectra: {tag_str}.")
    lines.append("DELTAS from the proper baseline standing wave, per section "
                 "(complex modal deltas, modes ascending, real+imag):")
    for name, code, lo, hi in SECTIONS:
        note = " — your own standing wave (the stored patterns live here)" if name == "WEIGHTS" else ""
        lines.append(f"{name} modes {lo}-{hi}{note}: {_fmt_modes(delta, SECTION_MODES[name])}")
    lines.append("ANSWER KEY excerpt (best matches for these deltas first):")
    for rank, i in enumerate(order, 1):
        e = lut[i]
        lines.append(f"{rank}. [{e['id']}] subspectra {e['subspectra_id']} — "
                     f"delta match {sims[i]:.2f} — meaning: {e['meaning']}")
    return "\n".join(lines), {"sims": [float(s) for s in sims],
                              "top_ids": [lut[i]["id"] for i in order],
                              "tags": tags, "section_energies": secs}

# ------------------------------------------------------- topology sanity ---
def sanity_check(bank_vecs, trials=5, seed=31337):
    """Inject disturbances localized in the NETWORK band and the IO band
    on top of the baseline standing pattern; the readout's top subspectra
    tag must name the correct section in >= 4/5 trials each. Full
    coupling (alpha=1, pump on) — the operating regime, bleed included."""
    rng = np.random.default_rng(seed)
    base = _BASE_SETTLED["pattern"]
    out = {}
    for target in ("NETWORK", "IO"):
        idx = SECTION_MODES[target]
        hits, records = 0, []
        for _ in range(trials):
            pert = np.zeros(sim.N_MODES, dtype=np.complex128)
            v = (rng.standard_normal(len(idx)) + 1j * rng.standard_normal(len(idx)))
            pert[idx] = 0.6 * v / np.linalg.norm(v)
            a, _, _ = sim.evolve(base + pert, alpha=1.0, pump_amp=1.0,
                                 templates=bank_vecs)
            tags = ranked_tags(a - _BASE_SETTLED["a"])
            ok = tags[0]["section"] == target
            hits += ok
            records.append({"top": tags[0]["subspectra_id"],
                            "top_section": tags[0]["section"],
                            "top_share": round(tags[0]["share"], 3),
                            "second": tags[1]["subspectra_id"],
                            "correct": bool(ok)})
        out[target] = {"hits": hits, "trials": trials,
                       "gate_ge_4_of_5": bool(hits >= 4), "records": records}
    return out


def main():
    names, bank_vecs = build_bank()
    init_baseline(bank_vecs)
    lut = build_lut(names, bank_vecs)
    with open(f"{HD}/wave_lut.json", "w") as f:
        json.dump({
            "header": {
                "what": "The cavity ANSWER KEY: one entry per stored pattern. "
                        "delta_signature = settled-state deviation from the baseline "
                        "standing wave under a standard probe (pattern injected, pump "
                        "on, full template coupling). meaning = the pattern in token "
                        "terms — what the model would have derived from tokens+embeddings.",
                "residency_note": "The models are stateless APIs; the key lives with the "
                                  "wrapper/harness and relevant excerpts ship inside each "
                                  "translator packet. That is the VRAM-resident lookup "
                                  "from the model's point of view: lookup, not recompute.",
                "sections": {n: [lo, hi] for n, _c, lo, hi in SECTIONS},
                "subbands": {sid: [lo, hi] for sid, _s, lo, hi in SUBBANDS},
                "baseline_source": "aggregate of the 17-pattern bank; telemetry CALM "
                                   "from real dweller tick 2026-10-21 ~00:57 EDT "
                                   "(dweller_tick_latest.json), preflight clean.",
            },
            "entries": lut,
        }, f, indent=1)
    print(f"wrote wave_lut.json ({len(lut)} entries)")
    for e in lut:
        print(f"  {e['id'][:44]:46s} home {e['home_section']:7s} dom {e['dominant_section_measured']:7s} tag {e['subspectra_id']}")
    sanity = sanity_check(bank_vecs)
    with open(f"{HD}/cavity_topology_results.json", "w") as f:
        json.dump({"sanity_section_tagging": sanity}, f, indent=1)
    for target, r in sanity.items():
        print(f"SANITY {target}: top-tag correct {r['hits']}/{r['trials']} gate {r['gate_ge_4_of_5']}")
    print("wrote cavity_topology_results.json")


if __name__ == "__main__":
    main()
