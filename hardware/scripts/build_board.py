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
SIZE, RAD = 36.0, 6.0          # outline (R6 corners clear the SW connector zone)

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
        # Rotation FIRST, then flip. Flip() encodes left-right as mirror+180deg
        # internally, so a later SetOrientationDegrees() would silently turn it
        # into a top-bottom flip (bug found the hard way — pads landed y-mirrored).
        fp.SetOrientationDegrees(rot)
        if side == 'B':
            fp.Flip(P(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        # net hookup by pad name
        for pad in fp.Pads():
            name = pad.GetNumber()
            netname = self.padnets.get(ref, {}).get(name)
            if netname:
                pad.SetNet(self.nets[netname])
        # dense wearable: no refdes silk (assembly uses fab layer + CPL);
        # functional silk (battery polarity, board id) added separately
        fp.Reference().SetVisible(False)
        self.fps[ref] = fp
        return fp

    def add_silk_text(self, text, x, y, layer, size=0.8):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(text)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(FromMM(size), FromMM(size)))
        t.SetTextThickness(FromMM(0.15))
        if layer in (pcbnew.B_SilkS, pcbnew.B_Cu, pcbnew.B_Fab):
            t.SetMirrored(True)
        self.board.Add(t)

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
        # NOTE on flips: Flip(pos, True) negates local X. Module pads with
        # local x<0 (pins 1-14) land EAST of center; pins 34-55 land WEST.
        # ---------------- anchors (x, y, rot, side)
        self.add_part('U1', CX, 90.55, 0, 'B')        # module, antenna north
        self.add_part('J1', CX, 113.60, 0, 'B')       # USB-C, opening south
        self.add_part('U2', 91.0, 104.2, 0, 'B')      # PMIC
        self.add_part('U3', 91.0, 92.0, 0, 'B')       # IMU — at module W col SPI pads
        self.add_part('Y1', 103.4, 100.3, 0, 'B')     # 32k crystal — XL pads land E
        self.add_part('U4', 92.2, 109.6, 90, 'B')     # USB ESD, in pair corridor
        self.add_part('J3', 85.4, 97.0, 90, 'B')      # battery conn, entry west
        self.add_part('J4', 86.9, 89.0, 90, 'B')      # TC2030 — SWD pads land W
        self.add_part('J2', 89.3, 112.5, 0, 'F')      # display FPC, TOP side (W of USB SH pads)
        self.add_part('SW1', 115.9, 95.0, 90, 'B')    # power button, east edge
        self.add_part('SW2', 115.9, 106.0, 90, 'B')   # user button, east edge
        self.add_part('L1', 98.0, 102.4, 90, 'B')     # BUCK1 L (east col of U2)
        self.add_part('L2', 98.0, 106.0, 90, 'B')     # BUCK2 L
        self.add_part('RT1', 84.3, 93.2, 0, 'B')      # NTC north of battery conn
        self.add_part('D1', 112.6, 95.0, 90, 'B')     # TVS at SW1
        self.add_part('D2', 112.6, 106.0, 90, 'B')    # TVS at SW2

        # ---------------- satellites: (value, net, x, y, rot, side)
        sats = []
        def sat(value, net, x, y, rot=0, side='B', idx=0):
            sats.append((value, net, x, y, rot, side, idx))

        # PMIC decoupling — U2 flipped: pins 1-8 east col (top->bot),
        # 9-16 south row (E->W), 17-24 west col (bot->top), 25-32 north (W->E)
        # Courtyard envelopes (KiCad lib): 0402 = 1.92 x 1.12 mm, 0603 =
        # 2.96 x 1.52 mm, custom L = 3.16 x 2.2. Pitches below respect them.
        # west column x=86.3, 0603 rot-90, pitch 3.05
        sat('10uF', 'VBUS_USB',  86.3, 101.0, 90)      # VBUS pin (closest)
        sat('2.2uF', 'VSYS',     86.3, 104.05, 90)
        sat('10uF', 'VSYS',      86.3, 107.1, 90)      # VSYS pin
        sat('10uF', 'VBAT',      86.3, 110.15, 90)     # VBAT (battery is west anyway)
        sat('1uF', 'VBUS_OUT',   84.7, 103.8, 90)      # VBUSOUT (west of col)
        sat('100nF', 'VSYS',     84.7, 107.0, 90)       # PVDD 100n on west bank
                                                        # (pocket kept clear for SW routes)
        # north row y=100.0, 0402 rot-0, pitch 2.05 (sits N of U2 courtyard)
        sat('1uF', 'VDD_DISP',   89.2, 100.0, 0)       # LSOUT1
        sat('1uF', 'VDD_IMU',    91.25, 100.0, 0)      # LSOUT2
        sat('100nF', '3V0',      93.3, 100.0, 0, idx=0)     # VDDIO (I2C ref)
        # buck bulk caps at inductor outputs
        sat('10uF', '3V0',       100.6, 106.2, 90, idx=0)   # BUCK2 output bulk
        sat('10uF', '1V8_AUX',   95.4, 100.9, 90)           # BUCK1 output bulk

        # module decoupling — VDD pad28 (98.4, 97.7), VDDH pad30 (100.0, 97.7),
        # VBUS pad32 (101.6, 97.7); module courtyard ends ~y=98.6
        sat('100nF', '3V0',      97.6, 99.9, 90, idx=1)     # VDD
        sat('100nF', '3V0',      99.0, 99.9, 90, idx=2)     # VDDH
        sat('10uF', '3V0',       100.55, 100.45, 90, idx=1)   # module bulk
        sat('100nF', 'VBUS_OUT', 93.2, 98.6, 0)             # module VBUS pin32 (96.0,97.7)
        # crystal load caps — row south of Y1 (XL pads at 103.2/102.4, 97.7);
        # XL2 stack west, XL1 stack east (matches crystal pin swap, no crossover)
        sat('12pF', 'XL2',       102.1, 102.65, 270)
        sat('12pF', 'XL1',       104.5, 102.65, 270)
        # IMU — U3 at (91.0, 92.0): caps south of U3, clear of J3/J4
        sat('100nF', 'VDD_IMU',  89.8, 94.35, 0)
        sat('100nF', '3V0',      91.9, 94.35, 0, idx=3)     # VDDIO
        # display connector caps (TOP side, row north of J2, pitch 2.05)
        sat('1uF', 'VDD_DISP',   87.0, 108.5, 0, 'F')
        sat('100nF', 'VDD_DISP', 89.05, 108.5, 0, 'F')
        sat('1uF', 'VDD_DISP',   91.1, 108.5, 0, 'F', idx=1)
        sat('100nF', 'VDD_DISP', 93.15, 108.5, 0, 'F', idx=1)

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
            # VSET straps are sampled once at power-on; placed in the open east
            # zone to decongest the west power bank (noted in review checklist)
            ('47k',  'N/A_VSET1', 110.0, 101.5, 0, 'B'),
            ('150k', 'N/A_VSET2', 110.0, 103.2, 0, 'B'),
            ('4.7k', 'I2C_SDA',   93.6, 96.9, 90, 'B'),   # near module I2C pads
            ('4.7k', 'I2C_SCL',   92.2, 96.9, 90, 'B'),
            ('100k', 'IMU_CS',    92.2, 89.4, 0, 'B'),    # CSB pad12 N of U3
            ('100k', 'DISP_CS',   84.95, 108.5, 0, 'F'),  # west of J2 cap row
            ('100R', 'BTN2',      110.9, 106.0, 90, 'B'),
            ('100R', 'SHPHLD',    110.9, 95.0, 90, 'B'),
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

        # functional silkscreen: battery polarity beside the actual J3 pads
        # (safety: pigtail polarity varies by vendor — see review checklist)
        for pad, sym in (('1', '+'), ('2', '-')):
            px, py = self.pad_xy('J3', pad)
            self.add_silk_text(sym, px + 1.6, py, pcbnew.B_SilkS, 0.9)
        self.add_silk_text('JRWatch r1', 100.0, 87.6, pcbnew.F_SilkS, 1.0)

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
        z.SetDoNotAllowZoneFills(True)
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
