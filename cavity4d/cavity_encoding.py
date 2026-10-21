"""
cavity_encoding.py — iteration-1 encoding front-ends for the audio cavity.

v1 debt (measured): rectified readout signatures are mutually >0.99 cosine —
the encoding carries almost no decisiveness; the bank of prompt spectra is
highly correlated and the readout inherits it.

Two front-ends, both applied identically to templates, calibration runs and
test inputs (an encoding is a door, not a cheat):

  WHITENING — project spectra through the floored pseudoinverse square root
  of the bank covariance (mode space). Directions the bank barely uses get
  amplified up to the floor; directions the bank saturates get compressed.
  The sigma floor is mandatory: with 13 templates in 32 modes the
  covariance has ~19 null directions, and an unfloored inverse would hand
  the cavity pure amplified noise. Whitening strength = the floor tau
  (fraction of the largest eigenvalue).

  PHASE SPREAD — multiply every mode by a fixed random unit-modulus phase
  (one codebook, seeded). A diagonal unitary: raw pairwise cosines are
  unchanged, but the square-law autocorrelation signature mixes modes with
  offsets, so the fixed phase pattern decorrelates the rectified
  signatures across templates.
"""

import numpy as np


def build_whitener(bank_vecs, tau):
    """W = C^{-1/2} with eigenvalues floored at tau * lambda_max.
    bank_vecs: (K, N) array of template spectra (rows)."""
    V = np.asarray(bank_vecs, dtype=np.complex128)
    K, N = V.shape
    C = (V.T @ V.conj()) / K                      # E[v v^H], mode space
    lam, U = np.linalg.eigh(C)
    floor = tau * lam.max()
    w = 1.0 / np.sqrt(np.maximum(lam, floor))
    W = (U * w) @ U.conj().T
    return W


def make_phases(seed=99, n_modes=32):
    rng = np.random.default_rng(seed)
    return np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, n_modes))


def encode(vec, W=None, phases=None):
    """Apply whitening (optional) then phase spread (optional), renormalize
    to unit norm (the v1 encoders all emit unit-norm spectra)."""
    out = np.asarray(vec, dtype=np.complex128)
    if W is not None:
        out = W @ out
    if phases is not None:
        out = out * phases
    n = np.linalg.norm(out)
    return out / n if n > 0 else out


def mean_mutual_cosine(vecs):
    """Mean |cosine| over off-diagonal pairs of a vector set."""
    V = np.asarray(vecs)
    K = len(V)
    vals = []
    for i in range(K):
        for j in range(i + 1, K):
            nx, ny = np.linalg.norm(V[i]), np.linalg.norm(V[j])
            if nx > 0 and ny > 0:
                vals.append(abs(np.vdot(V[i], V[j])) / (nx * ny))
    return float(np.mean(vals)) if vals else 0.0
