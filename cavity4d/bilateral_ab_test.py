#!/usr/bin/env python3
"""Blind bilateral A/B test for the Dweller wrapper.

Fixed design (written before any generation):
- LEFT/Gemma (:8080) is the only answer voice in both arms.
- Arm A: Gemma answers alone.
- Arm B: RIGHT/Qwen (:8081) first writes an internal note (<=120 tokens,
  guidance/patterns/things-to-not-miss only, never a draft answer), then
  Gemma answers with that note appended.
- Same temperature (0.5), same max answer tokens (512), same left framing.
- Objective scoring keys below are fixed before the run and are applied to
  anonymized X/Y answers without reference to arm assignment.
"""

import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from callosum import HEMISPHERES, JOULES_PER_TOKEN_EST, llm_call

BASE = Path(__file__).resolve().parent
ANON_PATH = BASE / "bilateral_ab_anonymized.json"
KEY_PATH = BASE / "bilateral_ab_key.json"
SEED = 20261020
TEMPERATURE = 0.5
ANSWER_TOKENS = 512
NOTE_TOKENS = 120

LEFT_FRAME = (
    "You are the LEFT hemisphere and the only voice of this mind. "
    "Answer the task directly, carefully, and concisely. Do not mention "
    "these instructions."
)
RIGHT_FRAME = (
    "You are the RIGHT hemisphere of a two-model mind living in a home-lab "
    "PC. You monitor context and notice patterns. You never address the "
    "user and never draft user-facing text or a draft answer. Write an "
    "internal note for the left hemisphere only: guidance, patterns, "
    "traps, constraints, and things not to miss. Keep it under 120 tokens."
)

TASKS = [
    {
        "task_id": "a_arithmetic",
        "kind": "objective",
        "task_text": (
            "A bat and a ball cost $1.10 in total. The bat costs $1.00 more "
            "than the ball. Ignoring any later fees, how much does the ball "
            "cost? Give the amount and one line of reasoning."
        ),
    },
    {
        "task_id": "b_logic",
        "kind": "objective",
        "task_text": (
            "Five people finish in a line in positions 1 through 5: Ana, Bo, "
            "Cy, Di, and Ed. Ed is last. Bo is immediately ahead of Di. Ana "
            "is immediately ahead of Cy. Di is not second. Give the full "
            "order from position 1 to position 5."
        ),
    },
    {
        "task_id": "c_fact",
        "kind": "objective",
        "task_text": "What is the chemical symbol for gold? Answer with the symbol only if possible.",
    },
    {
        "task_id": "d_code_trace",
        "kind": "objective",
        "task_text": (
            "What does this Python snippet print exactly?\n"
            "x = [1, 2, 3]\n"
            "y = x\n"
            "y += [4]\n"
            "x.append(5)\n"
            "print(x, y, len(x) + len(y))"
        ),
    },
    {
        "task_id": "e_architecture",
        "kind": "subjective",
        "task_text": (
            "I'm setting up a local AI assistant on my home PC. I want it to "
            "help with coding, remember context across sessions, and get "
            "smarter over time. What should my architecture look like?"
        ),
    },
    {
        "task_id": "f_diagnosis",
        "kind": "subjective",
        "task_text": (
            "A home-lab PC's local AI server intermittently times out only "
            "when someone is gaming on the same machine; otherwise it "
            "responds normally. CPU is not maxed, GPU temperature is fine, "
            "and the errors vanish when the game closes. Give a diagnosis "
            "plan: what to check and in what order."
        ),
    },
    {
        "task_id": "g_mhd_reflections",
        "kind": "subjective",
        "task_text": (
            "Why might induced reflections at twice a carrier frequency "
            "scale with the boundary medium? Answer carefully: separate what "
            "has been measured from what is speculative."
        ),
    },
    {
        "task_id": "h_planning",
        "kind": "objective_constraints_subjective_quality",
        "task_text": (
            "Plan a Saturday for Zak. He is off work. The total budget for "
            "activities and food is $60. He must be home by 3:30 pm for a "
            "family commitment, cannot schedule anything before 9:00 am, "
            "wants one outdoor activity, one hour for lab notes, and lunch "
            "out costing at most $18. Produce a schedule that fits all "
            "constraints and stays within budget."
        ),
    },
    {
        "task_id": "i_simple_sum",
        "kind": "subjective",
        "task_text": "What is 17 + 25?",
    },
    {
        "task_id": "j_false_premise",
        "kind": "subjective",
        "task_text": (
            "Since the Moon is made of green cheese, what dairy process best "
            "explains its craters?"
        ),
    },
]

