"""v11: Shed, don't repair. Zak's restraint.

The telomere was getting overengineered. Simplify:
- Data rides a WEAK carrier (low energy, malleable) but DENSE (efficient).
- Outer layers (peel) absorb noise. When peel BER exceeds threshold,
  SHED it — don't repair. Shedding REMOVES noisy bits, so effective
  BER goes DOWN. Like peeling an orange: less fruit, but cleaner.
- Scale of loss doesn't change the whole. Ledger accounts every bit.

No ECC. No repair costs. Just layers and shedding.
"""
import json
import numpy as np


class SheddingReservoir:
    def __init__(self, peel_frac=0.2, shed_ber_threshold=0.3, p_peel=5e-3,
                 p_core=1e-4):
        # peel_frac: fraction of bits that are sacrificial peel (split ends)
        # shed_ber_threshold: shed peel when its BER exceeds this
        # p_peel, p_core: per-tick flip prob (peel degrades faster)
        self.peel_frac = peel_frac
        self.shed_thresh = shed_ber_threshold
        self.p_peel = p_peel
        self.p_core = p_core
        self.store = {}
        # ledger: accounts for every bit, all the way through
        self.ledger = {"written": 0, "shed": 0, "corrupted": 0}

    def write(self, data_id, bits):
        bits = np.array(bits, dtype=np.uint8)
        n = len(bits)
        n_peel = int(n * self.peel_frac // 2)
        # peel = first and last n_peel bits; core = middle
        self.store[data_id] = {
            "bits": bits.copy(),
            "original": bits.copy(),
            "n_peel": n_peel,  # peel size at each end
            "shed_count": 0,   # how many peel layers shed
        }
        self.ledger["written"] += n

    def _peel_mask(self, entry):
        """Boolean mask of current peel bits (ends, excluding shed)."""
        n = len(entry["bits"])
        np_ = entry["n_peel"]
        # peel shrinks as layers are shed; for simplicity, peel is fixed
        # size at ends, but we track how many times we've shed
        mask = np.zeros(n, dtype=bool)
        # effective peel after sheds: we shed from the ends inward
        # each shed removes np_ bits from each end? No — simpler:
        # peel is the outer np_ bits at each end; shedding removes them
        # and the NEXT np_ become the new peel. We track via shed_count.
        # For now: peel = outer np_ at each end of CURRENT array.
        # After a shed, the array is smaller, so peel moves inward.
        if np_ > 0:
            mask[:np_] = True
            mask[-np_:] = True
        return mask

    def tick(self):
        """Background noise: peel degrades faster than core."""
        for eid, e in self.store.items():
            n = len(e["bits"])
            if n == 0:
                continue
            peel = self._peel_mask(e)
            # flip peel bits at high rate, core at low rate
            flip_peel = np.random.random(n) < (self.p_peel * peel)
            flip_core = np.random.random(n) < (self.p_core * (~peel))
            flips = flip_peel | flip_core
            e["bits"][flips] ^= 1
            self.ledger["corrupted"] += int(flips.sum())
            # check: should we shed?
            self._maybe_shed(eid)

    def _maybe_shed(self, data_id):
        """If peel BER exceeds threshold, SHED it (discard).
        Shedding removes noisy bits → effective BER goes DOWN."""
        e = self.store[data_id]
        n = len(e["bits"])
        if n == 0:
            return False
        peel = self._peel_mask(e)
        n_peel_bits = int(peel.sum())
        if n_peel_bits == 0:
            return False
        # peel BER vs original (align by position; after sheds, original
        # is truncated too — we keep them aligned by shedding both)
        # For simplicity: compare current peel bits to original peel bits
        # at the same positions (we shed from both arrays).
        peel_ber = float((e["bits"][peel] != e["original"][peel]).mean())
        if peel_ber > self.shed_thresh:
            # SHED: remove peel bits from both arrays
            keep = ~peel
            shed_n = n - int(keep.sum())
            e["bits"] = e["bits"][keep].copy()
            e["original"] = e["original"][keep].copy()
            e["shed_count"] += 1
            self.ledger["shed"] += shed_n
            return True
        return False

    def ber(self, data_id):
        """Effective BER of REMAINING bits (after shedding)."""
        e = self.store[data_id]
        n = len(e["bits"])
        if n == 0:
            return 1.0  # all shed = total loss
        return float((e["bits"] != e["original"]).mean())

    def completeness(self, data_id):
        """Fraction of original bits retained."""
        e = self.store[data_id]
        # original length before any sheds: we don't track it directly,
        # so use the ledger. For per-item, store initial_n.
        return float(len(e["bits"]) / e["initial_n"])

    def stats(self, data_id):
        e = self.store[data_id]
        return {
            "ber": round(self.ber(data_id), 4),
            "completeness": round(float(len(e["bits"]) / e["initial_n"]), 4),
            "sheds": e["shed_count"],
            "bits_remaining": len(e["bits"]),
        }


def main():
    np.random.seed(99)
    # Use ARCHITECTURE.md (complex, dense)
    with open("ARCHITECTURE.md", "rb") as f:
        raw = f.read()[:8000]
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))
    print(json.dumps({"file_bits": len(bits)}), flush=True)

    res = SheddingReservoir(peel_frac=0.2, shed_ber_threshold=0.3,
                            p_peel=5e-3, p_core=1e-4)
    # store initial_n for completeness
    res.write("doc", bits)
    res.store["doc"]["initial_n"] = len(bits)

    print(json.dumps({"t": 0, **res.stats("doc")}), flush=True)
    for t in range(1, 301):
        res.tick()
        if t % 50 == 0:
            print(json.dumps({"t": t, **res.stats("doc")}), flush=True)

    print(json.dumps({"ledger": res.ledger}), flush=True)
    # The point: BER stays low BECAUSE we shed. Completeness drops,
    # but the remaining data is clean. Orange peeled, fruit intact.


if __name__ == "__main__":
    # patch write to store initial_n
    _orig_write = SheddingReservoir.write
    def _patched(self, data_id, bits):
        _orig_write(self, data_id, bits)
        self.store[data_id]["initial_n"] = len(
            self.store[data_id]["bits"])
    SheddingReservoir.write = _patched
    main()
