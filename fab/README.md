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
  rotation nudges (especially QFN/SOT); footprints should be verified in
  their preview before the order is confirmed.
- `renders/` - top / bottom / iso PNG renders and copper-layer SVGs.
- `schematic-reference.pdf` - netlist listing; the schematic source of record
  is `hardware/skidl/`.

## Order status

**This revision is not ready to order.** Pre-order review (D-025) found the
display connector placed out of the panel tail's reach and with un-mirrored
pin order. The schematic is corrected and re-verified; the corresponding
layout rework has not landed yet.
