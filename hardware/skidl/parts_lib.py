"""
JRWatch part library — every part defined pin-by-pin from its datasheet.

Pin numbering matches the KiCad footprint pad names exactly (netlist import
maps by pad name). Sources:
  MDBT50Q-1MV2  Raytac spec Ver.K §2.5 (61 castellated/bottom pads)
  nPM1300-QEAA  Nordic PS, pin assignment table (QFN32 + EP=33)
  BMI270        Bosch BST-BMI270-DS000-08 Table 22
  LS013B7DH03   Sharp LD-26X06A Table 4 (via 10-pin FPC)
  USBLC6-2SC6   ST datasheet (SOT-23-6 flow-through)
"""
from skidl import Part, Pin, SKIDL, TEMPLATE

_t = Pin.types


def _mk(name, ref_prefix, footprint, description, pins, **fields):
    p = Part(name=name, tool=SKIDL, dest=TEMPLATE, ref_prefix=ref_prefix,
             description=description, footprint=footprint)
    for num, pname, ptype in pins:
        p += Pin(num=str(num), name=pname, func=ptype)
    for k, v in fields.items():
        p.fields[k] = v
    return p


# --------------------------------------------------------------------------
# Raytac MDBT50Q-1MV2 (nRF52840). Pins marked LF in the datasheet are
# "standard drive, low frequency I/O only" (radio-adjacent) — the schematic
# uses them only for buttons / EXTCOMIN / interrupts, never SPI/I2C.
# --------------------------------------------------------------------------
MDBT50Q = _mk(
    'MDBT50Q-1MV2', 'U', 'RF_Module:Raytac_MDBT50Q',
    'BLE module, nRF52840, chip antenna, BT5.x certified',
    [
        (1,  'GND',        _t.PWRIN),
        (2,  'GND',        _t.PWRIN),
        (3,  'P1.10',      _t.BIDIR),   # LF
        (4,  'P1.11',      _t.BIDIR),   # LF
        (5,  'P1.12',      _t.BIDIR),   # LF
        (6,  'P1.13',      _t.BIDIR),   # LF
        (7,  'P1.14',      _t.BIDIR),   # LF
        (8,  'P1.15',      _t.BIDIR),   # LF
        (9,  'P0.03/AIN1', _t.BIDIR),   # LF
        (10, 'P0.29/AIN5', _t.BIDIR),   # LF
        (11, 'P0.02/AIN0', _t.BIDIR),   # LF
        (12, 'P0.31/AIN7', _t.BIDIR),   # LF
        (13, 'P0.28/AIN4', _t.BIDIR),   # LF
        (14, 'P0.30/AIN6', _t.BIDIR),   # LF
        (15, 'GND',        _t.PWRIN),
        (16, 'P0.27',      _t.BIDIR),
        (17, 'P0.00/XL1',  _t.BIDIR),
        (18, 'P0.01/XL2',  _t.BIDIR),
        (19, 'P0.26',      _t.BIDIR),
        (20, 'P0.04/AIN2', _t.BIDIR),
        (21, 'P0.05/AIN3', _t.BIDIR),
        (22, 'P0.06',      _t.BIDIR),
        (23, 'P0.07',      _t.BIDIR),
        (24, 'P0.08',      _t.BIDIR),
        (25, 'P1.08',      _t.BIDIR),
        (26, 'P1.09',      _t.BIDIR),
        (27, 'P0.11',      _t.BIDIR),
        (28, 'VDD',        _t.PWRIN),
        (29, 'P0.12',      _t.BIDIR),
        (30, 'VDDH',       _t.PWRIN),
        (31, 'DCCH',       _t.NOCONNECT),  # REG0 DC/DC out — unused in normal-voltage mode
        (32, 'VBUS',       _t.PWRIN),      # 5 V input for internal USB regulator
        (33, 'GND',        _t.PWRIN),
        (34, 'D-',         _t.BIDIR),
        (35, 'D+',         _t.BIDIR),
        (36, 'P0.14',      _t.BIDIR),
        (37, 'P0.13',      _t.BIDIR),
        (38, 'P0.16',      _t.BIDIR),
        (39, 'P0.15',      _t.BIDIR),
        (40, 'P0.18/nRESET', _t.BIDIR),
        (41, 'P0.17',      _t.BIDIR),
        (42, 'P0.19',      _t.BIDIR),
        (43, 'P0.21',      _t.BIDIR),
        (44, 'P0.20',      _t.BIDIR),
        (45, 'P0.23',      _t.BIDIR),
        (46, 'P0.22',      _t.BIDIR),
        (47, 'P1.00/SWO',  _t.BIDIR),
        (48, 'P0.24',      _t.BIDIR),
        (49, 'P0.25',      _t.BIDIR),
        (50, 'P1.02',      _t.BIDIR),   # LF
        (51, 'SWDIO',      _t.BIDIR),
        (52, 'P0.09/NFC1', _t.BIDIR),   # LF
        (53, 'SWDCLK',     _t.INPUT),
        (54, 'P0.10/NFC2', _t.BIDIR),   # LF
        (55, 'GND',        _t.PWRIN),
        (56, 'P1.04',      _t.BIDIR),   # LF
        (57, 'P1.06',      _t.BIDIR),   # LF
        (58, 'P1.07',      _t.BIDIR),   # LF
        (59, 'P1.05',      _t.BIDIR),   # LF
        (60, 'P1.03',      _t.BIDIR),   # LF
        (61, 'P1.01',      _t.BIDIR),   # LF
    ],
    LCSC='C5118826', MPN='MDBT50Q-1MV2', Mfr='Raytac', Sourcing='hand/DigiKey')

