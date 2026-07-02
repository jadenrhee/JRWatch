#!/usr/bin/env python3
"""
JRWatch board builder — runs under KiCad's bundled python3.

Creates hardware/jrwatch.kicad_pcb from the SKiDL netlist JSON:
  * 4-layer stack (F.Cu routing/GND, In1.Cu power pours, In2.Cu GND, B.Cu components)
  * 36 x 36 mm rounded-square outline (R9), board center at (100,100)
  * JLCPCB-4L-derived DRC minimums and net classes
  * placement: anchors at explicit coords, satellites anchored to real pad positions
  * antenna keep-out per Raytac DS (module's built-in zones + board-level extension)

Placement strategy (bottom side unless noted):
  N edge : module antenna (keep-out strip to the edge)
  S edge : USB-C (opening south), FH12 display FPC on TOP side, south-west
  E edge : SW1/SW2 side buttons
  W edge : JST-SH battery connector
  center : PMIC cluster (west), crystal + IMU below module, TC2030 east
"""
import json
import os
import sys

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.abspath(os.path.join(HERE, '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')
NETLIST = os.path.join(HW, 'netlist', 'jrwatch-netlist.json')
KISYS = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
LOCAL_LIB = os.path.join(HW, 'footprints')

CX, CY = 100.0, 100.0          # board center (sheet mm)
SIZE, RAD = 36.0, 9.0          # outline

# ------------------------------------------------------------------ helpers
def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def load_netlist():
    with open(NETLIST) as f:
        return json.load(f)


def load_footprint(fpid):
    lib, name = fpid.split(':', 1)
    path = os.path.join(LOCAL_LIB, lib + '.pretty') if lib == 'JRWatch' \
        else os.path.join(KISYS, lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError(f'footprint not found: {fpid}')
    return fp


class Builder:
    def __init__(self):
        self.nl = load_netlist()
        self.board = pcbnew.CreateEmptyBoard()
        self.board.SetCopperLayerCount(4)
        self.nets = {}
        self.fps = {}
        self.part_by_ref = {p['ref']: p for p in self.nl['parts']}
        # ref -> {pad -> netname}
        self.padnets = {}
        for n in self.nl['nets']:
            for ref, pad in n['pins']:
                self.padnets.setdefault(ref, {})[pad] = n['name']

    # -------------------------------------------------------------- setup
    def setup_rules(self):
        ds = self.board.GetDesignSettings()
        ds.m_TrackMinWidth = FromMM(0.127)
        ds.m_MinClearance = FromMM(0.127)
        ds.m_ViasMinSize = FromMM(0.45)
        ds.m_MinThroughDrill = FromMM(0.20)
        ds.m_HoleToHoleMin = FromMM(0.50)
        ds.m_CopperEdgeClearance = FromMM(0.30)
        ds.m_MinSilkTextHeight = FromMM(0.6)

        ns = ds.m_NetSettings
        dflt = ns.GetDefaultNetclass()
        dflt.SetTrackWidth(FromMM(0.15))
        dflt.SetClearance(FromMM(0.15))
        dflt.SetViaDiameter(FromMM(0.6))
        dflt.SetViaDrill(FromMM(0.3))

        power = pcbnew.NETCLASS('POWER')
        power.SetTrackWidth(FromMM(0.35))
        power.SetClearance(FromMM(0.15))
        power.SetViaDiameter(FromMM(0.6))
        power.SetViaDrill(FromMM(0.3))
        ns.SetNetclass('POWER', power)

        usb = pcbnew.NETCLASS('USB_DIFF')
        usb.SetTrackWidth(FromMM(0.2))
        usb.SetClearance(FromMM(0.15))
        usb.SetViaDiameter(FromMM(0.5))
        usb.SetViaDrill(FromMM(0.25))
        ns.SetNetclass('USB_DIFF', usb)

        for net in ('VBAT', 'VSYS', '3V0', '1V8_AUX', 'VBUS_USB', 'VBUS_OUT',
                    'VDD_DISP', 'VDD_IMU', 'GND'):
            ns.SetNetclassPatternAssignment(net, 'POWER')
        for net in ('USB_DP', 'USB_DM', 'USB_DP_CONN', 'USB_DM_CONN'):
            ns.SetNetclassPatternAssignment(net, 'USB_DIFF')

    def make_nets(self):
        for n in self.nl['nets']:
            ni = pcbnew.NETINFO_ITEM(self.board, n['name'])
            self.board.Add(ni)
            self.nets[n['name']] = ni

    def outline(self):
        b = self.board
        x0, y0 = CX - SIZE / 2, CY - SIZE / 2
        x1, y1 = CX + SIZE / 2, CY + SIZE / 2
        r = RAD
        segs = [((x0 + r, y0), (x1 - r, y0)),
                ((x1, y0 + r), (x1, y1 - r)),
                ((x1 - r, y1), (x0 + r, y1)),
                ((x0, y1 - r), (x0, y0 + r))]
        for a, c in segs:
            s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*a)); s.SetEnd(P(*c))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(FromMM(0.1))
            b.Add(s)
        # corner arcs: (start, mid, end) counterclockwise in sheet coords
        k = r * (1 - 0.70710678)
        arcs = [((x1 - r, y0), (x1 - k, y0 + k), (x1, y0 + r)),   # NE
                ((x1, y1 - r), (x1 - k, y1 - k), (x1 - r, y1)),   # SE
                ((x0 + r, y1), (x0 + k, y1 - k), (x0, y1 - r)),   # SW
                ((x0, y0 + r), (x0 + k, y0 + k), (x0 + r, y0))]   # NW
        for st, mid, en in arcs:
            a = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_ARC)
            a.SetArcGeometry(P(*st), P(*mid), P(*en))
            a.SetLayer(pcbnew.Edge_Cuts); a.SetWidth(FromMM(0.1))
            b.Add(a)

    # -------------------------------------------------------- place parts
    def add_part(self, ref, x, y, rot, side):
        part = self.part_by_ref[ref]
        fp = load_footprint(part['footprint'])
        fp.SetReference(ref)
        fp.SetValue(part['value'])
        self.board.Add(fp)
        fp.SetPosition(P(x, y))
        if side == 'B':
            fp.Flip(P(x, y), True)          # left-right flip
        fp.SetOrientationDegrees(rot)
        # net hookup by pad name
        for pad in fp.Pads():
            name = pad.GetNumber()
            netname = self.padnets.get(ref, {}).get(name)
            if netname:
                pad.SetNet(self.nets[netname])
        self.fps[ref] = fp
        return fp

    def pad_xy(self, ref, pad):
        p = self.fps[ref].FindPadByNumber(str(pad))
        pos = p.GetPosition()
        return ToMM(pos.x), ToMM(pos.y)

    # ---- resolve passive refs by (value, net) from the netlist ----------
    def find_passives(self, value, netname):
        """all C/R refs with given value having a pin on netname (sorted)."""
        out = []
        for p in self.nl['parts']:
            if p['value'] != value or p['ref'][0] not in 'CR':
                continue
            if self.padnets.get(p['ref'], {}) and \
               netname in self.padnets[p['ref']].values():
                out.append(p['ref'])
        return sorted(out)

    def place_all(self):
        # ---------------- anchors (x, y, rot, side)
        self.add_part('U1', CX, 90.55, 0, 'B')        # module, antenna north
        self.add_part('J1', CX, 113.60, 0, 'B')       # USB-C, opening south
        self.add_part('U2', 91.0, 104.2, 0, 'B')      # PMIC
        self.add_part('U3', 91.3, 97.3, 0, 'B')       # IMU
        self.add_part('Y1', 97.2, 99.6, 0, 'B')       # 32k crystal
        self.add_part('U4', 96.3, 108.0, 90, 'B')     # USB ESD
        self.add_part('J3', 84.9, 97.0, 270, 'B')     # battery conn, entry west
        self.add_part('J4', 106.0, 101.0, 90, 'B')    # TC2030 pads
        self.add_part('J2', 91.5, 112.5, 0, 'F')      # display FPC, TOP side
        self.add_part('SW1', 115.9, 95.0, 270, 'B')   # power button, east edge
        self.add_part('SW2', 115.9, 106.0, 270, 'B')  # user button, east edge
        self.add_part('L1', 96.6, 102.4, 90, 'B')     # BUCK1 L
        self.add_part('L2', 96.6, 106.0, 90, 'B')     # BUCK2 L
        self.add_part('RT1', 86.5, 100.8, 0, 'B')     # NTC at battery conn
        self.add_part('D1', 113.4, 95.0, 90, 'B')     # TVS at SW1
        self.add_part('D2', 113.4, 106.0, 90, 'B')    # TVS at SW2

        # ---------------- satellites: (value, net, x, y, rot, side)
        sats = []
        def sat(value, net, x, y, rot=0, side='B', idx=0):
            sats.append((value, net, x, y, rot, side, idx))

        # PMIC decoupling — U2 at (91.0, 104.2), pins after flip:
        #   1-8 east col (top->bot), 9-16 south row (E->W), 17-24 west col
        #   (bot->top), 25-32 north row (W->E)
        sat('10uF', 'VBAT',      87.6, 106.6, 90)      # near VBAT pin (west col)
        sat('10uF', 'VSYS',      87.6, 104.4, 90)      # near VSYS pin
        sat('2.2uF', 'VSYS',     87.6, 102.4, 90)
        sat('100nF', 'VSYS',     89.2, 101.0, 0)       # PVDD
        sat('10uF', 'VBUS_USB',  87.6, 108.8, 90)      # near VBUS pin
        sat('1uF', 'VBUS_OUT',   89.6, 108.4, 90)      # VBUSOUT
        sat('100nF', '3V0',      93.0, 101.0, 0, idx=0)     # VDDIO
        sat('10uF', '3V0',       94.6, 106.9, 90, idx=0)    # BUCK2 output bulk
        sat('10uF', '1V8_AUX',   94.6, 101.2, 90)           # BUCK1 output bulk
        sat('1uF', 'VDD_DISP',   92.8, 107.2, 90)      # LSOUT1
        sat('1uF', 'VDD_IMU',    92.8, 105.4, 90)      # LSOUT2
        # VSET straps near south row pins 16/17 (flipped: west portion of S row)
        sat('150k', 'VSET2_R', 0, 0)   # placeholder replaced below
        sats.pop()
        # (VSET nets are named by SKiDL as N$ or the resistor nets — resolve via find)

        # module decoupling — module VDD pad28 flipped -> x = CX-1.6 = 98.4, y 97.7
        sat('10uF', '3V0',       98.4, 99.2, 90, idx=1)
        sat('100nF', '3V0',      96.9, 98.6, 0, idx=1)      # VDD
        sat('100nF', '3V0',      99.9, 98.6, 0, idx=2)      # VDDH (pad30 x=98.9... adjacent)
        sat('100nF', 'VBUS_OUT', 101.9, 98.6, 0)            # module VBUS pad32
        # crystal load caps — Y1 at (97.2, 99.6) pads E/W
        sat('12pF', 'XL1',       95.6, 100.6, 0)
        sat('12pF', 'XL2',       98.8, 100.6, 0)
        # IMU — U3 at (91.3, 97.3)
        sat('100nF', 'VDD_IMU',  89.3, 96.0, 90)
        sat('100nF', '3V0',      89.3, 98.4, 90, idx=3)     # VDDIO
        # display connector caps (TOP side, near J2 pads 6/7)
        sat('1uF', 'VDD_DISP',   88.0, 109.9, 0, 'F')
        sat('100nF', 'VDD_DISP', 90.4, 109.9, 0, 'F')
        sat('1uF', 'VDD_DISP',   92.8, 109.9, 0, 'F', idx=1)
        sat('100nF', 'VDD_DISP', 95.2, 109.9, 0, 'F', idx=1)

        used = set()
        for value, net, x, y, rot, side, idx in sats:
            cands = [r for r in self.find_passives(value, net) if r not in used]
            if not cands:
                print(f'!! no candidate for {value} on {net}')
                continue
            ref = cands[min(idx, 0) if idx < len(cands) else 0] \
                if idx >= len(cands) else cands[idx]
            used.add(ref)
            self.add_part(ref, x, y, rot, side)

        # resistors resolved by net membership
        rmap = [
            # (value, net, x, y, rot, side)
            ('47k',  'N/A_VSET1', 88.6, 99.4, 0, 'B'),
            ('150k', 'N/A_VSET2', 91.2, 99.4, 0, 'B'),
            ('4.7k', 'I2C_SDA',   95.0, 96.9, 90, 'B'),
            ('4.7k', 'I2C_SCL',   93.6, 96.9, 90, 'B'),
            ('100k', 'IMU_CS',    89.3, 94.6, 90, 'B'),
            ('100k', 'DISP_CS',   97.6, 109.9, 0, 'F'),
            ('100R', 'BTN2',      112.0, 106.0, 90, 'B'),
            ('100R', 'SHPHLD',    112.0, 95.0, 90, 'B'),
        ]
        for value, net, x, y, rot, side in rmap:
            if net.startswith('N/A_VSET'):
                # VSET nets connect U2 pin 16/17 to one 47k/150k resistor
                pin = '17' if net.endswith('1') else '16'
                netname = self.padnets['U2'][pin]
                cands = [r for r in self.find_passives(value, netname)
                         if r not in used]
            else:
                cands = [r for r in self.find_passives(value, net)
                         if r not in used]
            if not cands:
                print(f'!! no candidate for R {value} on {net}')
                continue
            used.add(cands[0])
            self.add_part(cands[0], x, y, rot, side)

        placed = set(self.fps)
        missing = [p['ref'] for p in self.nl['parts'] if p['ref'] not in placed]
        if missing:
            print('!! UNPLACED:', missing)

    # ------------------------------------------------- antenna keep-out
    def antenna_keepout(self):
        """Board-level rule area: extend the module's keep-out to the board
        edge (Raytac: no copper in the antenna region on ANY layer)."""
        u1 = self.fps['U1']
        # module courtyard bbox
        bb = u1.GetBoundingBox(False)
        left, right = ToMM(bb.GetLeft()), ToMM(bb.GetRight())
        top = ToMM(bb.GetTop())
        z = pcbnew.ZONE(self.board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetLayerSet(z.GetLayerSet().AddLayer(pcbnew.F_Cu)
                      .AddLayer(pcbnew.In1_Cu).AddLayer(pcbnew.In2_Cu)
                      .AddLayer(pcbnew.B_Cu))
        pts = [(93.8, CY - SIZE / 2 - 0.1), (106.2, CY - SIZE / 2 - 0.1),
               (106.2, 86.55), (93.8, 86.55)]
        outline = z.Outline()
        outline.NewOutline()
        for x, y in pts:
            outline.Append(FromMM(x), FromMM(y))
        z.SetZoneName('ANT_KEEPOUT_BOARD')
        self.board.Add(z)

    # ------------------------------------------------------------- output
    def save(self):
        pcbnew.SaveBoard(BOARD_PATH, self.board)
        print('saved', BOARD_PATH)

    def plot_review(self):
        pc = pcbnew.PLOT_CONTROLLER(self.board)
        po = pc.GetPlotOptions()
        po.SetOutputDirectory(os.path.join(HW, 'review'))
        po.SetPlotFrameRef(False)
        for layer, name in ((pcbnew.F_Cu, 'F_Cu'), (pcbnew.B_Cu, 'B_Cu'),
                            (pcbnew.Edge_Cuts, 'Edge'),
                            (pcbnew.F_CrtYd, 'F_CrtYd'),
                            (pcbnew.B_CrtYd, 'B_CrtYd'),
                            (pcbnew.F_SilkS, 'F_Silk'),
                            (pcbnew.B_SilkS, 'B_Silk')):
            pc.SetLayer(layer)
            pc.OpenPlotfile(name, pcbnew.PLOT_FORMAT_PDF, name)
            pc.PlotLayer()
        pc.ClosePlot()
        print('review plots written')


def main():
    b = Builder()
    b.setup_rules()
    b.make_nets()
    b.outline()
    b.place_all()
    b.antenna_keepout()
    b.save()
    b.plot_review()


if __name__ == '__main__':
    main()
