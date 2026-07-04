#!/usr/bin/env python3
"""
Stage 2: hand-constrained routing of the sensitive nets, plus copper pours.
Runs under KiCad python AFTER build_board.py. Everything added here is LOCKED
so the autorouter (stage 3) treats it as fixed.

Hand-routed (and why):
  * USB D+/D- - coupled pair on B.Cu. The 16-pin USB-C pinout interleaves the
    pair, so exactly one crossover is topologically required: A6 hops over the
    D- bridge on a short F.Cu strap. FS USB (12 Mbps) - inter-pair skew budget
    is enormous; measured lengths are printed and go in the verification report.
  * nPM1300 buck switch nodes SW1/SW2 - shortest practical loops to L1/L2 and
    output caps per the PS layout guidance (minimize switch-node area).
  * 32.768 kHz crystal - short direct pair with inline load caps and local
    ground-return vias.
  * VBUS entry - wide bridge across both connector VBUS pad stacks routed
    between the NPTH posts, via into the In1 VBUS plane.
  * Module VDD/VDDH - escapes onto a 3V0 rail stub tying the decoupling row,
    with two plane vias.
  * Module GND castellations - explicit stitching vias.
Left for the autorouter: DC housekeeping (VBAT/VSYS distribution, I2C, SPI,
buttons, straps). The In1/In2 planes are in the DSN so it can via into them.

All intermediate coordinates below were derived against measured pad positions
(see git history for the collision analysis).
"""
import os

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


