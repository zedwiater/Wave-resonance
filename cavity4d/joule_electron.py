"""joule_electron.py — the Joule-Electron transform pair (first draft).

FORWARD (evaluate the system):
  Every matrix is an electron condensate: a measured spectral density
  (from the SVD map: band_fraction = k99/n; density = 1 - band_fraction)
  and a cosmic class by role. Joule ratings are an ALLOCATION of a
  measured total (invariant-ledger: 1.69 J/token on the serving stack),
  distributed by params x class_factor x density — calibrated so a full
  all-active forward pass sums to the measured total. Per-layer Joules
  are modeled, the total is metered. That distinction is load-bearing.

  Classes (operational, role-derived):
    planet     embeddings + norms — stable routing, baseline structure
    star       attention — sustained burn, radiates state
    galaxy     MLP — massive, diffuse, flat spectrum
    black_hole explicit compression bottleneck (squeeze + concentrated)
    human      lm_head / boundary — interaction-dominated

INVERSE (evaluate the prompt):
  A query path lists layers as ACTIVE (proton/electron: burns Joules)
  or NEUTRON (skipped/cached: carries inertial mass — params x density —
  that shapes the trajectory but burns ZERO active Joules).
  predicted_joules, inertial_mass, velocity = mass / active_joules.

FALSIFIER (the kill switch):
  Beat the flat 1.69 J/token baseline at predicting MEASURED energy,
  or the verdict is ASTROLOGY and the transform dies.
"""
import json
from pathlib import Path

FLAT_J_PER_TOKEN = 1.69  # invariant-ledger demo measurement, serving stack

# fallback profile: measured aggregates from our GPT-2 SVD run (2026-10-08)
FALLBACK = {
    "wpe.weight": {"band_fraction": 0.014, "shape": [1024, 768]},
    "wte.weight": {"band_fraction": 0.915, "shape": [50257, 768]},
    "attn.c_attn": {"band_fraction": 0.862, "shape": [768, 2304]},
    "attn.c_proj": {"band_fraction": 0.374, "shape": [768, 768]},
    "mlp.c_fc": {"band_fraction": 0.917, "shape": [768, 3072]},
    "mlp.c_proj": {"band_fraction": 0.928, "shape": [3072, 768]},
}

CLASS_FACTOR = {"planet": 0.6, "star": 1.4, "galaxy": 1.0,
                "black_hole": 0.8, "human": 1.2}


