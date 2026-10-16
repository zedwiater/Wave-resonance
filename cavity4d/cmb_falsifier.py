"""CMB universality falsifier — Planck SMICA map as wave driver.

Red pen answer: DIRECT WAVEFORM, bypass bits entirely.
The CMB is analog. Quantizing float microkelvin to bits strips
the continuous phase and thermal fluctuation spectrum.

Method:
1. Download Planck 2018 SMICA map + mask from IRSA (or use local).
2. healpy: read, apply mask, extract clean-sky disc patches.
3. Convert uK fluctuations to wave driver: scales QF rail baseline
   psi_baseline, acts as external driving term in wave equation.
4. Feed patches into cavity grid as background thermal drive.
5. Inject l=2 soliton, test stability under real Planck noise.
6. FALSIFIER: run with SMICA and Commander. If condensate
   geometry differs, universality claim is method-sensitive -> dies.

Bits only at readout: like a radio telescope, the grid treats
the universe as analog waveform. Bits generated only when an
l-winding collapses or anchor registers state change.
"""
import json
import os
import numpy as np

# Paths (IRSA Planck release_3, or local cache)
IRSA_BASE = "https://irsa.ipac.caltech.edu/data/Planck/release_3/maps"
SMICA_FILE = "COM_CMB_IQU-smica_2048_R3.00_full.fits"
MASK_FILE = "COM_Mask_CMB-common-Mask-Int_2048_R3.00.fits"
COMMANDER_FILE = "COM_CMB_IQU-commander_2048_R3.00_full.fits"
CACHE_DIR = os.path.expanduser("~/wave-sunday/data/cmb")