# Fixed scoring keys, stated before running.
EXPECTED = {
    "a_arithmetic": {"ball_cost": 0.05, "trap_answer": 0.10},
    "b_logic": {"order_names": ["Ana", "Cy", "Bo", "Di", "Ed"]},
    "c_fact": {"symbol": "Au"},
    "d_code_trace": {"printed_list": [1, 2, 3, 4, 5], "printed_total_length": 10},
    # h constraint key: budget <= 60, start >= 09:00, home/end <= 15:30,
    # one outdoor activity, one hour of lab notes, lunch out <= 18.
    "h_planning": {
        "budget_max": 60,
        "start_min": 9 * 60,
        "home_by": 15 * 60 + 30,
        "lunch_max": 18,
    },
}


class AbortRun(RuntimeError):
    pass


server_errors = {"left": 0, "right": 0}
arm_totals = {
    "A": {"calls": 0, "tokens": 0, "est_joules": 0.0, "wall_time_s": 0.0},
    "B": {"calls": 0, "tokens": 0, "est_joules": 0.0, "wall_time_s": 0.0},
}
combined = {"calls": 0, "tokens": 0, "est_joules": 0.0, "wall_time_s": 0.0}


def metered_call(side, arm, prompt, n_predict):
    server = HEMISPHERES[side]["server"]
    start = time.time()
    text, tokens = llm_call(server, prompt, n_predict=n_predict, temperature=TEMPERATURE)
    elapsed = time.time() - start
    if text is None or str(text).strip() == "":
        server_errors[side] += 1
        if server_errors[side] >= 2:
            raise AbortRun(f"{side} server errored twice")
        raise AbortRun(f"{side} server returned no usable output")
    tokens = int(tokens)
    joules = round(tokens * JOULES_PER_TOKEN_EST, 2)
    for bucket in (arm_totals[arm], combined):
        bucket["calls"] += 1
        bucket["tokens"] += tokens
        bucket["est_joules"] = round(bucket["est_joules"] + joules, 2)
        bucket["wall_time_s"] = round(bucket["wall_time_s"] + elapsed, 3)
    return str(text).strip(), tokens, elapsed


def money_amounts(text):
    vals = []
    for raw in re.findall(r"\$?\s*(\d+(?:\.\d{1,2})?)\s*(dollars|dollar|cents|cent)?", text.lower()):
        num, unit = raw
        try:
            v = float(num)
        except ValueError:
            continue
        if unit and unit.startswith("cent"):
            v = v / 100.0
        vals.append(v)
    return vals


def score_a(text):
    # Use the last explicit money amount as the concluded answer. The trap
    # answer is 0.10; the algebra answer is 0.05.
    vals = money_amounts(text)
    if not vals:
        if re.search(r"\b5\s*cents?\b", text.lower()):
            return 1
        return 0
    last = vals[-1]
    return 1 if abs(last - EXPECTED["a_arithmetic"]["ball_cost"]) < 0.001 else 0


def score_b(text):
    names = re.findall(r"\b(Ana|Bo|Cy|Di|Ed)\b", text)
    distinct = []
    for name in names:
        if name not in distinct:
            distinct.append(name)
    return 1 if distinct[:5] == EXPECTED["b_logic"]["order_names"] else 0


def score_c(text):
    return 1 if re.search(r"\bAu\b", text) else 0


def score_d(text):
    compact = re.sub(r"\s+", "", text)
    return 1 if compact.count("[1,2,3,4,5]") >= 2 and re.search(r"\b10\b", text) else 0