def load_svd_profile(path=None):
    """Load the real SVD map; return {layer_key: {band_fraction, shape}}.
    Aggregates per-block matrices by role (attn.c_attn etc.)."""
    candidates = [path] if path else []
    candidates += [
        Path.home() / "wave-sunday/data/spectra/gpt2_svd.json",
        Path("/mnt/storage/neurodata/gpt2_svd.json"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            raw = json.load(open(c))
            prof = {}
            for name, v in raw.items():
                if not isinstance(v, dict) or "k99" not in v:
                    continue
                role = None
                for r in ("attn.c_attn", "attn.c_proj", "mlp.c_fc",
                          "mlp.c_proj"):
                    if r in name:
                        role = r
                        break
                if role is None and name in ("wte.weight", "wpe.weight"):
                    role = name
                if role is None:
                    continue
                bf = v["k99"] / v["n"]
                if role not in prof:  # first block is representative
                    prof[role] = {"band_fraction": bf, "shape": v["shape"],
                                  "source": str(c)}
            if prof:
                return prof
    return {k: dict(v, source="fallback-measured-aggregates")
            for k, v in FALLBACK.items()}


def classify(role, band_fraction, shape):
    """Cosmic class by role; black_hole needs a real compression
    signature (squeeze AND concentrated), not a vibe."""
    if role in ("wte.weight", "wpe.weight"):
        return "planet"
    if "lm_head" in role or "head" in role:
        return "human"
    if role.startswith("attn."):
        return "star"
    if role.startswith("mlp."):
        squeeze = min(shape) / max(shape) if shape else 1.0
        if squeeze <= 0.34 and band_fraction <= 0.5:
            return "black_hole"
        return "galaxy"
    return "galaxy"


class Layer:
    def __init__(self, role, band_fraction, shape):
        self.role = role
        self.band_fraction = band_fraction
        self.density = 1.0 - band_fraction      # electron density proxy
        self.shape = shape
        self.params = shape[0] * shape[1] if len(shape) == 2 else 0
        self.cls = classify(role, band_fraction, shape)
        self.joule_rating = 0.0                 # set by calibration

    def __repr__(self):
        return (f"<{self.role}: {self.cls}, density={self.density:.3f}, "
                f"params={self.params:,}, J/token={self.joule_rating:.4f}>")


class JouleElectronModel:
    """Forward transform: build layers, calibrate ratings to a metered
    total. Calibration constant defaults to the ledger measurement."""

    def __init__(self, profile=None, total_j_per_token=FLAT_J_PER_TOKEN,
                 n_blocks=12):
        profile = profile or load_svd_profile()
        self.layers = {}
        for role, v in profile.items():
            self.layers[role] = Layer(role, v["band_fraction"], v["shape"])
        self.n_blocks = n_blocks
        self.total_j_per_token = total_j_per_token
        self._calibrate()

    def _block_weight(self, layer):
        return (layer.params * CLASS_FACTOR[layer.cls]
                * (0.5 + layer.density))

    def _calibrate(self):
        # one full forward pass = embeddings (x1) + per-block roles (xN)
        total_w = 0.0
        for role, layer in self.layers.items():
            reps = 1 if role.endswith(".weight") and role.startswith("w") \
                else self.n_blocks
            total_w += self._block_weight(layer) * reps
        scale = self.total_j_per_token / total_w if total_w > 0 else 0.0
        for layer in self.layers.values():
            layer.joule_rating = self._block_weight(layer) * scale

    # -- inverse transform -------------------------------------------------
    def estimate_path(self, path, n_tokens=1):
        """path: [(role, mode)] mode in {'active', 'neutron'}.
        Returns predicted Joules, inertial mass, velocity, class mix."""
        active_j = 0.0
        neutron_mass = 0.0
        total_mass = 0.0
        mix = {}
        for role, mode in path:
            layer = self.layers[role]
            mass = layer.params * layer.density
            total_mass += mass
            mix[layer.cls] = mix.get(layer.cls, 0) + 1
            if mode == "active":
                active_j += layer.joule_rating
            elif mode == "neutron":
                neutron_mass += mass
            else:
                raise ValueError(f"unknown mode {mode!r}")
        return {
            "predicted_joules": active_j * n_tokens,
            "joules_per_token": active_j,
            "inertial_mass_neutron": neutron_mass,
            "total_mass": total_mass,
            "velocity": (total_mass / active_j) if active_j > 0 else None,
            "class_mix": mix,
        }

    def full_path(self, skip_fraction=0.0):
        """All layers active, or a fraction of block layers as neutron."""
        path = []
        block_roles = [r for r in self.layers
                       if not (r.startswith("w") and r.endswith(".weight"))]
        emb_roles = [r for r in self.layers if r not in block_roles]
        for r in emb_roles:
            path.append((r, "active"))
        n_skip = int(len(block_roles) * self.n_blocks * skip_fraction)
        count = 0
        for b in range(self.n_blocks):
            for r in block_roles:
                count += 1
                path.append((r, "neutron" if count <= n_skip else "active"))
        return path


class Falsifier:
    """The kill switch. Model must beat the flat baseline at predicting
    measured Joules, or it is astrology."""

    def __init__(self, flat_j_per_token=FLAT_J_PER_TOKEN, min_samples=5):
        self.flat = flat_j_per_token
        self.min_samples = min_samples
        self.model_err = 0.0
        self.flat_err = 0.0
        self.n = 0

    def record(self, n_tokens, predicted_j, actual_j):
        self.model_err += abs(predicted_j - actual_j)
        self.flat_err += abs(self.flat * n_tokens - actual_j)
        self.n += 1

    def verdict(self):
        if self.n < self.min_samples:
            return f"INSUFFICIENT DATA ({self.n}/{self.min_samples})"
        mae_m = self.model_err / self.n
        mae_f = self.flat_err / self.n
        if mae_m < mae_f:
            return (f"PREDICTIVE — model MAE {mae_m:.3f} J beats flat "
                    f"{mae_f:.3f} J over {self.n} samples")
        return (f"ASTROLOGY — model MAE {mae_m:.3f} J does not beat flat "
                f"{mae_f:.3f} J. Kill it.")


# ---------------------------------------------------------------------------
def _selftest():
    m = JouleElectronModel()
    print("forward transform — layer table:")
    tot = 0.0
    for role, layer in m.layers.items():
        reps = 1 if role.startswith("w") and role.endswith(".weight") \
            else m.n_blocks
        tot += layer.joule_rating * reps
        print(f"  {layer}")
    print(f"  calibrated full-pass total: {tot:.3f} J/token "
          f"(target {m.total_j_per_token})")
    assert abs(tot - m.total_j_per_token) < 0.01

    full = m.estimate_path(m.full_path(0.0), n_tokens=100)
    skip = m.estimate_path(m.full_path(0.3), n_tokens=100)
    print(f"\ninverse — full path: {full['predicted_joules']:.1f} J / 100 tok, "
          f"velocity {full['velocity']:.3e}")
    print(f"inverse — 30% neutron: {skip['predicted_joules']:.1f} J / 100 tok, "
          f"neutron mass {skip['inertial_mass_neutron']:.3e}, "
          f"velocity {skip['velocity']:.3e}")
    assert skip["predicted_joules"] < full["predicted_joules"]
    assert skip["inertial_mass_neutron"] > 0
    assert skip["velocity"] > full["velocity"]
    print("  [OK ] skipping burns less, carries mass, moves faster")

    # falsifier: correlated actuals -> PREDICTIVE
    f = Falsifier()
    for pred_j, act_j in [(150, 155), (90, 88), (170, 160), (120, 130),
                          (60, 66), (140, 138)]:
        f.record(100, pred_j, act_j)
    print(f"\nfalsifier (correlated): {f.verdict()}")
    assert f.verdict().startswith("PREDICTIVE")
    # falsifier: model no better than flat -> ASTROLOGY
    f2 = Falsifier()
    for act_j in [160, 175, 165, 172, 168, 171]:
        f2.record(100, 100, act_j)   # model predicts a useless constant
    print(f"falsifier (useless model): {f2.verdict()}")
    assert f2.verdict().startswith("ASTROLOGY")
    print("\nself-test: PASS")


if __name__ == "__main__":
    _selftest()
