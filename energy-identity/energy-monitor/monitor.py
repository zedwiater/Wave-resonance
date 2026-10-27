#!/usr/bin/env python3
"""Energy Monitor CLI.
  monitor.py voice <audio>   measure a voice file, compare to signature
  monitor.py text  <file>    text-energy PROXY arc, compare to signature
  monitor.py stamp <file>    one line (auto-detects audio vs text)
Every run appends its arc to energy_log.jsonl (subharmonic capture).
"""
import json, sys
from pathlib import Path
import energy

HERE = Path(__file__).parent
PROFILE = HERE / "signature_profile.json"
LOG = HERE / "energy_log.jsonl"
AUDIO_EXT = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac"}

def load_profile():
    return json.loads(PROFILE.read_text()) if PROFILE.exists() else None

def run(path, kind=None):
    p = Path(path)
    kind = kind or ("voice" if p.suffix.lower() in AUDIO_EXT else "text")
    a = energy.analyze_voice(p) if kind == "voice" else energy.analyze_text(p)
    prof = load_profile()
    cmp = energy.compare(a, prof) if prof and len(prof.get("arc", [])) >= 3 else None
    a["stamp"] = energy.stamp(a, cmp)
    if cmp:
        a["vs_signature"] = cmp
    with open(LOG, "a") as f:
        f.write(json.dumps(a) + "\n")
    print(json.dumps(a, indent=1))
    print("STAMP:", a["stamp"])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    run(sys.argv[2], None if sys.argv[1] == "stamp" else sys.argv[1])
