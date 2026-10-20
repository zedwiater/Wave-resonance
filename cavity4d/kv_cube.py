"""kv_cube.py — the KV cube: data reorganized around relational events.

Three faces per entry (the cube):
  ASKED    — what the person said (kv_id of the prompt)
  COMPUTED — the cascade sketch: which orbit, how long, how many
             Joules, which exit path. The summary, not raw activations.
  REPLIED  — what the LLM said back (kv_id of the response)

Plus the dimensions tonight added: WHEN the id was last used, HOW it
was used, and WHO it was used WITH (co-use). Entries orbit by shared
spectra range (node = nearest spectral centroid); co-use is gravity —
ids that keep firing together fall into the well together.

Tiers (the well), promoted by gravity = use_count + 2 x co-use:
  SELF_TALK  anticipation cache — new and recent ids
  WORK       deep research / work cache (gravity >= 5)
  LONGTERM   the archive (gravity >= 15)
  BLACKHOLE  everything else, eventually: truncated to a small point
             {kv_id, node, spectra_point, cascade sketch}. The text is
             dropped. Resurrection = talk it out: hand the source text
             back and the entry re-registers at full size.

The cube lives on DISK (JSONL), not in RAM — hot orbits get loaded
toward the GPU by the front end; the mass of history stays on the HDD,
which talks back and forth. idle_cycle() is the DWELL job: the burst
controller calls it while the node sleeps — promote the warm, cool
the stale, black-hole the forgotten.

kv_id here = sha256(text)[:16] — a stand-in for the true token-id
sequence fingerprint (same role, cheaper at this layer).
"""
import hashlib
import json
import math
import time
from pathlib import Path

SELF_TALK, WORK, LONGTERM, BLACKHOLE = (
    "SELF_TALK", "WORK", "LONGTERM", "BLACKHOLE")


def kv_id(text):
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def gravity(entry):
    co = sum(entry["co_use"].values())
    return entry["use_count"] + 2 * co + 2 * entry.get("value", 0.0)


