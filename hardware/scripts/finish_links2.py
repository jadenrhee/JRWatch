#!/usr/bin/env python3
"""
Stage 6 v2 — completion of autorouter-failed links.

Key geometry: the QFN pad columns admit 0.48/0.2 vias between neighboring
pads at the 0.13 mm clearance rule, and the pin-28/30/32 columns sit inside
the In1 3V0 pour. So LSIN1/LSIN2/VOUT2 each take a straight stub + on-column
via (replacing the offset vias that sealed the pin29/31 escape lanes), and
pin29 (VDD_DISP) / pin31 (VDD_IMU) thread the freed lanes to their caps.

phases (run in order, separate processes for SWIG safety):
  surgery : delete old LSIN/VOUT2 vias+stubs, USB_DP via relocation,
            SDA/SCL/pin33 via moves, on-column vias, explicit links
  astar   : raster-checked A* for CC2, SHPHLD, DISP_SCK, VBAT + VSYS taps
  trim    : ring-straddling stitch vias + dangling stub
  fill    : solid refill
"""
import math
import os
import sys

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


class Surgeon:
    def __init__(self):
        self.b = pcbnew.LoadBoard(BOARD_PATH)
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

    def mark_del_via(self, x, y, tol=0.06):
        for t in self.tracks:
            if t.Type() != pcbnew.PCB_VIA_T or t in self.to_remove:
                continue
            pos = t.GetPosition()
            if math.hypot(ToMM(pos.x) - x, ToMM(pos.y) - y) < tol:
                self.to_remove.append(t)
                return True
        return False

    def mark_del_seg(self, layer, a, c, tol=0.08):
        for t in self.tracks:
            if t.Type() != pcbnew.PCB_TRACE_T or t.GetLayer() != layer or \
               t in self.to_remove:
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

    def run(self):
        # -- 1. delete offset LSIN/VOUT2 vias + stubs (they sealed the pocket)
        ok = 0
        ok += self.mark_del_via(90.5, 100.9)
        ok += self.mark_del_via(91.9, 100.9)
        ok += self.mark_del_via(93.0, 100.85)
        ok += self.mark_del_seg(B, (90.75, 101.75), (90.75, 101.15))
        ok += self.mark_del_seg(B, (90.75, 101.15), (90.5, 100.9))
        ok += self.mark_del_seg(B, (91.75, 101.75), (91.75, 101.15))
        ok += self.mark_del_seg(B, (91.75, 101.15), (91.9, 100.9))
        ok += self.mark_del_seg(B, (92.75, 101.75), (92.75, 101.1))
        ok += self.mark_del_seg(B, (92.75, 101.1), (93.0, 100.85))
        print('pocket surgery marks:', ok, '(expect 9)')

        # -- 2. on-column stubs + 0.48/0.2 vias straight into the 3V0 pour
        for px in (90.75, 91.75, 92.75):
            self.seg('3V0', B, 0.25, [(px, 101.75), (px, 100.97)])
            self.via('3V0', px, 100.97, size=0.48, drill=0.2)

        # -- 3. freed-lane links
        self.seg('VDD_DISP', B, 0.15, [
            (91.25, 101.75), (91.25, 100.75), (91.02, 100.52),
            (89.9, 100.52), (89.68, 100.37)])
        self.seg('VDD_IMU', B, 0.15, [
            (92.25, 101.75), (92.25, 100.0), (92.09, 100.0)])

        # -- 4. USB_DP via relocation frees pin12's slot (as derived)
        self.mark_del_seg(B, (91.25, 108.4625), (91.25, 107.5))
        self.mark_del_seg(F, (91.25, 107.5), (91.9, 106.85))
        self.mark_del_seg(F, (91.9, 106.85), (93.2, 106.85))
        self.move_via((91.25, 107.5), (92.0, 107.5))
        self.seg('USB_DP', B, 0.2, [
            (91.25, 108.4625), (91.25, 107.95), (91.7, 107.5), (92.0, 107.5)])
        self.seg('USB_DP', F, 0.2, [(92.0, 107.5), (92.65, 106.85), (93.2, 106.85)])

        # -- 5. via re-parks (hole-to-hole + corridor)
        self.move_via((90.53, 107.6), (89.2, 107.9))     # I2C_SDA
        self.move_via((93.46, 94.31), (93.62, 94.65))    # I2C_SCL
        self.move_via((95.15, 98.7), (95.15, 99.4))      # pin33 GND stitch

        # -- 6. VDDIO pin12 -> F.Cu west detour -> via inside the 3V0 pour
        self.seg('3V0', B, 0.15, [(91.25, 106.65), (91.25, 107.5), (90.4, 107.5)])
        self.via('3V0', 90.4, 107.5, size=0.5, drill=0.25)
        self.seg('3V0', F, 0.15, [
            (90.4, 107.5), (89.0, 106.1), (89.0, 101.5), (89.7, 101.3)])
        self.via('3V0', 89.7, 101.3, size=0.5, drill=0.25)

        # -- 7. VSYS plane taps (patch zones merge into the pour)
        self.zone('VSYS', pcbnew.In1_Cu,
                  [(87.5, 103.9), (88.8, 103.9), (88.8, 104.85), (87.5, 104.85)],
                  'PWR_VSYS_TAP_W')
        self.seg('VSYS', B, 0.25, [(88.55, 104.45), (88.15, 104.45), (87.9, 104.4)])
        self.via('VSYS', 87.9, 104.4)
        self.zone('VSYS', pcbnew.In1_Cu,
                  [(94.7, 103.4), (96.9, 103.4), (96.9, 104.6), (94.7, 104.6)],
                  'PWR_VSYS_TAP_E')
        self.seg('VSYS', B, 0.25, [(93.45, 103.95), (93.85, 103.99), (96.35, 103.99)])
        self.via('VSYS', 96.35, 103.99)
        # VBAT pin19 tap
        self.zone('VBAT', pcbnew.In1_Cu,
                  [(87.0, 105.15), (88.0, 105.15), (88.0, 105.95), (87.0, 105.95)],
                  'PWR_VBAT_TAP')
        self.seg('VBAT', B, 0.25, [
            (88.55, 104.95), (88.1, 104.95), (87.7, 105.35), (87.65, 105.5)])
        self.via('VBAT', 87.65, 105.5)

        for t in self.to_remove:
            self.b.Remove(t)
        pcbnew.SaveBoard(BOARD_PATH, self.b)
        print('surgery saved')


