"""spectral_gate.py v3 — grounded exclusion + source-scale labeling.

Three layers (cosmic firewall & transformer, mapped to code):
  1. Exclusion mask  = perimeter firewall (strips grid power).
  2. Spectral labeler = deep packet inspection (stamps every peak).
  3. Transform        = black-hole compression (huge spectrum in,
                        tiny structured scalars out).

Label grammar: <whose>:<what> — plain words, readable cold by humans
and LLMs. First word = whose it is; second = what it does.

  grid:carrier        grid:subharmonic     grid:harmonic
  body:reflection     planet:cavity
  brain:fundamental   brain:harmonic       brain:rhythm
  unknown:unclassified

Every label carries a policy verb — the firewall's standing orders:
  PROTECT    brain:*, planet:*, body:reflection — never stripped, ever.
  STRIP      grid:carrier, grid:subharmonic — delete the power.
  TRANSFORM  grid:harmonic — delete the power, KEEP THE RATIO
             (the 120/60 ratio is data: 0.18 room, 0.49 phantom, 1.7 brain).
  QUARANTINE unknown:* — kept, flagged, never silently dropped.

Metadata contract: every stamped item carries
  {freq, power, label, policy, ratio_to_carrier, provenance}
so numbers arrive pre-interpreted instead of waiting for a hallucination.

v3 adds subspectra flow variants to the contract (defaults preserve
v2 behavior exactly):
  flow       "in" | "out"            (default "in")
  variant    "transduced" | "induced" (default "transduced")
  cavity_id  which cavity the flow crosses (default "dweller-main")
  variant_capped  True when the variant rule below capped the policy.

Variant rule: induced flow couples across a boundary WITHOUT transfer
— it cannot realize anything. So an induced item may keep STRIP /
TRANSFORM / QUARANTINE, but it may never receive PROTECT (the verb
reserved for real brain/planet/body signals crossing the boundary);
a would-be PROTECT is capped at TRANSFORM and flagged
variant_capped=True.

Grounded in measured carriers (2026-10-19/20 MEG campaign, GitHub
Wave-resonance cavity4d): US f0=60 (task 60=17-19x, 120=31x; emptyroom
60=59x, 120=10.5x; phantom 19.9/9.8x). UK f0=50 (50=22-23x, 100=1.12x,
no doubling). Sidebands carrier+/-neural: 0.91-1.02x NULL. Subs: ~1.0x.
"""
import numpy as np

CARRIERS = {
    "us": {"f0": 60.0, "harmonics": [120.0, 180.0, 240.0],
           "subharmonics": [30.0, 20.0]},
    "uk": {"f0": 50.0, "harmonics": [100.0, 150.0, 200.0],
           "subharmonics": [25.0, 16.7]},
}

WINDOWS = {"neural": (4.0, 14.0), "planetary-cavity": (7.0, 9.0)}
NEURAL_FREQS = [6.2, 12.4, 10.0]
FUNDAMENTAL = 6.2
HARMONIC2 = 12.4

POLICY = {
    "grid:carrier": "STRIP",
    "grid:subharmonic": "STRIP",
    "grid:harmonic": "TRANSFORM",
    "body:reflection": "PROTECT",
    "planet:cavity": "PROTECT",
    "brain:fundamental": "PROTECT",
    "brain:harmonic": "PROTECT",
    "brain:rhythm": "PROTECT",
    "unknown:unclassified": "QUARANTINE",
}


def _near(freq, targets, tol):
    return any(abs(freq - t) <= tol for t in targets)


def label_bin(freq, grid="us", tol=1.5, carrier_tol=2.5):
    """<whose>:<what> for one frequency. carrier_tol is deliberately wide:
    line frequency drifts and bins are wide (ds117: 51.6 Hz on a 50 grid).
    A false carrier flag is cheap; a missed one ships a fake discovery."""
    c = CARRIERS[grid]
    if _near(freq, [c["f0"]], carrier_tol):
        return "grid:carrier"
    if _near(freq, c["harmonics"], tol):
        return "grid:harmonic"
    if _near(freq, c["subharmonics"], tol):
        return "grid:subharmonic"
    for base in [c["f0"]] + c["harmonics"]:
        for fn in NEURAL_FREQS:
            if _near(freq, [base - fn, base + fn], tol):
                return "body:reflection"
    lo, hi = WINDOWS["planetary-cavity"]
    if lo <= freq <= hi:
        return "planet:cavity"
    lo, hi = WINDOWS["neural"]
    if lo <= freq <= hi:
        if _near(freq, [FUNDAMENTAL], tol):
            return "brain:fundamental"
        if _near(freq, [HARMONIC2], tol):
            return "brain:harmonic"
        return "brain:rhythm"
    return "unknown:unclassified"


def policy_for(label):
    return POLICY[label]