class Router:
    def __init__(self):
        self.b = pcbnew.LoadBoard(BOARD_PATH)
        self.nets = {}
        for code, ni in self.b.GetNetInfo().NetsByNetcode().items():
            if ni.GetNetname():
                self.nets[ni.GetNetname()] = ni
        self.fps = {f.GetReference(): f for f in self.b.GetFootprints()}

    def pad(self, ref, num):
        p = self.fps[ref].FindPadByNumber(str(num))
        pos = p.GetPosition()
        return (ToMM(pos.x), ToMM(pos.y))

    def netof(self, ref, num):
        return self.fps[ref].FindPadByNumber(str(num)).GetNetname()

    def padof(self, ref, netname):
        """pad position of `ref` whose net is `netname` (2-pin passives)."""
        for n in ('1', '2'):
            if self.netof(ref, n) == netname:
                return self.pad(ref, n)
        raise RuntimeError(f'{ref} has no pad on {netname}')

    def seg(self, netname, layer, width, pts):
        total = 0.0
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(*a)); t.SetEnd(P(*c))
            t.SetLayer(layer); t.SetWidth(FromMM(width))
            t.SetNet(self.nets[netname])
            t.SetLocked(True)
            self.b.Add(t)
            total += ((a[0] - c[0]) ** 2 + (a[1] - c[1]) ** 2) ** 0.5
        return total

    def via(self, netname, x, y, size=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(P(x, y))
        v.SetWidth(FromMM(size)); v.SetDrill(FromMM(drill))
        v.SetNet(self.nets[netname])
        v.SetLocked(True)
        self.b.Add(v)

    def zone(self, netname, layer, pts, name, priority=0):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(layer)
        z.SetNet(self.nets[netname])
        ol = z.Outline(); ol.NewOutline()
        for x, y in pts:
            ol.Append(FromMM(x), FromMM(y))
        z.SetZoneName(name)
        z.SetAssignedPriority(priority)
        z.SetLocalClearance(FromMM(0.2))
        z.SetMinThickness(FromMM(0.2))
        z.SetThermalReliefGap(FromMM(0.25))
        z.SetThermalReliefSpokeWidth(FromMM(0.35))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        self.b.Add(z)

    # ------------------------------------------------------------- routes
    def route_crystal(self):
        # XL1 -> Y1.2 (east pad) -> C(12p east stack); XL2 -> Y1.1 -> west stack
        self.seg('XL1', pcbnew.B_Cu, 0.15, [
            self.pad('U1', 17), (103.2, 98.6), (104.3, 99.7),
            (104.65, 100.05), self.padof('Y1', 'XL1'),
            (104.5, 101.85), (104.5, 102.17)])
        self.seg('XL2', pcbnew.B_Cu, 0.15, [
            self.pad('U1', 18), (102.4, 99.0), (102.15, 99.25),
            self.padof('Y1', 'XL2'), (102.1, 101.5), (102.1, 102.17)])
        self.via('GND', 102.1, 103.9)
        self.via('GND', 104.5, 103.9)
        self.seg('GND', pcbnew.B_Cu, 0.2, [(102.1, 103.13), (102.1, 103.9)])
        self.seg('GND', pcbnew.B_Cu, 0.2, [(104.5, 103.13), (104.5, 103.9)])

    def route_usb(self):
        # measured row (LR flip): B6=99.25 A7=99.75 A6=100.25 B7=100.75;
        # CC2 at 98.25, CC1 at 101.25 escape north freely outside the bridges
        a6 = self.pad('J1', 'A6'); a7 = self.pad('J1', 'A7')
        b6 = self.pad('J1', 'B6'); b7 = self.pad('J1', 'B7')
        p1 = self.pad('U4', 1); p3 = self.pad('U4', 3)         # south row: E=1, W=3
        p4 = self.pad('U4', 4); p6 = self.pad('U4', 6)         # north row: W=4, E=6
        w = 0.2

        # --- D+ (IO2): B6+A6 bridge at y=108.5 (0.23 clear of the pad row)
        self.seg('USB_DP_CONN', pcbnew.B_Cu, w, [b6, (99.25, 108.5)])
        self.seg('USB_DP_CONN', pcbnew.B_Cu, w, [a6, (100.25, 108.5),
                                                 (99.25, 108.5)])
        dpc = self.seg('USB_DP_CONN', pcbnew.B_Cu, w, [
            (99.25, 108.5), (94.95, 108.5), (94.9, 108.55),
            (94.9, 111.75), (90.55, 111.75), (90.3, 111.5), (90.3, 110.74),
            (p3[0], p3[1]), p3])
        # --- D- (IO1): B7 escapes east of the D+ bridge, runs at y=108.05.
        # A7 (between the D+ pads) is the topologically-required crossover:
        # no via fits inside the 0.5mm pad row, so it stubs SOUTH into the
        # window below the row, then rides F.Cu back over everything to an
        # inline via on the D- run.
        self.seg('USB_DM_CONN', pcbnew.B_Cu, w, [b7, (100.75, 108.05)])
        dmc = self.seg('USB_DM_CONN', pcbnew.B_Cu, w, [
            (100.75, 108.05), (94.5, 108.05),
            (94.5, 110.29), (94.05, 110.74), (p1[0] + 0.5, p1[1]), p1])
        self.seg('USB_DM_CONN', pcbnew.B_Cu, w, [a7, (99.85, 110.85)])
        self.via('USB_DM_CONN', 99.85, 110.85, size=0.5, drill=0.25)
        self.seg('USB_DM_CONN', pcbnew.F_Cu, w, [
            (99.85, 110.85), (99.85, 107.95), (99.45, 107.55)])
        self.via('USB_DM_CONN', 99.45, 107.55, size=0.5, drill=0.25)
        self.seg('USB_DM_CONN', pcbnew.B_Cu, w, [
            (99.45, 107.55), (99.45, 108.05)])

        # --- module side: the B-side corridor is owned by the buck pocket, so
        # the long run rides the (empty) top layer: via pairs at both ends.
        m34 = self.pad('U1', 34); m35 = self.pad('U1', 35)
        dm = self.seg('USB_DM', pcbnew.B_Cu, w, [p6, (93.15, 107.5)])
        self.via('USB_DM', 93.15, 107.5, size=0.5, drill=0.25)
        dm += self.seg('USB_DM', pcbnew.F_Cu, w, [
            (93.15, 107.5), (94.5, 106.15), (94.5, 97.3), (94.45, 97.0)])
        self.via('USB_DM', 94.45, 97.0, size=0.5, drill=0.25)
        dm += self.seg('USB_DM', pcbnew.B_Cu, w, [
            (94.45, 97.0), (94.9, 96.75), m34])
        # D+ F.Cu path skirts EAST of the U2 exposed-pad thermal via field
        dp = self.seg('USB_DP', pcbnew.B_Cu, w, [p4, (91.25, 107.5)])
        self.via('USB_DP', 91.25, 107.5, size=0.5, drill=0.25)
        dp += self.seg('USB_DP', pcbnew.F_Cu, w, [
            (91.25, 107.5), (91.9, 106.85), (93.2, 106.85), (93.55, 106.5),
            (93.55, 96.3), (94.05, 95.8), (94.45, 95.6)])
        self.via('USB_DP', 94.45, 95.6, size=0.5, drill=0.25)
        dp += self.seg('USB_DP', pcbnew.B_Cu, w, [
            (94.45, 95.6), (94.75, 95.9), m35])
        print(f"USB lengths (mm): conn-side D+={dpc:.2f} D-={dmc:.2f} | "
              f"module-side D+={dp:.2f} D-={dm:.2f} | "
              f"total D+={dpc+dp:.2f} D-={dmc+dm:.2f} "
              f"delta={abs(dpc+dp-dmc-dm):.2f}")

    def route_vbus_entry(self):
        # Each physical VBUS pad on this footprint is already the merged
        # A/B pair (A4/B9 on one pad, A9/B4 on the other), so ONE pad powers
        # the board in both plug orientations. The west pad is boxed in by the
        # NPTH post + CC2 + shield pad; the east pad connects cleanly. West pad
        # left on the plane-connected net via the In1 pour if reachable -
        # otherwise it is redundant current capacity only (documented, D-019).
        pa = self.pad('J1', 'A4')   # east stack (102.45, 109.56)
        self.seg('VBUS_USB', pcbnew.B_Cu, 0.3, [
            pa, (102.45, 110.2), (101.9, 110.75), (101.6, 110.75)])
        self.via('VBUS_USB', 101.6, 110.75)

    def route_bucks(self):
        # pads (measured): SW1 (93.45,103.45) SW2 (93.45,104.45);
        # L1: pad1 S (98,103.25) = SW net, pad2 N (98,101.55) = 1V8;
        # L2: pad1 S (98,106.85) = SW net, pad2 N (98,105.15) = 3V0.
        # 0.4 mm: fits the 0.25 mm gap rows between adjacent QFN pads with
        # >=0.175 mm clearance while still generous for 200 mA
        sw1 = self.pad('U2', 3); sw2 = self.pad('U2', 5)
        self.seg(self.netof('U2', 3), pcbnew.B_Cu, 0.4, [
            sw1, (94.3, 103.45), (96.9, 103.45), (97.45, 103.3),
            self.pad('L1', 1)])
        self.seg(self.netof('U2', 5), pcbnew.B_Cu, 0.4, [
            sw2, (94.3, 104.45), (95.6, 104.45), (96.6, 105.45),
            (96.6, 106.5), (96.95, 106.85), self.pad('L2', 1)])

        # BUCK1 output loop: L1 north -> C7(10u 1V8) -> VOUT1 sense (U2.1)
        c7_1v8 = self.padof('C7', '1V8_AUX')
        self.seg('1V8_AUX', pcbnew.B_Cu, 0.35, [
            self.pad('L1', 2), (96.4, 101.55), (c7_1v8[0] + 0.3, c7_1v8[1]), c7_1v8])
        self.seg('1V8_AUX', pcbnew.B_Cu, 0.35, [
            c7_1v8, (c7_1v8[0], 102.3), (94.35, 102.45), self.pad('U2', 1)])

        # BUCK2 output loop: L2 north -> C12(10u 3V0) -> via into 3V0 finger
        c12_3v0 = self.padof('C12', '3V0')
        c12_gnd = self.padof('C12', 'GND')
        self.seg('3V0', pcbnew.B_Cu, 0.45, [
            self.pad('L2', 2), (99.3, 105.15), (100.2, c12_3v0[1]), c12_3v0])
        self.seg('3V0', pcbnew.B_Cu, 0.45, [c12_3v0, (101.5, c12_3v0[1])])
        self.via('3V0', 101.5, c12_3v0[1])
        self.seg('GND', pcbnew.B_Cu, 0.45, [c12_gnd, (101.5, c12_gnd[1])])
        self.via('GND', 101.5, c12_gnd[1])

        # VOUT2 sense + LSIN feeds -> 3V0 plane. QFN top row numbers RIGHT
        # to LEFT (CCW): measured 28=(90.75,101.75) 30=(91.75) 32=(92.75).
        p32 = self.pad('U2', 32)
        self.seg('3V0', pcbnew.B_Cu, 0.35, [p32, (92.75, 101.1), (93.0, 100.85)])
        self.via('3V0', 93.0, 100.85)
        p30 = self.pad('U2', 30)
        self.seg('3V0', pcbnew.B_Cu, 0.35, [p30, (91.75, 101.15), (91.9, 100.9)])
        self.via('3V0', 91.9, 100.9)
        p28 = self.pad('U2', 28)
        self.seg('3V0', pcbnew.B_Cu, 0.35, [p28, (90.75, 101.15), (90.5, 100.9)])
        self.via('3V0', 90.5, 100.9)

    def route_module_power(self):
        m28 = self.pad('U1', 28); m30 = self.pad('U1', 30)   # (98.4/100.0, 97.7)
        self.seg('3V0', pcbnew.B_Cu, 0.45, [m28, (m28[0], 98.45)])
        self.seg('3V0', pcbnew.B_Cu, 0.45, [m30, (m30[0], 98.45)])
        self.seg('3V0', pcbnew.B_Cu, 0.45, [(96.9, 98.45), (100.0, 98.45)])
        self.via('3V0', 99.0, 98.45)         # two plane vias
        self.via('3V0', 100.0, 98.45)
        # cap 3V0 pads are the FAR (south) pads - stubs detour around the
        # GND pads in the free lanes between the cap columns
        self.seg('3V0', pcbnew.B_Cu, 0.35, [        # C14 via west lane
            (96.9, 98.45), (96.9, 100.38), (97.32, 100.38)])
        self.seg('3V0', pcbnew.B_Cu, 0.35, [        # C13 via center lane
            (98.3, 98.45), (98.3, 100.38), (98.72, 100.38)])
        self.seg('3V0', pcbnew.B_Cu, 0.25, [        # C8 via west lane
            (99.7, 98.45), (99.7, 101.225), (100.07, 101.225)])

    def route_gnd_stitching(self):
        # explicit via spots: staggered for hole-to-hole and clear of the
        # neighboring castellation pads (pin2's via angles further out so its
        # stub clears the pin3 pad)
        spots = {1: (105.55, 87.2), 2: (105.85, 87.95), 55: (94.45, 87.2),
                 15: (105.7, 97.7), 33: (95.15, 98.7)}
        for gp, (vx, vy) in spots.items():
            x, y = self.pad('U1', gp)
            self.seg('GND', pcbnew.B_Cu, 0.4, [(x, y), (vx, vy)])
            self.via('GND', vx, vy)

    # ------------------------------------------------------------- pours
    def pours(self):
        self.zone('GND', pcbnew.In2_Cu,
                  [(81, 81), (119, 81), (119, 119), (81, 119)], 'GND_PLANE_IN2')
        # 3V0: center block + east finger reaching the BUCK2 output via
        self.zone('3V0', pcbnew.In1_Cu,
                  [(88.0, 94.5), (106.5, 94.5), (106.5, 107.8), (99.5, 107.8),
                   (99.5, 103.0), (88.0, 103.0)], 'PWR_3V0_IN1', priority=1)
        self.zone('VSYS', pcbnew.In1_Cu,
                  [(88.6, 103.4), (94.9, 103.4), (94.9, 108.6), (88.6, 108.6)],
                  'PWR_VSYS_IN1', priority=1)
        self.zone('VBUS_USB', pcbnew.In1_Cu,
                  [(88.0, 109.0), (103.5, 109.0), (103.5, 113.2), (88.0, 113.2)],
                  'PWR_VBUS_IN1', priority=1)
        self.zone('VBAT', pcbnew.In1_Cu,
                  [(83.4, 94.0), (87.2, 94.0), (87.2, 111.5), (83.4, 111.5)],
                  'PWR_VBAT_IN1', priority=1)
        self.zone('GND', pcbnew.B_Cu,
                  [(81, 81), (119, 81), (119, 119), (81, 119)], 'GND_FILL_B')
        self.zone('GND', pcbnew.F_Cu,
                  [(81, 81), (119, 81), (119, 119), (81, 119)], 'GND_FILL_F')

    def run(self):
        self.route_crystal()
        self.route_usb()
        self.route_vbus_entry()
        self.route_bucks()
        self.route_module_power()
        self.route_gnd_stitching()
        self.pours()
        pcbnew.SaveBoard(BOARD_PATH, self.b)
        print('critical routes + pours saved')


if __name__ == '__main__':
    Router().run()
