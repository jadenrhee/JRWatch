# Decision Log

Every non-trivial design decision, the options considered, and the reasoning.
Priorities used to break ties, in order:

1. **Demonstrable, measured low-power design** (headline metric: sleep current / battery life)
2. **Manufacturability + reliability for a solo builder** (hand-solderable, certified RF, JLCPCB-friendly)
3. **Small, clean, dense layout** (wearable form factor)
4. **Clarity of process/rationale**

---

## D-001: BLE radio — pre-certified module vs. bare nRF52840

- **Options:** (a) Raytac MDBT50Q-1MV2 module (nRF52840 inside, integrated antenna,
  FCC/CE/TELEC certified); (b) bare nRF52840-QIAA + meandered-F trace antenna.
- **Decision: (a) Raytac MDBT50Q-1MV2.**
- **Why:** A trace antenna requires matching-network tuning with a VNA that is not
  available; an untuned antenna silently costs link budget and battery (retransmissions),
  which attacks priority #1. The module is pre-certified (priority #2), still demands
  real high-density layout around its castellations and an antenna keep-out (priority #3),
  and its datasheet gives an explicit keep-out rule that can be *verified* (priority #4).
- **Cost accepted:** ~$6 module premium vs. bare chip; module footprint is larger than a
  bare QFN. Documented stretch goal: respin with bare nRF52840 + tuned antenna once a VNA
  is available.

## D-002: Power management — integrated PMIC vs. discrete chain

- **Options:** (a) Nordic nPM1300 (linear charger + 2 bucks + 2 load-switch/LDOs +
  fuel-gauge measurement chain + USB-C CC detection + ship mode, one QFN32);
  (b) discrete: MCP73831 charger + MAX17048 fuel gauge + low-Iq LDO + discrete load
  switches.
- **Decision: (a) nPM1300**, with (b) held as a logged fallback if LCSC sourcing fails.
- **Why:** Power management *is* the project story. The nPM1300 gives coulomb-counting
  class fuel gauging (VBAT/IBAT/temp measurement feeding Nordic's fuel-gauge algorithm),
  hardware ship mode (~µA off-state), programmable charge current, and two load-switch
  outputs used here to hard-gate the display and sensor rails in deep sleep — that gating
  is what makes the µA sleep story real instead of rhetorical (priority #1). One QFN32
  replaces 4+ packages (priority #3) and is a part Apple/Nordic-adjacent interviewers
  recognize (priority #4).
- **Risk accepted:** QFN-32 0.4 mm... *(pitch verified against datasheet in D-010)*
  reflow requires hot-air/stencil rather than an iron; acceptable for a solo builder
  with paste + hot plate, and JLCPCB can assemble it if hand assembly fails (priority #2).

## D-003: IMU — Bosch BMI270

- **Options:** (a) Bosch BMI270; (b) ST LSM6DSO.
- **Decision: (a) BMI270.**
- **Why:** Wearable-industry-standard low-power IMU (5.9 µA low-power accel mode with
  any-motion interrupt — exactly the motion-wake mechanism this design needs), built-in
  step counter offloads counting from the SoC so it can sleep (priority #1), Zephyr has
  an in-tree driver (priority #2), and it connects to hands-on Bosch internship
  experience (priority #4). LSM6DSO is an equivalent fallback if stock fails.

## D-004: Display — Sharp Memory-in-Pixel LCD

- **Options:** (a) Sharp MIP LCD LS013B7DH03 (1.28", 128×128, SPI);
  (b) GC9A01 round TFT (240×240, SPI).
- **Decision: (a) Sharp MIP LS013B7DH03.** *(Supply voltage and FPC pinout verified
  against the Sharp datasheet in D-011 before committing the schematic.)*
- **Why:** Power is the deciding factor and it is not close: the MIP panel holds a
  static image at single-digit-µW (it only draws meaningful current while lines are
  being rewritten), needs no backlight, and is always readable in daylight — a watch
  face that costs ~µA average. A GC9A01 TFT draws tens of mA with backlight on and
  ~mA-class even dimmed; it would destroy the deep-sleep budget that is the entire
  headline (priority #1). MIP sourcing is via Digi-Key/Mouser/Adafruit rather than LCSC —
  acceptable because the display is a hand-attached FPC module, never JLC-assembled;
  only its 10-pin FPC *connector* must be LCSC-stocked (priority #2).
- **Logged:** GC9A01 kept as the documented fallback if MIP sourcing collapses.

## D-005: System rails and power-gating topology

- **Options considered:** (a) single 3.0 V always-on buck + load-switch-gated peripheral
  domains; (b) dual rails 1.8 V + 3.3 V both always-on; (c) 1.8 V logic rail + 3.0 V
  peripheral rail.
- **Decision: (a)** BUCK1 = 3.0 V always-on feeding the MDBT50Q (VDD), pull-ups, and
  bus IO; nPM1300 **LSW1 gates the display** 3.0 V domain and **LSW2 gates the
  IMU (+ future PPG) domain**, both fed from BUCK1. BUCK2 is configured but unloaded by
  default (available as a 1.8 V experiment rail; disabled in firmware for production
  power figures).
- **Why:** Every always-on rail costs quiescent current; one hysteretic-mode buck is the
  minimum viable always-on domain (priority #1). Full hardware gating of display+sensors
  removes their leakage entirely in ship/deep-sleep states and prevents sneak back-feed
  paths through GPIO (verified in the leakage review). 3.0 V (not 3.3 V) is chosen
  because every load (nRF52840: 1.7–3.6 V, BMI270: 1.71–3.6 V, Sharp MIP: 2.7–3.3 V
  typ 3.0 V) is happy there, it maximizes usable LiPo discharge range through the buck,
  and it is the MIP panel's nominal supply.
- **Nuance logged:** BMI270 VDD could run from a 1.8 V rail for ~40% sensor energy
  savings, but that adds an always-on second buck whose quiescent current exceeds the
  saving at the ~6 µA sensor budget of this design. Rejected on net-µA math.

## D-006: Sleep-state architecture (drives all later verification)

Three power tiers, each with a projected budget to be computed part-by-part in
`docs/verification-report.md`:

1. **Ship / off** — nPM1300 ship mode, SYS rail dead, wake by SHPHLD button only.
   Target: < 1 µA from battery.
2. **Watch idle (armed sleep)** — the headline number. nRF52840 in System ON idle with
   RTC + full RAM retention (BLE off or long-interval advertising), BMI270 in low-power
   any-motion mode (its INT1 wakes the SoC), display statically holding the watch face
   (EXTCOMIN toggled at 1 Hz by nRF RTC/GPIOTE, zero CPU), display+IMU rails ON but
   idle. Target: **≤ ~20 µA total** → months on a 150 mAh cell.
3. **Active** — BLE connected, display refresh on change only, IMU at 50 Hz.

- **Why this structure:** it maps 1:1 to what wearable teams actually ship (off / wrist-
  down / wrist-up), and every number in it is measurable at bring-up with a µCurrent or
  PPK2 — the resume claim stays honest.

## D-007: Board format — 4-layer, ~36 mm rounded square, 0.8 mm thick

- **Decision:** 36 × 36 mm rounded-square outline (R = 9 mm), JLCPCB 4-layer,
  **0.8 mm** finished thickness (JLC04081H-3313 stackup), layers:
  L1 components/signal, L2 solid GND, L3 power pours, L4 signal/components.
- **Why:** The Sharp 1.28" panel (~27 × 28 mm active module) sets the minimum face size;
  36 mm is small-watch territory and leaves a real antenna keep-out strip plus button /
  USB edge room (priority #3). 4 layers with a dedicated unbroken GND plane directly
  under L1 is what makes the PMIC switching loops and module grounding verifiable
  (priority #1); 0.8 mm halves stack height in a wearable and is a standard JLC 4-layer
  offering (priority #2). USB is FS-only (12 Mbps) over ~15 mm — controlled impedance
  is not required; the pair is still routed tightly coupled and length-matched as good
  practice.

## D-008: Programming/debug — Tag-Connect TC2030 + USB DFU

- **Decision:** TC2030-IDC-NL footprint (no connector BOM cost, zero height) for SWD,
  plus nRF52840 USB DFU (factory Nordic bootloader is absent on Raytac modules —
  a UF2/MCUboot bootloader is flashed once over SWD, then USB DFU serves daily
  development). Also: SWDIO/SWCLK castellations are what Tag-Connect lands on; no
  10-pin Cortex header fits a 36 mm watch.
- **Why:** Space (priority #3) and solo-builder practicality (priority #2).

## D-009: 32.768 kHz timekeeping crystal — include it

- **Options:** (a) external 32.768 kHz crystal (Epson FC-135 class) on P0.00/P0.01;
  (b) internal LFRC oscillator.
- **Decision: (a) external crystal.**
- **Why:** This is a *watch*: LFRC's ±250 ppm-class error is minutes/week of drift and
  it costs more current than the LFXO once calibration wakeups are counted
  (LFXO ≈ 0.23 µA vs LFRC ≈ 0.7 µA + periodic HFCLK calibration bursts on nRF52840).
  Crystal accuracy also tightens BLE sleep-clock windows → shorter radio-on time per
  connection event (priority #1). Cost: one 3215 crystal + 2 caps (12 pF class, set from
  the FC-135 CL spec against nRF52840 pin capacitance — calc in verification report).

---

*Part-number-level decisions (exact LCSC numbers, stock status, packages) are appended
as D-010+ after the sourcing-verification pass — see below.*
