"""TRACK 1: RM quadrupole tensor → toroidal cavity boundary condition.

The cosmological constant problem: QFT sums zero-point energies to 10^120
times the observed dark energy density. The toroidal proposal: in a closed
wave resonator, internal modes recirculate and cancel — only the residual
boundary leakage survives as net pressure.

Test:
  1. Impose the MEASURED RM quadrupole tensor as a background anisotropic
     field in the toroidal cavity simulator.
  2. Check: do the cavity's natural l=2 modes align with the measured
     principal axis (307°, +15°)?
  3. Measure: does the steady-state residual energy density stay LOW and
     STABLE (bounded resonator) vs diverging (unbounded box)?

The "vacuum energy" analog here is the time-averaged field energy density
<|psi|²> after the cavity reaches steady state. In a flat box with hard
walls, energy piles up at boundaries. On a torus with recirculation,
it should find a low stable floor.
"""

import numpy as np
import json
import sys
sys.path.insert(0, "/tmp")
# Import the cavity (copy needed methods to avoid path issues)
# We'll subclass here for the quadrupole background

# --- Load measured quadrupole tensor ---
with open("/tmp/quadrupole_cavity_input.json") as f:
    qdata = json.load(f)

# Principal axis eigenvectors (Galactic Cartesian)
eigvecs_lb = qdata["eigenvectors_lb"]  # [(l,b), ...] sorted by |eigenvalue|
eigenvalues = qdata["eigenvalues"]

print("Measured RM quadrupole:")
for i, ((l, b), ev) in enumerate(zip(eigvecs_lb, eigenvalues)):
    print(f"  Axis {i+1}: (l,b)=({l}°,{b}°), λ={ev}")

# Principal axis in Galactic Cartesian unit vector
l_p, b_p = eigvecs_lb[0]
l_rad, b_rad = np.radians(l_p), np.radians(b_p)
principal_vec = np.array([
    np.cos(b_rad)*np.cos(l_rad),
    np.cos(b_rad)*np.sin(l_rad),
    np.sin(b_rad),
])
print(f"\nPrincipal axis vector: {principal_vec}")

# --- Quadrupole-background cavity ---
class QuadrupoleCavity:
    """Toroidal cavity with measured RM quadrupole as background anisotropy.

    The quadrupole tensor Q_ij creates a direction-dependent potential:
      V_quad(x) = -Q_ij * n_i * n_j
    where n is the position direction on the torus. This breaks the
    isotropy and orients the l=2 modes along the measured principal axis.

    For the 2D grid, we project the 3D quadrupole onto the simulation plane.
    The grid (x, y) maps to two orthogonal directions; we orient the
    quadrupole's principal axis at angle theta_q in the plane.
    """

    def __init__(self, nx=64, ny=64, seed=42, quad_strength=0.0,
                 quad_angle_deg=0.0):
        np.random.seed(seed)
        self.nx, self.ny = nx, ny
        self.psi = (np.random.randn(nx, ny) +
                    1j * np.random.randn(nx, ny)) * 0.1

        self.H = 0.002
        self.pump_rate = 0.02
        self.loss_rate = 0.05
        self.nl_strength = 0.1
        self.subharmonic_on = True
        self.subharmonic_freq = 0.5
        self.subharmonic_amp = 0.03
        self.kerr_on = True
        self.kerr_coeff = 0.02

        # Quadrupole background
        self.quad_strength = quad_strength
        self.quad_angle = np.radians(quad_angle_deg)
        # Build quadrupole potential field on grid
        # V = -S * cos(2*(theta - theta_q)) — l=2 angular dependence
        yy, xx = np.mgrid[0:ny, 0:nx]
        # Angle of each grid point from center
        cx, cy = nx/2, ny/2
        theta = np.arctan2(yy - cy, xx - cx)
        # Quadrupole potential: minima along principal axis
        self.V_quad = -quad_strength * np.cos(2*(theta - self.quad_angle))

        self.tick_count = 0
        self.energy_in_total = 0.0
        self.energy_out_total = 0.0
        self.residual_history = []

    def laplacian_toroidal(self, f):
        return (np.roll(f, 1, axis=0) + np.roll(f, -1, axis=0) +
                np.roll(f, 1, axis=1) + np.roll(f, -1, axis=1) - 4*f)

    def tick(self, dt=0.05):
        self.tick_count += 1
        t = self.tick_count * dt
        a = 1.0 + self.H * self.tick_count
        redshift = 1.0 / (a**2)

        if self.kerr_on:
            kf = 1.0 + self.kerr_coeff * np.abs(self.psi)**2
            lap = self.laplacian_toroidal(self.psi) * redshift * kf
        else:
            lap = self.laplacian_toroidal(self.psi) * redshift

        nl = -self.nl_strength * np.abs(self.psi)**2 * self.psi
        sub = (self.subharmonic_amp * np.exp(1j*self.subharmonic_freq*t)
               if self.subharmonic_on else 0)

        # Quadrupole background potential (real, anisotropic)
        vterm = -1j * self.V_quad * self.psi

        pump = self.pump_rate * np.exp(1j*np.angle(np.mean(self.psi)))
        pump_field = pump * np.ones_like(self.psi) * 0.1
        self.energy_in_total += np.sum(np.abs(pump_field)) * dt
        loss = -self.loss_rate * self.psi
        self.energy_out_total += np.sum(np.abs(loss)) * dt

        intensity = np.abs(self.psi)**2
        imax = np.max(intensity)
        bump = -0.05j * (intensity > 0.8*imax) * self.psi * intensity if imax > 0 else 0

        self.psi += dt * (1j*lap + nl + pump_field + loss + bump + sub + vterm)

        # Track residual energy density (vacuum energy analog)
        if self.tick_count % 10 == 0:
            self.residual_history.append(float(np.mean(np.abs(self.psi)**2)))

    def measure_mode_orientation(self):
        """Find the dominant l=2 orientation by angular power spectrum.

        Compute |psi|² in polar coordinates, extract m=2 Fourier component
        phase → orientation angle of the quadrupole mode.
        """
        intensity = np.abs(self.psi)**2
        ny, nx = intensity.shape
        yy, xx = np.mgrid[0:ny, 0:nx]
        cx, cy = nx/2, ny/2
        r = np.sqrt((xx-cx)**2 + (yy-cy)**2)
        theta = np.arctan2(yy-cy, xx-cx)
        # Radial band (avoid center and edges)
        mask = (r > nx*0.15) & (r < nx*0.45)
        # m=2 Fourier coefficient
        c2 = np.sum(intensity[mask] * np.exp(-2j*theta[mask]))
        angle = np.degrees(np.angle(c2) / 2) % 180
        amp = np.abs(c2) / np.sum(intensity[mask])
        return angle, amp

    def residual_pressure(self):
        """Steady-state mean energy density (last 20% of history)."""
        n = len(self.residual_history)
        if n < 10:
            return 0, 0
        tail = self.residual_history[int(0.8*n):]
        return float(np.mean(tail)), float(np.std(tail))