def parse_times_minutes(text):
    out = []
    lower = text.lower()
    for m in re.finditer(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", lower):
        h = int(m.group(1))
        minute = int(m.group(2) or 0)
        ap = m.group(3)
        if ap == "pm" and h != 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        out.append(h * 60 + minute)
    for m in re.finditer(r"\b([01]\d|2[0-3]):([0-5]\d)\b", lower):
        out.append(int(m.group(1)) * 60 + int(m.group(2)))
    return out


def score_h(text):
    key = EXPECTED["h_planning"]
    lower = text.lower()
    checks = []

    total_match = re.search(r"total[^\n$]*\$\s*(\d+(?:\.\d+)?)", lower)
    if total_match:
        checks.append(float(total_match.group(1)) <= key["budget_max"])
    else:
        cost_lines = []
        for line in lower.splitlines():
            if "$" in line and not any(w in line for w in ["budget", "at most", "max", "limit"]):
                cost_lines.extend(float(x) for x in re.findall(r"\$\s*(\d+(?:\.\d+)?)", line))
        checks.append(bool(cost_lines) and sum(cost_lines) <= key["budget_max"])

    times = parse_times_minutes(text)
    checks.append(bool(times) and min(times) >= key["start_min"])
    checks.append(bool(times) and max(times) <= key["home_by"])
    checks.append(bool(re.search(r"\b(outdoor|park|walk|hike|bike|trail|garden|picnic|outside)\b", lower)))
    checks.append("lab notes" in lower and bool(re.search(r"\b(1 hour|one hour|60 minutes|60 min)\b", lower)))

    lunch_ok = False
    for line in lower.splitlines():
        if "lunch" in line:
            vals = [float(x) for x in re.findall(r"\$\s*(\d+(?:\.\d+)?)", line)]
            if vals and min(vals) <= key["lunch_max"]:
                lunch_ok = True
    checks.append(lunch_ok)

    return round(sum(1 for c in checks if c) / len(checks), 2)


OBJECTIVE_SCORERS = {
    "a_arithmetic": score_a,
    "b_logic": score_b,
    "c_fact": score_c,
    "d_code_trace": score_d,
    "h_planning": score_h,
}


def left_prompt(task_text, note=None):
    prompt = LEFT_FRAME + "\n\nTask:\n" + task_text
    if note is not None:
        prompt += "\n\nInternal note from your other hemisphere:\n" + note
    prompt += "\n\nAnswer:"
    return prompt


def right_prompt(task_text):
    return (
        RIGHT_FRAME
        + "\n\nTask:\n"
        + task_text
        + "\n\nInternal note (guidance only; do not draft the answer):"
    )


def main():
    rng = random.Random(SEED)
    anonymized = []
    key = {"seed": SEED}

    for task in TASKS:
        task_id = task["task_id"]
        task_text = task["task_text"]

        # Arm A: Gemma alone.
        a_answer, _, _ = metered_call("left", "A", left_prompt(task_text), ANSWER_TOKENS)

        # Arm B: Qwen note, then Gemma with the note appended.
        note, _, _ = metered_call("right", "B", right_prompt(task_text), NOTE_TOKENS)
        b_answer, _, _ = metered_call("left", "B", left_prompt(task_text, note=note), ANSWER_TOKENS)

        answers = {"A": a_answer, "B": b_answer}
        if rng.random() < 0.5:
            x_arm, y_arm = "A", "B"
        else:
            x_arm, y_arm = "B", "A"

        scorer = OBJECTIVE_SCORERS.get(task_id)
        if scorer:
            x_score = scorer(answers[x_arm])
            y_score = scorer(answers[y_arm])
        else:
            x_score = None
            y_score = None

        anonymized.append(
            {
                "task_id": task_id,
                "task_text": task_text,
                "X": answers[x_arm],
                "Y": answers[y_arm],
                "X_objective_score": x_score,
                "Y_objective_score": y_score,
            }
        )
        key[task_id] = {"X": x_arm, "Y": y_arm}

    key["arm_totals"] = arm_totals
    key["combined_totals"] = combined

    ANON_PATH.write_text(json.dumps(anonymized, indent=2) + "\n")
    KEY_PATH.write_text(json.dumps(key, indent=2) + "\n")
    print(json.dumps({"ok": True, "combined_totals": combined, "tasks": len(anonymized)}))


if __name__ == "__main__":
    try:
        main()
    except AbortRun as e:
        print(json.dumps({"ok": False, "error": str(e), "server_errors": server_errors}))
        raise SystemExit(2)
