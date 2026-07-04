# Fabrication package

Everything needed to order the JRWatch r1 board from JLCPCB.

## Order parameters (JLCPCB)

| Option | Value |
|---|---|
| Layers | 4 |
| Stackup | **JLC04081H-3313** (0.8 mm finished thickness) |
| Dimensions | 36 × 36 mm, rounded corners R6 |
| Min track/space used | 0.127 mm (design rule floor; smallest actual gap 0.13 mm) |
| Min via | 0.4 mm / 0.2 mm drill (a few 0.48/0.2 vias between QFN pads) |
| Surface finish | **ENIG recommended** (0.5 mm QFN + 0.5 mm FPC pitch) |
| Copper | 1 oz outer / 0.5 oz inner (default) |
| Solder mask | any; silkscreen carries battery polarity + board ID only |

## Files

- `gerbers/` - RS-274X plots (`--no-x2`, mask-subtracted paste) + Excellon
  drill + map. Zip this folder for the JLC order.
- `bom-jlcpcb.csv` - JLC format (`Comment,Designator,Footprint,LCSC`).
  Lines tagged `[HAND-PLACE]` are not for SMT assembly:
  - **U1** MDBT50Q-1MV2 and **U2** nPM1300 - LCSC listed but out of stock at
    design time; source from DigiKey and reflow by hand (module castellations
    iron-friendly; QFN with hot air/plate).
  - **J2** FPC connector - low LCSC stock, order early.
- `cpl-jlcpcb.csv` - pick-and-place. JLC's viewer often needs per-part
  rotation nudges (especially QFN/SOT); verify footprints in their preview
  before confirming, as usual.
- `renders/` - top / bottom / iso PNG renders and copper-layer SVGs.
- `schematic-reference.pdf` - generated netlist listing (this project's
  schematic source of record is code: `hardware/skidl/`).

## Before ordering - blocking items

**DO NOT ORDER THIS REVISION.** Pre-order review (D-025) found the display
connector placed out of the panel tail's reach and with un-mirrored pin
order; the schematic is corrected but the layout rework has not landed.
Additionally the board has 4 unrouted links and 3 unstitched capacitor
ground islands
left for interactive completion (zero DRC violations otherwise; the power
tree is complete). See `docs/human-review-checklist.md` §1 for exact
endpoints, what blocks each one, and suggested fixes - about 20 minutes in
the KiCad router. Do not order before closing them and re-running
`kicad-cli pcb drc`.

Also confirm the display FPC fold reach and battery pigtail polarity
(checklist §3).