# --------------------------------------------------------------------------
# Nordic nPM1300-QEAA (QFN32 5x5, EP = pad 33 = AVSS)
# --------------------------------------------------------------------------
NPM1300 = _mk(
    'nPM1300-QEAA', 'U',
    'Package_DFN_QFN:VQFN-32-1EP_5x5mm_P0.5mm_EP3.5x3.5mm_ThermalVias',
    'PMIC: LiPo charger + 2x buck + 2x LDO/loadswitch + fuel gauge + ship mode',
    [
        (1,  'VOUT1',   _t.PWROUT),
        (2,  'PVSS1',   _t.PWRIN),
        (3,  'SW1',     _t.OUTPUT),
        (4,  'PVDD',    _t.PWRIN),
        (5,  'SW2',     _t.OUTPUT),
        (6,  'PVSS2',   _t.PWRIN),
        (7,  'GPIO0',   _t.BIDIR),
        (8,  'GPIO1',   _t.BIDIR),
        (9,  'GPIO2',   _t.BIDIR),
        (10, 'GPIO3',   _t.BIDIR),
        (11, 'GPIO4',   _t.BIDIR),
        (12, 'VDDIO',   _t.PWRIN),
        (13, 'SDA',     _t.BIDIR),
        (14, 'SCL',     _t.INPUT),
        (15, 'SHPHLD',  _t.INPUT),
        (16, 'VSET2',   _t.INPUT),
        (17, 'VSET1',   _t.INPUT),
        (18, 'NTC',     _t.INPUT),
        (19, 'VBAT',    _t.PWRIN),
        (20, 'VSYS',    _t.PWROUT),
        (21, 'VBUS',    _t.PWRIN),
        (22, 'VBUSOUT', _t.PWROUT),
        (23, 'CC1',     _t.BIDIR),
        (24, 'CC2',     _t.BIDIR),
        (25, 'LED0',    _t.OPENCOLL),
        (26, 'LED1',    _t.OPENCOLL),
        (27, 'LED2',    _t.OPENCOLL),
        (28, 'LSIN1',   _t.PWRIN),
        (29, 'LSOUT1',  _t.PWROUT),
        (30, 'LSIN2',   _t.PWRIN),
        (31, 'LSOUT2',  _t.PWROUT),
        (32, 'VOUT2',   _t.PWROUT),
        (33, 'EP_AVSS', _t.PWRIN),
    ],
    LCSC='C7501206', MPN='nPM1300-QEAA-R7', Mfr='Nordic', Sourcing='hand/DigiKey')

# --------------------------------------------------------------------------
# Bosch BMI270, LGA-14 (custom footprint from DS §8.3)
# --------------------------------------------------------------------------
BMI270 = _mk(
    'BMI270', 'U', 'Package_LGA:Bosch_LGA-14_3x2.5mm_P0.5mm',
    '6-axis IMU, low-power any-motion wake + step counter, SPI 4-wire',
    [
        (1,  'SDO',   _t.TRISTATE),
        (2,  'ASDX',  _t.INPUT),    # aux I/F unused -> strapped to VDDIO (DS Table 22)
        (3,  'ASCX',  _t.INPUT),    # aux I/F unused -> strapped to VDDIO
        (4,  'INT1',  _t.OUTPUT),
        (5,  'VDDIO', _t.PWRIN),
        (6,  'GNDIO', _t.PWRIN),
        (7,  'GND',   _t.PWRIN),
        (8,  'VDD',   _t.PWRIN),
        (9,  'INT2',  _t.NOCONNECT),
        (10, 'OCSB',  _t.NOCONNECT),  # OIS unused -> DNC
        (11, 'OSDO',  _t.NOCONNECT),  # OIS unused -> DNC
        (12, 'CSB',   _t.INPUT),
        (13, 'SCX',   _t.INPUT),
        (14, 'SDX',   _t.INPUT),      # SDI in SPI 4W
    ],
    LCSC='C2836813', MPN='BMI270', Mfr='Bosch Sensortec', Sourcing='jlc')

