# Wave-Resonance Feature Spec: Hardware vs Software, Applications & Materials

**Date:** 2026-10-16
**Status:** Draft for Zak's red pen
**Principle:** Software defines the geometry of what should happen; hardware is the thing happening.

---

## SOFTWARE FEATURES (Blueprint — logic, no Joules spent)

### S1. Burn vs Bury Availability Model
**Tag:** SOFTWARE

**Description:** Data availability as geometric access control. Every bit is a wave oscillating in specific geometry. A wave is "available" (readable) only when the geometry permits access. Burning = dissipating the wave (energy to reservoir, destroyed). Burying = changing geometry so the wave persists but is unreachable (behind potential barrier, in wrong mode, inside Hill sphere).

**Applications by industry:**
- **Data centers:** Tiered storage where "cold" data is buried (geometrically inaccessible but intact) vs "deleted" data is burned. Zero-copy archival — change the access geometry, not the bits.
- **Telecommunications:** Conditional packet availability — packets exist in the waveguide but are only "available" to authorized geometric receivers (mode-keyed access).
- **Defense/intelligence:** Bury- don't-burn data sanitization. Data persists for forensics but is geometrically locked. Burning for true destruction.
- **Healthcare:** Patient data buried by default (HIPAA geometric isolation), burned on request. Audit trail of burn-vs-bury decisions.
- **Financial:** Regulatory data retention — bury for compliance period, burn after. Provable destruction via burn ledger.

**Materials (software stack):**
- Geometric access control library (mode-key → accessibility mapping)
- Burn/bury decision engine (policy → geometric transform)
- Availability ledger (tracks which waves are buried where, burn certificates)
- Integration: existing filesystem/block layer via FUSE or kernel module

**User profiles:**
- Data center architects (tiered storage design)
- Security engineers (data lifecycle management)
- Compliance officers (provable deletion)
- Network architects (conditional delivery)

---

### S2. Routing Decisions (Power vs Data Gradient)
**Tag:** SOFTWARE

**Description:** Router reads local energy, mode, position, and gradients to select path: toward power gradient (replenishment) or data gradient (storage/access/manipulation). The missing piece from v14 — the router that should have existed.

**Applications by industry:**
- **Telecommunications:** Energy-aware routing — packets route toward powered repeaters when low, toward data centers when charged. Extends battery life in mesh networks.
- **Data centers:** Workload placement based on power availability (route compute to where energy is cheap/abundant) vs data locality (route to where data lives).
- **AI/ML:** Inference routing — send queries to nodes with power headroom vs nodes with cached weights. Dynamic tradeoff.
- **IoT/edge:** Sensor data routes toward power (solar-charged nodes) or toward gateways (data sinks) based on local energy state.
- **Smart grid:** Power packets (energy) and data packets (telemetry) share infrastructure, routed by gradient type.

**Materials (software stack):**
- Gradient sensor API (local energy, mode, position query)
- Routing table (gradient → next hop mapping)
- Power/data classifier (packet type identification)
- Integration: SDN controller plugin, or eBPF program for kernel-level routing

**User profiles:**
- Network operators (traffic engineering)
- Data center operators (workload placement)
- IoT system designers (edge routing)
- Smart grid engineers (dual-packet routing)

---

### S3. M_0 Ledger (Universal Energy Accounting)
**Tag:** SOFTWARE

**Description:** Global energy bookkeeping: M_0 = E_field + E_reservoir + E_bodies + E_dissipated. Every Joule accounted for. Closes the books — no energy created or destroyed, only transformed. Already proven in cavity sims.

**Applications by industry:**
- **Data centers:** Per-workload energy accounting. Know exactly how many Joules each query, training run, or storage operation costs. Carbon-aware scheduling.
- **Telecommunications:** Per-packet energy cost across the network. Energy-aware SLAs.
- **Energy:** Microgrid energy trading — every device's generation/consumption ledgered. Peer-to-peer energy markets.
- **AI/ML:** Training run energy budgets. "This model cost 4.2 MWh" as a first-class metric alongside accuracy.
- **Consumer electronics:** Battery-aware OS — the M_0 ledger at device scale. Every app's energy cost visible.

