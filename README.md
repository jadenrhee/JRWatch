# JRWatch

[![firmware build](https://github.com/jadenrhee/JRWatch/actions/workflows/firmware.yml/badge.svg)](https://github.com/jadenrhee/JRWatch/actions/workflows/firmware.yml)

A smartwatch built from scratch. 36 mm 4-layer board with an nRF52840 module,
nPM1300 PMIC, BMI270 IMU, and a Sharp memory-in-pixel display, running Zephyr.
Built around low sleep current.

<p align="center">
  <img src="fab/renders/board-iso.png" width="420" alt="board render"/>
</p>

| | |
|---|---|
| Sleep current | ~15 µA projected, ~26 µA still advertising |
| Battery life | ~4–8 months on a 150 mAh cell |
| Firmware | Zephyr v4.1.0, 231 KiB flash / 40 KiB RAM |

Projected from datasheet typicals, not measured. Itemized with sources in the
[verification report](docs/verification-report.md); part choices in the
[design rationale](docs/design-rationale.md).

## Status

Not yet fabricated. A pre-order review caught the display FPC connector in a
spot the panel's tail can't reach, with its pin order mirrored for fold-under
mounting. Both fixed and re-verified — D-025 in the
[decision log](docs/decision-log.md).

## Firmware

Custom Zephyr board definition. Three power tiers (active, armed sleep, ship
mode) mapped to the hardware power domains. Display redraws only on change,
IMU wakes the SoC on motion, RTT console. BLE exposes battery plus a custom
step-count service ([protocol](docs/protocol.md)).

## Repo layout

| Path | What's in it |
|---|---|
| `hardware/skidl/` | Schematic source of record |
| `hardware/jrwatch.kicad_pcb` | The board (KiCad 10) |
| `hardware/scripts/` | Board generation and verification tooling |
| `hardware/enclosure/` | Printable case (OpenSCAD + STLs) |
| `fab/` | Gerbers, BOM/CPL, renders, order notes |
| `firmware/` | Zephyr app, board definition, CI |
| `docs/` | [Decisions](docs/decision-log.md) · [Rationale](docs/design-rationale.md) · [Verification](docs/verification-report.md) · [Protocol](docs/protocol.md) |
