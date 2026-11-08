# Bilingual Dictionary — academia ↔ plain speech, and the AI-prompting dialect

Compiled 2026-11-08 on Zak Wiater's order, as a companion to the TP filament
light-model paper (Inverse Superfluid Bifurcation Theory). Two dialects,
because there are two translation problems, and Zak's program lives on both:

1. **Academia ↔ plain speech.** The same claim stated in the discipline's
   terms and in kitchen terms. Neither is the "real" one; the pair is the
   dictionary. Rule of use — borrowed from the side dictionary next to this
   file: borrow the word, state the difference once, never let a borrowed
   word smuggle in somebody else's mechanism.
2. **AI prompting dialect.** How to say the claim to a language calculator
   (Gemini, Muse, a local model) so it works on the claim instead of
   admiring it: name the unknowns, demand the falsifier, forbid the gloss.
   Zak's formulation: language calculators parse the equations so people
   don't have to — but they only parse what the prompt actually specifies.

Status labels ride along on every entry: a translation never upgrades a
claim. Graded stays graded, null stays null, ungraded stays ungraded.

## Part I — Academia ↔ plain speech

| Plain speech (Zak's dialect) | Academia's terms | The difference to state once |
|---|---|---|
| The loop is closed | A self-consistent cycle whose outputs sustain its inputs; no open forcing term | "Closed" here means the circuit maintains itself, not that the question is settled |
| Sweet spot | Closure curve / band of marginal stability in parameter space | It is a curve, not a point — maintenance inside a band |
| Null / it died | Null result; the measured quantity is consistent with the control | A null here is retained data, not a failed experiment |
| Gloss | An underspecified step; an assertion carrying no operational content | Naming a gloss is a technical act, not an insult |
| Language calculator | Large language model used as a translation/computation layer | The calculator is an instrument; its output is checked, not believed |
| The wall | A phase boundary held by a phase difference (Δφ); interface | Not a material wall — a maintained difference |
| Settling | Relaxation toward a marginal-stability locus under dissipation | Not "falling down" — flow-mediated relaxation |
| Parking validation / dwell | Acceptance timing; the interval during which a joining request is evaluated | Dwell is a duration with a decision at the end, not a delay |
| The web / scaffolding | Crystallized superfluid filament network; candidate states: supersolid, pinned vortex lattice | NOT cold dark matter halos — the difference is the medium |
| Precipitation (internal) | Phase-slip shedding of twist quanta into an internal inventory | NOT Voit precipitation (baryonic cooling, t_cool ≈ 10 t_ff) — false friend |
| Daughters / second expansion | Secondary nucleation and bifurcation of condensed structures | Merger trees run the other way; this inversion is deliberate |
| Encasement | Second-generation structure formed by daughter bifurcation | Not a shell placed from outside — grown from inside |
| Checkerboard return | Patchy, antiphase acceptance of the poloidal return flux | "Checkerboard" is ours; the published home is counterflow rectification |
| Thermal diode | Directional acceptance across a normal-fraction gradient f = ρₙ/ρ | A gradient in f, not a device |
| Rollin film | Superfluid film creep over a rim under chemical-potential gradient | Real helium physics, used here at vacuum scale — say so |
| Second sound | Entropy/temperature wave in a two-fluid system, u₂² ∝ (TS²/C)(ρₛ/ρₙ) | A heat wave, not an acoustic echo |
| Kin-soup | A decoherence medium composed of the processing qubits' own sibling decoherence | The kinship is the claim; density alone is the control |
| Sacrificed majority | A population fraction spent as the containing medium | A budget line with a ratio, not a defect |
| Pattern hold time X | Coherence/persistence time of a maintained configuration | X is measured, not asserted |
| Near miss | Approximate reconnection of a pattern under similar conditions, graded by residue | Exact reconnection from truly unique data is impossible — by definition here |
| Projection / shadow | The observable cast of a structure; read inversely to infer the source | The shadow is evidence about the projector, not the thing itself |
| Premold | The resolution-setting structure formed before a casting | Its unit scale caps cast fidelity — cf. metamaterial unit cells |
| Metamaterial | Engineered sub-wavelength structure giving effective properties no bulk material has | Today's bench premold; its cell size is its resolution |
| Right energy, right geometry | A two-coordinate gate in (energy, geometry) space | The gate must appear as a boundary, clustered events inside, none outside |
| Quantum foam (our reading) | Planck-scale fluctuation, read here as shadow tightening/loosening | A reading, not the standard usage — flagged as ours |
| Solved (Zak's usage) | Mental closure: the loop is complete in the author's account | Publication status is the ledger's, not the word's — labels stay exact |

## Part II — The AI prompting dialect

Prompts that make a language calculator do work instead of word salad.
Each is a pattern; fill the brackets.

**The falsifier demand.**
"For the claim [X]: state (1) what measurement would kill it, (2) the
control it must beat, (3) the number that decides. If you cannot, say the
claim is not yet testable and name the missing piece."

**The gloss hunt.**
"Read [text]. Flag every sentence that sounds like an explanation but
contains no measurable quantity, no mechanism, and no failure mode. Quote
each one. Do not fix them; list them."

**The steelman.**
"Give the strongest objection to [claim] that a hostile expert in [field]
would raise, with the citation they would use. Then stop — do not answer
your own objection."

**The translation check.**
"Restate [plain-speech claim] in the formal terms of [field]. Then restate
your restatement back into plain speech. Flag anything that changed meaning
in either direction."

**The provenance readback.**
"Before using the material in [source/run], state in one line what run it
came from, what it measured, and what it did not measure."

**The null keeper.**
"Summarize this result without improving it: if the gate failed, say it
failed, name the margin, and name the mechanism the data supports. Do not
offer a rescue the data does not contain."

**The pins table.**
"List every constant in [model] as OBSERVED (with source) or PRESUMED
(flagged). No third category."

**The red pen.**
"Here is draft text. Mark only: claims stronger than their evidence,
numbers without a source, and words borrowed from another mechanism.
Leave the voice alone."

## How the two dialects work together

A claim is born in plain speech (Zak's side). It crosses into academia's
terms through Part I, where its falsifier gets attached. It crosses into
computation through Part II, where a language calculator runs it against
the gate. What survives returns in plain speech — with its status label.
That round trip is the whole method: collaboration through language,
calculation, and approximation. Nothing enters the record upgraded by the
trip.
