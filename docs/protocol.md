# BLE protocol

Device name `JRWatch`, BLE peripheral, connectable slow advertising
(1–2 s interval). Preferred connection parameters: 50–100 ms interval,
slave latency 4, timeout 4 s — chosen for idle-connected current, not
latency.

## Services

### Battery Service — standard `0x180F`

| Characteristic | UUID | Access | Format |
|---|---|---|---|
| Battery Level | `0x2A19` | read / notify | uint8, percent |

Fed from the nPM1300 measurement chain (VBAT via the charger's sensor
channels + OCV table; NCS `nrf_fuel_gauge` is the drop-in upgrade).

### Motion Service — custom base `6a570000-8f9d-4a7c-9b31-24d1c30f51aa`

| Characteristic | UUID (short) | Access | Format |
|---|---|---|---|
| Step count | `6a570001-…` | read / notify | uint32 little-endian, steps since boot |
| Activity state | `6a570002-…` | read | uint8: 0 = idle (armed sleep), 1 = active |

Step notifications are emitted only when the value changes and only while a
client has subscribed — no periodic radio traffic otherwise.

## Planned (documented, not yet implemented)

- Current Time Service client → real wall-clock on the face.
- MCUboot + USB DFU for cable updates (flash partitions already laid out).
