# Design Rationale — block by block

Why each block is what it is. Decisions with real alternatives are
cross-referenced to `decision-log.md` (D-nnn); sourcing facts live in
`hardware/parts.yaml`.

## System architecture

```
USB-C ──► nPM1300 PMIC ──► BUCK2 3.0V (always-on) ──► nRF52840 module
 5V/CC      │  ▲                │                        │  │  │
            │  └─ LiPo 150mAh   ├─ LSW1 ─► VDD_DISP ─► Sharp MIP 128×128
            │     + 10k NTC     └─ LSW2 ─► VDD_IMU  ─► BMI270
            └─ VBUSOUT ─► module VBUS (USB detect/DFU)
```

One always-on rail, two hardware-gated domains, everything else dead in
sleep. Nothing that can leak stays electrically attached when the watch is
idle, which is what makes the sleep-current budget hold.

## BLE SoC — Raytac MDBT50Q-1MV2 (D-001, D-010)

nRF52840 with the antenna already tuned and certified (FCC/CE/TELEC).
A bare chip + meandered-F antenna needs VNA matching this project can't do;
an untuned antenna costs link budget → retransmissions → battery, silently.
The module still demands real layout discipline: 61 castellations, a
hard 12.4 × 3.8 mm all-layer keep-out, and radio-adjacent pins that are
restricted to low-frequency signals (datasheet §2.6) — respected in the pin
map (buttons/EXTCOMIN only on those pins). Datasheet: Raytac spec Ver.K.

## PMIC — Nordic nPM1300 (D-002, D-011, D-012)

The one-chip version of the entire power story: linear LiPo charger with
NTC/JEITA windows, two 200 mA bucks, two load switches, USB-C sink
detection, ship mode (370 nA), and the measurement chain for Nordic's fuel
gauge. Bucks are asymmetric in their VSET tables, which decided the rail
plan: **BUCK2 = 3.0 V via a 150 kΩ strap is correct at power-on with zero
firmware involvement**; BUCK1 (1.8 V per the reference config) is populated
but held off. The rail is 3.0 V because every load (module 1.7–3.6 V, IMU
1.71–3.6 V, display 2.7–3.3 V typ 3.0) is happy there and it maximizes the
usable LiPo discharge window. Charge current 76 mA ≈ 0.5 C for the 150 mAh
pack.

## IMU — Bosch BMI270 (D-003)

The common choice in shipping wearables, picked for its 5.9 µA low-power
accel mode with a hardware any-motion interrupt: the SoC sleeps and the
wrist wakes it. SPI (not I2C) keeps active-mode transactions short; VDDIO
rides the always-on rail so the interface stays defined while VDD is gated
(explicitly allowed by the datasheet); unused aux/OIS pins strapped per
Table 22.

## Display — Sharp Memory-in-Pixel LS013B7DH03 (D-004, D-013)

Chosen on power: the panel retains its image at 12 µW typical, so the watch
face costs ~4 µA while the system sleeps — no backlight, sunlight-readable.
A GC9A01-class TFT draws three orders of magnitude more. The costs: 10-pin FPC assembly, a 1 Hz EXTCOMIN toggle
(driven by a timer, not the CPU; EXTMODE strapped high), and 128×128 mono
aesthetics. Firmware only redraws when content changes.

## USB-C (D-015, D-019)

Charge + Full-Speed data (nRF52840 USB for DFU). CC lines go straight to
the nPM1300 — it implements Type-C sink detection internally, so the
classic 5.1 k pull-downs would be wrong here, not just redundant. ESD
(USBLC6-2SC6) sits in the data path; VBUS enters through one merged pad
pair (each physical pad on this connector already bridges A/B) with an
IPC-2221-verified width.

## Controls (D-014)

Two side buttons. SW1 goes **only** to the PMIC's SHPHLD pin — that node
swings to VBAT and must never meet an nRF GPIO; it wakes the board from
ship mode in hardware. SW2 is the user button on P1.13 (a radio-restricted
low-frequency pin — buttons are exactly what those pins are for) with GPIO
SENSE wake. Both lines: 100 Ω series + SOD-923 TVS sized to their voltage
domains (5 V part on the VBAT-domain node, 3.3 V part on the logic node).

## Timekeeping (D-009)

A watch drifts minutes per week on the RC oscillator; the FC-135-class
32.768 kHz crystal costs two 0402 caps and *saves* current (no periodic
HFCLK calibration, tighter BLE sleep-clock windows → shorter radio-on).

## Board & layout (D-007, D-020..D-022)

36 × 36 mm R6, 4-layer 0.8 mm (JLC04081H-3313): L1 top = display side +
escape routing, In1 = power pours (3V0/VSYS/VBUS/VBAT), In2 = solid ground,
L4 bottom = components. Antenna strip at the north edge, USB south, buttons
east, battery west, PMIC + inductors clustered with hand-routed switch
loops. The display panel occupies the top face; the FPC connector hides
under its south edge. Silkscreen carries only what matters at assembly:
battery polarity and the board ID.

## Firmware (see firmware/README.md)

Zephyr with a custom board definition pin-mapped 1:1 from the SKiDL source.
Event-driven; three power tiers (ACTIVE / armed-sleep IDLE / PMIC ship
mode); rails gated through the regulator API; display treated as
write-only-on-change. Console over RTT because the design spends no pins on
UART.

## Not included (and why)

- Charge LED (D-016) — invisible in a case, ruinous to the µA budget.
- PPG heart rate (stretch in the brief) — omitted to protect the core
  power/size goals; the gated `VDD_IMU` domain and spare module pins are
  the landing zone for a future MAX30101 daughter experiment.
- NFC antenna — module pins exist, no user story on this product.
- Bare-chip + tuned trace antenna respin — documented stretch once a VNA
  is available (D-001).
