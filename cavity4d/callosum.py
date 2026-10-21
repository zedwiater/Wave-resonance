"""callosum.py — the corpus callosum of the Dweller's two-model mind.

Zak's original directive (2026-10-20 20:41) coded a right-handed
hierarchy: left as the only voice and right as internal-only. Zak's
2026-10-20 23:39 correction supersedes that bias: the hemispheres
are AMBIDEXTROUS. Both have the full role set, both may use either
hand, and both may emit user-facing output.

One voice is now a concurrency rule rather than a caste rule. The
wrapper's OutputChannel is a mutex: it grants the single output
channel to exactly one hemisphere at a time and records the holder.
The CrossTalk log remains the shared memory both sides can read and
append to; run_exchange alternates which hemisphere speaks first by
cycle parity, so initiative is symmetric over time.

Failure discipline: a dead server, a timeout, or garbage output can
never break the dweller tick. llm_call returns (None, 0) on any error;
run_exchange converts failures into kind="error" log entries and
returns normally. No retries, no loops.
"""

import json
import os
import threading
import time
import urllib.request

_FULL_ROLES = ["speak", "sequential_reasoning", "final_answer",
               "context", "pattern", "monitor", "propose"]
HEMISPHERES = {
    "left": {"server": "http://127.0.0.1:8080", "model": "gemma-3-4b",
             "roles": list(_FULL_ROLES),
             "controls": "either_hand",
             "may_emit_user_output": True},
    "right": {"server": "http://127.0.0.1:8081", "model": "qwen2.5-3b",
              "roles": list(_FULL_ROLES),
              "controls": "either_hand",
              "may_emit_user_output": True},
}

JOULES_PER_TOKEN_EST = 0.5     # labelled estimate, never a measurement
JOULES_BASIS = "est 0.5 J/tok"
MAX_TEXT_CHARS = 500
DEFAULT_CAP_BYTES = 5_000_000  # cross-talk log ceiling, rotate to .1/.2

def _frame(side, first):
    role = "open the exchange with" if first else "respond to"
    return (
        f"You are the {side.upper()} hemisphere of a two-model mind "
        "living in a home-lab PC. Both hemispheres are ambidextrous: "
        "either may monitor, reason, propose, speak, or act with "
        "either hand. " + role + " ONE short note, answer, or "
        "proposal (<=60 words) in the shared log about the current "
        "state. To propose work, begin with 'Proposal:'; to dispose "
        "of a proposal, begin with 'Ack:', 'Veto:', or 'Adopt:'.")


