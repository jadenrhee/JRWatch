# Verification Report

This is where I check my own work: every design rule against theory or a
datasheet, with the value and where it came from. Anything marked
**PROJECTED** is calculated from datasheet typicals, not measured. I'll
replace those with real PPK2 measurements at bring-up (item 3 in
`NEEDS-INPUT.md`).

## 1. Headline: power budget and projected battery life

**Projected armed-sleep current: ~ 15 µA (BLE off) / ~ 26 µA (slow advertising).**
**Projected battery life on the 150 mAh cell: ~ 4-8 months per charge in
typical watch use; > 2 years in ship mode (battery self-discharge dominates).**

### Sleep tier budget - "IDLE / armed sleep" (battery side, VBAT = 3.8 V)

Motion-wake armed, watch face statically displayed, RTC running.

| Item | Draw at its rail | Battery-side* | Source |
|---|---|---|---|
| nRF52840 System ON idle, full RAM retention, LFXO + RTC | ~ 3.0 µA @3.0 V | ~ 3.2 µA | nRF52840 PS typicals (ION + RAM retention + ILFXO + IRTC); PROJECTED |
| BMI270 low-power mode, 25 Hz, any-motion armed | 5.9 µA @3.0 V | ~ 6.2 µA | BMI270 DS (BST-BMI270-DS000), low-power mode table |
| Sharp LS013B7DH03 holding static image | 12 µW typ @3.0 V = 4.0 µA | ~ 4.2 µA | Sharp spec §6-4, measurement condition 1 (typ; max 50 µW) |
| nPM1300 quiescent (battery operation) | - | 0.8 µA | nPM1300 PS v1.1 Table 4: IQBAT = 800 nA |
| Strapping/TVS/capacitor leakage | - | ≤ 0.5 µA | D-018: every pull is toward its idle state (0 standing current by design); TVS I_leak ≪ 0.1 µA each |
| **Total (BLE off)** | | **~ 15 µA** | |
| BLE advertising, 1.5 s interval, 0 dBm, DCDC | - | ~ +11 µA | Nordic online power profiler class figure; PROJECTED |
| **Total (slow advertising)** | | **~ 26 µA** | |

\* battery-side = rail current × (3.0 V / 3.8 V) / η, with BUCK2 hysteretic-mode
efficiency taken as η ~ 0.75 at µA loads (PS efficiency curves; PWM-mode spec
is 93 % at 200 mA - light-load hysteretic efficiency is graph-derived and is a
priority bring-up measurement).

### Other tiers

| Tier | Projection | Notes |
|---|---|---|
| Ship mode | 0.37 µA (PMIC) - cell self-discharge (~2-3 %/month) dominates | nPM1300 PS Table 4: IQSHIP = 370 nA; battery fully disconnected from VSYS |
| Hibernate | 0.5 µA | IQSHIPT = 500 nA (wake-timer running) |
| ACTIVE (display refresh on change, IMU 50 Hz, BLE connected 100 ms/latency 4) | ~ 250-400 µA avg | dominated by IMU full-ODR (~ 200 µA) + BLE connection events; display redraw is event-driven, ~0 between changes |

### Life projections (150 mAh)

| Profile | Average draw | Projected life |
|---|---|---|
| Armed sleep only, BLE off (worn, no interaction) | 15 µA | ~ 13 months |
| Armed sleep + slow advertising | 26 µA | ~ 240 days |
| Watch use: 30 min/day ACTIVE + advertising idle | ~ 32 µA avg | **~ 6.5 months** |
| Always-connected + hourly interactions | ~ 45 µA avg | ~ 4.5 months |

## 2. RF / antenna - **PASS**

- Keep-out per Raytac Ver.K §2.2-2.3: 12.4 × 3.8 mm, all layers, plus the
  1.6 × 1.2 mm top-layer notch. Implemented three ways and geometrically
  verified from the live board: the module's own two keep-out zones, a
  board-level rule area extending to the edge, and the edge ring. Copper on
  F/In1/In2/B inside the region: **none** (DRC rule areas active during both
  autorouting and fills).
- Module placed with the antenna at the board's north edge (Raytac: "place
  the module towards the edge of PCB"). PASS.
- Caveat (checklist §3): keep display tail metal and enclosure screws out of
  the zone too.

## 3. Power / PMIC layout - **PASS with notes**

- Buck loops: SW1/SW2 nodes are 0.4 mm, hand-routed, 4.6 mm long, with the
  output caps (10 µF each) directly at the inductor outputs and PVSS pads on
  the B.Cu ground fill over the In2 plane. Layout follows nPM1300 PS
  reference layout intent. PASS.
