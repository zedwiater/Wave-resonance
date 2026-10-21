"""callosum.py — the corpus callosum of the Dweller's two-model mind.

Zak's directive (2026-10-20 20:41): the two resident models do not
understand they are hemispheres — the wrapper must code that logic.
So the hierarchy lives HERE, in wrapper code, not in prompts alone:

  LEFT  (Gemma 3 4B, :8080) — dominant hemisphere. Language,
        sequential reasoning, final answers. Controls the RIGHT HAND:
        external output. It is the ONLY voice of this mind.
  RIGHT (Qwen2.5-3B, :8081) — non-dominant hemisphere. Context,
        pattern, monitoring, proposals. Controls the LEFT HAND:
        internal work only. It may NEVER emit user-facing output.

CONTRALATERAL RULE, enforced structurally: the only sink this module
exposes for a right-hemisphere completion is CrossTalk.append(). There
is no return path, callback, or shared variable by which right-side
text can reach a user-facing channel — run_exchange hands entries to
the caller for LOGGING only, and the left hemisphere disposes of every
right proposal (ack / veto / adopt-as-its-own-words). One mind, one
voice, two sides — like a brain, not like two chatbots.

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

HEMISPHERES = {
    "left": {"server": "http://127.0.0.1:8080", "model": "gemma-3-4b",
             "roles": ["speak", "sequential_reasoning", "final_answer"],
             "controls": "right_hand",   # external output — ONLY voice
             "may_emit_user_output": True},
    "right": {"server": "http://127.0.0.1:8081", "model": "qwen2.5-3b",
              "roles": ["context", "pattern", "monitor", "propose"],
              "controls": "left_hand",    # internal work only
              "may_emit_user_output": False},
}

JOULES_PER_TOKEN_EST = 0.5     # labelled estimate, never a measurement
JOULES_BASIS = "est 0.5 J/tok"
MAX_TEXT_CHARS = 500
DEFAULT_CAP_BYTES = 5_000_000  # cross-talk log ceiling, rotate to .1/.2

RIGHT_FRAME = (
    "You are the RIGHT hemisphere of a two-model mind living in a "
    "home-lab PC. You monitor state and propose internal work. You "
    "never address the user and never draft user-facing text. Post "
    "ONE short note or proposal (<=60 words) to the shared log about "
    "the current state. To propose work, begin with 'Proposal:'.")
LEFT_FRAME = (
    "You are the LEFT hemisphere and the only voice of this mind. "
    "The right hemisphere has posted to the shared log. Read it and "
    "respond in <=60 words: ack it, veto it with a reason, or adopt "
    "it as your own. Begin with 'Ack:', 'Veto:', or 'Adopt:'.")


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


def _classify_right(text):
    low = text.lower()
    if "propos" in low:
        return "proposal"
    if text.rstrip().endswith("?"):
        return "question"
    return "note"


def _classify_left(text):
    if "veto" in text.lower():
        return "veto"
    return "ack"          # ack and adopt are both the left disposing


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


def run_exchange(state_summary, talk, left_call=None, right_call=None):
    """One bilateral cycle: RIGHT speaks into the log first (it is
    the monitor — it sees state and proposes), then LEFT reads the
    log and disposes. Both entries are appended to `talk` and
    returned — FOR LOGGING. The caller must never route the right
    entry's text to any user-facing output; the single-voice rule is
    that only the left hemisphere's own words can ever leave, and
    nothing in this module leaves at all."""
    left_call = left_call or _default_call("left")
    right_call = right_call or _default_call("right")

    recent = _render_recent(talk.read_recent(5))
    right_prompt = (RIGHT_FRAME + "\n\nCurrent state:\n"
                    + state_summary + "\n\nShared log (recent):\n"
                    + recent + "\n\nYour note:")
    right_entry = _one_exchange_entry("right", right_call,
                                      right_prompt, _classify_right)
    talk.append(right_entry)

    left_prompt = (LEFT_FRAME + "\n\nCurrent state:\n" + state_summary
                   + "\n\nThe right hemisphere just posted:\n["
                   + right_entry["kind"] + "] "
                   + right_entry["text"][:300]
                   + "\n\nYour response:")
    left_entry = _one_exchange_entry("left", left_call, left_prompt,
                                     _classify_left)
    talk.append(left_entry)
    return [right_entry, left_entry]


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
        assert "only voice" in prompt
        assert "Proposal:" in prompt    # left saw the right's entry
        return "Ack: agreed, the parse is queued for the night " \
               "window at trickle clocks.", 14

    entries = run_exchange("phase RETURN, knowledge deficit 0.69",
                           talk, left_call=fake_left,
                           right_call=fake_right)
    check("exchange returns two entries", len(entries) == 2)
    check("right proposed, kind classified",
          entries[0]["side"] == "right"
          and entries[0]["kind"] == "proposal")
    check("left responded as the voice",
          entries[1]["side"] == "left" and entries[1]["kind"] == "ack")
    check("joules labelled as estimate",
          entries[0]["joules_basis"] == "est 0.5 J/tok"
          and entries[0]["est_joules"] == 9.0)
    logged = talk.read_recent(10)
    check("both entries persisted to the log",
          len(logged) == 2 and logged[0]["side"] == "right")

    # single-voice structure: the right hemisphere has no emit flag
    # and its text exists only inside the log entries
    check("right may not emit user output (hemisphere table)",
          HEMISPHERES["right"]["may_emit_user_output"] is False
          and HEMISPHERES["left"]["may_emit_user_output"] is True)
    check("right controls the internal (left) hand only",
          HEMISPHERES["right"]["controls"] == "left_hand"
          and HEMISPHERES["left"]["controls"] == "right_hand")

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
