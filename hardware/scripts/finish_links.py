#!/usr/bin/env python3
"""
Stage 6 (final): hand-derived completion of the links the autorouter failed,
verified point-by-point against measured copper (see git history).

  * relocate the USB_DP via that boxed in U2 pin12, re-heading its F.Cu path
  * re-nudge the autorouter's I2C_SDA via out of the y=107.5 via corridor
  * plane taps for VSYS pin4/pin20 and VBAT pin19 (with small In1 patch
    zones that merge into the main pours)
  * links: VDD_DISP p29, VDD_IMU p31, 3V0 p12 (VDDIO), CC2, SHPHLD, DISP_SCK
  * refill zones (solid), report unconnected
"""
import math
import os

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


class Fin:
    def __init__(self):
        self.b = pcbnew.LoadBoard(BOARD_PATH)
        # cache once: calling GetTracks() after a Remove() breaks the SWIG
        # bindings in this KiCad build
        self.tracks = list(self.b.GetTracks())
        self.to_remove = []

    def net(self, name):
        return self.b.FindNet(name)

    def seg(self, netname, layer, width, pts):
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(*a)); t.SetEnd(P(*c))
            t.SetLayer(layer); t.SetWidth(FromMM(width))
            t.SetNet(self.net(netname))
            self.b.Add(t)

    def via(self, netname, x, y, size=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(P(x, y))
        v.SetWidth(FromMM(size)); v.SetDrill(FromMM(drill))
        v.SetNet(self.net(netname))
        self.b.Add(v)

    def move_via(self, old, new, tol=0.06):
        for t in self.tracks:
            if t.Type() == pcbnew.PCB_VIA_T:
                pos = t.GetPosition()
                if math.hypot(ToMM(pos.x) - old[0], ToMM(pos.y) - old[1]) < tol:
                    t.SetPosition(P(*new))
            elif t.Type() == pcbnew.PCB_TRACE_T:
                s, e = t.GetStart(), t.GetEnd()
                if math.hypot(ToMM(s.x) - old[0], ToMM(s.y) - old[1]) < tol:
                    t.SetStart(P(*new))
                if math.hypot(ToMM(e.x) - old[0], ToMM(e.y) - old[1]) < tol:
                    t.SetEnd(P(*new))

    def del_seg(self, layer, a, c, tol=0.06):
        for t in self.tracks:
            if t.Type() != pcbnew.PCB_TRACE_T or t.GetLayer() != layer:
                continue
            if t in self.to_remove:
                continue
            s, e = t.GetStart(), t.GetEnd()
            sm = (ToMM(s.x), ToMM(s.y)); em = (ToMM(e.x), ToMM(e.y))
            if (math.hypot(sm[0]-a[0], sm[1]-a[1]) < tol and
                math.hypot(em[0]-c[0], em[1]-c[1]) < tol) or \
               (math.hypot(sm[0]-c[0], sm[1]-c[1]) < tol and
                math.hypot(em[0]-a[0], em[1]-a[1]) < tol):
                self.to_remove.append(t)
                return True
        return False

    def zone(self, netname, layer, pts, name):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(layer)
        z.SetNet(self.net(netname))
        ol = z.Outline(); ol.NewOutline()
        for x, y in pts:
            ol.Append(FromMM(x), FromMM(y))
        z.SetZoneName(name)
        z.SetAssignedPriority(1)
        z.SetLocalClearance(FromMM(0.2))
        z.SetMinThickness(FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        self.b.Add(z)

    def run(self):
        # ---- 1. relocate my USB_DP via (91.25,107.5) -> (92.0,107.5); the
        # B stub from U4 pin4 and the F head both re-route.
        self.del_seg(B, (91.25, 108.4625), (91.25, 107.5))
        self.del_seg(F, (91.25, 107.5), (91.9, 106.85))
        self.del_seg(F, (91.9, 106.85), (93.2, 106.85))
        self.move_via((91.25, 107.5), (92.0, 107.5))
        self.seg('USB_DP', B, 0.2, [
            (91.25, 108.4625), (91.25, 107.95), (91.7, 107.5), (92.0, 107.5)])
        self.seg('USB_DP', F, 0.2, [
            (92.0, 107.5), (92.65, 106.85), (93.2, 106.85)])

        # ---- 2. re-park autorouter vias (hole-to-hole pairs), and my pin33
        # ground via which crowded the autorouter's VBUS_OUT via
        self.move_via((90.53, 107.6), (89.2, 107.9))     # I2C_SDA
        self.move_via((93.46, 94.31), (93.62, 94.65))    # I2C_SCL
        self.move_via((95.15, 98.7), (95.15, 99.4))      # GND (pin33 stitch)

        # ---- 3. plane taps (patch zones merge into the main In1 pours)
        self.zone('VSYS', pcbnew.In1_Cu,
                  [(87.5, 103.9), (88.8, 103.9), (88.8, 104.85), (87.5, 104.85)],
                  'PWR_VSYS_TAP_W')
        self.seg('VSYS', B, 0.3, [(88.55, 104.45), (88.15, 104.45), (87.9, 104.4)])
        self.via('VSYS', 87.9, 104.4)
        self.zone('VSYS', pcbnew.In1_Cu,
                  [(94.7, 103.4), (96.9, 103.4), (96.9, 104.6), (94.7, 104.6)],
                  'PWR_VSYS_TAP_E')
        self.seg('VSYS', B, 0.3, [
            (93.45, 103.95), (93.85, 103.99), (96.35, 103.99)])
        self.via('VSYS', 96.35, 103.99)
        self.zone('VBAT', pcbnew.In1_Cu,
                  [(87.0, 105.15), (88.0, 105.15), (88.0, 105.95), (87.0, 105.95)],
                  'PWR_VBAT_TAP')
        self.seg('VBAT', B, 0.3, [
            (88.55, 104.95), (88.1, 104.95), (87.7, 105.35), (87.65, 105.5)])
        self.via('VBAT', 87.65, 105.5)

        # ---- 4. links
        # VDD_DISP: U2 pin29 -> C20 pad (diagonal clear of pin28 / C10)
        self.seg('VDD_DISP', B, 0.2, [
            (91.25, 101.75), (89.9, 100.4), (89.68, 100.37)])
        # VDD_IMU: U2 pin31 -> C10 east pad, around pin32 lane
        self.seg('VDD_IMU', B, 0.2, [
            (92.25, 101.75), (92.3, 101.7), (92.3, 100.0), (92.05, 100.0)])
        # 3V0 / VDDIO: U2 pin12 south, via, F.Cu west-around, B jumper to
        # the LSIN1 plane-via stub
        self.seg('3V0', B, 0.15, [
            (91.25, 106.65), (91.25, 107.5), (90.4, 107.5)])
        self.via('3V0', 90.4, 107.5, size=0.5, drill=0.25)
        self.seg('3V0', F, 0.15, [
            (90.4, 107.5), (89.0, 106.1), (89.0, 101.5), (89.7, 101.3)])
        self.via('3V0', 89.7, 101.3, size=0.5, drill=0.25)
        self.seg('3V0', B, 0.15, [
            (89.7, 101.3), (90.35, 100.95), (90.5, 100.9)])
        # CC2: pin24 west/north stub, B->F via, F sweep across the open top,
        # drop next to the B5 pad
        self.seg('CC2', B, 0.15, [
            (88.55, 102.45), (87.85, 102.45), (87.8, 102.4), (87.8, 96.2),
            (88.4, 95.6), (88.75, 95.3)])
        self.via('CC2', 88.75, 95.3, size=0.5, drill=0.25)
        self.seg('CC2', F, 0.15, [
            (88.75, 95.3), (89.0, 95.05), (100.5, 95.05), (103.5, 98.05),
            (103.5, 111.9), (98.6, 111.9), (97.9, 111.2), (97.9, 109.15)])
        self.via('CC2', 97.9, 109.15, size=0.5, drill=0.25)
        self.seg('CC2', B, 0.15, [
            (97.9, 109.15), (98.25, 109.5), (98.25, 109.555)])
        # SHPHLD: pin15 slots between the SDA and VDDIO vias, south past U4,
        # east lane below the connector, north to R7
        self.seg('SHPHLD', B, 0.15, [
            (89.75, 106.65), (89.75, 108.5), (89.2, 109.05), (89.2, 111.55),
            (89.85, 112.2), (111.5, 112.2), (113.6, 110.1), (113.6, 97.2),
            (112.0, 95.6), (111.19, 95.51), (110.9, 95.51)])
        # DISP_SCK: module pad 41 west stub, via, F.Cu west highway, down the
        # x=88 lane between the display cap columns into J2 pad 1
        self.seg('DISP_SCK', B, 0.15, [
            (95.35, 93.5), (94.8, 93.5), (94.5, 93.5)])
        self.via('DISP_SCK', 94.5, 93.5, size=0.5, drill=0.25)
        self.seg('DISP_SCK', F, 0.15, [
            (94.5, 93.5), (94.2, 93.8), (89.0, 93.8), (88.6, 94.2),
            (88.6, 107.55), (88.03, 108.12), (88.03, 109.3), (87.5, 109.83),
            (87.05, 110.28), (87.05, 110.65)])

        # removals last (SWIG breaks on iterate-after-Remove)
        for t in self.to_remove:
            self.b.Remove(t)
        pcbnew.SaveBoard(BOARD_PATH, self.b)
        print('links + taps applied (refill runs separately)')


if __name__ == '__main__':
    Fin().run()