- Inductors: 2.2 µH ±20 %, DCR 116 mΩ < 400 mΩ requirement, Isat 2.4 A ≫
  0.2 A buck limit (Murata DFE201612E-2R2M, the part Nordic's EK uses). PASS
  (PS reference BOM).
- Rails: BUCK2 = 3.0 V by VSET2 = 150 kΩ (PS BUCK table) - correct at power-on
  with no firmware dependency; BUCK1 populated per reference config,
  firmware-disabled (D-012, enforced in devicetree + `power.c`). PASS.
- Decoupling: every power pin has its cap; VBUS 10 µF, VBAT 10 µF, VSYS
  10 µF + 2.2 µF, VOUT1/VOUT2 10 µF, VBUSOUT 1 µF, VDDIO 100 nF, LSOUT 1 µF
  each, module VDD 10 µF + 100 nF ×2. Values per PS reference circuitry BOM.
  PASS. *Note:* PVDD's dedicated 100 nF sits on the west bank ~5 mm from the
  pin (pocket congestion); VSYS bulk is 2.6 mm away. Flagged for review.
- **Charge-temperature protection is real hardware**: on-board 10 k B=3380 NTC
  (D-017) matching the devicetree charger config. PASS.
- Load-switch gating: display and IMU rails are LDO1/LDO2 in LDSW mode fed
  from BUCK2 - deep sleep can cut both domains to zero. PASS.
- Ground return integrity: review found 16 outer-layer ground islands whose
  component pads had no via to the In2 plane (initially mis-assessed as
  cosmetic). 13 stitch vias added, covering the IMU ground pins, ESD array,
  buttons and most decoupling returns; 3 capacitor islands remain
  (checklist §1). PASS after checklist item closes.

## 4. Sneak-leakage review - **PASS (design), verify at bring-up**

- Every strap pulls toward its net's idle state (D-018): I2C pulls to the
  always-on rail (idle high = 0 µA), CSB pull-up to always-on VDDIO
  (deselected = 0 µA), SCS pull-down (deselected = 0 µA). PASS.
- Display rail off: `ui.c` blanks and quiesces the SPI lines before cutting
  VDD_DISP - no back-feed through panel input clamps. PASS (code review).
- IMU: VDDIO stays on the always-on rail while VDD is gated - explicitly
  permitted ("no limitations with respect to the voltage level applied to the
  VDD and VDDIO pins", BMI270 DS §POR/supply); interface pins remain defined.
  PASS.
- No LEDs anywhere (D-016). PASS.

## 5. Charge path & IPC-2221 - **PASS**

Formula: I = k/ΔT^0.44/A^0.725 with k = 0.048 (external layers).
Worst case is the 500 mA USB input limit (charging + system), ΔT = 10 °C:

- Required area A = (0.5 / (0.048 × 10^0.44))^(1/0.725) = **6.3 mil²**
  -> at 1 oz (1.378 mil) = **4.6 mil ~ 0.12 mm** minimum width.
- Implemented: 0.3 mm minimum on the VBUS entry (D-019 pinch), 0.5 mm
  elsewhere, then In1 plane copper. **Margin ≥ 2.5×.** PASS.
- Charge current itself is configured at 76 mA (0.5 C for 150 mAh; devicetree
  `current-microamp = 76000`), where required width is < 0.03 mm. PASS.
- Battery polarity marked on silk; connector pin 1 = BAT+; PCM-protected pack
  specified (checklist §3). PASS.

## 6. USB - **PASS**

- D+/D− routed as a coupled pair (0.2 mm), one deliberate F.Cu crossover
  strap (the 16-pin connector interleaves the pair; one crossover is
  topologically required - D-log). Total length D+ 30.0 mm vs D− 23.0 mm:
  **skew 7.0 mm ~ 46 ps = 0.06 %** of a Full-Speed bit (83 ns). Full-Speed
  USB has no intra-pair skew requirement at this scale, so no serpentine was
  added; the skew is recorded here instead. PASS.
- Controlled impedance: not required at FS over ~25 mm; pair reference is the
  In2 ground plane. PASS (rationale documented).
- ESD: USBLC6-2SC6 in the data path between connector and module, VBUS pin
  protected. PASS.
- CC1/CC2 direct to nPM1300 (internal Type-C sink detection, D-015);
  VBUS at one merged pad pair (D-019). PASS with note.

## 7. Crystal (32.768 kHz) - **PASS, value check at bring-up**

- CL = 12.5 pF crystal (Epson Q13FC13500004). C = 2(CL − Cstray): fitted
  C16/C17 = 12 pF assumes Cstray ~ 6.5 pF/side (nRF XL pin ~ 4 pF + PCB
  ~ 2.5 pF). Startup and ppm verified at bring-up; pads are 0402 so a value
  swap is trivial. Short guarded pair, ground-return vias at the caps. PASS
  (design), value confirmation flagged.

## 8. DFM vs JLCPCB 4-layer - **PASS except documented items**

| Rule | JLC capability | This board | Verdict |
|---|---|---|---|
| Min track/space | 0.09 / 0.09 mm | 0.13 / 0.13 mm | PASS |
| Min via | 0.15 mm drill / 0.25 pad | 0.2 drill / 0.4 pad (0.48 pad on-column) | PASS |
| Hole-to-hole | 0.5 mm | ≥ 0.5 mm (drill-shrink fix) | PASS |
| Copper-to-edge | 0.2 mm | 0.3 mm + 0.45 ring | PASS |
| Board | 4-layer 0.8 mm | JLC04081H-3313 | PASS |
| DRC | zero violations | **zero violations** | PASS |
| Connectivity | complete | **4 links + 3 ground islands open - documented** (D-022..D-024, checklist §1); power tree complete | **NEEDS REVIEW** |
| BOM stock | all lines LCSC | all verified 2026-07-02; U1/U2 DigiKey hand-place; J2 low stock | PASS with notes |
| Hand-solderability | - | castellated module + QFN/LGA via hot air; 0402 minimum; solid pours noted (D-021) | PASS |

## 9. ERC / netlist - **PASS**

SKiDL ERC: **0 errors, 0 warnings** (`hardware/netlist/erc-report.txt`),
47 parts / 43 nets, pin types assigned from datasheets, netlist -> board pad
mapping by name verified during placement.

## 10. Firmware build - **PASS**

`west build -b jrwatch` green in CI (GitHub Actions, Zephyr CI image
v0.27.4, Zephyr pinned v4.1.0): **flash 236 840 B (22.6 % of 1 MB), RAM
40 752 B (15.6 % of 256 KB)** - MCUboot partition layout already reserved
in the devicetree fits with margin. Build is configuration-verified only;
on-target behavior (BLE, IMU wake, display, PMIC) is a bring-up item.