class OutputChannel:
    """Wrapper-level single-voice mutex.

    Both hemispheres may emit, but only one may hold the channel at
    a time. `emit` records the holder for the entire sink call, then
    releases it; concurrent emit calls therefore serialize instead
    of interleaving two voices.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.holder = None
        self.history = []

    def emit(self, side, text, sink=None):
        if side not in HEMISPHERES:
            raise ValueError(f"unknown hemisphere: {side}")
        if not HEMISPHERES[side]["may_emit_user_output"]:
            raise PermissionError(f"{side} may not emit user output")
        record = {"ts": time.time(), "side": side,
                  "text": str(text)[:MAX_TEXT_CHARS]}
        with self._lock:
            self.holder = side
            try:
                if sink is not None:
                    sink(record["text"])
                self.history.append(record)
                return record
            finally:
                self.holder = None


OUTPUT_CHANNEL = OutputChannel()


def emit(side, text, sink=None):
    """Emit through the process-wide output mutex."""
    return OUTPUT_CHANNEL.emit(side, text, sink=sink)


class CrossTalk:
    """The shared cross-talk log: append-only JSONL both hemispheres
    (and Zak) can read. One writer discipline: every entry lands via
    append(); rotation keeps the file under its cap."""

    KINDS = ("note", "proposal", "question", "ack", "veto", "error")

    def __init__(self, path, cap_bytes=DEFAULT_CAP_BYTES):
        self.path = path
        self.cap_bytes = cap_bytes
        self._lock = threading.Lock()

    def append(self, entry):
        """entry: {ts, side, kind, text, tokens, est_joules, ...}.
        Text is truncated to MAX_TEXT_CHARS — the log is a working
        memory, not an archive of monologues."""
        e = dict(entry)
        e.setdefault("ts", time.time())
        e["text"] = str(e.get("text", ""))[:MAX_TEXT_CHARS]
        line = json.dumps(e) + "\n"
        with self._lock:
            os.makedirs(os.path.dirname(self.path) or ".",
                        exist_ok=True)
            self._rotate_if_needed(len(line))
            with open(self.path, "a") as f:
                f.write(line)
        return e

    def _rotate_if_needed(self, incoming):
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return
        if size + incoming <= self.cap_bytes:
            return
        # keep two generations: .1 (newest archive), .2 (oldest)
        try:
            if os.path.exists(self.path + ".1"):
                os.replace(self.path + ".1", self.path + ".2")
            os.replace(self.path, self.path + ".1")
        except OSError:
            pass

    def read_recent(self, n=20):
        try:
            lines = open(self.path).read().splitlines()
        except OSError:
            return []
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out


def llm_call(server, prompt, n_predict=128, temperature=0.5):
    """One completion from a llama-server. Returns (text, tokens);
    (None, 0) on ANY error — this layer must never raise into the
    dweller tick."""
    body = json.dumps({"prompt": prompt, "n_predict": n_predict,
                       "temperature": temperature,
                       "cache_prompt": False}).encode()
    req = urllib.request.Request(
        server.rstrip("/") + "/completion", data=body,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
    except Exception:
        return None, 0
    text = data.get("content")
    if text is None:
        return None, 0
    tokens = None
    timings = data.get("timings") or {}
    if isinstance(timings.get("predicted_n"), int):
        tokens = timings["predicted_n"]
    if tokens is None:
        tokens = max(1, len(text) // 4)   # rough fallback estimate
    return text, tokens


def _default_call(side):
    server = HEMISPHERES[side]["server"]

    def call(prompt):
        return llm_call(server, prompt)
    return call


def _render_recent(entries, n=5):
    lines = []
    for e in entries[-n:]:
        lines.append(f"[{e.get('side', '?')}/{e.get('kind', '?')}] "
                     f"{str(e.get('text', ''))[:200]}")
    return "\n".join(lines) if lines else "(log is empty)"


def _classify_exchange(text):
    low = text.lower()
    if "propos" in low:
        return "proposal"
    if "veto" in low:
        return "veto"
    if low.lstrip().startswith(("ack:", "adopt:")):
        return "ack"
    if text.rstrip().endswith("?"):
        return "question"
    return "note"


# Backwards-compatible aliases for older harness imports/tests.
_classify_right = _classify_exchange
_classify_left = _classify_exchange


def _one_exchange_entry(side, call, prompt, classify):
    """Run one hemisphere's call; any failure becomes an error entry.
    Returns the entry dict (already shaped for the log)."""
    try:
        text, tokens = call(prompt)
    except Exception as e:            # injected callables may raise
        text, tokens = None, 0
        err = str(e)[:120]
    else:
        err = None
    if text is None:
        return {"ts": time.time(), "side": side, "kind": "error",
                "text": f"hemisphere unreachable ({err})" if err
                        else "hemisphere unreachable",
                "tokens": 0, "est_joules": 0.0,
                "joules_basis": JOULES_BASIS}
    text = str(text).strip()
    kind = classify(text) if text else "note"
    return {"ts": time.time(), "side": side, "kind": kind,
            "text": text[:MAX_TEXT_CHARS], "tokens": tokens,
            "est_joules": round(tokens * JOULES_PER_TOKEN_EST, 2),
            "joules_basis": JOULES_BASIS}


def run_exchange(state_summary, talk, left_call=None, right_call=None,
                 cycle=None):
    """One symmetric bilateral cycle.

    The first speaker alternates by cycle parity: odd cycles open
    with RIGHT, even cycles open with LEFT. When `cycle` is omitted
    it is inferred from the number of completed two-entry exchanges
    already in the log. Both entries are appended to `talk` and
    returned for logging/coordination. If the caller surfaces either
    side's text, it must do so through `emit()` so the wrapper-level
    output mutex grants the channel to one hemisphere at a time.
    """
    calls = {"left": left_call or _default_call("left"),
             "right": right_call or _default_call("right")}
    if cycle is None:
        cycle = len(talk.read_recent(10000)) // 2 + 1
    order = ("right", "left") if int(cycle) % 2 == 1 \
        else ("left", "right")
    recent = _render_recent(talk.read_recent(5))
    entries = []
    first_entry = None
    for idx, side in enumerate(order):
        if idx == 0:
            prompt = (_frame(side, first=True)
                      + "\n\nCurrent state:\n" + state_summary
                      + "\n\nShared log (recent):\n" + recent
                      + "\n\nYour opening:")
        else:
            other = order[0]
            prompt = (_frame(side, first=False)
                      + "\n\nCurrent state:\n" + state_summary
                      + f"\n\nThe {other} hemisphere just posted:\n["
                      + first_entry["kind"] + "] "
                      + first_entry["text"][:300]
                      + "\n\nYour response:")
        entry = _one_exchange_entry(side, calls[side], prompt,
                                    _classify_exchange)
        entry["cycle"] = int(cycle)
        entry["speaking_order"] = idx + 1
        talk.append(entry)
        entries.append(entry)
        if idx == 0:
            first_entry = entry
    return entries


# ---------------------------------------------------------------------------
def _selftest():
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    tmp = tempfile.mkdtemp()
    path = os.path.join(tmp, "crosstalk.jsonl")
    talk = CrossTalk(path)

    def fake_right(prompt):
        assert "RIGHT hemisphere" in prompt
        return "Proposal: parse the Takeout backlog during " \
               "DEEP_NIGHT dwell, it is the top deficit.", 18

    def fake_left(prompt):
        assert "LEFT hemisphere" in prompt
        assert "ambidextrous" in prompt
        if "just posted" in prompt:
            assert "Proposal:" in prompt  # left saw right's entry
        return "Ack: agreed, the parse is queued for the night " \
               "window at trickle clocks.", 14

    entries = run_exchange("phase RETURN, knowledge deficit 0.69",
                           talk, left_call=fake_left,
                           right_call=fake_right, cycle=1)
    check("exchange returns two entries", len(entries) == 2)
    check("odd cycle: right opens with a proposal",
          entries[0]["side"] == "right"
          and entries[0]["kind"] == "proposal")
    check("left responds and disposes",
          entries[1]["side"] == "left" and entries[1]["kind"] == "ack")
    entries_even = run_exchange("phase RETURN, knowledge deficit 0.69",
                                talk, left_call=fake_left,
                                right_call=fake_right, cycle=2)
    check("even cycle: speaking order alternates to left first",
          entries_even[0]["side"] == "left"
          and entries_even[1]["side"] == "right")
    check("joules labelled as estimate",
          entries[0]["joules_basis"] == "est 0.5 J/tok"
          and entries[0]["est_joules"] == 9.0)
    logged = talk.read_recent(10)
    check("exchange entries persisted to the log",
          len(logged) == 4 and logged[0]["side"] == "right"
          and logged[2]["side"] == "left")

    check("hemispheres are symmetric in the table",
          HEMISPHERES["right"]["may_emit_user_output"] is True
          and HEMISPHERES["left"]["may_emit_user_output"] is True
          and HEMISPHERES["right"]["controls"] == "either_hand"
          and HEMISPHERES["left"]["controls"] == "either_hand"
          and HEMISPHERES["right"]["roles"]
          == HEMISPHERES["left"]["roles"])

    # Output mutex: two slow emitters must serialize, and the holder
    # must be visible/recorded while each sink call is in flight.
    channel = OutputChannel()
    active = []
    holders = []
    concurrency = {"now": 0, "max": 0}

    def slow_sink(text):
        concurrency["now"] += 1
        concurrency["max"] = max(concurrency["max"], concurrency["now"])
        active.append(text)
        holders.append(channel.holder)
        time.sleep(0.03)
        active.remove(text)
        concurrency["now"] -= 1

    threads = [threading.Thread(target=channel.emit,
                                args=(side, side, slow_sink))
               for side in ("left", "right")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    check("output mutex serializes concurrent emitters",
          len(channel.history) == 2 and len(active) == 0
          and concurrency["max"] == 1
          and holders in (["left", "right"], ["right", "left"]))

    # failing server: error entries, no raise
    def dead(prompt):
        return None, 0

    def raiser(prompt):
        raise RuntimeError("boom")

    e2 = run_exchange("state", talk, left_call=dead,
                      right_call=raiser)
    check("failing servers -> error entries, no exception",
          all(e["kind"] == "error" for e in e2))

    # rotation: tiny cap, many entries -> archives appear, size kept
    path2 = os.path.join(tmp, "talk2.jsonl")
    talk2 = CrossTalk(path2, cap_bytes=600)
    for i in range(30):
        talk2.append({"side": "right", "kind": "note",
                      "text": "x" * 100, "tokens": 1,
                      "est_joules": 0.5})
    check("rotation archives exist",
          os.path.exists(path2 + ".1"))
    check("live log stays near cap",
          os.path.getsize(path2) <= 600 + 200)
    check("read_recent still parses after rotation",
          len(talk2.read_recent(3)) >= 1
          and all("side" in e for e in talk2.read_recent(3)))
    print("ALL PASS" if ok else "SOME FAILED")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if _selftest() else 1)