# --------------------------------------------------------------------------
# Connectors
# --------------------------------------------------------------------------
USB_C = _mk(
    'TYPE-C-31-M-12', 'J', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
    'USB-C receptacle 16P (charge + FS data)',
    [
        ('A1',  'GND',  _t.PWRIN), ('A12', 'GND',  _t.PWRIN),
        ('B1',  'GND',  _t.PWRIN), ('B12', 'GND',  _t.PWRIN),
        ('A4',  'VBUS', _t.PWRIN), ('A9',  'VBUS', _t.PWRIN),
        ('B4',  'VBUS', _t.PWRIN), ('B9',  'VBUS', _t.PWRIN),
        ('A5',  'CC1',  _t.BIDIR), ('B5',  'CC2',  _t.BIDIR),
        ('A6',  'DP1',  _t.BIDIR), ('B6',  'DP2',  _t.BIDIR),
        ('A7',  'DM1',  _t.BIDIR), ('B7',  'DM2',  _t.BIDIR),
        ('A8',  'SBU1', _t.NOCONNECT), ('B8', 'SBU2', _t.NOCONNECT),
        ('SH',  'SHIELD', _t.PASSIVE),
    ],
    LCSC='C165948', MPN='TYPE-C-31-M-12', Mfr='Korean Hroparts', Sourcing='jlc')

FPC10 = _mk(
    'FH12A-10S-0.5SH', 'J',
    'Connector_FFC-FPC:Hirose_FH12-10S-0.5SH_1x10-1MP_P0.50mm_Horizontal',
    'Display FPC connector — LS013B7DH03 pinout (Sharp Table 4)',
    [
        (1, 'SCLK',     _t.INPUT),
        (2, 'SI',       _t.INPUT),
        (3, 'SCS',      _t.INPUT),
        (4, 'EXTCOMIN', _t.INPUT),
        (5, 'DISP',     _t.INPUT),
        (6, 'VDDA',     _t.PWRIN),
        (7, 'VDD',      _t.PWRIN),
        (8, 'EXTMODE',  _t.INPUT),
        (9, 'VSS',      _t.PWRIN),
        (10, 'VSSA',    _t.PWRIN),
        ('MP', 'MP',    _t.PASSIVE),
    ],
    LCSC='C5139870', MPN='FH12A-10S-0.5SH(55)', Mfr='Hirose', Sourcing='hand',
    Note='display LS013B7DH03 attaches here; panel from DigiKey/Adafruit')

JST_SH2 = _mk(
    'SM02B-SRSS-TB', 'J',
    'Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal',
    'Battery connector, JST-SH 2P right angle. PIN 1 = BAT+ (verify pigtail!)',
    [
        (1, 'BAT+', _t.PASSIVE),
        (2, 'BAT-', _t.PASSIVE),
        ('MP', 'MP', _t.PASSIVE),
    ],
    LCSC='C160402', MPN='SM02B-SRSS-TB(LF)(SN)', Mfr='JST', Sourcing='jlc')

TC2030 = _mk(
    'TC2030-IDC-NL', 'J', 'Connector:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical',
    'SWD pads (Tag-Connect, no part fitted)',
    [
        (1, 'VTREF',  _t.PWRIN),
        (2, 'SWDIO',  _t.BIDIR),
        (3, 'nRESET', _t.BIDIR),
        (4, 'SWDCLK', _t.BIDIR),   # pad driven by the external probe
        (5, 'GND',    _t.PWRIN),
        (6, 'SWO',    _t.BIDIR),
    ],
    MPN='TC2030-IDC-NL', Mfr='Tag-Connect', Sourcing='none', DNP='footprint only')

# --------------------------------------------------------------------------
# Small parts
# --------------------------------------------------------------------------
USBLC6 = _mk(
    'USBLC6-2SC6', 'U', 'Package_TO_SOT_SMD:SOT-23-6',
    'USB ESD protection array (flow-through)',
    [
        (1, 'IO1',  _t.PASSIVE),
        (2, 'GND',  _t.PWRIN),
        (3, 'IO2',  _t.PASSIVE),
        (4, 'IO2B', _t.PASSIVE),
        (5, 'VBUS', _t.PWRIN),
        (6, 'IO1B', _t.PASSIVE),
    ],
    LCSC='C7519', MPN='USBLC6-2SC6', Mfr='ST', Sourcing='jlc')

