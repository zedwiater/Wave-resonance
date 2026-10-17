# Power Grid as Data Backbone: Leapfrog Infrastructure for the Developing World

## The Problem

Laying fiber costs $20,000–$50,000 per mile (trenching, permits, labor).
In rural Africa, South Asia, and Latin America, that math never works.
Result: 2.6 billion people remain offline, not for lack of demand but for
lack of trenches.

Meanwhile, electrical grids already reach these communities. The wires are
there. They're just dumb.

## The Trick

A $130 magnetic coupler clamps onto any existing power line — no cutting,
no splicing, no electrician. It reads and writes data via the magnetic
field around the conductor. The power grid becomes a data grid overnight.

No new wires. No trenches. No permits. Just clamps.

## The Architecture: Starlink In, Power Lines Out

```
    ┌─────────────┐
    │  Starlink    │  Satellite backhaul
    │  Terminal    │  (100-200 Mbps down)
    └──────┬──────┘
           │ Ethernet
           ▼
    ┌─────────────┐
    │ Village Hub  │  Solar + battery powered
    │ Pi Gateway   │  Coupler on main distribution line
    └──────┬──────┘
           │ Power line data (magnetic coupling)
     ┌─────┼─────┬─────────┐
     ▼     ▼     ▼         ▼
  ┌────┐ ┌────┐ ┌────┐  ┌────┐
  │Home│ │Home│ │Shop│  │Scl │  Clamp-on couplers
  │ 1  │ │ 2  │ │    │  │    │  at each drop
  └────┘ └────┘ └────┘  └────┘
```

One Starlink terminal serves an entire village. The existing power
distribution network carries the signal house to house. Each home needs
only a coupler + a Pi (or the production Wall-Plug Gateway).

## Why This Works Where Fiber Doesn't

| Factor | Fiber | Power-Line Coupler |
|--------|-------|-------------------|
| Cost per mile | $20K–$50K | ~$500 (couplers only) |
| Installation | Trenching crew, weeks | Clamp on, minutes |
| Permits | Right-of-way, municipal | None (non-contact) |
| Skill required | Fiber splicing tech | Anyone who can use a clamp |
| Power | Needs separate supply | Already on the wire |
| Theft risk | Copper theft is endemic | Nothing to steal (clamp-on) |
| Maintenance | Breaks when dug up | Survives; no exposed components |

## Bandwidth Path

- **Today (prototype):** 1–5 kbps per coupler. Enough for text, sensor data,
  mobile money confirmations. Proves the physics.
- **Near-term ($130 build):** ~10 Mbps per coupler. Enough for a shared
  village link — web browsing, WhatsApp, mobile banking for 20–50 homes
  off one Starlink terminal.
- **Production (Wall-Plug Gateway):** ~2 Gbps backbone on the distribution
  lines. Full broadband. Streaming, video calls, remote school.

## The Leapfrog

Developed nations built: telegraph → telephone → dial-up → DSL → fiber.
Each layer took decades and billions.

With Starlink + power-line couplers, a village goes from zero to broadband
in a weekend. No intermediate steps. The power grid they already have
becomes the last mile they could never afford to build.

This isn't a cheaper version of our infrastructure. It's a different
topology — one where energy distribution and information distribution
are the same network.

## Open Hardware, Open Standard

All coupler designs, schematics, and firmware are open source:

- Prototype spec: `cavity4d/magnetic_coupler.md`
- Pi bridge: `cavity4d/powerline_bridge_blueprint.md`
- Production PCBs: `cavity4d/pcbway_hardware_specs.md` (pending)

No licensing fees. No vendor lock-in. A kid in a basement — or a village
in Malawi — can build this.

## Call to Action

If you work in rural connectivity, community networks, or disaster relief
communications: the bottleneck was never the satellite. It was the last
mile. This removes it.

Build it. Deploy it. Fork it.
