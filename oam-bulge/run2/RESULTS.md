# OAM-Bulge Run 2 (closed loop) - Results (verdict first)

- **VERDICT: FAIL (run aborted - see run_summary)** - A(T)/A(0) = -0.173 (bar >= 0.80: FAIL); maintenance score = 0.074 (2/27 readings in-band; bar >= 0.80: FAIL).
- **Bulge:** A(0) = 1.250 (snapshot) / 1.250 (boundary sense); A(T) = -0.216; boundary A_k range [-0.522, 1.250], last sense -0.216; snapshot A range [-0.522, 1.570].
- **Compression:** C(0) = 2.250; C_k range [0.704, 2.250] vs band [1.800, 2.812].
- **Run 1 vs run 2:** A ratio 0.075 (open loop, DECAYED) -> -0.173 (closed loop); wall 2208 s -> 1441 s (run 2 is T=10, run 1 was T=5).
- **Spectrum gradient** (centroid_bulge - centroid_floor): -1.3898 at t=0 -> -0.1625 at t=T (run 1: -1.3898 -> -1.5972); mean first 20% -1.1762, last 20% -0.3559.
- **Twist signature** (Pearson r, dg_k vs centroid change over segment k; lag+1 control; run-1 r in brackets):

## Early window (t <= 1.0, segment by segment)

Run 1's bulge had already collapsed by t=0.5 (A = -0.507); this is the headline comparison.

| k | t | A_k | C_k | in-band | e_k | dg_k | beta_k | A_run1(t) |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.0 | +1.250 | 2.250 | 1 | +0.000 | +0.000 | 0.000 | +1.250 |
| 1 | 0.1 | +0.727 | 1.728 | 0 | +0.523 | +0.500 | 0.262 | +0.721 |
| 2 | 0.2 | +0.898 | 1.980 | 1 | +0.352 | +0.500 | 0.176 | +0.293 |
| 3 | 0.3 | +0.228 | 1.452 | 0 | +1.022 | +0.500 | 0.511 | -0.020 |
| 4 | 0.4 | -0.239 | 0.818 | 0 | +1.489 | +0.500 | 0.745 | -0.431 |
| 5 | 0.5 | -0.146 | 1.001 | 0 | +1.396 | +0.500 | 0.698 | -0.507 |
| 6 | 0.6 | -0.398 | 1.057 | 0 | +1.648 | +0.500 | 0.824 | -0.637 |
| 7 | 0.7 | -0.493 | 0.959 | 0 | +1.743 | +0.500 | 0.872 | -0.738 |
| 8 | 0.8 | -0.205 | 0.966 | 0 | +1.455 | +0.500 | 0.728 | -0.113 |
| 9 | 0.9 | -0.408 | 1.020 | 0 | +1.658 | +0.500 | 0.829 | +0.207 |
| 10 | 1.0 | -0.395 | 1.148 | 0 | +1.645 | +0.500 | 0.822 | -0.221 |

  - bulge: r = -0.13184608165174488, lag-control r = -0.05624470665491987 [run 1: r = -0.5018959446783338, lag = 0.15127081210251225]; mean |dcentroid|/seg = 0.27733
  - floor: r = -0.004506452675582729, lag-control r = -0.38964293666706573 [run 1: r = -0.024125757401984874, lag = -0.36741392084648916]; mean |dcentroid|/seg = 0.18169
  - outside: r = -0.22864121331305354, lag-control r = -0.12950498900990842 [run 1: r = -0.4745616376092351, lag = -0.37266297706274554]; mean |dcentroid|/seg = 0.12070
  - gradient: r = -0.11252679717214963, lag-control r = 0.18350994620495373 [run 1: r = -0.30746027559738043, lag = 0.3187479740955388]; mean |dcentroid|/seg = 0.29399
- **Actuation ledgers:** total dE_twist = +113.2243; total dE_precip = +4568.5421 over 26 active feeds (shortfalls: 0); max |N| change across a boundary actuation = 1.137e-13 (feed conserves N by construction).
- **Books:** cumulative relative N drift max 3.902e-11 (bar 1e-7: PASS); within-segment relative E drift max 3.506e-04 (bar 1e-3: PASS); max Picard sweeps 16, max residual 9.971e-12; max KE fraction above K2=1600: 1.662e-02.
- **Drive:** 27 updates, dg in [0.000, 0.500], G_cum final 13.0; temp curve 35361 samples.
- **Run:** {'N': 128, 'completed_segments': 26, 't_final': 2.5999999999999353, 'aborted': 'SolverNonConvergence: Picard non-convergence: resid=4.964e-11 after 16 sweeps at t=2.6000 arm=base', 'wall_s': 1441.2174999713898, 'G_cum_final': 13.0, 'A_target': 1.2499950693192123, 'C_target': 2.2499950693192123, 'N0': 248.05021344239853, 'E0': 3771.7612501444573}.

Full numbers: results.json; per-snapshot spectra: snapshots.jsonl; per-segment books: books.json; drive: drive_log2.csv; temperatures: temp_curve2.csv.