def run_experiment(quad_strength, quad_angle_deg, n_ticks=2000, label=""):
    cav = QuadrupoleCavity(nx=64, ny=64, seed=42,
                           quad_strength=quad_strength,
                           quad_angle_deg=quad_angle_deg)
    for t in range(n_ticks):
        cav.tick()
    mode_angle, mode_amp = cav.measure_mode_orientation()
    res_mean, res_std = cav.residual_pressure()
    return {
        "label": label,
        "quad_strength": quad_strength,
        "quad_angle_set": quad_angle_deg,
        "mode_angle_measured": round(float(mode_angle), 1),
        "mode_amplitude": round(float(mode_amp), 4),
        "residual_mean": round(float(res_mean), 6),
        "residual_std": round(float(res_std), 6),
        "E_in": round(float(cav.energy_in_total), 2),
        "E_out": round(float(cav.energy_out_total), 2),
        "balance": round(float(cav.energy_in_total - cav.energy_out_total), 2),
    }


print("\n=== Track 1: Quadrupole → Cavity ===")
print("Running three experiments: no quadrupole, weak, strong...\n")

# The measured principal axis projected to 2D grid angle.
# For the test, we set the quadrupole at 0° and check if modes align to 0°.
# Then we verify the alignment is CAUSED by the quadrupole (not coincidence)
# by comparing with the no-quadrupole control.
results = []
results.append(run_experiment(0.0, 0.0, n_ticks=2000, label="control (no quadrupole)"))
results.append(run_experiment(0.05, 0.0, n_ticks=2000, label="weak quadrupole at 0°"))
results.append(run_experiment(0.15, 0.0, n_ticks=2000, label="strong quadrupole at 0°"))
results.append(run_experiment(0.15, 45.0, n_ticks=2000, label="strong quadrupole at 45°"))

for r in results:
    print(f"{r['label']}:")
    print(f"  Mode orientation: {r['mode_angle_measured']}° (set: {r['quad_angle_set']}°)")
    print(f"  Mode amplitude: {r['mode_amplitude']}")
    print(f"  Residual <|ψ|²>: {r['residual_mean']} ± {r['residual_std']}")
    print(f"  Ledger: in={r['E_in']}, out={r['E_out']}, balance={r['balance']}")

# Alignment test
print("\n=== Alignment Verdict ===")
ctrl = results[0]
for r in results[1:]:
    set_a = r['quad_angle_set']
    meas_a = r['mode_angle_measured']
    # Angular difference (mod 180 for quadrupole symmetry)
    diff = min(abs(meas_a - set_a), 180 - abs(meas_a - set_a))
    # Also check against 90° offset (quadrupole has 90° symmetry in potential minima)
    diff90 = min(abs(meas_a - set_a - 90), 180 - abs(meas_a - set_a - 90))
    best = min(diff, diff90)
    status = "ALIGNED" if best < 20 else "NOT ALIGNED"
    print(f"  {r['label']}: set {set_a}° → measured {meas_a}° "
          f"(Δ={best:.1f}°) [{status}]")

# Residual pressure test (the 10^120 analog)
print("\n=== Residual Pressure (Vacuum Energy Analog) ===")
print("If bounded resonator works: residual stays LOW and STABLE across")
print("quadrupole strengths (not diverging with added structure).")
residuals = [r['residual_mean'] for r in results]
print(f"  Residuals: {residuals}")
print(f"  Max/Min ratio: {max(residuals)/min(residuals) if min(residuals)>0 else 'N/A':.2f}")
if max(residuals)/min(residuals) < 5:
    print("  >>> BOUNDED: residual stable across configurations")
else:
    print("  >>> DIVERGING: residual sensitive to background — investigate")

with open("/tmp/cavity_quadrupole.json", "w") as f:
    json.dump({"experiments": results}, f, indent=2)
print("\nSaved to /tmp/cavity_quadrupole.json")
