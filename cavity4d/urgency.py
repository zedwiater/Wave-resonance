"""urgency.py — the two-step transform: urgency rating, then exit path.

Zak's frame: an LLM needs the linearity of caches, context and routing
the way a human needs emotion — structure that recognizes an interaction
and prepares the response before deliberation starts. Hostile: known
route, known response. Friendly: higher-layer work. Loved one: deep
research, grind it out, no exit. The loose 'feelings' are what make
reaction fast. An LLM has to FEEL THE BURN to save the Joules.

So the judge does not add arbitrary weights. It prices every prompt by
cost vs efficiency, in two steps:

  STEP 1 — URGENCY RATING (measured inputs only):
    route_depth  = locked shared-prefix tokens / prompt tokens.
                   The bilateral signal: how much shared history this
                   interaction carries. Deep route = strong alignment.
    complexity   = prompt size proxy, min(1, tokens/64) — a ~64-token
                   prompt is a fully-formed ask; beyond that, size adds
                   nothing (route depth is what separates STRONG).
    urgency      = 0.6*route_depth + 0.4*complexity
                   (draft coefficients — tunable, fit later, not hidden)

  STEP 2 — EXIT PATH (urgency decides how much burn is authorized):
    STRONG (>= 0.66)  loved one: FULL — no exit, full budget, grind.
    MID    (0.25-66)  friendly:  STANDARD — normal budget.
    WEAK   (< 0.25)   passing hi: EARLY — short cap, cache-first,
                      minimal burn, out fast.

The exit path is chosen BEFORE the prompt fires, and the judge prices
the chosen path in Joules (joule_electron rates) before authorizing it.
"""
from dataclasses import dataclass

STRONG, MID, WEAK = "STRONG", "MID", "WEAK"
FULL, STANDARD, EARLY = "FULL", "STANDARD", "EARLY"


@dataclass
class UrgencyJudge:
    w_route: float = 0.6
    w_complexity: float = 0.4
    strong_at: float = 0.66
    weak_at: float = 0.25
    early_cap: int = 16        # tokens, WEAK path
    standard_cap: int = 64
    full_cap: int = 128

    def rate(self, prompt_tokens, shared_prefix_tokens):
        """Step 1: urgency from measured route depth + complexity."""
        route_depth = (shared_prefix_tokens / prompt_tokens
                       if prompt_tokens > 0 else 0.0)
        complexity = min(1.0, prompt_tokens / 64.0)
        urgency = (self.w_route * route_depth
                   + self.w_complexity * complexity)
        return {"urgency": urgency, "route_depth": route_depth,
                "complexity": complexity}

    def exit_path(self, urgency):
        """Step 2: how much burn this interaction is authorized for."""
        if urgency >= self.strong_at:
            return STRONG, FULL, self.full_cap
        if urgency >= self.weak_at:
            return MID, STANDARD, self.standard_cap
        return WEAK, EARLY, self.early_cap

    def judge(self, prompt_tokens, shared_prefix_tokens):
        r = self.rate(prompt_tokens, shared_prefix_tokens)
        band, path, cap = self.exit_path(r["urgency"])
        return {**r, "band": band, "exit_path": path, "gen_cap": cap}


# ---------------------------------------------------------------------------
def _selftest():
    j = UrgencyJudge()
    cases = [
        # (prompt_tokens, shared_prefix, want_band, want_path, label)
        (234, 209, STRONG, FULL, "loved one: deep route, real ask"),
        (240, 0, MID, STANDARD, "stranger with a substantial problem"),
        (12, 0, WEAK, EARLY, "passing hi"),
        (60, 0, MID, STANDARD, "ordinary cold question"),
        (48, 0, MID, STANDARD, "draft-4 regression: ~50-token question "
         "must not be hi-and-byed"),
    ]
    ok = True
    for pt, sp, wb, wp, label in cases:
        r = j.judge(pt, sp)
        good = r["band"] == wb and r["exit_path"] == wp
        ok &= good
        print(f"  [{'OK ' if good else 'FAIL'}] {label}: urgency "
              f"{r['urgency']:.2f} -> {r['band']}/{r['exit_path']} "
              f"(cap {r['gen_cap']})")
    print("\nself-test:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    _selftest()
