# Decision Log

Every non-trivial design decision, the options considered, and the reasoning.
Priorities used to break ties, in order:

1. **Demonstrable, measured low-power design** (headline metric: sleep current / battery life)
2. **Manufacturability + reliability for a solo builder** (hand-solderable, certified RF, JLCPCB-friendly)
3. **Small, clean, dense layout** (wearable form factor)
4. **Clarity of process/rationale**

---

## D-001: BLE radio - pre-certified module vs. bare nRF52840

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

## D-002: Power management - integrated PMIC vs. discrete chain

- **Options:** (a) Nordic nPM1300 (linear charger + 2 bucks + 2 load-switch/LDOs +
  fuel-gauge measurement chain + USB-C CC detection + ship mode, one QFN32);
  (b) discrete: MCP73831 charger + MAX17048 fuel gauge + low-Iq LDO + discrete load
  switches.
- **Decision: (a) nPM1300**, with (b) held as a logged fallback if LCSC sourcing fails.
- **Why:** Power management *is* the project story. The nPM1300 gives coulomb-counting
  class fuel gauging (VBAT/IBAT/temp measurement feeding Nordic's fuel-gauge algorithm),
  hardware ship mode (~µA off-state), programmable charge current, and two load-switch
  outputs used here to hard-gate the display and sensor rails in deep sleep - that gating
  is what makes the µA sleep story real instead of rhetorical (priority #1). One QFN32
  replaces 4+ packages (priority #3) and is a part Apple/Nordic-adjacent interviewers
  recognize (priority #4).
- **Risk accepted:** QFN-32 0.4 mm... *(pitch verified against datasheet in D-010)*
  reflow requires hot-air/stencil rather than an iron; acceptable for a solo builder
  with paste + hot plate, and JLCPCB can assemble it if hand assembly fails (priority #2).

## D-003: IMU - Bosch BMI270

- **Options:** (a) Bosch BMI270; (b) ST LSM6DSO.
- **Decision: (a) BMI270.**
- **Why:** Wearable-industry-standard low-power IMU (5.9 µA low-power accel mode with
  any-motion interrupt - exactly the motion-wake mechanism this design needs), built-in
  step counter offloads counting from the SoC so it can sleep (priority #1), Zephyr has
  an in-tree driver (priority #2), and it connects to hands-on Bosch internship
  experience (priority #4). LSM6DSO is an equivalent fallback if stock fails.

## D-004: Display - Sharp Memory-in-Pixel LCD

- **Options:** (a) Sharp MIP LCD LS013B7DH03 (1.28", 128×128, SPI);
  (b) GC9A01 round TFT (240×240, SPI).
- **Decision: (a) Sharp MIP LS013B7DH03.** *(Supply voltage and FPC pinout verified
  against the Sharp datasheet in D-011 before committing the schematic.)*
- **Why:** Power is the deciding factor and it is not close: the MIP panel holds a
  static image at single-digit-µW (it only draws meaningful current while lines are
  being rewritten), needs no backlight, and is always readable in daylight - a watch
  face that costs ~µA average. A GC9A01 TFT draws tens of mA with backlight on and
  ~mA-class even dimmed; it would destroy the deep-sleep budget that is the entire
  headline (priority #1). MIP sourcing is via Digi-Key/Mouser/Adafruit rather than LCSC -
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
  because every load (nRF52840: 1.7-3.6 V, BMI270: 1.71-3.6 V, Sharp MIP: 2.7-3.3 V
  typ 3.0 V) is happy there, it maximizes usable LiPo discharge range through the buck,
  and it is the MIP panel's nominal supply.
- **Nuance logged:** BMI270 VDD could run from a 1.8 V rail for ~40% sensor energy
  savings, but that adds an always-on second buck whose quiescent current exceeds the
  saving at the ~6 µA sensor budget of this design. Rejected on net-µA math.

## D-006: Sleep-state architecture (drives all later verification)

Three power tiers, each with a projected budget to be computed part-by-part in
`docs/verification-report.md`:

1. **Ship / off** - nPM1300 ship mode, SYS rail dead, wake by SHPHLD button only.
   Target: < 1 µA from battery.
2. **Watch idle (armed sleep)** - the headline number. nRF52840 in System ON idle with
   RTC + full RAM retention (BLE off or long-interval advertising), BMI270 in low-power
   any-motion mode (its INT1 wakes the SoC), display statically holding the watch face
   (EXTCOMIN toggled at 1 Hz by nRF RTC/GPIOTE, zero CPU), display+IMU rails ON but
   idle. Target: **≤ ~20 µA total** -> months on a 150 mAh cell.
3. **Active** - BLE connected, display refresh on change only, IMU at 50 Hz.

- **Why this structure:** it maps 1:1 to what wearable teams actually ship (off / wrist-
  down / wrist-up), and every number in it is measurable at bring-up with a µCurrent or
  PPK2, so the headline figure can be replaced by a measurement before anyone quotes it.

## D-007: Board format - 4-layer, ~36 mm rounded square, 0.8 mm thick

- **Decision:** 36 × 36 mm rounded-square outline (R = 9 mm), JLCPCB 4-layer,
  **0.8 mm** finished thickness (JLC04081H-3313 stackup), layers:
  L1 components/signal, L2 solid GND, L3 power pours, L4 signal/components.
- **Why:** The Sharp 1.28" panel (~27 × 28 mm active module) sets the minimum face size;
  36 mm is small-watch territory and leaves a real antenna keep-out strip plus button /
  USB edge room (priority #3). 4 layers with a dedicated unbroken GND plane directly
  under L1 is what makes the PMIC switching loops and module grounding verifiable
  (priority #1); 0.8 mm halves stack height in a wearable and is a standard JLC 4-layer
  offering (priority #2). USB is FS-only (12 Mbps) over ~15 mm - controlled impedance
  is not required; the pair is still routed tightly coupled and length-matched as good
  practice.

## D-008: Programming/debug - Tag-Connect TC2030 + USB DFU

- **Decision:** TC2030-IDC-NL footprint (no connector BOM cost, zero height) for SWD,
  plus nRF52840 USB DFU (factory Nordic bootloader is absent on Raytac modules -
  a UF2/MCUboot bootloader is flashed once over SWD, then USB DFU serves daily
  development). Also: SWDIO/SWCLK castellations are what Tag-Connect lands on; no
  10-pin Cortex header fits a 36 mm watch.
- **Why:** Space (priority #3) and solo-builder practicality (priority #2).

## D-009: 32.768 kHz timekeeping crystal - include it

- **Options:** (a) external 32.768 kHz crystal (Epson FC-135 class) on P0.00/P0.01;
  (b) internal LFRC oscillator.
- **Decision: (a) external crystal.**
- **Why:** This is a *watch*: LFRC's ±250 ppm-class error is minutes/week of drift and
  it costs more current than the LFXO once calibration wakeups are counted
  (LFXO ~ 0.23 µA vs LFRC ~ 0.7 µA + periodic HFCLK calibration bursts on nRF52840).
  Crystal accuracy also tightens BLE sleep-clock windows -> shorter radio-on time per
  connection event (priority #1). Cost: one 3215 crystal + 2 caps (12 pF class, set from
  the FC-135 CL spec against nRF52840 pin capacitance - calc in verification report).

---

## D-010: Module sourcing - LCSC listed but out of stock; keep MDBT50Q-1MV2 via DigiKey

- **Finding (2026-07-02):** LCSC lists every Raytac variant - MDBT50Q-1MV2 = C5118826
  ($6.83), P1MV2 = C5119772, U1MV2 = C2688382 - but all show **zero stock**. DigiKey has
  MDBT50Q-1MV2 in stock, ships today.
- **Options:** (a) keep 1MV2, source DigiKey, hand-place; (b) swap to an LCSC-stocked
  non-Raytac module (e.g. Ebyte E73-2G4M08S1C); (c) wait for restock.
- **Decision: (a).** The module's castellated pads are the single most iron-friendly
  package on the board - hand-placing it costs nothing in practice (priority #2 intact),
  and Raytac + nRF52840 is the wearable-industry-standard combination the project story
  depends on (priorities #1/#4). The KiCad footprint accepts 1MV2 and P1MV2
  interchangeably (identical pads per datasheet §2.1), so a future JLC-assembled run can
  use whichever variant LCSC restocks - C-numbers recorded in `hardware/parts.yaml`.
- **Verified datasheet rules to carry into layout:** antenna keep-out **12.4 mm wide ×
  3.8 mm deep, all layers, no copper**, extending ~1 mm beyond both module sides; plus a
  1.6 × 1.2 mm top-layer-only keep-out notch 2.95 mm from the module's left edge;
  module placed with antenna at the board edge (DS §2.2-2.3, Ver.K).

## D-011: nPM1300 sourcing - same situation, same call

- **Finding:** nPM1300-QEAA-R7 = LCSC C7501206, listed, **zero stock**; WLCSP variant
  (CAAA) in stock but not hand-solderable - rejected. DigiKey: $2.95, ships today.
- **Options:** (a) keep nPM1300, DigiKey, hand hot-air reflow; (b) invoke the discrete
  fallback (MCP73831 + MAX17048 + LDO + 2× load switch, all LCSC basic).
- **Decision: (a).** The fallback would cost the design its ship mode, hardware
  power-gating, coulomb-counting-class fuel gauge, and USB-C detection - i.e. the
  measurable low-power architecture that is priority #1 - in exchange for fixing a
  sourcing gap that DigiKey already fills. QFN32 @ 0.5 mm pitch with a 3.5 mm EP
  (PS mech spec) reflows fine with paste + hot plate. The two hand-place lines (U1, U2)
  are exactly the two parts a JLC economic-assembly order can't place today; everything
  else on the BOM is LCSC-stocked, so the board still assembles as
  "JLC does the fiddly passives, builder places two ICs."

## D-012: Rail strapping - BUCK2 is the system rail (3.0 V at power-on, no firmware needed)

- **Finding:** nPM1300 buck startup voltages are strapped by VSET resistors, and the two
  tables are asymmetric: VSET1 tops out at 2.7 V (250-500 kΩ), while **VSET2 = 150 kΩ
  gives exactly 3.0 V** (PS BUCK chapter).
- **Decision:** System 3V0 rail = **BUCK2, VSET2 = 150 kΩ 1%** -> correct-by-hardware at
  first power, no I2C bootstrap dependency for the SoC supply. BUCK1 is populated per
  Nordic reference configuration 1 (L + caps + VSET1 = 47 kΩ -> 1.8 V) but **disabled by
  firmware at init** - it exists as a validated-by-datasheet 1.8 V experiment rail
  without inventing an un-datasheet-ed "unused buck" strapping. Its disable is a checked
  item in the verification report's leakage review.
- **Load switches:** LSW1 ← 3V0 -> display VDD/VDDA; LSW2 ← 3V0 -> IMU VDD.
  (LSIN1/LSIN2 wired from BUCK2 output, load-switch mode, so deep sleep can cut both
  domains completely.)

## D-013: Display connector - Hirose FH12A, low stock flagged

- FH12A-10S-0.5SH(55) = C5139870, **91 units** in stock (genuine FH12 = C506791, 38).
  Kept: it's the proven connector for this panel family (Adafruit breakout uses FH12),
  KiCad ships the exact footprint, and the build needs 1-2 units - but flagged in
  `parts.yaml` to order early. Display module itself (LS013B7DH03, VDD 2.7-3.3 V
  verified from Sharp spec §6-1, 12 µW static typ §6-4) ships from DigiKey/Adafruit and
  is hand-attached - never JLC-assembled, so LCSC stock is not required for it.

## D-014: Button architecture - power button on SHPHLD, user button on GPIO

- **Constraint found in PS:** SHPHLD has an internal 50 kΩ pull-up to the battery
  domain - the node swings to VBAT (up to 4.2 V), which exceeds the nRF52840 GPIO
  absolute max (VDD + 0.3 V). The two nets must not share a button naively.
- **Decision:** SW1 = power button -> nPM1300 SHPHLD only (ship-mode exit ≥ 96 ms press,
  also readable as a PMIC event over I2C/GPIO interrupt). SW2 = user button -> nRF
  P1.13 with internal pull-up (uses a radio-adjacent "low-frequency-only" module pin,
  which buttons are perfect for) - GPIO SENSE wakes the SoC from System OFF.
  Both lines get 100 Ω series + ESD9B3.3ST5G TVS at the switch (user-touchable nets).
  No external pull-ups -> zero standing current either way (priority #1).

## D-015: No discrete USB-C CC pull-downs - nPM1300 does Type-C detection

- The task brief specified 5.1 kΩ CC pull-downs; the nPM1300 PS reference circuit
  connects CC1/CC2 straight to the receptacle because the PMIC implements USB Type-C
  sink detection (100/500/1500 mA input-limit negotiation) internally. **Datasheet wins;
  resistors deleted.** Logged as a deliberate deviation from the brief, per its own
  "follow the datasheet, document why" escape hatch.

## D-016: No charge LED

- nPM1300 offers 3 LED drivers; a charge LED at ~2 mA would dwarf the entire sleep
  budget if left on and is invisible inside a watch case anyway. Charge status is
  reported via the fuel-gauge/charger registers -> BLE Battery Service and the
  watch face. PMIC GPIO0 is wired to nRF P0.12 as the charger/fuel-gauge interrupt
  line instead. (Priority #1 over blinkenlights.)

## D-017: On-board NTC (10 kΩ, populated)

- Small hobby LiPo packs frequently omit the thermistor lead; the nPM1300 requires NTC
  or an explicit register disable. Populating a board NTC (Murata NCP15XH103F03RC,
  10 k B3380 1%, placed at the battery connector) keeps hardware charge-temperature
  protection real (JEITA windows in the charger) instead of software-disabled - a
  safety-credibility point for a wearable strapped to a wrist. If a pack with its own
  NTC is chosen later, the board part is depopulated and the pack lead lands on the
  same net (noted in human-review checklist).

## D-018: Bus strapping and idle-current hygiene

- I2C (PMIC, 400 kHz): 4.7 kΩ pulls to the always-on 3V0 rail - idle-high bus burns
  zero standing current; PMIC must stay reachable in every sleep state, so its bus
  cannot live on a gated rail.
- BMI270 CSB: 100 kΩ pull-up to the *gated* IMU rail (deselected during nRF reset when
  GPIOs float; pull-up to its own domain can't back-feed the rail when gated).
- Display SCS: 100 kΩ pull-down (Sharp SCS is active-high; float-low keeps it
  deselected; a pull-down holding an idle-low node costs zero current).
- ASDx/ASCx (BMI270 aux bus, unused): tied to VDDIO per DS Table 22; OCSB/OSDO: DNC.
- All strapping resistors chosen so that **every pull is toward its net's idle state**
  -> 0 µA standing current across the board (verified line-by-line in the report).

## D-019: USB-C VBUS wired at one merged pad pair

- **Finding:** on the HRO 16-pin footprint each *physical* VBUS pad is already
  the merged A/B pair (A4/B9 on one pad, A9/B4 on the other), so a single pad
  delivers VBUS in both plug orientations; the second pad only adds current
  capacity. The west pad is boxed in by an NPTH shell post, the CC2 pad and
  the shield pad - connecting it forced clearance violations in every variant
  tried.
- **Decision:** wire the east pad only (0.3 mm entry + via into the In1 VBUS
  plane). At the 500 mA input limit this is a comfortable margin (IPC-2221
  calc in the verification report); the unwired pad is noted here rather than
  silently left.

## D-020: Copper clearance rule 0.15 -> 0.13 mm

- Mid-routing the default clearance was lowered to 0.13 mm (all net classes).
  JLCPCB's 4-layer capability floor is 0.09 mm, so 0.13 keeps ~ 45 % margin
  over fab limits while opening the QFN escape lanes that made the PMIC
  fan-out routable (the 0.5 mm-pitch pad gaps admit 0.48/0.2 mm vias at 0.13,
  not at 0.15). All pre-existing routing was done at 0.15 and passes trivially.

## D-021: Solid zone connections (no thermal reliefs)

- Starved-thermal DRC violations on dense 0402 ground pads were eliminated by
  switching all pours to solid connection. Tradeoff: hand-iron rework of
  ground pads needs more heat; JLC reflow and hot-air work are unaffected.
  Chosen because the alternative (per-pad spoke tuning) added no electrical
  value on a board with a dedicated In2 ground plane.

## D-022: Seven links left unrouted at the autoroute stage

- After three autoroute rounds and a raster-verified completion pass, seven
  links in the congested U2 south-west quadrant still could not be closed
  without clearance violations (each attempt collided with other nets'
  copper). Rather than force them in, each was documented with exact endpoints
  and the surrounding copper that blocks it. The board is otherwise DRC-clean
  (zero violations), and the fab README gates ordering on closing them.

## D-023: Review pass closed the three power-critical links

- A dedicated layout review re-attacked the seven open links with a full
  survey of local copper (hardware/scripts/survey.py) instead of the earlier
  incomplete obstacle model. Result: VBAT (pin 19), VSYS pin 20 and VSYS
  pin 4 (PVDD) are now routed and DRC-clean. This took relocating the NTC
  trace out of the south-west slot, one drill resize on a cluster via, a
  via at the VBAT pour edge, a via-less B.Cu path for pin 20 onto existing
  VSYS copper, and an In1 connection lane under the PMIC exposed pad.
  These three links were mandatory: pin 20 is the PMIC's VSYS output, so the
  board was electrically dead without them.
- The remaining four (DISP_SCK, 3V0 to pin 12, SHPHLD, CC2) were also
  attempted: two further Freerouting rounds with 13 corridor nets ripped
  closed SHPHLD but broke I2C_SCL in exchange, so that state was reverted.
  Manual analysis shows each survivor is blocked by locked routing (the
  USB_DP via sits 0.45 mm under pin 12's pad mouth) or requires multi-net
  shoves beyond safe scripted reach. They stay documented in the review
  checklist with the updated analysis; closing them interactively is the
  remaining pre-order work.

## D-024: Ground-island stitching (correction to earlier assessment)

- The 16 zone-island ratsnest entries were previously described as cosmetic.
  Review showed the opposite: every island carries real component ground
  pads (IMU ground pins, decoupling-cap returns, the USB ESD ground, both
  buttons), which floated without a via to the In2 plane. A clearance-checked
  stitching pass (hardware/scripts/stitch_islands.py) added 13 vias; three
  islands (C1.2, C9.2, C21.2/C22.2 - four capacitor ground pads) have no
  legal via site without moving adjacent routing and are listed in the
  checklist for the same interactive session.

## D-025: Display connector placement and pin order are wrong - found at pre-order review

- Sharp's outline drawing (LS013B7DH03 spec fig 8-1) shows the FPC tail
  **centered** on the panel (13.3 mm from the panel edge) with terminal 1 on
  the **right** in the front view, contacts on the tail's back side, and a
  mandatory fold away from the polarizer. Consequences for this board:
  1. J2 at x=89.3 is unreachable - with the panel on the board, the tail
     center can only fall between x=95.3 and x=104.7. J2 must move to x=100.
  2. After the 180-degree fold the contact face flips up and left-right
     reverses as seen by the connector: pad k must carry panel terminal
     (11-k). The schematic and netlist are corrected (this commit); ERC 0/0.
     The FH12A (top-contact) is the right part for this mounting.
  3. The active area is 1.85 mm north of panel center - enclosure aperture
     offset corrected to 4.2 mm in a follow-up.
- Layout consequences (verified by trial re-route, then reverted to keep the
  board in a known-good state): J2 belongs at pads y~109.8 so its body sits
  between the USB-C shell-leg pairs at (95.7/104.3, 114.65) and the tail
  folds between them; the J2 MP pads need trimming (custom footprint) to
  clear the leg holes; the USB_DM_CONN crossover descent at x=99.85 crosses
  the new pad row and must be redesigned north of y~109; the display fan
  re-routes south from the module (trial run closed it plus SHPHLD and
  I2C_SCL cleanly). Ordering is blocked until this lands.
- Second review session findings (branch `d025-layout-wip` holds the work in
  progress): the USB-C shell has four top-protruding solder slots at
  (95.68/104.32, 110.47 and 114.65) that bracket the whole south strip, so
  the connector cannot sit south of the panel at all. Final verified
  position: J2 at (100, 107.75) - pads y=105.9, body fully under the panel
  (which mounts on 1.2 mm foam so its terminal ledge clears the 1.0 mm body),
  tail folding at the board edge between the leg columns. Proven on the
  branch: J2 placement + mirrored nets, USB CONN highways re-laid at
  y=107.95/108.35, the DM crossover loop, CC2 landing directly on J1.B5 via
  a (98.24, 108.87) via, CC1 landing from the north-east, and a
  zero-violation checkpoint with the display fan, I2C, SHPHLD and CC pair
  routed. Remaining: the south-quadrant fabric (strap highways, DISP_SCK
  east path, 3V0 pin 12, pin 28/29 pocket) needs one interactive-router
  session; scripted attempts oscillate against the autorouter's re-lays.

---

*Layout-phase constraint decisions (stackup, keep-outs, netclasses) live in the
build scripts and the verification report; this log records the choices.*
