# Neural Thread: Data Inventory & Test Queue

**Started:** 2026-10-18
**Purpose:** Organize what's pullable now for the brain-as-cavity-resonator
thread. No new hardware required for any item below except where marked.

---

## 1. Simultaneous EEG-fMRI (the coherence-vs-BOLD test)

**Framework prediction:** Gamma *phase coherence* (narrowband, high Q)
anticorrelates with BOLD amplitude — high coherence + low BOLD = efficient
resonator. Note: this is about *coherence*, not *power*. Existing literature
mostly correlates gamma *power* with BOLD (usually positive). The
distinguishing test is phase-locking value (PLV) or spectral Q vs BOLD.

**Useful literature found:**
- Resting-state simultaneous EEG-fMRI (deconvolution analysis): most
  zero-lag EEG-BOLD correlations are NEGATIVE. Authors describe an "idling"
  mechanism of simultaneous electric-metabolic anticorrelation — directly
  compatible with the framework's efficiency claim.
  (sciencedirect.com/science/article/abs/pii/S1053811916304906)
- Attentional task: trial-by-trial BOLD correlates positively with
  narrowband 60–80 Hz gamma power, negatively with alpha/beta.
  (PMC8952790)
- Working memory: gamma showed only positive BOLD correlations in
  DLPFC/MPFC — but again, *power*, not *coherence*.
  (PMC2858659)
- Intracranial EEG + fMRI (semantic control): gamma-band energy
  differences colocalize with BOLD clusters — spatial correspondence
  established, coherence-vs-power question open.

**Gap:** Nobody has published PLV/Q-factor vs BOLD directly. That's the
opening. Needs: simultaneous EEG-fMRI dataset with a working-memory or
attention task → compute gamma PLV per trial → correlate with BOLD.

**Pullable datasets:** HCP (db.humanconnectome.org) has simultaneous
EEG-fMRI in some releases. OpenNeuro has several EEG-fMRI BIDS datasets.
Status: NOT YET PULLED — needs dataset selection + download (large).

## 2. MEG working-memory n-back (the 90° coupling test)

**Framework prediction:** Toroidal/poloidal field decomposition shows
~90° coupling during high-integration phases (2-back > 0-back).

**Pullable datasets:**
- HCP MEG: n-back working memory task, public at db.humanconnectome.org.
  (PMC6628086 — topological analysis of MEG n-back, confirms dataset exists)
- OpenNeuro ds000117 (Wakeman & Henson): faces task, 400GB with derivatives.
  Standard MNE-Python/Brainstorm tutorial dataset — good for pipeline
  validation before touching HCP.
- MNE-Python built-in fetchers: `mne.datasets` — sample, brainstorm,
  spm_faces, somatosensory. Zero-friction pipeline testing.

**Pipeline:** MNE-Python (free) → source reconstruction → vector field
decomposition into toroidal/poloidal components → coupling angle per
trial → compare 0-back vs 2-back.
Status: NOT YET PULLED. MNE-Python install + ds000117 pipeline test is
the first step (validates the decomposition code before the real data).

## 3. Jaw-clench gamma Q-factor test ($0, needs EEG hardware)

**Mechanism chain:**
1. Voluntary jaw clench → masseter + temporalis contract (lateral
   clamping on temporal/parietal sutures) + tensor tympani contracts
   (middle-ear dampening).
2. Mechanical effect: cranial boundary impedance shifts — suture
   compression changes dielectric/mechanical properties, tensor tympani
   alters internal acoustic resonance.
3. Framework prediction: this is a mechanical pinch bias on the cranial
   cavity → cavity Q-factor changes → gamma band (30–80 Hz) spectral
   peak narrows (Q up) or widens (Q down).

**Protocol:**
- EEG (any headset with gamma-range sampling, even consumer Muse headband
  for pilot).
- Alternate 30s blocks: jaw clenched (moderate, sustainable) vs relaxed.
  5+ blocks each. Eyes open, same visual fixation throughout.
- Compute gamma-band PSD per block (Welch's method, same as subspectra.py).
- Measure Q = f_center / FWHM of the dominant gamma peak per block.
- Compare clenched vs relaxed (paired t-test).

**Prediction:** Clenched → narrower gamma peak (higher Q).
**Falsifier:** No Q difference between conditions.
**Confound to control:** Muscle artifact (EMG) from jaw muscles bleeds
into gamma band. Mitigate: use occipital/parietal electrodes (far from
jaw), ICA artifact rejection, and verify the effect is *narrowing*
(artifact would *broaden*/raise the floor, opposite direction).

**Hardware gap:** Zak has no EEG headset on record. Options: consumer
Muse headband (~$250, pilot-grade), OpenBCI (~$500+, research-grade),
or borrow. NOT YET RUNNABLE.

## 4. Posture/EEG literature (review, no hardware)

**Question:** What's already documented vs what the framework newly predicts?
**Known:** Posture affects EEG (usually attributed to arousal/artifact).
**Framework's new claim:** Specific *spectral* effects — Q-factor changes,
not just amplitude shifts — tied to mechanical cavity tuning.
Status: NOT YET REVIEWED.

---

## Priority order

1. MNE-Python + ds000117 pipeline test (validates decomposition code, free)
2. HCP MEG n-back pull + 90° coupling analysis (the headline test)
3. EEG-fMRI dataset selection for PLV-vs-BOLD (the coherence test)
4. Posture/EEG literature sweep (fills the background)
5. Jaw-clench test (blocked on EEG hardware)
