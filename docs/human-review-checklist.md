# Human Review Checklist

What a human must eyeball or finish before ordering boards. Honest accounting:
the automated flow got the board to **zero DRC violations** with the seven
links below left unrouted rather than routed badly.

## 1. NEEDS REVIEW — unrouted links (interactive routing required, ~30 min)

The autorouter and the scripted completion passes could not close these in the
congested south-west quadrant around the nPM1300 (U2). Every attempt that
forced them produced clearance violations against other nets, so they were
left open deliberately. Endpoints are exact; suggested approach for each:

| Net | From | To | Suggested fix |
|---|---|---|---|
| `VSYS` | U2 pin 4 PVDD (93.45, 103.95) | VSYS plane/pin 20 | Nudge the locked SW1 trace bend at (96.9, 103.45) 0.3 mm north, then a 0.3 mm stub east into a via at ~(95.6, 103.8) tapping the In1 VSYS pour |
| `VSYS` | U2 pin 20 (88.55, 104.45) | VSYS plane | Short west stub + via ~(87.7, 104.6) after nudging the VBUS_USB F.Cu descent at x=87.75 east |
| `VBAT` | U2 pin 19 (88.55, 104.95) | In1 VBAT pour | Same pocket as pin 20 — one via serves both if the FR west cluster is tidied |
| `3V0` | U2 pin 12 VDDIO (91.25, 106.65) | 3V0 plane | Via in the pin-12 column at y≈107.4 after shifting the USB_DP via at (91.25, 107.5) east (U4 pin-5 pad starts y=107.8 — watch it) |
| `CC2` | U2 pin 24 (88.55, 102.45) | J1 pad B5 (98.25, 109.555) | Re-shape CC1's escape (87.89–88.24 cluster) 0.3 mm west, drop CC2 through the vacated slot, F.Cu sweep south-east |
| `SHPHLD` | U2 pin 15 (89.75, 106.65) | R7 (110.9, 95.51) | Slot between the N$4 and I2C_SCL south verticals (x≈89.55) after re-parking the I2C_SDA via at (90.53, 107.6) |
| `DISP_SCK` | U1 pad 41 (95.35, 93.5) | J2 pad 1 (87.05, 110.65) | F.Cu west highway at x≈88.3 between the display cap columns (C21/C22 at y 108.5) into J2 pin 1 |

Also: **16 GND zone-island edges** — drop stitching vias on the small isolated
B.Cu/F.Cu fill islands (or let them be removed by island culling; they are
cosmetic, In2 is the real ground plane).

## 2. Hand-constrained vs autorouted (what to trust at what level)

- **Hand-routed, locked, verified**: USB differential pair (one deliberate
  F.Cu crossover, total skew 7.0 mm ≈ 46 ps = 0.06 % of a Full-Speed bit —
  no serpentine, documented), nPM1300 buck switch-node loops, 32.768 kHz
  crystal pair with local ground returns, VBUS entry, module VDD/VDDH rail,
  module ground stitching, all pours and the antenna keep-outs.
- **Autorouted (Freerouting), DRC-clean**: I2C, IMU SPI, display data,
  buttons, VSET straps, NTC, PMIC interrupt, CC1.
- **Scripted completion, verified**: LSIN1/LSIN2/VOUT2 on-column
  0.48/0.2 mm vias (between QFN pads — check they reflow clean),
  VDD_DISP / VDD_IMU links threading the freed lanes.

## 3. Physical/BOM checks before ordering

- **Battery pigtail polarity**: J3 pin 1 = BAT+. Silkscreen +/− is on the
  board. JST-SH pigtail vendors are inconsistent — verify with a meter before
  first connection.
- **Murata DFE201612E land pattern** (L1/L2) was derived per IPC-7351B from
  body dimensions because Murata's official pattern wasn't retrievable —
  cross-check against the datasheet before assembly (oversize is safe here).
- **FPC connector stock**: FH12A-10S-0.5SH(55) had 91 units at LCSC at design
  time — order early or fall back to C506791.
- **Display FPC fold reach**: J2 sits south-west on the top face; the
  LS013B7DH03 tail must fold to (89.3, 112.5) with contacts down — verify
  against the panel drawing before committing the enclosure.
- **VSET straps live far from U2** (moved east for routability). They are
  sampled once at power-on; long traces are acceptable, but confirm no
  assembly bridging on R1/R2.
- **Solid zone connections everywhere** (chosen to kill starved-thermal DRC):
  fine for hot-air/JLC reflow, but hand-iron rework of 0402 GND pads will
  need more heat.
- **Antenna keep-out**: verified copper-free on all 4 layers (module zones +
  board rule area + edge ring), but keep the display panel's metal tail and
  any enclosure screws out of the 12.4 × 3.8 mm zone at the north edge too.
