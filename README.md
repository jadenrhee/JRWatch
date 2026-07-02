# JRWatch — Low-Power BLE Wearable

[![firmware build](https://github.com/jadenrhee/JRWatch/actions/workflows/firmware.yml/badge.svg)](https://github.com/jadenrhee/JRWatch/actions/workflows/firmware.yml)

A 36 mm, 4-layer smartwatch board (nRF52840 + nPM1300 + BMI270 + Sharp
memory-in-pixel display) with Zephyr firmware whose power states map 1:1 to
the hardware's gated power domains. Schematic is code (SKiDL), placement and
routing are scripted (pcbnew API + autorouter + verified completion passes),
and every claim below is either calculated with its source cited or marked
for measurement.

<p align="center">
  <img src="fab/renders/board-iso.png" width="420" alt="JRWatch board render"/>
</p>

| | |
|---|---|
| **Projected armed-sleep current** | **≈ 15 µA** (motion-wake armed, watch face displayed, BLE off) · ≈ 26 µA with slow advertising |
| **Projected battery life (150 mAh)** | **≈ 4–8 months per charge** in typical use · 370 nA ship mode |
| **Firmware** | Zephyr v4.1.0, builds green in CI: 231 KiB flash / 40 KiB RAM |

Projections come from datasheet typicals and are itemized line-by-line in the
[verification report](docs/verification-report.md); they get replaced with
PPK2 measurements at bring-up.

## Hardware

- **SoC/BLE**: Raytac MDBT50Q-1MV2 (nRF52840, certified chip antenna) —
  datasheet keep-out held on all 4 layers, verified copper-free
- **PMIC**: Nordic nPM1300 — LiPo charging with on-board NTC, 3.0 V buck rail
  correct at power-on with no firmware involvement, two load-switched power
  domains, 370 nA ship mode
- **IMU**: Bosch BMI270 — 5.9 µA any-motion wake over SPI
- **Display**: Sharp LS013B7DH03 memory-in-pixel 128×128 — holds a static
  watch face at ~4 µA, no backlight
- USB-C charge + Full-Speed DFU, Tag-Connect SWD, two side buttons (one is
  the hardware ship-mode pin), 32.768 kHz crystal
- 36 × 36 mm, 4-layer 0.8 mm (JLCPCB JLC04081H-3313); every BOM line
  identity-checked against LCSC with stock state recorded
- **3D-printable enclosure** ([hardware/enclosure/](hardware/enclosure/)):
  two-piece parametric OpenSCAD case with strap lugs, dimensioned from the
  board file — order the STLs from any print service

| Top | Bottom |
|---|---|
| ![top](fab/renders/board-top.png) | ![bottom](fab/renders/board-bottom.png) |

## Verification ([full report](docs/verification-report.md))

- ERC 0 errors / 0 warnings; board DRC **zero violations**
- Complete power tree: battery, VSYS and buck-input routing closed and
  DRC-verified; ground islands stitched to the internal plane
- Charge path ≥ 2.5× IPC-2221 width at the 500 mA USB limit (calc shown)
- USB pair skew 7.0 mm ≈ 46 ps = 0.06 % of a Full-Speed bit
- Known gaps: 4 signal links and 3 capacitor ground vias need ~20 min of
  interactive routing before ordering — exact endpoints, blocking analysis
  and fixes in the [review checklist](docs/human-review-checklist.md)

## Firmware ([firmware/](firmware/) · [BLE protocol](docs/protocol.md))

Custom Zephyr board definition pin-mapped from the SKiDL source. Event-driven
ACTIVE / armed-sleep / ship-mode tiers; display redrawn only on content
change; IMU interrupt wake; BLE battery service + step-count GATT; RTT
console (no UART pins spent). Built in CI with `west`.

## Repository

| Path | Contents |
|---|---|
| `hardware/skidl/` | Schematic as code (source of record) + ERC report |
| `hardware/scripts/` | Board build, placement, routing, review and fab pipeline |
| `hardware/jrwatch.kicad_pcb` | The board (KiCad 10) |
| `hardware/enclosure/` | OpenSCAD case source + printable STLs + assembly notes |
| `fab/` | Gerbers, drill, BOM+CPL (JLC format), renders, order notes |
| `firmware/` | Zephyr app + custom board + CI |
| `docs/` | [Decision log](docs/decision-log.md) · [design rationale](docs/design-rationale.md) · [verification report](docs/verification-report.md) · [review checklist](docs/human-review-checklist.md) · [BLE protocol](docs/protocol.md) |

## Status / next steps

1. Close the checklist §1 items (~20 min in the KiCad router), re-run DRC
2. Order JLCPCB (parameters in [fab/README.md](fab/README.md)); hand-place
   U1/U2 from DigiKey
3. Bring-up: SWD flash → RTT logs → BLE, display, charge path
4. Measure sleep current with a PPK2 and replace every projection above

*Designed using modern automated design tooling; every decision and its
reasoning is logged in [docs/decision-log.md](docs/decision-log.md).*