XTAL32K = _mk(
    'Q13FC13500004', 'Y', 'Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm',
    '32.768 kHz crystal, CL=12.5 pF, +/-20 ppm (FC-135R family)',
    [(1, 'X1', _t.PASSIVE), (2, 'X2', _t.PASSIVE)],
    LCSC='C32346', MPN='Q13FC13500004', Mfr='Epson', Sourcing='jlc')

BUCK_L = _mk(
    'DFE201612E-2R2M', 'L', 'JRWatch:L_Murata_DFE201612E_2016',
    '2.2 uH power inductor, 116 mOhm, Isat 2.4 A (nPM1300 buck)',
    [(1, '1', _t.PASSIVE), (2, '2', _t.PASSIVE)],
    LCSC='C337893', MPN='DFE201612E-2R2M=P2', Mfr='Murata', Sourcing='jlc')

TACT_SIDE = _mk(
    'SKRTLAE010', 'SW',
    'Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010',
    'Side-actuated tact switch 4.5x3.4 mm',
    [(1, '1', _t.PASSIVE), (2, '2', _t.PASSIVE), ('MP', 'MP', _t.PASSIVE)],
    LCSC='C110293', MPN='SKRTLAE010', Mfr='Alps Alpine', Sourcing='jlc')

ESD_3V3 = _mk(
    'ESD9B3.3ST5G', 'D', 'Diode_SMD:D_SOD-923',
    'Bidirectional ESD TVS, 3.3 V working (logic-level button line)',
    [(1, 'A1', _t.PASSIVE), (2, 'A2', _t.PASSIVE)],
    LCSC='C96512', MPN='ESD9B3.3ST5G', Mfr='onsemi', Sourcing='jlc')

ESD_5V0 = _mk(
    'ESD9B5.0ST5G', 'D', 'Diode_SMD:D_SOD-923',
    'Bidirectional ESD TVS, 5.0 V working (SHPHLD swings to VBAT)',
    [(1, 'A1', _t.PASSIVE), (2, 'A2', _t.PASSIVE)],
    LCSC='C3008065', MPN='ESD9B5.0ST5G', Mfr='MSKSEMI', Sourcing='jlc',
    Note='onsemi original acceptable substitute')

NTC10K = _mk(
    'NCP15XH103F03RC', 'RT', 'Resistor_SMD:R_0402_1005Metric',
    'NTC 10k 1% B=3380 (battery temperature, nPM1300 NTC)',
    [(1, '1', _t.PASSIVE), (2, '2', _t.PASSIVE)],
    LCSC='C77131', MPN='NCP15XH103F03RC', Mfr='Murata', Sourcing='jlc')


def _passive(name, ref_prefix, fp):
    return _mk(name, ref_prefix, fp, name,
               [(1, '1', _t.PASSIVE), (2, '2', _t.PASSIVE)])

C0402 = _passive('C_0402', 'C', 'Capacitor_SMD:C_0402_1005Metric')
C0603 = _passive('C_0603', 'C', 'Capacitor_SMD:C_0603_1608Metric')
R0402 = _passive('R_0402', 'R', 'Resistor_SMD:R_0402_1005Metric')

# JLCPCB basic-catalog C-numbers for jellybean passives (re-verified at BOM cut)
PASSIVE_LCSC = {
    ('C', '100nF'): ('C1525',  'CL05B104KO5NNNC', 'Samsung'),
    ('C', '1uF'):   ('C52923', 'CL05A105KA5NQNC', 'Samsung'),
    ('C', '2.2uF'): ('C23630', 'CL10B225KO8NNNC', 'Samsung'),
    ('C', '10uF'):  ('C19702', 'CL10A106KP8NNNC', 'Samsung'),
    ('C', '12pF'):  ('C1546',  'CL05C120JB5NNNC', 'Samsung'),
    ('R', '100R'):  ('C25076', '0402WGF1000TCE', 'UNI-ROYAL'),
    ('R', '4.7k'):  ('C25900', '0402WGF4701TCE', 'UNI-ROYAL'),
    ('R', '47k'):   ('C25563', '0402WGF4702TCE', 'UNI-ROYAL'),
    ('R', '100k'):  ('C25741', '0402WGF1003TCE', 'UNI-ROYAL'),
    ('R', '150k'):  ('C25867', '0402WGF1503TCE', 'UNI-ROYAL'),
}
