# JRWatch firmware (Zephyr RTOS)

Vanilla-Zephyr application (pinned `v4.1.0` via `west.yml`) with a custom
board definition (`boards/jr/jrwatch/`) that mirrors the schematic pin map
exactly — the devicetree is generated-from/checked-against
`hardware/skidl/jrwatch.py`.

## Build

CI builds every push (`.github/workflows/firmware.yml`, Zephyr CI container).
Locally:

```sh
mkdir jr-ws && cd jr-ws
git clone https://github.com/jadenrhee/JRWatch jrwatch
west init -l --mf firmware/west.yml jrwatch
west update
west build -b jrwatch jrwatch/firmware
west flash   # SWD via TC2030
```

First-time flash is over SWD (Tag-Connect TC2030). USB DFU (MCUboot +
`slot1` partition is already laid out in the devicetree) is the documented
follow-up for cable-only updates.

## How the firmware maps to the power goals

| State | What runs | What's off | Budget driver |
|---|---|---|---|
| **SHIP** | nPM1300 only (battery disconnected from VSYS) | everything | PMIC ship mode ≈ sub-µA; exit = SW1 ≥ 96 ms or USB plug |
| **IDLE** ("armed sleep") | nRF System ON idle + RTC (LFXO), BMI270 low-power any-motion @25 Hz, MIP panel statically holding the face, slow BLE adv (1–2 s) | display SPI quiet (image is retained in-pixel), CPU in WFI, BUCK1 off | the headline number — itemized in `docs/verification-report.md` |
| **ACTIVE** | display redraw *only on content change*, IMU 50 Hz, BLE connectable | — | 20 s inactivity drops back to IDLE |

Mechanisms:

- **Hardware power gating**: `VDD_DISP` and `VDD_IMU` are nPM1300 load
  switches (devicetree `npm1300_lsw_disp` / `npm1300_lsw_imu`), driven via
  the Zephyr regulator API. Before cutting the display rail the interface
  lines are quiesced so the unpowered panel is never back-fed (`ui.c`).
- **BUCK1 held off** at boot (`regulator-boot-off` + a runtime check) —
  it is the populated-but-unused 1.8 V experiment rail (decision D-012).
- **Wake sources**: BMI270 INT1 (any-motion) and SW2 both post to a
  `k_event`; between events the idle thread keeps the SoC in System ON idle
  with everything clock-gated. SW1 is wired to the PMIC's SHPHLD only.
- **Display never polled**: the frame is diffed as a string; identical
  content means zero SPI traffic, and the MIP panel holds the image at ~µW
  with the driver toggling EXTCOMIN at 1 Hz.
- **32.768 kHz crystal** (LFXO) for timekeeping and tight BLE sleep-clock
  accuracy — cheaper than LFRC + calibration (decision D-009).
- **Ship mode**: 5 s long-press on SW2 gates both rails then calls
  `mfd_npm1300_hibernate()`; the PMIC disconnects the battery.
- **Battery %**: nPM1300 charger measurements (VBAT/status via sensor
  channels) + an OCV table. Nordic's `nrf_fuel_gauge` (NCS) is the
  higher-accuracy drop-in when building under nRF Connect SDK.

Known follow-ups: on-chip BMI270 step counter (Zephyr driver
doesn't expose it; host-side estimator in `motion.c` meanwhile), BLE
Current Time Service for real wall-clock, MCUboot + USB DFU enablement.

## BLE GATT protocol

Advertises as `JRWatch`, connectable, 1–2 s advertising interval.
Preferred connection parameters 50–100 ms interval, latency 4.

| Service | Characteristic | UUID | Access | Format |
|---|---|---|---|---|
| Battery Service (0x180F) | Battery Level (0x2A19) | standard | read/notify | uint8 % |
| Motion (custom) | — | `6a570000-8f9d-4a7c-9b31-24d1c30f51aa` | — | — |
| | Step count | `6a570001-…` | read/notify | uint32 LE |
| | Activity state | `6a570002-…` | read | uint8 (0 idle / 1 active) |

Console/logs are on SEGGER RTT (no UART pins on the board).