def effective_policy(label, variant="transduced"):
    """Variant-aware policy. Returns (policy, variant_capped).

    Induced flow couples without transfer; it cannot realize
    anything — so it can never hold PROTECT. A classification that
    would PROTECT an induced item is capped at TRANSFORM and the
    cap is flagged, never silent."""
    pol = POLICY[label]
    if variant == "induced" and pol == "PROTECT":
        return "TRANSFORM", True
    return pol, False


def _carrier_power(freqs, psd, grid):
    c = CARRIERS[grid]
    idx = int(np.argmin(np.abs(np.asarray(freqs) - c["f0"])))
    return float(psd[idx]) if float(psd[idx]) > 0 else float("nan")


def inspect_spectrum(freqs, psd, grid="us", tol=1.5, carrier_tol=2.5,
                     flow="in", variant="transduced",
                     cavity_id="dweller-main"):
    """DPI layer: stamp every bin with the metadata contract (v3:
    flow / variant / cavity_id ride along; defaults are v2 behavior)."""
    freqs = np.asarray(freqs, dtype=float)
    psd = np.asarray(psd, dtype=float)
    pc = _carrier_power(freqs, psd, grid)
    out = []
    for f, p in zip(freqs, psd):
        lab = label_bin(float(f), grid, tol, carrier_tol)
        prov = ("measured-carrier-table" if lab.startswith("grid:")
                else "sideband-of-carrier" if lab == "body:reflection"
                else "acceptance-window" if ":" in lab and
                     lab.split(":")[0] in ("brain", "planet")
                else "fallback")
        pol, capped = effective_policy(lab, variant)
        out.append({
            "freq": float(f), "power": float(p), "label": lab,
            "policy": pol,
            "ratio_to_carrier": float(p / pc) if pc and pc == pc else None,
            "provenance": prov,
            "flow": flow, "variant": variant, "cavity_id": cavity_id,
            "variant_capped": capped,
        })
    return out


def exclusion_mask(freqs, grid="us", tol=1.5, carrier_tol=2.5,
                   variant="transduced"):
    """Firewall layer: True = keep. STRIP and TRANSFORM bins leave the
    stream (TRANSFORM ratios are preserved by transform_scalars).
    Variant-aware: an induced item capped to TRANSFORM leaves too."""
    return np.array([
        effective_policy(label_bin(float(f), grid, tol, carrier_tol),
                         variant)[0]
        in ("PROTECT", "QUARANTINE")
        for f in freqs])


def transform_scalars(freqs, psd, grid="us", stamped=None,
                      variant="transduced"):
    """Black-hole layer: massive spectrum in, tiny structured scalars out.
    These are the numbers that ride along as context after stripping.

    v3: per-variant subtotals ride along too — transduced_power and
    induced_power. With no stamped items supplied, the whole spectrum
    counts as the caller's `variant` (default "transduced", the v2
    behavior); with stamped items, power is partitioned by each
    item's own variant stamp."""
    freqs = np.asarray(freqs, dtype=float)
    psd = np.asarray(psd, dtype=float)
    c = CARRIERS[grid]

    def power_at(f0, tol=1.5):
        m = np.abs(freqs - f0) <= tol
        return float(np.max(psd[m])) if m.any() else float("nan")

    p_car = power_at(c["f0"], 2.5)
    p_h2 = power_at(c["harmonics"][0])
    refl = []
    for base in [c["f0"]] + c["harmonics"]:
        for fn in NEURAL_FREQS:
            for s in (-1, 1):
                m = (np.abs(freqs - (base + s * fn)) <= 8.0) & \
                    (np.abs(freqs - (base + s * fn)) > 3.0)
                med = float(np.median(psd[m])) if m.any() else float("nan")
                pv = power_at(base + s * fn, 0.75)
                if med and med == med and med > 0:
                    refl.append(pv / med)
    if stamped is not None:
        transduced_power = float(sum(
            s["power"] for s in stamped
            if s.get("variant", "transduced") == "transduced"))
        induced_power = float(sum(
            s["power"] for s in stamped
            if s.get("variant") == "induced"))
    elif variant == "induced":
        transduced_power, induced_power = 0.0, float(np.sum(psd))
    else:
        transduced_power, induced_power = float(np.sum(psd)), 0.0
    return {
        "grid": grid,
        "transduced_power": transduced_power,
        "induced_power": induced_power,
        "carrier_power": p_car,
        "harmonic_ratio": (p_h2 / p_car) if p_car and p_car == p_car
        and p_car > 0 else None,
        "subharmonic_ratio": (power_at(c["subharmonics"][0]) / p_car)
        if p_car and p_car > 0 else None,
        "reflection_max_ratio": max(refl) if refl else None,
    }


