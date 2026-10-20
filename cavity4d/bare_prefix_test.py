"""Bare-prefix prime test (draft 5 discriminator).

Hypothesis: this llama.cpp build reuses KV only when the cached
prompt is an EXACT prefix of the incoming request. Drafts 2-4 primed
with prefix+suffix, so diverging warm prompts found nothing reusable.
Prime with the bare prefix this time; if cache_n fires on divergent
suffixes, the route lock is: register bare prefixes only.
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from live_verdict import PREFIX  # noqa: E402

SERVER = "http://localhost:8080"


def fire(prompt, n_predict=16):
    body = json.dumps({"prompt": prompt, "n_predict": n_predict,
                       "cache_prompt": True, "temperature": 0.0}).encode()
    req = urllib.request.Request(SERVER + "/completion", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def show(tag, resp):
    t = resp.get("timings", {})
    print(f"[{tag}] prompt_n={t.get('prompt_n')} cache_n="
          f"{t.get('cache_n')} prompt_ms={t.get('prompt_ms', 0):.0f} "
          f"gen={t.get('predicted_n')}")
    return t


print("prime: BARE prefix (no suffix)")
show("PRIME", fire(PREFIX, 8))

print("warm 1: prefix + divergent suffix A")
show("WARM-A", fire(PREFIX + "Given all of the above, write one "
                    "sentence about what the boundary contributes.", 32))

print("warm 2: prefix + divergent suffix B")
show("WARM-B", fire(PREFIX + "Given all of the above, write one "
                    "sentence about why empty rooms differ from "
                    "living subjects.", 32))

print("control: bare prefix again, exact repeat")
show("CTRL", fire(PREFIX, 8))