**Materials (software stack):**
- Ledger daemon (systemd service or kernel module)
- RAPL/amdgpu-hwmon telemetry integration (already spec'd, needs authorization)
- Per-process/per-packet energy attribution
- API: `m0_balance()`, `m0_charge(joules)`, `m0_audit()`
- Blockchain optional: distributed ledger for multi-party energy trading

**User profiles:**
- Data center sustainability officers (carbon accounting)
- Network operators (energy-aware SLAs)
- AI researchers (training cost transparency)
- OS developers (battery-aware scheduling)
- Energy traders (microgrid markets)

---

### S4. Shapiro Delay Calculator
**Tag:** SOFTWARE

**Description:** Given a mass/energy distribution, compute gravitational time delay for wave packets traversing the region. In network terms: predict latency through high-density zones (data centers, IXPs) based on their "gravitational" pull on packets.

**Applications by industry:**
- **Telecommunications:** Latency prediction through congested exchanges. Route around "heavy" nodes.
- **Financial (HFT):** Microsecond-accurate latency modeling through network topology. Predict which path is truly fastest including congestion-gravity.
- **Data centers:** Capacity planning — model how adding servers (mass) slows packet transit (Shapiro delay).
- **Aerospace:** Deep-space network delay calculation (already done by NASA, but generalized to any mass distribution).
- **Scientific computing:** Distributed simulation synchronization — account for delay through compute-heavy nodes.

**Materials (software stack):**
- Mass distribution mapper (network topology → gravitational field)
- Delay integrator (path integral through potential)
- Real-time updater (as nodes add/remove load, recalculate)
- Integration: BGP/OSPF metric plugin, or standalone planning tool

**User profiles:**
- Network planners (latency engineering)
- HFT infrastructure engineers (microsecond optimization)
- Data center capacity planners
- Aerospace comms engineers

---

### S5. QF Rail Model (Vacuum as Circuit)
**Tag:** SOFTWARE

**Description:** Treat quantum fluctuations as positive/negative terminal rails maintaining baseline potential. The vacuum isn't empty — it's a live circuit with base oscillation. Individual wave packets achieve discrete Planck-scale radiative release against this baseline without short-circuiting.

**Applications by industry:**
- **Semiconductor:** Chip design with vacuum-circuit-aware power delivery. Model substrate noise as QF rails.
- **Quantum computing:** Qubit baseline calibration — the rails define the "zero" that qubits oscillate against. Better error models.
- **Energy:** Zero-point energy harvesting models (theoretical, but the math framework applies).
- **Telecommunications:** Fiber noise floor modeling — the QF rails define the minimum detectable signal.
- **Scientific instruments:** Detector calibration — gravitational wave detectors, quantum sensors.

**Materials (software stack):**
- QF rail simulator (baseline potential field solver)
- Noise floor calculator (minimum signal vs rail oscillation)
- Integration: SPICE-like circuit simulator plugin, or quantum SDK extension

**User profiles:**
- Chip designers (power integrity)
- Quantum engineers (qubit calibration)
- Photonics researchers (noise floor analysis)
- Metrology scientists (precision measurement)

---

## HARDWARE FEATURES (Work — Joules, photons, heat)

### H1. Wave Messenger (ℓ=2 Propagating Packet)
**Tag:** HARDWARE

**Description:** Actual physical wave packet with ℓ=2 orbital angular momentum propagating through fiber at 200,000 km/s. Not a simulation — photons with real OAM traveling through real glass. v14/v15d proved software cannot do this.

**Applications by industry:**
- **Telecommunications:** OAM-multiplexed fiber — each ℓ mode is an independent channel. 48 modes × 200 Tbps = 9.6 Pbps theoretical per fiber.
- **Data centers:** OAM interconnects — top-of-rack switches using mode-division multiplexing instead of wavelength.
- **AI/ML:** Photonic neural network interconnects — ℓ modes as parallel weight channels.
- **Defense:** Mode-keyed secure comms — intercept requires sorting the OAM, which is the #1 hardware gap (natural security).
- **Scientific:** OAM quantum key distribution — high-dimensional quantum states.

**Materials (physical):**
- Single-mode fiber (existing) or few-mode fiber (for OAM preservation)
- OAM generator: spiral phase plate or spatial light modulator (SLM)
- OAM sorter: **BLOCKED** — this is the #1 gap. Options: log-polar transform optics ($5K+), metasurface sorter (research grade), or interferometric sorter (bulk optics)
- Laser source: 1550nm DFB laser (telecom standard), ~$200
- Detector: InGaAs photodiode array or CCD for mode imaging
- Estimated benchtop: $343–486 for signal-and-observe (no sorting); $5K+ with sorting

**User profiles:**
- Telecom R&D engineers (next-gen fiber)
- Data center interconnect architects
- Photonics researchers
- Defense comms engineers

---

### H2. 1D Waveguide (Physical Fiber Channel)
**Tag:** HARDWARE

**Description:** A real optical fiber acting as a 1D waveguide for ℓ-mode packets. Unlike the 3D cavity simulation (which traps and sloshes), a fiber guides — the wave travels ballistically along the axis. This is the physical answer to v15d's failure.

**Applications by industry:**
- **Telecommunications:** Transoceanic cables (already exist — this is the calibration baseline). OAM modes add capacity.
- **Data centers:** Fiber interconnects between racks, rows, buildings.
- **Industrial:** Fiber sensing — pipeline monitoring, structural health, perimeter security (the fiber IS the sensor).
- **Medical:** Endoscopic OAM imaging — ℓ modes for super-resolution through fiber bundles.
- **Aerospace:** Fly-by-light — fiber optic control systems immune to EMI.

**Materials (physical):**
- Standard SMF-28 fiber: $0.50/meter
- Few-mode fiber (for OAM): $5–10/meter
- Hollow-core fiber (lowest latency, for HFT): $50+/meter
- Fiber couplers, splices, connectors: standard telecom parts
- EDFA repeaters (for long haul): $1K–5K each, every 50km

**User profiles:**
- Telecom infrastructure engineers
- Data center cabling architects
- Industrial sensing engineers
- Medical device developers

---

### H3. OAM Sorter/Demultiplexer
**Tag:** HARDWARE — **#1 BLOCKED GAP**

**Description:** Physical device that separates overlapping OAM modes into distinct output channels. The critical missing piece — without this, OAM multiplexing can't be received. This is why the benchtop can observe but not sort.

**Applications by industry:**
- **Telecommunications:** OAM demux at fiber endpoints — separates 48 mode-channels back into individual data streams.
- **Data centers:** Optical mode-router — routes packets by ℓ value without electronic conversion.
- **Quantum:** High-dimensional quantum state measurement — sort entangled OAM photons.
- **Astronomy:** OAM coronagraphy — sort starlight by ℓ to detect exoplanets (vortex coronagraph).
- **Microscopy:** OAM-based super-resolution sorting.

**Materials (physical):**
- **Option A: Log-polar transform** — two custom refractive elements (unwrapper + corrector). $5K–10K custom optics. Highest efficiency (~90%).
- **Option B: Metasurface sorter** — flat optics, nanostructured. Research grade, $2K–5K from foundry. Compact.
- **Option C: Interferometric** — Mach-Zehnder cascade with Dove prisms. Bulk optics, $1K–3K. Lower efficiency, but buildable on bench.
- **Option D: Diffractive** — SLM-based (programmable). $3K for SLM. Flexible but lossy.
- **Recommendation for benchtop:** Start with Option C (interferometric) — buildable, teaches the physics, upgrade later.

**User profiles:**
- Photonics R&D engineers
- Telecom system architects
- Quantum optics researchers
- Astronomical instrument builders

---

### H4. Distributed Edge Power (Hydrogen/Solar Harvesting)
**Tag:** HARDWARE

**Description:** Every edge device and repeater as a local power generation cell. Solar + hydrogen fuel cell + condensation harvesting. Back-feeds the M_0 reserve. Turns the network from a "cooling Big Bang" (central power, dissipating) into a steady-state universe (distributed generation, cycling).

**Applications by industry:**
- **Telecommunications:** Solar-powered 5G small cells, remote repeaters. Off-grid network expansion.
- **IoT:** Self-powered sensors — harvest ambient energy, back-feed surplus to mesh.
- **Data centers:** On-site solar + hydrogen for peak shaving. Fuel cells for backup (already done by some hyperscalers).
- **Smart grid:** Home generation bank — rooftop solar + electrolyzer → hydrogen storage → fuel cell. Powers home data + contributes to grid.
- **Aerospace:** Satellite power — solar + regenerative fuel cells for eclipse periods.
- **Automotive:** Vehicle-to-grid (V2G) — EV fleet as distributed storage/generation.

**Materials (physical):**
- Solar panels: $0.30–0.50/Watt (utility scale)
- PEM electrolyzer (H2 generation): $500–1K/kW
- Hydrogen storage (metal hydride or compressed): $200–500/kWh equivalent
- PEM fuel cell: $1K–2K/kW
- Atmospheric water generator (condensation harvesting): $500–2K
- Power electronics (DC-DC, inverter): $100–300
- Home-scale system (5kW solar + 10kWh H2): ~$15K–25K

**User profiles:**
- Telecom infrastructure planners (off-grid sites)
- Smart home integrators
- Microgrid developers
- Data center energy managers
- Off-grid community builders

---

### H5. CMB Sink (Radiative Cooling)
**Tag:** HARDWARE

**Description:** Physical radiative cooling to a cold bath. The Cosmic Microwave Background (2.7K) is the universal heat sink — but on the bench, we use the night sky (~250K effective) or cryogenic cooling. Dissipates waste heat as infrared radiation without energy input (passive).

**Applications by industry:**
- **Data centers:** Radiative cooling panels — reject heat to the night sky, reduce chiller load. Already in pilot by some operators.
- **Telecommunications:** Passive cooling for remote equipment shelters. No AC needed.
- **Buildings:** Cool roof coatings, radiative cooling films. 5–10°C sub-ambient achievable.
- **Electronics:** Chip-level radiative cooling — metamaterial emitters tuned to atmospheric transparency window (8–13 μm).
- **Spacecraft:** Only cooling method available — radiators sized by Stefan-Boltzmann.

**Materials (physical):**
- Radiative cooling film (3M, SkyCool): $10–50/m²
- Metamaterial emitter (tuned 8–13 μm): research grade, $100+/m²
- Cryogenic cold finger (for lab): $2K–5K
- IR-transparent cover (ZnSe or polyethylene): $50–200
- Heat pipes (to move heat to radiator): $20–100 each

**User profiles:**
- Data center thermal engineers
- Building energy modelers
- Spacecraft thermal designers
- Electronics cooling engineers

---

## BORDER FEATURES (Coded now, hardware later)

### B1. Eddington Saturation
**Tag:** BORDER (software now → hardware later)

**Description:** Radiation pressure self-regulates accretion: `kappa_eff = kappa_sink / (1 + M/M_edd)`. Currently coded in `cavity_orbits.py`. In hardware, this is actual photons pushing against infalling matter — the physics is real, we're just simulating the force.

**Migration path:** Software proves the equation → photonic hardware implements with real radiation pressure in optical traps → astrophysical systems do it naturally.

**Applications by industry:**
- **Astrophysics:** Stellar mass limits, AGN feedback modeling. (Already the standard model.)
- **Laser physics:** Optical tweezer force limits — how much power before the trap blows out.
- **Telecommunications:** EDFA gain saturation — same math, different scale. Prevents amplifier blowup.
- **Data centers:** Thermal throttling models — compute "radiation pressure" as heat limiting throughput.

**Materials:**
- Software: already in `cavity_orbits.py`
- Hardware (future): optical trap with variable laser power, microparticles

**User profiles:**
- Astrophysicists (accretion modeling)
- Photonics engineers (optical trap design)
- Data center operators (thermal management models)

---

### B2. Viscosity (Smoothstep Ablation)
**Tag:** BORDER (software now → hardware later)

**Description:** Selective dissipation via relative gradient detector with smoothstep threshold and density floor protection. Currently coded. In hardware, this is real thermal dissipation in a nonlinear medium — the physics of smoothing without destroying topology.

**Migration path:** Software proves selectivity (smoothstep > linear) → nonlinear optical material implements natively (saturable absorber) → physical viscosity in fluid systems.

**Applications by industry:**
- **Photonics:** Saturable absorbers for mode-locking (already exist — SESAMs). Our smoothstep is the mathematical ideal.
- **Fluid dynamics:** Turbulence modeling — selective dissipation of small scales preserving large structures.
- **Image processing:** Edge-preserving smoothing (bilateral filter is the discrete analog).
- **AI/ML:** Gradient clipping with topological protection — don't destroy learned features while regularizing.

**Materials:**
- Software: already in `cavity_orbits.py` (`visc_mode="smoothstep"`)
- Hardware: SESAM (semiconductor saturable absorber mirror), $500–2K; nonlinear fiber, $10/meter

**User profiles:**
- Laser physicists (mode-locking)
- CFD engineers (turbulence models)
- ML researchers (regularization)

---

### B3. Nonlinear Mixing (Wave Interaction)
**Tag:** BORDER (software now → hardware later)

**Description:** Wave-wave interaction via nonlinear coupling. Currently done with FFTs and pointwise multiplications (software). In hardware, a nonlinear crystal does this with physics — sum-frequency generation, four-wave mixing, phase conjugation.

**Migration path:** Software proves the math (Chebyshev coupling, harmonic generation) → PPLN crystal implements natively → photonic neural network weights.

**Applications by industry:**
- **Telecommunications:** Wavelength conversion, all-optical switching.
- **AI/ML:** Photonic neural networks — the crystal IS the weight matrix. Matrix multiplication at light speed.
- **Quantum:** Entangled photon pair generation (SPDC in BBO/PPLN).
- **Spectroscopy:** Upconversion detection — shift IR to visible for silicon detectors.
- **Defense:** All-optical signal processing (no electronic bottleneck).

**Materials:**
- Software: FFT-based (current)
- Hardware: PPLN crystal (periodically poled lithium niobate), $500–2K; BBO crystal, $300–800; highly nonlinear fiber (HNLF), $50/meter
- Pump laser: required for parametric processes, $1K–5K

**User profiles:**
- Photonics engineers (nonlinear optics)
- AI hardware researchers (photonic computing)
- Quantum optics researchers
- Spectroscopy instrument builders

---

## Cross-Industry Summary Matrix

| Feature | Tag | Telecom | Data Center | AI/ML | Energy | Defense | Healthcare | Consumer |
|---------|-----|---------|-------------|-------|--------|---------|------------|----------|
| S1 Burn/Bury | S | ✓ | ✓ | | | ✓ | ✓ | |
| S2 Routing | S | ✓ | ✓ | ✓ | ✓ | | | |
| S3 M_0 Ledger | S | ✓ | ✓ | ✓ | ✓ | | | ✓ |
| S4 Shapiro | S | ✓ | ✓ | | | | | |
| S5 QF Rails | S | ✓ | | | | | | |
| H1 Wave Messenger | H | ✓ | ✓ | ✓ | | ✓ | | |
| H2 Waveguide | H | ✓ | ✓ | | | | ✓ | |
| H3 OAM Sorter | H | ✓ | ✓ | ✓ | | ✓ | | |
| H4 Edge Power | H | ✓ | ✓ | | ✓ | | | ✓ |
| H5 CMB Sink | H | ✓ | ✓ | | ✓ | | | ✓ |
| B1 Eddington | B | ✓ | ✓ | | | | | |
| B2 Viscosity | B | | | ✓ | | | | |
| B3 Nonlinear | H | ✓ | | ✓ | | ✓ | | |

---

## Benchtop Build Order (by dependency)

1. **H2 (Waveguide)** — fiber spool, $50. Foundation for everything.
2. **H1 (Wave Messenger)** — laser + SLM, $3K. Generate ℓ=2, observe propagation.
3. **B3 (Nonlinear)** — PPLN crystal, $500. Mix waves, prove coupling.
4. **H3 (OAM Sorter)** — interferometric, $1K–3K. **The gate.** Sort modes, close the loop.
5. **H4 (Edge Power)** — solar + fuel cell demo, $2K. Prove distributed generation.
6. **H5 (CMB Sink)** — radiative film, $50. Passive cooling demo.

**Total benchtop (without sorter):** ~$3,600
**Total benchtop (with sorter):** ~$5,000–7,000
**Signal-and-observe only:** $343–486 (from gap survey)

---

*End of spec. Awaiting Zak's red pen.*
