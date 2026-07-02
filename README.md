# JRWatch — Low-Power BLE Wearable

A wrist-wearable, 4-layer BLE smartwatch board built around the Raytac MDBT50Q-1MV2
(nRF52840) module, Nordic nPM1300 PMIC, Bosch BMI270 IMU, and a Sharp Memory-in-Pixel
display — designed end-to-end using a modern automated design workflow
(schematic-as-code, programmatic placement and routing, scripted verification).

> **Status: in design.** This README is finalized at the end of the design flow with
> board renders, the projected sleep-current / battery-life numbers, and verification
> results. See `docs/decision-log.md` for the running record of design decisions.

## Repository layout

| Path | Contents |
|---|---|
| `hardware/` | SKiDL schematic source, KiCad board, custom footprints, build scripts |
| `fab/` | Gerbers, drill, BOM, pick-and-place, board renders |
| `firmware/` | Zephyr RTOS (nRF Connect SDK) application |
| `docs/` | Decision log, verification report, design rationale, review checklists |
