"""v9: Telomere reservoir — data retention + manipulation under degradation.

The E_reservoir isn't just energy accounting; it stores DATA. Bits degrade
from thermal noise (universal dissipation). Telomeres — sacrificial protection
budgets — keep the core data below the mutation threshold.

Biology: telomeres (TTAGGG repeats) cap chromosomes, shorten each division
(Hayflick limit), protect coding DNA. When exhausted → senescence.
Here: every read/write shortens the telomere. Background aging too.
Core BER ≈ 0 while telomere holds; rises after depletion.

The telomere costs energy to maintain (refresh), drawn from E_reservoir —
data retention is thermodynamic work, closing the M_0 loop.
"""
import json
import numpy as np


class TelomereReservoir:
    def __init__(self, p_flip=1e-3, e_per_telomere_bit=1e-6):
        # p_flip: per-bit flip prob per tick when fully exposed
        # e_per_telomere_bit: energy/tick to maintain one telomere unit
        self.p_flip = p_flip
        self.e_maintain = e_per_telomere_bit
        self.store = {}
        self.energy_spent = 0.0

    def write(self, data_id, bitstring, telomere_len=100):
        """Store bits with a telomere protection budget."""
        self.store[data_id] = {
            "bits": np.array(bitstring, dtype=np.uint8).copy(),
            "original": np.array(bitstring, dtype=np.uint8).copy(),
            "telomere": float(telomere_len),
            "telomere_max": float(telomere_len),
            "accesses": 0,
        }

    def _degrade(self, entry, ticks=1):
        """Apply stochastic bit flips. Telomere shields core:
        p_core scales with depletion (vulnerable when telomere low)."""
        n = len(entry["bits"])
        depletion = 1.0 - (entry["telomere"] / max(entry["telomere_max"], 1e-9))
        depletion = np.clip(depletion, 0.0, 1.0)
        # Core flip prob: near-zero when telomere full, rises as it depletes
        p_core = self.p_flip * (0.01 + 0.99 * depletion ** 2)
        flips = np.random.random(n) < (p_core * ticks)
        entry["bits"][flips] ^= 1
        return int(flips.sum())

    def read(self, data_id):
        """Read costs telomere (Hayflick limit). Returns (bits, integrity)."""
        e = self.store[data_id]
        e["accesses"] += 1
        e["telomere"] -= 1.0  # access cost
        e["telomere"] = max(e["telomere"], 0.0)
        self._degrade(e, ticks=1)
        integrity = e["telomere"] / max(e["telomere_max"], 1e-9)
        return e["bits"].copy(), float(integrity)

    def append(self, data_id, bitstring):
        """Append data; new bits get fresh telomere (like telomerase)."""
        e = self.store[data_id]
        e["bits"] = np.concatenate([e["bits"], np.array(bitstring, np.uint8)])
        e["original"] = np.concatenate(
            [e["original"], np.array(bitstring, np.uint8)])
        # telomerase: extend protection for the new segment
        e["telomere"] += len(bitstring) * 0.1
        e["telomere_max"] += len(bitstring) * 0.1
        e["accesses"] += 1
        e["telomere"] -= 1.0

    def repair(self, data_id):
        """Self-repair operator (telomerase). If telomere is damaged but not
        exhausted (0 < telomere < max), regenerate it at an energy cost.
        This is the active defense Gemini specified: local Hill-sphere
        shielding rebuilds the guard bands before the core is breached.
        Returns (repaired: bool, energy_cost: float)."""
        e = self.store[data_id]
        frac = e["telomere"] / max(e["telomere_max"], 1e-9)
        if frac <= 0.0:
            return False, 0.0  # exhausted → senescence, no repair possible
        if frac >= 1.0:
            return False, 0.0  # already full, nothing to repair
        # Repair cost: proportional to damage (like biological telomerase
        # consuming ATP). More damage = more energy to rebuild.
        damage = 1.0 - frac
        cost = damage * e["telomere_max"] * self.e_maintain * 10.0
        # Regenerate telomere to full (guard bands rebuilt)
        e["telomere"] = e["telomere_max"]
        self.energy_spent += cost
        return True, cost

    def tick(self, n=1):
        """Background universal aging: telomeres slowly shorten, bits flip.
        Returns energy cost (drawn from E_reservoir in the full system)."""
        cost = 0.0
        for e in self.store.values():
            # maintain telomere: costs energy proportional to length
            cost += self.e_maintain * e["telomere"] * n
            # aging shortens telomere
            e["telomere"] -= 0.2 * n
            e["telomere"] = max(e["telomere"], 0.0)
            self._degrade(e, ticks=n)
        self.energy_spent += cost
        return cost

    def ber(self, data_id):
        """Bit error rate vs original."""
        e = self.store[data_id]
        n = min(len(e["bits"]), len(e["original"]))
        if n == 0:
            return 0.0
        return float((e["bits"][:n] != e["original"][:n]).mean())

    def telomere_frac(self, data_id):
        e = self.store[data_id]
        return float(e["telomere"] / max(e["telomere_max"], 1e-9))


def text_to_bits(text):
    return np.unpackbits(np.frombuffer(text.encode("utf-8"), dtype=np.uint8))


def bits_to_text(bits):
    # trim to whole bytes
    n = (len(bits) // 8) * 8
    b = np.packbits(bits[:n].astype(np.uint8))
    return b.tobytes().decode("utf-8", errors="replace")


def main():
    np.random.seed(42)
    # "complex enough" file: natural language (high redundancy)
    with open("ARCHITECTURE.md") as f:
        text = f.read()[:4000]  # first 4KB
    bits = text_to_bits(text)
    print(json.dumps({"file_bits": len(bits), "file_chars": len(text)}),
          flush=True)

    RUIN_THRESHOLD = 0.15  # BER beyond which text is ruined

    for name, tel_len in [("T_telomere", 80), ("N_no_telomere", 0)]:
        res = TelomereReservoir(p_flip=2e-3, e_per_telomere_bit=1e-6)
        res.write("doc", bits, telomere_len=tel_len)
        ticks_to_ruin = None
        for t in range(300):
            # every 3rd tick: read (manipulation costs telomere)
            if t % 3 == 0:
                res.read("doc")
            cost = res.tick()
            b = res.ber("doc")
            if b > RUIN_THRESHOLD and ticks_to_ruin is None:
                ticks_to_ruin = t
                break
        # final state
        final_bits, integrity = res.read("doc")
        print(json.dumps({
            "branch": name,
            "ticks_to_ruin": ticks_to_ruin,
            "final_ber": round(res.ber("doc"), 4),
            "telomere_frac": round(res.telomere_frac("doc"), 3),
            "energy_spent": round(res.energy_spent, 6),
            "accesses": res.store["doc"]["accesses"],
        }), flush=True)

    # manipulation demo: append survives via telomerase
    res = TelomereReservoir(p_flip=2e-3)
    res.write("doc", bits[:800], telomere_len=40)
    for t in range(60):
        if t % 3 == 0:
            res.read("doc")
        res.tick()
    # append new data (gets fresh telomere)
    res.append("doc", bits[800:1600])
    for t in range(40):
        if t % 3 == 0:
            res.read("doc")
        res.tick()
    print(json.dumps({
        "manipulation": "append",
        "ber_after_append": round(res.ber("doc"), 4),
        "telomere_frac": round(res.telomere_frac("doc"), 3),
    }), flush=True)


if __name__ == "__main__":
    main()