class Cube:
    def __init__(self, model_id=None):
        self.entries = {}       # kv_id -> entry
        self.orbits = {}        # node_id -> {size, centroid}
        self.sessions = {}      # session_id -> [kv_id, ...]
        self.model_id = model_id   # computed faces are model-specific
        self.anticipation_stats = {"anticipated": 0, "realized": 0,
                                   "daydreamed": 0}
        # registry of REAL arrivals: kv_ids recorded by add_interaction
        # from actual traffic (any session except "self-talk"). Only an
        # id in here can realize an anticipation — self-talk can never
        # certify its own predictions.
        self._real_arrivals = set()

    # -- orbits ------------------------------------------------------------
    def load_orbits(self, nodes_path):
        nodes = json.load(open(nodes_path))
        for n in nodes:
            self.orbits[n["id"]] = {"size": n.get("size", 0),
                                    "centroid": n.get("centroid")}
        return len(self.orbits)

    def orbit_weight(self, node_id):
        base = self.orbits.get(node_id, {}).get("size", 0)
        member = sum(gravity(e) for e in self.entries.values()
                     if e["node"] == node_id)
        return base + member

    # -- entries ------------------------------------------------------------
    def _entry(self, text, ts):
        return {
            "kv_id": kv_id(text), "text": text, "node": None,
            "spectra_point": None,
            "asked": None, "computed": None, "replied": None,
            "first_seen": ts, "last_used": ts, "use_count": 0,
            "co_use": {}, "tier": SELF_TALK,
            "model_id": self.model_id, "provenance": "original",
            "value": 0.0, "kind": "interaction", "cycles_left": None,
        }

    def add_interaction(self, prompt_text, response_text=None,
                        computed=None, ts=None, session=None):
        """One relational event: asked + computed + replied, linked."""
        ts = ts if ts is not None else time.time()
        ids = []
        pe = self.entries.setdefault(kv_id(prompt_text),
                                     self._entry(prompt_text, ts))
        pe["asked"] = {"chars": len(prompt_text)}
        if computed:
            pe["computed"] = computed
            if "node" in computed:
                pe["node"] = computed["node"]
        pe["use_count"] += 1
        pe["last_used"] = ts
        ids.append(pe["kv_id"])
        if response_text:
            re_ = self.entries.setdefault(kv_id(response_text),
                                          self._entry(response_text, ts))
            re_["replied"] = {"chars": len(response_text)}
            re_["use_count"] += 1
            re_["last_used"] = ts
            ids.append(re_["kv_id"])
        if session:
            members = self.sessions.setdefault(session, [])
            for other in members:
                for i in ids:
                    if i != other:
                        self.entries[i]["co_use"][other] = \
                            self.entries[i]["co_use"].get(other, 0) + 1
                        self.entries[other]["co_use"][i] = \
                            self.entries[other]["co_use"].get(i, 0) + 1
            members.extend(ids)
        for i in ids:
            self._promote(self.entries[i])
        if session != "self-talk":
            # real traffic arrived — register it as a ground-truth
            # arrival for the anticipation falsifier
            self._real_arrivals.update(ids)
        return ids

    def record_outcome(self, kid, success):
        """Value signal: +1 when the interaction completed / was used,
        -1 when it failed or was discarded. Gravity follows value,
        not mere repetition."""
        e = self.entries.get(kid)
        if e is None:
            return False
        e["value"] += 1.0 if success else -1.0
        self._promote(e)
        return True

    def _promote(self, entry):
        if entry["tier"] == BLACKHOLE:
            return
        g = gravity(entry)
        if g >= 15:
            entry["tier"] = LONGTERM
        elif g >= 5:
            entry["tier"] = WORK
        else:
            entry["tier"] = SELF_TALK

    # -- anticipation: self-talk triples with a destination falsifier ------
    def add_anticipation(self, prompt_text, response_text=None,
                         computed=None, cycles=3, ts=None):
        """The Dweller thinks ahead: a full self-talk triple (prompt,
        compute path, response) cached BEFORE anyone asks. It is NOT
        restricted — it is judged. If the anticipated conversation
        does not arrive within `cycles` idle cycles, it was a
        daydream, and the well takes it."""
        ids = self.add_interaction(prompt_text, response_text, computed,
                                   ts=ts, session="self-talk")
        e = self.entries[ids[0]]
        e["kind"] = "anticipation"
        e["cycles_left"] = cycles
        self.anticipation_stats["anticipated"] += 1
        return ids

    def resolve_anticipations(self, arrived_kids=None):
        """One idle cycle of judgment. An anticipation is realized
        only on an EXACT kv_id match against registered real-traffic
        arrivals (ids recorded by add_interaction from sessions other
        than "self-talk"). A caller-supplied list is intersected with
        that registry, so self-talk ids can never realize anything,
        even if a caller passes them; with no list, the registry
        itself is the arrived set. One that keeps missing loses a
        cycle, and at zero it black-holes. Facts gravitate; daydreams
        fall."""
        if arrived_kids is None:
            arrived = set(self._real_arrivals)
        else:
            arrived = set(arrived_kids) & self._real_arrivals
        for e in list(self.entries.values()):
            if e.get("kind") != "anticipation" or e["tier"] == BLACKHOLE:
                continue
            if e["kv_id"] in arrived:
                e["kind"] = "interaction"
                e["cycles_left"] = None
                self.anticipation_stats["realized"] += 1
            else:
                e["cycles_left"] -= 1
                if e["cycles_left"] <= 0:
                    self.blackhole(e)
                    self.anticipation_stats["daydreamed"] += 1
        st = self.anticipation_stats
        judged = st["realized"] + st["daydreamed"]
        return {**st, "hit_rate": (st["realized"] / judged)
                if judged else None}

    def set_model(self, new_model_id):
        """Model swap: text faces survive (re-talk them), computed
        faces go stale in place — never silently trusted again."""
        stale = 0
        for e in self.entries.values():
            if e.get("computed") and e.get("model_id") != new_model_id:
                e["computed"]["stale"] = True
                stale += 1
        self.model_id = new_model_id
        return stale

    # -- the well ------------------------------------------------------------
    def blackhole(self, entry):
        """Truncate to a small point. Text dropped; identity, orbit and
        the cascade sketch survive. Resurrection needs the source."""
        entry["spectra_point"] = (
            self.orbits.get(entry["node"], {}).get("centroid") or
            [0.0])[:8]
        entry["text"] = None
        entry["asked"] = None
        entry["replied"] = None
        entry["tier"] = BLACKHOLE

    def resurrect(self, kid, source_text, ts=None):
        """Talk it out: the source text returns, the entry rebuilds."""
        e = self.entries.get(kid)
        if e is None or kv_id(source_text) != kid:
            return False
        e["text"] = source_text
        e["provenance"] = "regenerated"   # a rebuild, not the record
        e["tier"] = SELF_TALK
        e["use_count"] += 1
        e["last_used"] = ts if ts is not None else time.time()
        self._promote(e)
        return True

    def idle_cycle(self, now=None, stale_s=7 * 24 * 3600):
        """The DWELL job: cool the stale, black-hole the forgotten.
        LONGTERM is the archive — age alone never black-holes it."""
        now = now if now is not None else time.time()
        holed = 0
        for e in self.entries.values():
            if e["tier"] == SELF_TALK and gravity(e) < 5 \
                    and now - e["last_used"] > stale_s:
                self.blackhole(e)
                holed += 1
        return {"blackholed": holed, "entries": len(self.entries)}

    # -- persistence (the disk talks back) -----------------------------------
    def save(self, path):
        with open(path, "w") as f:
            for e in self.entries.values():
                f.write(json.dumps(e) + "\n")
            # Sidecar record in the same JSONL (the file's existing
            # persistence pattern): the real-arrival registry rides
            # along so a reload keeps the anticipation falsifier's
            # ground truth. This set only ever holds real-traffic
            # ids — add_interaction registers nothing from sessions
            # named "self-talk" — so persistence cannot smuggle a
            # self-talk id into the registry either.
            f.write(json.dumps({"_meta": "cube_state",
                                "saved_at": time.time(),
                                "real_arrivals":
                                    sorted(self._real_arrivals)}) + "\n")

    def load(self, path, now=None, cycle_seconds=3600.0):
        """Restore entries + the real-arrival registry from disk.

        Invariant: the arrivals registry survives restart intact —
        ground truth does not decay. Anticipations do NOT survive
        for free: downtime burns their cycles. The wall-clock gap
        since the save's saved_at stamp is converted to missed idle
        cycles (cycle_seconds each), subtracted from every live
        anticipation's cycles_left; one that hits zero black-holes
        on load, counted as daydreamed. A stale daydream from a
        previous session therefore dies at the door instead of
        realizing later. Old save files without saved_at get no
        decay (saved_at treated as now); clock skew clamps at 0.
        """
        now = now if now is not None else time.time()
        saved_at = None
        for line in open(path):
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("_meta") == "cube_state":
                self._real_arrivals.update(e.get("real_arrivals", []))
                saved_at = e.get("saved_at", saved_at)
                continue
            self.entries[e["kv_id"]] = e
        if saved_at is not None:
            downtime = max(0.0, now - saved_at)
            missed_cycles = int(downtime // cycle_seconds)
            if missed_cycles > 0:
                for e in list(self.entries.values()):
                    if e.get("kind") != "anticipation" \
                            or e["tier"] == BLACKHOLE \
                            or e.get("cycles_left") is None:
                        continue
                    e["cycles_left"] -= missed_cycles
                    if e["cycles_left"] <= 0:
                        self.blackhole(e)
                        self.anticipation_stats["daydreamed"] += 1
        return len(self.entries)


# -- seeding from wave-sunday's real history ---------------------------------
def seed(cube, data_dir, prompt_limit=500):
    data = Path(data_dir)
    n_orbits = cube.load_orbits(data / "spectra/prompt_nodes.json")
    n_trails = 0
    trails = data / "trails/v1.jsonl"
    if trails.exists():
        for line in open(trails):
            r = json.loads(line)
            if "prompt" not in r:
                continue
            # windowed sessions: an interaction links to its neighbours,
            # not to the whole history of the harness
            cube.add_interaction(
                r["prompt"],
                computed={"node": r.get("node"),
                          "total_ms": r.get("total_ms"),
                          "llm_ms": r.get("llm_ms"),
                          "response_len": r.get("response_len")},
                ts=r.get("ts"), session=f"trails-{n_trails // 3}")
            n_trails += 1
    n_prompts = 0
    prompts = data / "corpora/prompts/prompts.jsonl"
    if prompts.exists():
        for line in open(prompts):
            if n_prompts >= prompt_limit:
                break
            # archival prompts arrive UNLINKED — the corpus is not one
            # conversation, so no co-use gravity is invented for them
            cube.add_interaction(json.loads(line)["text"])
            n_prompts += 1
    return {"orbits": n_orbits, "trail_events": n_trails,
            "prompts": n_prompts, "entries": len(cube.entries)}


# ---------------------------------------------------------------------------
def _selftest():
    c = Cube()
    c.orbits[6] = {"size": 100, "centroid": [0.1] * 16}
    # a working relationship: same ids together, repeatedly
    for i in range(4):
        c.add_interaction("What is the capital of France?",
                          "The capital of France is Paris.",
                          computed={"node": 6, "total_ms": 900},
                          ts=1000 + i, session="s1")
    pe = c.entries[kv_id("What is the capital of France?")]
    print(f"  prompt entry: uses={pe['use_count']} gravity="
          f"{gravity(pe)} tier={pe['tier']} node={pe['node']}")
    assert gravity(pe) >= 5 and pe["tier"] in (WORK, LONGTERM)
    assert pe["computed"]["node"] == 6
    # a passing hi, long ago
    c.add_interaction("hi", ts=1000, session="s2")
    out = c.idle_cycle(now=1000 + 8 * 24 * 3600)
    he = c.entries[kv_id("hi")]
    print(f"  idle cycle: blackholed={out['blackholed']} "
          f"'hi' tier={he['tier']} text kept={he['text'] is not None}")
    assert he["tier"] == BLACKHOLE and he["text"] is None
    assert he["spectra_point"] is not None      # the point survives
    # resurrection by talking it out
    assert c.resurrect(kv_id("hi"), "hi", ts=2000)
    assert c.entries[kv_id("hi")]["tier"] == SELF_TALK
    print("  [OK ] promotion by co-use gravity, black-hole truncation, "
          "resurrection")
    assert c.entries[kv_id("hi")]["provenance"] == "regenerated"

    # value signal: success paves, failure doesn't
    c2 = Cube(model_id="gemma-3-4b")
    ids = c2.add_interaction("deploy the harness", "done",
                             computed={"node": 6, "joules": 12.0})
    e0 = c2.entries[ids[0]]
    assert e0["model_id"] == "gemma-3-4b"
    g_before = gravity(e0)
    c2.record_outcome(ids[0], True)
    c2.record_outcome(ids[0], True)
    assert gravity(e0) > g_before
    print("  [OK ] value signal moves gravity; model stamp recorded")

    # anticipation falsifier: one arrives (as REAL traffic), one
    # daydreams into the well
    c2.add_anticipation("will he ask about tides?", "prepared answer",
                        cycles=2)
    c2.add_anticipation("will he ask about nothing real?", "dream",
                        cycles=2)
    # the tides conversation actually shows up — a real interaction,
    # not self-talk — which registers its id as a ground-truth arrival
    c2.add_interaction("will he ask about tides?", session="live")
    st = c2.resolve_anticipations([kv_id("will he ask about tides?")])
    assert c2.entries[kv_id("will he ask about tides?")]["kind"] == \
        "interaction"
    c2.resolve_anticipations([])
    st = c2.resolve_anticipations([])
    dream = c2.entries[kv_id("will he ask about nothing real?")]
    print(f"  anticipation stats: {st}")
    assert dream["tier"] == BLACKHOLE and st["daydreamed"] == 1
    assert abs(st["hit_rate"] - 0.5) < 1e-9
    print("  [OK ] anticipation: realized kept, daydream black-holed, "
          "hit_rate 0.5")

    # anticipation guard: passing an anticipation's OWN id (with no
    # real-traffic arrival behind it) must NOT realize it — self-talk
    # can never certify itself. It just loses cycles and black-holes.
    c3 = Cube()
    c3.add_anticipation("will he ask the cube's own question?",
                        "self answer", cycles=2)
    own = kv_id("will he ask the cube's own question?")
    st = c3.resolve_anticipations([own])
    ge = c3.entries[own]
    assert ge["kind"] == "anticipation" and st["realized"] == 0
    st = c3.resolve_anticipations([own])
    print(f"  guard stats: {st}")
    assert ge["tier"] == BLACKHOLE and st["daydreamed"] == 1
    assert st["hit_rate"] == 0.0
    print("  [OK ] anticipation guard: self-passed id never realizes, "
          "daydream black-holed, hit_rate 0")

    # model swap: computed faces stale, text survives
    n = c2.set_model("qwen3-8b")
    assert n >= 1 and e0["computed"]["stale"] is True
    assert e0["text"] == "deploy the harness"
    print("  [OK ] model swap stales computed faces, text faces survive")

    # persistence: the real-arrival registry survives save/load —
    # an anticipation whose prompt really arrived can still be
    # realized after a reload, while a self-talk-only id stays OUT
    # of the registry across the round trip.
    import tempfile
    c4 = Cube()
    c4.add_interaction("the persisted question", session="live")
    c4.add_anticipation("the persisted question", "prepared",
                        cycles=3)
    c4.add_anticipation("a self-talk only dream", "dream", cycles=3)
    real_kid = kv_id("the persisted question")
    dream_kid = kv_id("a self-talk only dream")
    assert real_kid in c4._real_arrivals
    assert dream_kid not in c4._real_arrivals
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cube.jsonl"
        c4.save(p)
        c5 = Cube()
        c5.load(p)
    assert real_kid in c5._real_arrivals
    assert dream_kid not in c5._real_arrivals
    st = c5.resolve_anticipations()
    assert st["realized"] == 1
    assert c5.entries[real_kid]["kind"] == "interaction"
    print(f"  persistence stats after reload: {st}")
    print("  [OK ] arrivals persist: real arrival realized after "
          "reload, self-talk id never registered")

    # downtime decay on load: the registry survives restart intact,
    # anticipations do not — downtime burns their remaining cycles,
    # so a stale daydream black-holes at the door.
    c6 = Cube()
    c6.add_interaction("the question that really came", session="live")
    c6.add_anticipation("a dream with three cycles", "dream",
                        cycles=3)
    decay_kid = kv_id("a dream with three cycles")
    arrived_kid = kv_id("the question that really came")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cube_decay.jsonl"
        c6.save(p)
        saved_at = None
        for line in open(p):
            rec = json.loads(line)
            if rec.get("_meta") == "cube_state":
                saved_at = rec["saved_at"]
        assert saved_at is not None
        # (a) 2.5 h down at 1 h/cycle: loses 2 cycles, survives on 1
        c7 = Cube()
        c7.load(p, now=saved_at + 2.5 * 3600, cycle_seconds=3600.0)
        e7 = c7.entries[decay_kid]
        print(f"  decay (a): cycles_left={e7['cycles_left']} "
              f"tier={e7['tier']} kind={e7['kind']}")
        assert e7["kind"] == "anticipation" and e7["cycles_left"] == 1
        assert e7["tier"] != BLACKHOLE
        print("  [OK ] downtime decay: 2 missed cycles burned, "
              "anticipation survives with 1")
        # (b) 4 h down: cycles exhausted — black-holed on load,
        # daydreamed counted, registry still intact
        c8 = Cube()
        c8.load(p, now=saved_at + 4 * 3600, cycle_seconds=3600.0)
        e8 = c8.entries[decay_kid]
        print(f"  decay (b): tier={e8['tier']} daydreamed="
              f"{c8.anticipation_stats['daydreamed']} registry "
              f"intact={arrived_kid in c8._real_arrivals}")
        assert e8["tier"] == BLACKHOLE
        assert c8.anticipation_stats["daydreamed"] == 1
        assert arrived_kid in c8._real_arrivals
        print("  [OK ] downtime decay: stale daydream black-holed on "
              "load, arrivals registry intact")
        # (c) old-format file (no saved_at): no decay, however late
        lines = []
        for line in open(p):
            rec = json.loads(line)
            if rec.get("_meta") == "cube_state":
                rec.pop("saved_at", None)
            lines.append(json.dumps(rec))
        p_old = Path(td) / "cube_old.jsonl"
        p_old.write_text("\n".join(lines) + "\n")
        c9 = Cube()
        c9.load(p_old, now=saved_at + 100 * 3600,
                cycle_seconds=3600.0)
        e9 = c9.entries[decay_kid]
        print(f"  decay (c): cycles_left={e9['cycles_left']} "
              f"tier={e9['tier']} (old format, no saved_at)")
        assert e9["cycles_left"] == 3 and e9["tier"] != BLACKHOLE
        print("  [OK ] downtime decay: old-format save loads with "
              "no decay")
    print("\nself-test: PASS")


if __name__ == "__main__":
    _selftest()
