#!/usr/bin/env python3
"""
JRWatch — schematic as code.

Builds the complete netlist, runs ERC, and emits:
  hardware/netlist/jrwatch.net            KiCad netlist
  hardware/netlist/jrwatch-netlist.json   parts+nets for the board build scripts
  hardware/netlist/erc-report.txt         ERC output

Block structure mirrors docs/design-rationale.md:
  power   — nPM1300: USB-C in, LiPo charge path, BUCK1/BUCK2, load switches
  mcu     — MDBT50Q-1MV2 module, 32k crystal, decoupling, Tag-Connect SWD
  usb     — USB-C data pairs through USBLC6 ESD to the module
  imu     — BMI270 on its own SPI, INT1 motion wake
  display — Sharp MIP LCD via 10-pin FPC, gated rail
  controls— SW1 power (SHPHLD), SW2 user (GPIO wake), both ESD-protected
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skidl import Net, ERC, generate_netlist, POWER
# NC and default_circuit are injected into builtins by skidl on import
from parts_lib import (MDBT50Q, NPM1300, BMI270, USB_C, FPC10, JST_SH2, TC2030,
                       USBLC6, XTAL32K, BUCK_L, TACT_SIDE, ESD_3V3, ESD_5V0,
                       NTC10K, C0402, C0603, R0402, PASSIVE_LCSC)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'netlist')
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------- global nets
gnd      = Net('GND');       gnd.drive = POWER
vbat     = Net('VBAT');      vbat.drive = POWER      # battery + (J3.1)
vbus_usb = Net('VBUS_USB');  vbus_usb.drive = POWER  # USB-C VBUS -> PMIC
vsys     = Net('VSYS')                               # PMIC power path output
v3v0     = Net('3V0')                                # BUCK2 — always-on system rail
v1v8     = Net('1V8_AUX')                            # BUCK1 — populated, fw-disabled
vbus_out = Net('VBUS_OUT')                           # PMIC VBUSOUT -> module VBUS (5V)
vdd_disp = Net('VDD_DISP')                           # LSW1-gated display rail
vdd_imu  = Net('VDD_IMU')                            # LSW2-gated sensor rail

usb_dp_conn = Net('USB_DP_CONN'); usb_dm_conn = Net('USB_DM_CONN')
usb_dp      = Net('USB_DP');      usb_dm      = Net('USB_DM')
cc1 = Net('CC1'); cc2 = Net('CC2')

i2c_sda = Net('I2C_SDA'); i2c_scl = Net('I2C_SCL')
pmic_int = Net('PMIC_INT')
shphld = Net('SHPHLD')            # PMIC side of power button (swings to VBAT!)
btn2 = Net('BTN2')                # nRF side of user button (3V0 logic)

imu_sck = Net('IMU_SCK'); imu_mosi = Net('IMU_MOSI')
imu_miso = Net('IMU_MISO'); imu_cs = Net('IMU_CS'); imu_int1 = Net('IMU_INT1')

disp_sck = Net('DISP_SCK'); disp_mosi = Net('DISP_MOSI'); disp_cs = Net('DISP_CS')
disp_on = Net('DISP_ON'); extcomin = Net('EXTCOMIN')

swdio = Net('SWDIO'); swdclk = Net('SWDCLK'); nrst = Net('nRESET'); swo = Net('SWO')
xl1 = Net('XL1'); xl2 = Net('XL2')
ntc = Net('NTC')

# ------------------------------------------------------------------- helpers
def _tag(part, kind, value):
    info = PASSIVE_LCSC.get((kind, value))
    if info:
        part.fields['LCSC'], part.fields['MPN'], part.fields['Mfr'] = info
        part.fields['Sourcing'] = 'jlc'
    return part

def cap(value, size='0402'):
    c = (C0603 if size == '0603' else C0402)(value=value)
    return _tag(c, 'C', value)

def res(value):
    return _tag(R0402(value=value), 'R', value)

def decouple(net, *specs):
    """specs: ('100nF','0402') tuples or bare '100nF' strings."""
    for s in specs:
        v, sz = s if isinstance(s, tuple) else (s, '0402')
        c = cap(v, sz)
        c[1] += net
        c[2] += gnd

# ============================================================ POWER (nPM1300)
u2 = NPM1300(ref='U2', value='nPM1300-QEAA-R7')

# charge path & power path
u2['VBAT'] += vbat
u2['VSYS'] += vsys
u2['PVDD'] += vsys                       # bucks fed from system power path
u2['VBUS'] += vbus_usb
u2['VBUSOUT'] += vbus_out
u2['EP_AVSS'] += gnd
u2['PVSS1'] += gnd
u2['PVSS2'] += gnd
decouple(vbat, ('10uF', '0603'))
decouple(vsys, ('10uF', '0603'), ('2.2uF', '0603'), '100nF')
decouple(vbus_usb, ('10uF', '0603'))
decouple(vbus_out, '1uF')

# USB-C CC lines — nPM1300 implements Type-C sink detection internally (D-015)
u2['CC1'] += cc1
u2['CC2'] += cc2

# BUCK1: 1.8 V aux (populated per Nordic ref config 1, disabled by firmware, D-012)
l1 = BUCK_L(ref='L1', value='2.2uH')
u2['SW1'] += l1[1]
l1[2] += v1v8
u2['VOUT1'] += v1v8
decouple(v1v8, ('10uF', '0603'))
r_vset1 = res('47k')                     # VSET1 47k -> 1.8 V startup
u2['VSET1'] += r_vset1[1]
gnd += r_vset1[2]

# BUCK2: 3.0 V system rail — correct at power-on by VSET2 strap (D-012)
l2 = BUCK_L(ref='L2', value='2.2uH')
u2['SW2'] += l2[1]
l2[2] += v3v0
u2['VOUT2'] += v3v0
decouple(v3v0, ('10uF', '0603'))
r_vset2 = res('150k')                    # VSET2 150k -> 3.0 V startup
u2['VSET2'] += r_vset2[1]
gnd += r_vset2[2]

# load switches: LSIN from the 3V0 rail so gated domains see clean 3.0 V
u2['LSIN1'] += v3v0
u2['LSOUT1'] += vdd_disp
decouple(vdd_disp, '1uF')
u2['LSIN2'] += v3v0
u2['LSOUT2'] += vdd_imu
decouple(vdd_imu, '1uF')

# PMIC housekeeping
u2['VDDIO'] += v3v0
decouple(v3v0, '100nF')                  # at VDDIO pin
u2['SDA'] += i2c_sda
u2['SCL'] += i2c_scl
for pull_net in (i2c_sda, i2c_scl):
    r = res('4.7k')
    pull_net += r[1]
    v3v0 += r[2]
u2['GPIO0'] += pmic_int
u2['SHPHLD'] += shphld
for p in ('GPIO1', 'GPIO2', 'GPIO3', 'GPIO4', 'LED0', 'LED1', 'LED2'):
    u2[p] += NC

# battery temperature: on-board NTC at the battery connector (D-017)
rt1 = NTC10K(ref='RT1', value='10k NTC')
u2['NTC'] += ntc
ntc += rt1[1]
gnd += rt1[2]

# battery connector — PIN 1 = BAT+
j3 = JST_SH2(ref='J3', value='SM02B-SRSS-TB')
j3[1] += vbat
j3[2] += gnd
j3['MP'] += gnd

# ======================================================== MCU (MDBT50Q-1MV2)
u1 = MDBT50Q(ref='U1', value='MDBT50Q-1MV2')

u1[28] += v3v0                           # VDD
u1[30] += v3v0                           # VDDH tied to VDD — normal voltage mode
u1[32] += vbus_out                       # VBUS from PMIC VBUSOUT
for gpin in (1, 2, 15, 33, 55):
    u1[gpin] += gnd
decouple(v3v0, ('10uF', '0603'), '100nF', '100nF')   # module VDD + VDDH
decouple(vbus_out, '100nF')

# 32.768 kHz crystal (D-009). Load caps 12 pF placeholder — final value from
# the LFXO budget calc in docs/verification-report.md (CL=12.5 pF crystal).
y1 = XTAL32K(ref='Y1', value='32.768kHz')
u1[17] += xl1
u1[18] += xl2
y1[1] += xl1
y1[2] += xl2
for xnet in (xl1, xl2):
    c = cap('12pF')
    xnet += c[1]
    gnd += c[2]

# SWD via Tag-Connect
j4 = TC2030(ref='J4', value='TC2030-IDC-NL')
j4[1] += v3v0
j4[2] += swdio;  u1[51] += swdio
j4[3] += nrst;   u1[40] += nrst
j4[4] += swdclk; u1[53] += swdclk
j4[5] += gnd
j4[6] += swo;    u1[47] += swo

# peripheral pin map (see docs/design-rationale.md pin table)
u1[36] += i2c_sda                        # P0.14
u1[37] += i2c_scl                        # P0.13
u1[29] += pmic_int                       # P0.12
u1[42] += imu_sck                        # P0.19
u1[43] += imu_mosi                       # P0.21
u1[45] += imu_miso                       # P0.23
u1[46] += imu_cs                         # P0.22
u1[49] += imu_int1                       # P0.25
u1[41] += disp_sck                       # P0.17
u1[44] += disp_mosi                      # P0.20
u1[39] += disp_cs                        # P0.15
u1[38] += disp_on                        # P0.16
u1[50] += extcomin                       # P1.02 (LF pin, 1 Hz signal — allowed)
u1[6]  += btn2                           # P1.13 (LF pin, button — allowed)

# unused module pins
u1[31] += NC                             # DCCH — REG0 unused in normal-voltage mode
for spare in (3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 16, 19, 20, 21, 22, 23,
              24, 25, 26, 27, 48, 52, 54, 56, 57, 58, 59, 60, 61):
    u1[spare] += NC

# ================================================================ USB-C DATA
j1 = USB_C(ref='J1', value='TYPE-C-31-M-12')
u4 = USBLC6(ref='U4', value='USBLC6-2SC6')

for p in ('A1', 'A12', 'B1', 'B12'):
    j1[p] += gnd
j1['SH'] += gnd
for p in ('A4', 'A9', 'B4', 'B9'):
    j1[p] += vbus_usb
j1['A5'] += cc1
j1['B5'] += cc2
j1['A6'] += usb_dp_conn; j1['B6'] += usb_dp_conn
j1['A7'] += usb_dm_conn; j1['B7'] += usb_dm_conn
j1['A8'] += NC; j1['B8'] += NC

# ESD array in the data path (flow-through), before the module
u4[1] += usb_dp_conn                     # IO1
u4[6] += usb_dp                          # IO1'
u4[3] += usb_dm_conn                     # IO2
u4[4] += usb_dm                          # IO2'
u4[5] += vbus_usb
u4[2] += gnd
u1[35] += usb_dp                         # D+
u1[34] += usb_dm                         # D-

# ===================================================================== IMU
u3 = BMI270(ref='U3', value='BMI270')
u3['VDD'] += vdd_imu
u3['VDDIO'] += v3v0                      # always-on: interface stays defined when VDD gated
u3['GND'] += gnd
u3['GNDIO'] += gnd
decouple(vdd_imu, '100nF')
decouple(v3v0, '100nF')                  # at VDDIO pin
u3['SCX'] += imu_sck
u3['SDX'] += imu_mosi
u3['SDO'] += imu_miso
u3['CSB'] += imu_cs
r_csb = res('100k')                      # CSB pull-up: deselected while nRF pins float
imu_cs += r_csb[1]
v3v0 += r_csb[2]
u3['INT1'] += imu_int1
u3['ASDX'] += v3v0                       # aux I/F unused -> VDDIO (DS Table 22)
u3['ASCX'] += v3v0
for p in ('INT2', 'OCSB', 'OSDO'):
    u3[p] += NC

# ================================================================== DISPLAY
j2 = FPC10(ref='J2', value='FH12A-10S-0.5SH')
j2[1] += disp_sck
j2[2] += disp_mosi
j2[3] += disp_cs
r_scs = res('100k')                      # SCS is active-high: pull-down = deselected
disp_cs += r_scs[1]
gnd += r_scs[2]
j2[4] += extcomin
j2[5] += disp_on
j2[6] += vdd_disp                        # VDDA
j2[7] += vdd_disp                        # VDD
j2[8] += vdd_disp                        # EXTMODE=H -> EXTCOMIN pin mode (Sharp Rmk 4-1)
j2[9] += gnd                             # VSS
j2[10] += gnd                            # VSSA
j2['MP'] += gnd
decouple(vdd_disp, '1uF', '100nF', '1uF', '100nF')   # VDD + VDDA pairs

# ================================================================= CONTROLS
# SW1: power button -> SHPHLD only (node swings to VBAT — never to an nRF pin, D-014)
sw1 = TACT_SIDE(ref='SW1', value='PWR/SHIP')
d1 = ESD_5V0(ref='D1', value='ESD9B5.0')
r_sw1 = res('100R')
shphld += r_sw1[1]
btn1_pad = Net('BTN1_PAD')
r_sw1[2] += btn1_pad
sw1[1] += btn1_pad
d1[1] += btn1_pad
d1[2] += gnd
sw1[2] += gnd
sw1['MP'] += gnd

# SW2: user button -> nRF GPIO with internal pull-up (wake from System OFF)
sw2 = TACT_SIDE(ref='SW2', value='USER')
d2 = ESD_3V3(ref='D2', value='ESD9B3.3')
r_sw2 = res('100R')
btn2 += r_sw2[1]
btn2_pad = Net('BTN2_PAD')
r_sw2[2] += btn2_pad
sw2[1] += btn2_pad
d2[1] += btn2_pad
d2[2] += gnd
sw2[2] += gnd
sw2['MP'] += gnd

# ================================================================ OUTPUTS
if __name__ == '__main__':
    ERC()
    # archive the ERC report next to the netlist
    erc_src = os.path.splitext(os.path.basename(__file__))[0] + '.erc'
    if os.path.exists(erc_src):
        os.replace(erc_src, os.path.join(OUT_DIR, 'erc-report.txt'))

    net_file = os.path.join(OUT_DIR, 'jrwatch.net')
    generate_netlist(file_=net_file)

    data = {'parts': [], 'nets': []}
    for p in sorted(default_circuit.parts, key=lambda x: x.ref):
        data['parts'].append({
            'ref': p.ref,
            'value': str(p.value),
            'name': p.name,
            'footprint': str(p.footprint),
            'fields': {k: str(v) for k, v in p.fields.items()
                       if k not in ('F0', 'F1', 'F2')},
        })
    for n in default_circuit.get_nets():
        if not n.pins:
            continue
        data['nets'].append({
            'name': n.name,
            'pins': sorted([[pin.part.ref, str(pin.num)] for pin in n.pins]),
        })
    data['nets'].sort(key=lambda x: x['name'])
    with open(os.path.join(OUT_DIR, 'jrwatch-netlist.json'), 'w') as f:
        json.dump(data, f, indent=1)

    print(f"parts: {len(data['parts'])}  nets: {len(data['nets'])}")
    print(f"wrote {net_file}")
