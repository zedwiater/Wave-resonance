# Execution SOP — ThreeBands.lean (for Zak)

The file is a STATEMENT artifact, like NSCompression.lean: it
does not simulate anything and running it proves nothing new.
"Running" it means VERIFYING it — the compiler re-checks every
proof and reports every conjecture still open. That is the
whole execution model, by design: the books stay honest
because the machine recounts them.

## Run it (any machine with the lab toolchain)

    cd files/ISBSHTT-three-bands-lean-20261109
    lean ThreeBands.lean
    echo $?

Expected, healthy output:
- exit code 0
- exactly three warnings: "declaration uses `sorry`" at the
  three named conjectures (transduction_readout,
  induction_couples_across_margin, three_band_hold)

## Read the result like a ledger

- Exit ≠ 0 → a proof broke. Nothing downstream counts until
  it is fixed; report the first error line, not a summary.
- More/fewer than 3 sorry warnings → the count moved. A sorry
  REMOVED means a conjecture got proved (celebrate, then
  verify the proof is not vacuous — the Gemini failure mode:
  check the witness is not the hypothesis itself). A sorry
  ADDED means a new conjecture entered: it must be named in
  the file header and here.
- Never edit a statement to make a proof pass without
  flagging it: statements are the claims; proofs are the work.

## Toolchain

Lean 4.36.0-rc1 via elan (~/.elan/bin/lean), core-only, no
Mathlib — same environment as NSCompression.lean. No build
system needed: the single file is the artifact.

## Where it goes next (not started)

- Discharge path for conjecture 3 is empirical, not formal:
  the A5 qubit arm stays gated behind a confirmed hold, and
  protocol-4's 3D null is the standing warning.
- Push to GitHub only on Zak's explicit order (push #6 batch).