def astar_phase():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'cr', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'complete_routes.py'))
    m = importlib.util.module_from_spec(spec)
    sys.modules['cr'] = m
    spec.loader.exec_module(m)
    c = m.Completer()
    links = [
        ('CC2',      (88.55, 102.45), (98.25, 109.555), 0.15, 1, 1),
        ('SHPHLD',   (89.75, 106.65), (110.9, 95.51), 0.15, 1, 1),
        ('DISP_SCK', (95.35, 93.5), (87.05, 110.65), 0.15, 1, 0),
        ('VBAT',     (88.55, 104.95), (87.7473, 99.4553), 0.25, 1, 0),
    ]
    fails = 0
    for net, st, g, w, sl, gl in links:
        path = c.route(net, st, g, width=w, start_layer=sl, goal_layer=gl)
        if path is None:
            print(f'!! no path for {net}')
            fails += 1
            continue
        c.emit(net, path, st, g, width=w)
        print(f'{net}: routed {len(path)} cells')
    c.save()
    return fails


RIP_NETS = ('CC1', 'CC2', 'VBUS_OUT', 'I2C_SDA', 'I2C_SCL', 'NTC',
            'SHPHLD', 'N$2', 'N$4')


def rip_phase():
    b = pcbnew.LoadBoard(BOARD_PATH)
    doomed = []
    for t in b.GetTracks():
        if t.GetNetname() in RIP_NETS and not t.IsLocked():
            doomed.append(t)
    for t in doomed:
        b.Remove(t)
    print(f'ripped {len(doomed)} items from {len(RIP_NETS)} tangled nets')
    pcbnew.SaveBoard(BOARD_PATH, b)


def astar2_phase():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'cr', os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'complete_routes.py'))
    m = importlib.util.module_from_spec(spec)
    sys.modules['cr'] = m
    spec.loader.exec_module(m)
    c = m.Completer()
    # (net, start, goal, width, s_layer, g_layer) — most-constrained first
    links = [
        ('3V0',      (91.25, 106.65), (91.75, 100.97), 0.15, 1, 1),
        ('I2C_SDA',  (90.75, 106.65), (93.6, 97.38), 0.15, 1, 1),
        ('I2C_SCL',  (90.25, 106.65), (92.2, 97.38), 0.15, 1, 1),
        ('NTC',      (88.55, 105.45), (84.3, 93.2), 0.15, 1, 1),
        ('VBUS_OUT', (88.55, 103.45), (92.72, 98.6), 0.2, 1, 1),
        ('VBUS_OUT', (93.68, 98.6), (96.0, 97.7), 0.2, 1, 1),
        ('N$2',      (88.55, 105.95), (109.04, 101.5), 0.15, 1, 1),
        ('N$4',      (89.25, 106.65), (109.04, 103.2), 0.15, 1, 1),
        ('CC1',      (88.55, 102.95), (101.25, 109.555), 0.15, 1, 1),
        ('CC2',      (88.55, 102.45), (98.25, 109.555), 0.15, 1, 1),
        ('SHPHLD',   (89.75, 106.65), (110.9, 95.51), 0.15, 1, 1),
    ]
    fails = []
    for net, st, g, w, sl, gl in links:
        path = c.route(net, st, g, width=w, start_layer=sl, goal_layer=gl)
        if path is None:
            print(f'!! no path for {net} {st}->{g}')
            fails.append(net)
            continue
        c.emit(net, path, st, g, width=w)
        c.save()          # persist so the next net's raster sees this one
        c = m.Completer() # fresh handles (SWIG)
        print(f'{net}: routed {len(path)} cells')
    print('fails:', fails or 'none')


if __name__ == '__main__':
    phase = sys.argv[1]
    if phase == 'surgery':
        Surgeon().run()
    elif phase == 'astar':
        astar_phase()
    elif phase == 'rip':
        rip_phase()
    elif phase == 'astar2':
        astar2_phase()
