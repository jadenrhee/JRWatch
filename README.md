# JRWatch

[![firmware build](https://github.com/jadenrhee/JRWatch/actions/workflows/firmware.yml/badge.svg)](https://github.com/jadenrhee/JRWatch/actions/workflows/firmware.yml)

A smartwatch built from scratch: a 36 mm 4-layer board carrying an nRF52840
BLE module, a Nordic nPM1300 PMIC, a Bosch BMI270 IMU, and a Sharp
memory-in-pixel display, plus Zephyr firmware. The design target was sleep
current — how low it can go on a wearable that still wakes on motion and
holds a watch face.

<p align="center">
  <img src="fab/renders/board-iso.png" width="420" alt="board render"/>
</p>

| | |
|---|---|
| Projected sleep current | **~15 µA** with motion wake armed and the watch face showing (~26 µA if it keeps advertising over BLE) |
| Projected battery life | **~4–8 months** on a 150 mAh cell, depending on use |
| Firmware | Zephyr v4.1.0, builds in CI: 231 KiB flash / 40 KiB RAM |

These are calculated from datasheet typicals, not measured. Every line of the
estimate is itemized with its source in the
[verification report](docs/verification-report.md).

## Why these parts

- **Raytac MDBT50Q-1MV2** (nRF52840 module) — pre-certified with a tuned
  antenna. Without a VNA, a hand-tuned trace antenna would quietly waste
  battery on retransmissions. The module keep-out is held on all four layers
  and verified copper-free.
- **Nordic nPM1300** — one chip for LiPo charging (with a real NTC on the
  board), two bucks, two load switches, USB-C detection, and a 370 nA ship
  mode. The load switches are what make the sleep numbers work: the display
  and IMU rails get physically cut, so nothing leaks.
- **Bosch BMI270** — 5.9 µA low-power accel mode with a hardware any-motion
  interrupt, so the SoC sleeps until a wrist-raise.
- **Sharp LS013B7DH03** memory-in-pixel LCD — holds a static image at ~4 µA
  with no backlight. A normal TFT would spend the entire power budget alone.
- **3.0 V rail** — every chip on the board is happy there, and it's set by a
  resistor strap, so the PMIC comes up correct before any firmware runs.

## Verification

- Schematic ERC: 0 errors, 0 warnings. Board DRC: **zero violations** against
  JLCPCB's 4-layer rules.
- Every BOM line checked against its LCSC part individually — this caught
  three wrong capacitor/resistor numbers.
- Charge path width checked against IPC-2221 (2.5× margin at the 500 mA USB
  limit), USB pair skew measured at 46 ps (0.06% of a Full-Speed bit), ground
  islands stitched to the internal plane.
- PMIC pinout re-verified pin-by-pin against Nordic's datasheet table; the
  module pin map matches the firmware devicetree exactly.

## Status

Not yet fabricated. A pre-order review against the Sharp panel's mechanical
drawing turned up two problems with the display FPC connector: it sat where
the panel's tail physically cannot reach, and its pin order was mirrored for
the fold-under mounting — the fold flips the contact face, which reverses the
order the connector sees. The schematic and netlist are corrected and
re-verified, and the connector's corrected position is checked against every
mechanical obstacle (D-025 in the [decision log](docs/decision-log.md)).

Catching that on paper rather than on an assembly run is the reason the
review step exists.

## Firmware

A custom Zephyr board definition, pin-mapped from the schematic. Three power
tiers — active, armed sleep, ship mode — mapping 1:1 to the hardware power
domains. The display redraws only when content changes, the IMU wakes the SoC
on motion, and the console is RTT so no pins are spent on UART. BLE exposes
the standard battery service plus a small custom step-count service
([protocol](docs/protocol.md)).

## Repo layout

| Path | What's in it |
|---|---|
| `hardware/skidl/` | Schematic source of record |
| `hardware/jrwatch.kicad_pcb` | The board (KiCad 10) |
| `hardware/scripts/` | Board generation and verification tooling |
| `hardware/enclosure/` | Printable case (OpenSCAD + STLs) |
| `fab/` | Gerbers, BOM/CPL in JLCPCB format, renders, order notes |
| `firmware/` | Zephyr app, custom board definition, CI |
| `docs/` | [Decision log](docs/decision-log.md), [design rationale](docs/design-rationale.md), [verification report](docs/verification-report.md), [BLE protocol](docs/protocol.md) |
