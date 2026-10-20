"""passport.py — the ID -> joule passport (inverted-cavity delta spec, §4-§5).

One trace object per interaction. Every ID in the chain leads to joules:

    token_ids            (what crossed the boundary, transduced in)
      -> embedding_point (spectra coordinate / orbit-node assignment)
      -> prompt_kv_id    (cube key for the asked face)
      -> path            (ordered hops: orbit -> route -> slot -> layers,
                          neutron flag per hop)
      -> response_kv_id  (cube key for the replied face)

Joules per hop and per passport:

    j_segment     full_price vs paid_price per hop. full_price is what the
                  segment would cost with an empty cavity; paid_price is
                  what the standing state let it cancel down to (a neutron
                  / fully-cancelled hop pays 0).
    j_interacted  joules of OTHER ids this interaction touched en route
                  (co-use events, shared stems, orbit neighbours).
    j_oscillation the cube's own motion charged to this id — gravity
                  changes, promotions, dwell/idle cycles. Dwell work is
                  NOT free; this is the term the old accounting missed.

ACCOUNTING DISCIPLINE (spec §5, load-bearing):
    gross_joules and cancelled_joules are MODELLED — computed from segment
    prices. delta_joules is METERED — read off the energy meter,
    idle-subtracted. Only the metered delta is headline-legal. The passport
    stores modelled numbers and checks them against a metered delta via
    cancellation_report(); it never manufactures a delta of its own.

DECOUPLING: this module imports nothing from kv_cube and holds no cube
objects. It accepts plain dicts / lists / simple values throughout, so a
thin adapter can feed it from the cube (or anything else) later.

Joule-electron integration: `hops_from_joule_electron()` builds hops from
a JouleElectronModel's route pricing (see its docstring for the fit).
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Hops
# ---------------------------------------------------------------------------
@dataclass
class Hop:
    """One segment of the path hierarchy.

    full_price: segment cost with an empty cavity (no cancellation).
    paid_price: what was actually charged after cancellation. Defaults:
        neutron hop -> 0.0 (carries mass, burns nothing);
        active hop  -> full_price (no cancellation).
    j_segment is accepted as an alias for full_price (the spec's §4 name
    for a hop's priced cost).
    """
    name: str
    full_price: float = 0.0
    paid_price: Optional[float] = None
    neutron: bool = False

    def __init__(self, name, full_price=None, paid_price=None,
                 neutron=False, j_segment=None):
        if full_price is None:
            full_price = j_segment if j_segment is not None else 0.0
        self.name = name
        self.full_price = float(full_price)
        self.neutron = bool(neutron)
        if paid_price is None:
            paid_price = 0.0 if self.neutron else self.full_price
        self.paid_price = float(paid_price)

    @property
    def j_segment(self):
        """The paid (post-cancellation) price of this segment."""
        return self.paid_price

    @property
    def cancelled(self):
        return self.full_price - self.paid_price

    @classmethod
    def from_dict(cls, d):
        """Accept {'name', 'j_segment'|'full_price', 'paid_price',
        'neutron'} in any combination the caller has on hand."""
        if isinstance(d, Hop):
            return d
        return cls(
            name=d["name"],
            full_price=d.get("full_price", d.get("j_segment")),
            paid_price=d.get("paid_price"),
            neutron=d.get("neutron", False),
        )

    def to_dict(self):
        return {"name": self.name, "full_price": self.full_price,
                "paid_price": self.paid_price, "neutron": self.neutron}


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
@dataclass
class InteractionEvent:
    """Joules of another id this interaction interacted with en route."""
    other_id: str
    joules: float

    @classmethod
    def from_dict(cls, d):
        if isinstance(d, InteractionEvent):
            return d
        return cls(other_id=d["other_id"], joules=float(d["joules"]))

    def to_dict(self):
        return {"other_id": self.other_id, "joules": self.joules}


@dataclass
class OscillationEvent:
    """Cube-motion joules charged to this id: gravity changes,
    promotions, dwell cycles spent on it."""
    cause: str
    joules: float

    @classmethod
    def from_dict(cls, d):
        if isinstance(d, OscillationEvent):
            return d
        return cls(cause=d["cause"], joules=float(d["joules"]))

    def to_dict(self):
        return {"cause": self.cause, "joules": self.joules}


# ---------------------------------------------------------------------------
# Passport
# ---------------------------------------------------------------------------
@dataclass
class Passport:
    """The full ID -> joule trace for one interaction (spec §4).

    All fields are plain values: token_ids is a list, embedding_point is
    whatever spectra coordinate / node id the router produced (stored
    as-is), path items may be Hop objects or plain dicts (normalised to
    Hop on construction), interaction/oscillation events likewise.
    """
    token_ids: List[Any] = field(default_factory=list)
    embedding_point: Any = None
    prompt_kv_id: Optional[str] = None
    path: List[Hop] = field(default_factory=list)
    response_kv_id: Optional[str] = None
    interactions: List[InteractionEvent] = field(default_factory=list)
    oscillations: List[OscillationEvent] = field(default_factory=list)

    def __post_init__(self):
        self.path = [Hop.from_dict(h) for h in self.path]
        self.interactions = [InteractionEvent.from_dict(e)
                             for e in self.interactions]
        self.oscillations = [OscillationEvent.from_dict(e)
                             for e in self.oscillations]

    # -- event appenders (plain values in, events stored) ------------------
    def add_interaction(self, other_id, joules):
        self.interactions.append(InteractionEvent(other_id, float(joules)))

    def add_oscillation(self, cause, joules):
        self.oscillations.append(OscillationEvent(cause, float(joules)))

    # -- computed totals ---------------------------------------------------
    @property
    def gross_joules(self):
        """MODELLED. Sum of all segment full prices — what this
        interaction would cost with an empty cavity (no cache, no
        anticipation, no neutrons)."""
        return sum(h.full_price for h in self.path)

    @property
    def paid_joules(self):
        """MODELLED. Sum of segment paid prices after cancellation.
        This is the passport's delta ESTIMATE — an estimate, never to be
        quoted as the measured delta."""
        return sum(h.paid_price for h in self.path)

    @property
    def delta_estimate_joules(self):
        return self.paid_joules

    @property
    def cancelled_joules(self):
        """MODELLED. gross - paid: the part the standing state absorbed
        (prefix reuse + anticipation hits + neutron layers), valued at
        their would-be segment prices."""
        return self.gross_joules - self.paid_joules

    @property
    def j_total_interacted(self):
        return sum(e.joules for e in self.interactions)

    @property
    def j_total_oscillation(self):
        return sum(e.joules for e in self.oscillations)

    # -- cancellation accounting -------------------------------------------
    def cancellation_report(self, metered_delta_joules, tolerance_j=None):
        return cancellation_report(self, metered_delta_joules,
                                   tolerance_j=tolerance_j)

    # -- serialisation -------------------------------------------------------
    def to_dict(self):
        return {
            "token_ids": list(self.token_ids),
            "embedding_point": self.embedding_point,
            "prompt_kv_id": self.prompt_kv_id,
            "path": [h.to_dict() for h in self.path],
            "response_kv_id": self.response_kv_id,
            "interactions": [e.to_dict() for e in self.interactions],
            "oscillations": [e.to_dict() for e in self.oscillations],
            "totals": {
                "gross_joules": self.gross_joules,
                "cancelled_joules": self.cancelled_joules,
                "paid_joules": self.paid_joules,
                "j_total_interacted": self.j_total_interacted,
                "j_total_oscillation": self.j_total_oscillation,
            },
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            token_ids=d.get("token_ids", []),
            embedding_point=d.get("embedding_point"),
            prompt_kv_id=d.get("prompt_kv_id"),
            path=d.get("path", []),
            response_kv_id=d.get("response_kv_id"),
            interactions=d.get("interactions", []),
            oscillations=d.get("oscillations", []),
        )


# ---------------------------------------------------------------------------
# Cancellation accounting (spec §5)
# ---------------------------------------------------------------------------
def cancellation_report(passport, metered_delta_joules, tolerance_j=None):
    """Check the cancellation identity: gross - cancelled ~= delta.

    gross and cancelled are MODELLED — they come from this passport's
    segment prices (full vs paid). delta is METERED — `metered_delta_joules`
    is read off the energy meter, idle-subtracted, by the caller. Only the
    metered delta is headline-legal; the modelled numbers exist to be
    checked against it. A residual beyond tolerance means the prices are
    wrong — that drift IS the recalibration signal for the joule-electron
    falsifier (if priced predictions cannot beat the flat baseline, the
    accounting labels itself astrology and stops being quoted).

    tolerance_j: allowed |residual|. Default max(2 J, 10% of delta).
    Returns {gross, cancelled, delta, identity_residual, identity_ok,
    tolerance_j}.
    """
    gross = passport.gross_joules
    cancelled = passport.cancelled_joules
    delta = float(metered_delta_joules)
    if tolerance_j is None:
        tolerance_j = max(2.0, 0.10 * abs(delta))
    residual = (gross - cancelled) - delta
    return {
        "gross": gross,
        "cancelled": cancelled,
        "delta": delta,
        "identity_residual": residual,
        "identity_ok": abs(residual) <= tolerance_j,
        "tolerance_j": tolerance_j,
    }


# ---------------------------------------------------------------------------
# Joule-electron adapter
# ---------------------------------------------------------------------------
def hops_from_joule_electron(model, path, n_tokens=1):
    """Build passport hops from joule_electron route pricing.

    Fit note: JouleElectronModel.estimate_path(path, n_tokens) prices a
    route only in AGGREGATE (predicted_joules for the whole path), but it
    computes that aggregate as sum(layer.joule_rating for active layers)
    * n_tokens, and the per-layer ratings live on model.layers. So this
    adapter prices each hop from the same ratings estimate_path sums —
    no new pricing is invented, and the hop paid total reconciles exactly
    with estimate_path's predicted_joules (asserted in the self-test).

    model: a JouleElectronModel instance (imported by the CALLER from
        joule_electron; this module stays import-light and decoupled).
    path:  [(role, mode)] with mode in {'active', 'neutron'} — exactly
        the shape estimate_path / full_path() use.
    n_tokens: segment prices are per-token ratings * n_tokens.

    Hop mapping: name=role, full_price=rating*n_tokens,
    neutron=(mode=='neutron'), paid_price=0 for neutron else full_price.
    Partial cancellation (e.g. prefix-reuse discounts) is NOT in the
    joule-electron model; callers adjust paid_price afterwards if their
    router knows more.
    """
    hops = []
    for role, mode in path:
        if mode not in ("active", "neutron"):
            raise ValueError(f"unknown mode {mode!r}")
        layer = model.layers[role]
        full = layer.joule_rating * n_tokens
        hops.append(Hop(name=role, full_price=full,
                        neutron=(mode == "neutron")))
    return hops


# ---------------------------------------------------------------------------
def _selftest():
    # --- synthetic passport, hand-computed expectations -------------------
    p = Passport(
        token_ids=[101, 202, 303],
        embedding_point={"node": "orbit-7", "spectra": [0.125, 0.5]},
        prompt_kv_id="kv-prompt-abc",
        path=[
            {"name": "embed", "full_price": 10.0, "paid_price": 10.0},
            {"name": "shared-prefix-layers", "full_price": 40.0,
             "neutron": True},                      # paid defaults to 0
            {"name": "mlp-compute", "j_segment": 30.0, "paid_price": 18.0},
        ],
        response_kv_id="kv-resp-xyz",
        interactions=[
            {"other_id": "kv-shared-stem", "joules": 5.0},
            {"other_id": "orbit-neighbour-3", "joules": 2.5},
        ],
        oscillations=[
            {"cause": "gravity +2 co-use", "joules": 1.25},
            {"cause": "promotion SELF_TALK->WORK", "joules": 0.75},
            {"cause": "dwell cycle", "joules": 0.5},
        ],
    )
    print(f"gross={p.gross_joules}  paid={p.paid_joules}  "
          f"cancelled={p.cancelled_joules}  "
          f"interacted={p.j_total_interacted}  "
          f"oscillation={p.j_total_oscillation}")
    assert p.gross_joules == 80.0            # 10 + 40 + 30 (full prices)
    assert p.paid_joules == 28.0             # 10 + 0 (neutron) + 18
    assert p.cancelled_joules == 52.0        # 80 - 28
    assert p.delta_estimate_joules == 28.0
    assert p.j_total_interacted == 7.5       # 5.0 + 2.5
    assert p.j_total_oscillation == 2.5      # 1.25 + 0.75 + 0.5
    assert p.path[1].neutron and p.path[1].paid_price == 0.0
    assert p.path[2].full_price == 30.0      # j_segment alias honoured
    print("  [OK ] totals: gross 80 / cancelled 52 / paid 28 / "
          "interacted 7.5 / oscillation 2.5")

    # --- cancellation identity ---------------------------------------------
    ok = cancellation_report(p, metered_delta_joules=27.0)
    print(f"report (metered 27.0): {ok}")
    assert ok["gross"] == 80.0 and ok["cancelled"] == 52.0
    assert ok["delta"] == 27.0
    assert ok["identity_residual"] == 1.0    # (80 - 52) - 27
    assert ok["tolerance_j"] == max(2.0, 0.10 * 27.0)
    assert ok["identity_ok"] is True
    print("  [OK ] identity holds within tolerance (residual 1.0 J)")

    bad = p.cancellation_report(metered_delta_joules=5.0)
    print(f"report (metered 5.0):  {bad}")
    assert bad["identity_residual"] == 23.0
    assert bad["identity_ok"] is False
    print("  [OK ] identity fails loudly when the meter disagrees "
          "(residual 23.0 J)")

    # --- dict round-trip -----------------------------------------------------
    p2 = Passport.from_dict(p.to_dict())
    assert p2.gross_joules == p.gross_joules
    assert p2.cancelled_joules == p.cancelled_joules
    assert p2.j_total_interacted == p.j_total_interacted
    assert p2.j_total_oscillation == p.j_total_oscillation
    print("  [OK ] to_dict / from_dict round-trip preserves totals")

    # --- joule-electron adapter reconciliation -------------------------------
    import joule_electron
    model = joule_electron.JouleElectronModel()
    spec = [("wte.weight", "active"), ("attn.c_attn", "neutron"),
            ("mlp.c_fc", "active")]
    hops = hops_from_joule_electron(model, spec, n_tokens=10)
    pp = Passport(path=hops)
    est = model.estimate_path(spec, n_tokens=10)
    print(f"adapter: gross={pp.gross_joules:.4f}  paid={pp.paid_joules:.4f}"
          f"  estimate_path predicted={est['predicted_joules']:.4f}")
    assert abs(pp.paid_joules - est["predicted_joules"]) < 1e-9
    assert hops[1].neutron and hops[1].paid_price == 0.0
    assert abs(pp.gross_joules -
               sum(model.layers[r].joule_rating * 10 for r, _ in spec)) < 1e-9
    print("  [OK ] adapter paid total reconciles exactly with "
          "estimate_path; neutron hop pays 0")

    print("\nself-test: PASS")


if __name__ == "__main__":
    _selftest()
