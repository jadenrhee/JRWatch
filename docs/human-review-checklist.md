# Review Checklist

Items to finish or eyeball in KiCad before ordering boards. The board passes
DRC with zero violations; the open items below are connectivity gaps that
were documented rather than routed badly (D-022..D-024 in the decision log).

## 1. Open links — interactive routing required (~20 min)

Four links remain open after the scripted review pass closed the three
power-critical ones (VBAT, VSYS ×2). Each was re-analyzed against a full
survey of surrounding copper; the notes state exactly what blocks it.

| Net | From | To | Blocking situation / suggested fix |
|---|---|---|---|
| `3V0` | U2 pin 12 (91.25, 106.65) | 3V0 pins/pour to the north | The locked USB_DP via at (91.25, 107.50) sits 0.45 mm below the pad mouth and pins 11/13 flank it at 0.25 mm — no exit survives. Fix: drag the USB_DP via ~0.75 mm east (U4 pin-5 pad top is at y=107.80, watch it), then drop a via in the freed column and ride In1/F north. Re-verify USB pair skew after (currently 46 ps; the move adds ~3 ps). |
| `CC2` | U2 pin 24 (88.55, 102.45) | J1 pad B5 (98.25, 109.56) | Every north–south climb between the connector and the PMIC dies on the display power web (VDD_DISP horizontal y=107.85), the C22 cap pair, or the VBUS_USB descent at x=87.75. Fix: shove the VDD_DISP horizontal 0.3 mm south in the interactive router and climb at x≈87.3, or re-plan CC2 on In1 next to the VBUS pour. |
| `SHPHLD` | U2 pin 15 (89.75, 106.65) | R7 (110.9, 95.51) | Routable — a Freerouting pass with corridor nets ripped closed it via the x≈89.55 slot and the south strip, but broke I2C_SCL in exchange, so it was reverted. Interactively: take the same slot south, east along y≈113.5, north at x≈111.5 after nudging the BTN2_PAD horizontal at y=105.49. |
| `DISP_SCK` | U1 pad 41 (95.35, 93.5) | J2 pad 1 (87.05, 110.65) | Its siblings (MOSI, CS) own the west-edge corridor with 0.6 mm vias that pinch every parallel lane to <0.13 mm. Fix: shift the DISP_CS B.Cu vertical at x=83.30 west by 0.2 mm, then run SCK as a third parallel diagonal at ~0.5 mm offset. |

Also three ground islands with no legal via site (13 of 16 were stitched —
D-024): **C1.2** (blocked by the display-signal web on F.Cu plus two 0.6 mm
vias), **C9.2** (pinched between the USB_DP B.Cu vertical and U4 pin 5), and
**C21.2/C22.2** (VDD_DISP horizontal above, J2 below). Nudge the neighbour
noted and drop a GND via in each; re-run
`kicad-cli pcb drc` and confirm zero violations and zero unconnected.

## 2. Routing provenance (what to trust at what level)

- **Hand-routed, locked, verified**: USB differential pair (one deliberate
  F.Cu crossover; total skew 7.0 mm ≈ 46 ps = 0.06 % of a Full-Speed bit),
  nPM1300 buck switch-node loops, 32.768 kHz crystal pair with local ground
  returns, VBUS entry, module VDD/VDDH rail, module ground stitching, pours,
  antenna keep-outs.
- **Scripted with per-segment clearance math, DRC-verified**: the VBAT /
  VSYS pocket reshuffle (close_links.py), LSIN1/LSIN2/VOUT2 on-column
  0.48/0.2 mm vias (check they reflow clean), VDD_DISP / VDD_IMU links,
  13 ground-island stitch vias (stitch_islands.py).
- **Autorouted (Freerouting), DRC-clean**: I2C, IMU SPI, display data,
  buttons, VSET straps, NTC (relocated during review), PMIC interrupt, CC1.

## 3. Physical/BOM checks before ordering

- **Battery pigtail polarity**: J3 pin 1 = BAT+, marked on silkscreen.
  JST-SH pigtail vendors are inconsistent — verify with a meter before the
  first connection.
- **Murata DFE201612E land pattern** (L1/L2): derived per IPC-7351B from body
  dimensions because Murata's official pattern wasn't retrievable.
  Cross-check against the datasheet before assembly; oversize is safe here.
- **FPC connector stock**: FH12A-10S-0.5SH(55) had 91 units at LCSC at design
  time — order early or fall back to C506791.
- **Display FPC fold reach**: J2 sits south-west on the top face; the
  LS013B7DH03 tail must fold to (89.3, 112.5) with contacts down. Verify
  against the panel drawing before committing the enclosure.
- **VSET straps sit far from U2** (moved east for routability). They are
  sampled once at power-on, so trace length is fine, but check R1/R2 for
  assembly bridging.
- **PVDD decoupling distance**: the dedicated 100 nF sits ~5 mm from the pin
  (pocket congestion); VSYS bulk is 2.6 mm away. Acceptable for a 200 mA
  hysteretic buck, but measure input ripple at bring-up.
- **Solid zone connections everywhere** (kills starved-thermal DRC): fine
  for hot-air/JLC reflow; hand-iron rework of 0402 GND pads needs more heat.
- **Antenna keep-out**: verified copper-free on all 4 layers, but keep the
  display panel's metal tail and enclosure screws out of the 12.4 × 3.8 mm
  zone at the north edge too.
- **Crystal load caps**: 12 pF fitted assumes ~6.5 pF stray per side.
  Confirm startup and ppm at bring-up; 0402 pads make a value swap trivial.