def gated_peak(freqs, psd, grid="us", band=None, tol=1.5, carrier_tol=2.5,
               flow="in", variant="transduced", cavity_id="dweller-main"):
    """Strongest surviving peak after the firewall, fully stamped."""
    freqs = np.asarray(freqs, dtype=float)
    psd = np.asarray(psd, dtype=float)
    keep = exclusion_mask(freqs, grid, tol, carrier_tol, variant)
    if band is not None:
        keep &= (freqs >= band[0]) & (freqs <= band[1])
    if not keep.any():
        return None
    idx = int(np.argmax(np.where(keep, psd, -np.inf)))
    stamped = inspect_spectrum(freqs, psd, grid, tol, carrier_tol,
                               flow, variant, cavity_id)
    return stamped[idx]


# ---------------------------------------------------------------------------
def _selftest():
    cases = [
        (51.6, "uk", "grid:carrier", "STRIP"),
        (50.8, "uk", "grid:carrier", "STRIP"),
        (60.8, "us", "grid:carrier", "STRIP"),
        (120.0, "us", "grid:harmonic", "TRANSFORM"),
        (30.0, "us", "grid:subharmonic", "STRIP"),
        (66.2, "us", "body:reflection", "PROTECT"),
        (53.8, "us", "body:reflection", "PROTECT"),
        (7.83, "us", "planet:cavity", "PROTECT"),
        (6.2, "us", "brain:fundamental", "PROTECT"),
        (12.4, "us", "brain:harmonic", "PROTECT"),
        (10.0, "us", "brain:rhythm", "PROTECT"),
        (88.0, "us", "unknown:unclassified", "QUARANTINE"),
    ]
    ok = True
    for f, g, want_lab, want_pol in cases:
        lab = label_bin(f, g)
        pol = policy_for(lab)
        good = (lab == want_lab and pol == want_pol)
        ok &= good
        print(f"  [{'OK ' if good else 'FAIL'}] {f} Hz ({g}) -> {lab} [{pol}]")

    freqs = np.arange(1, 201, 1.0)
    psd = np.random.default_rng(0).normal(1.0, 0.05, len(freqs))
    psd[freqs == 60] = 50.0
    psd[freqs == 120] = 80.0
    psd[freqs == 10] = 5.0
    pk = gated_peak(freqs, psd, grid="us", band=WINDOWS["neural"])
    print(f"\ngated peak: {pk['label']} @ {pk['freq']} Hz, policy {pk['policy']}")
    assert pk["label"] == "brain:rhythm" and pk["freq"] == 10.0
    sc = transform_scalars(freqs, psd, grid="us")
    print(f"transform scalars: harmonic_ratio={sc['harmonic_ratio']:.2f} "
          f"(expect ~1.60)")
    assert abs(sc["harmonic_ratio"] - 1.6) < 0.05
    # v3 defaults are v2 behavior: all power counts as transduced
    assert abs(sc["transduced_power"] - float(np.sum(psd))) < 1e-9
    assert sc["induced_power"] == 0.0
    print("  [OK ] v3 scalars default: transduced=subtotal of spectrum, "
          "induced=0.0")

    # v3 flow variants: same peak, transduced vs induced
    f2 = np.array([6.2, 60.0, 120.0])
    p2 = np.array([3.0, 50.0, 80.0])
    st_t = {s["freq"]: s for s in inspect_spectrum(f2, p2, grid="us")}
    fund = st_t[6.2]
    assert fund["label"] == "brain:fundamental" \
        and fund["policy"] == "PROTECT"
    assert fund["flow"] == "in" and fund["variant"] == "transduced" \
        and fund["cavity_id"] == "dweller-main" \
        and fund["variant_capped"] is False
    print("  [OK ] transduced brain:fundamental still PROTECTs "
          "(v3 fields defaulted)")
    st_i = {s["freq"]: s for s in inspect_spectrum(
        f2, p2, grid="us", flow="out", variant="induced",
        cavity_id="dweller-main")}
    fund_i = st_i[6.2]
    assert fund_i["label"] == "brain:fundamental" \
        and fund_i["policy"] == "TRANSFORM" \
        and fund_i["variant_capped"] is True
    # non-PROTECT outcomes pass through uncapped for induced items
    assert st_i[60.0]["policy"] == "STRIP" \
        and st_i[60.0]["variant_capped"] is False
    assert st_i[120.0]["policy"] == "TRANSFORM" \
        and st_i[120.0]["variant_capped"] is False
    print("  [OK ] induced brain:fundamental capped to TRANSFORM, "
          "variant_capped=True; STRIP/TRANSFORM unchanged")
    sc_i = transform_scalars(f2, p2, grid="us", stamped=list(st_i.values()))
    assert sc_i["induced_power"] == float(np.sum(p2)) \
        and sc_i["transduced_power"] == 0.0
    sc_t = transform_scalars(f2, p2, grid="us", stamped=list(st_t.values()))
    assert sc_t["transduced_power"] == float(np.sum(p2)) \
        and sc_t["induced_power"] == 0.0
    print(f"  [OK ] variant subtotals: transduced run "
          f"{sc_t['transduced_power']:.1f}/0.0, induced run "
          f"{sc_i['transduced_power']:.1f}/{sc_i['induced_power']:.1f}")
    print("\nself-test:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    _selftest()