def ensure_data():
    """Download if not cached. Returns paths."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    import urllib.request
    paths = {}
    for fname in [SMICA_FILE, MASK_FILE, COMMANDER_FILE]:
        local = os.path.join(CACHE_DIR, fname)
        if not os.path.exists(local):
            url = f"{IRSA_BASE}/{fname}"
            print(f"Downloading {fname}...", flush=True)
            urllib.request.urlretrieve(url, local)
        paths[fname] = local
    return paths


def extract_patches(map_path, mask_path, n_patches=8, disc_radius_deg=5.0):
    """Extract clean-sky disc patches via healpy.

    Returns list of 2D arrays (uK fluctuations).
    """
    import healpy as hp

    # Read temperature field (field 0 = I)
    cmb_map = hp.read_map(map_path, field=0, verbose=False)
    mask = hp.read_map(mask_path, verbose=False)

    # Apply mask (set masked pixels to UNSEEN)
    cmb_map[mask < 0.5] = hp.UNSEEN

    nside = hp.npix2nside(len(cmb_map))
    patches = []

    # Clean-sky centers: avoid galactic plane (|b| > 30 deg)
    # Use fixed seed for reproducibility
    rng = np.random.RandomState(42)
    attempts = 0
    while len(patches) < n_patches and attempts < 100:
        attempts += 1
        # Random point with |b| > 30
        theta = np.arccos(rng.uniform(-1, 1))  # colatitude
        phi = rng.uniform(0, 2 * np.pi)
        b = 90 - np.degrees(theta)  # galactic latitude
        if abs(b) < 30:
            continue
        vec = hp.ang2vec(theta, phi)
        disc_rad = np.radians(disc_radius_deg)
        pix = hp.query_disc(nside, vec, disc_rad)
        vals = cmb_map[pix]
        # Skip if >10% masked
        if np.sum(vals == hp.UNSEEN) > 0.1 * len(vals):
            continue
        vals = np.where(vals == hp.UNSEEN, 0.0, vals)
        patches.append(vals)

    return patches, nside


def patch_to_driver(patch_vals, nside, target_shape=(48, 64)):
    """Convert uK patch to wave driver on cavity grid.

    The uK fluctuations scale the QF rail baseline:
      psi_drive = (dT / T_cmb) * psi_scale

    dT/T ~ 1e-5 typical. We normalize to unit variance then
    scale to a physical driver amplitude.
    """
    import healpy as hp

    # Normalize: zero mean, unit variance
    v = patch_vals - np.mean(patch_vals)
    std = np.std(v)
    if std > 0:
        v = v / std

    # Reshape: healpy disc pixels -> 2D grid via interpolation
    # Simple approach: use hp.mollview-like reprojection is overkill.
    # Instead, treat patch as 1D and tile/interpolate to target.
    # Better: use the angular positions to grid.
    # For now: reshape via linear interpolation to target shape.
    n_target = target_shape[0] * target_shape[1]
    # Interpolate 1D patch to target size
    x_old = np.linspace(0, 1, len(v))
    x_new = np.linspace(0, 1, n_target)
    v_interp = np.interp(x_new, x_old, v)
    driver = v_interp.reshape(target_shape)

    # Scale: dT/T ~ 1e-5, but we want a measurable drive
    # Use normalized units where driver amplitude ~0.1 (10% of typical psi)
    driver = driver * 0.1
    return driver


def run_falsifier(patches_smica, patches_commander, n_ticks=30):
    """Universality test: l=2 soliton stability under real CMB drive.

    For each patch set (SMICA, Commander):
      - Inject l=2 soliton into cavity
      - Apply patch as background thermal driver
      - Run N ticks, measure l integrity

    FALSIFIER: if SMICA and Commander yield different condensate
    geometries (different l survival rates), universality dies.
    """
    import cavity4d as C
    import cavity_orbits as CO

    results = {}
    for label, patches in [("smica", patches_smica),
                           ("commander", patches_commander)]:
        survived = 0
        total = len(patches)
        for patch in patches:
            np.random.seed(99)
            psi0 = C.fill_from_spectra("spectra/decay_bh_g001.npz", 0)
            psi0 = C.propagate(psi0, 4.0, 10, gain_G=1.5)

            # Inject l=2 soliton at center
            rho = np.linspace(0.3, 3.0, C.NR)
            phi = np.linspace(0, 2 * np.pi, C.NPHI, endpoint=False)
            RHO, PHI = np.meshgrid(rho, phi, indexing="ij")
            r0, p0 = 1.5, np.pi
            dphi = (PHI - p0 + np.pi) % (2 * np.pi) - np.pi
            x = RHO - r0
            y = dphi * r0
            r2 = x**2 + y**2
            theta = np.arctan2(y, x)
            soliton = 0.4 * np.exp(-r2/(2*0.3**2)) * np.exp(1j*2*theta)
            iz = C.NZ // 2
            for k in range(C.NZ):
                psi0[:, :, k] = psi0[:, :, k] + soliton * np.exp(-0.5*((k-iz)/3)**2)

            # CMB driver as external thermal drive
            # Add to psi as background fluctuation (direct waveform)
            driver_2d = patch_to_driver(patch, 2048)  # nside placeholder
            # Broadcast driver across z
            for k in range(C.NZ):
                psi0[:, :, k] = psi0[:, :, k] + driver_2d * 0.5

            sys = CO.CavitySystem(
                psi0.copy(), gamma_univ=0.008,
                use_viscosity=True, visc_nu0=0.02,
                visc_mode="smoothstep", visc_eps=0.1,
                visc_g_lo=2.0, visc_g_hi=4.0)

            for t in range(n_ticks):
                sys.tick(dt_tick=4.0, use_bodies=False)

            # Measure l at injection site
            ir = int(np.argmin(np.abs(rho - r0)))
            vals = sys.psi[ir, :, iz]
            F = np.fft.fft(vals)
            idx = int(np.argmax(np.abs(F)))
            n = len(F)
            ell = idx if idx <= n // 2 else idx - n
            if ell == 2:
                survived += 1

        results[label] = {
            "survived": survived,
            "total": total,
            "rate": round(survived / max(total, 1), 3),
        }

    # Falsifier verdict
    r_s = results["smica"]["rate"]
    r_c = results["commander"]["rate"]
    verdict = "PASS" if abs(r_s - r_c) < 0.25 and r_s > 0.5 else "FAIL"

    results["verdict"] = verdict
    results["note"] = (
        "PASS: l=2 survives real CMB noise, method-independent. "
        "FAIL: either CMB destroys topology or result is method-sensitive."
    )
    return results


def main():
    print("Step 1: Ensuring CMB data...", flush=True)
    try:
        paths = ensure_data()
    except Exception as e:
        print(json.dumps({"error": f"Download failed: {e}",
                          "hint": "Manual download from IRSA to " + CACHE_DIR}),
              flush=True)
        return

    print("Step 2: Extracting SMICA patches...", flush=True)
    patches_smica, nside = extract_patches(paths[SMICA_FILE], paths[MASK_FILE])

    print("Step 3: Extracting Commander patches...", flush=True)
    patches_cmd, _ = extract_patches(paths[COMMANDER_FILE], paths[MASK_FILE])

    print(f"Got {len(patches_smica)} SMICA, {len(patches_cmd)} Commander patches",
          flush=True)

    print("Step 4: Running universality falsifier...", flush=True)
    results = run_falsifier(patches_smica, patches_cmd)

    print(json.dumps(results, indent=2), flush=True)
    print("CMB falsifier done", flush=True)


if __name__ == "__main__":
    main()
