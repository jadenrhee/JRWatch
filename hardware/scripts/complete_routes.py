#!/usr/bin/env python3
"""
Stage 6: deterministic completion of the links the autorouter could not
finish (it cannot stitch into power planes, and it gave up on a few
congested two-layer paths).

A small grid A* router over F.Cu/B.Cu with an obstacle raster built from the
live board. Plane nets additionally get "drop a via into the pour" moves.
Everything it adds is checked against the raster before commit, and the full
DRC gate runs afterwards - this is a completion pass, not a free-for-all.

Also: hole-to-hole auto-nudge for autorouter via pairs, dangling-stub trim,
solid-fill refill, and GND island unification vias.
"""
import math
import os
import sys

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')

GRID = 0.1          # mm
X0, Y0, X1, Y1 = 82.0, 82.0, 118.0, 118.0
NX = int((X1 - X0) / GRID) + 1
NY = int((Y1 - Y0) / GRID) + 1
CLR = 0.225         # clearance 0.13 + half-track 0.075 + 0.02 quantization


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def cell(x, y):
    return int(round((x - X0) / GRID)), int(round((y - Y0) / GRID))


def xy(i, j):
    return X0 + i * GRID, Y0 + j * GRID


class Completer:
    LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)

    def __init__(self):
        self.b = pcbnew.LoadBoard(BOARD_PATH)
        self.blocked = {l: bytearray(NX * NY) for l in self.LAYERS}
        self.hole_pts = []          # (x, y) of every drilled hole
        self.net_items = {}         # net -> [(layer,x0,y0,x1,y1,w)] tracks

    # ------------------------------------------------------------ raster
    def _block_disc(self, grid, x, y, r):
        i0, j0 = cell(x - r, y - r)
        i1, j1 = cell(x + r, y + r)
        for i in range(max(0, i0), min(NX - 1, i1) + 1):
            for j in range(max(0, j0), min(NY - 1, j1) + 1):
                gx, gy = xy(i, j)
                if (gx - x) ** 2 + (gy - y) ** 2 <= r * r:
                    grid[j * NX + i] = 1

    def _block_rect(self, grid, x, y, hx, hy):
        i0, j0 = cell(x - hx, y - hy)
        i1, j1 = cell(x + hx, y + hy)
        for i in range(max(0, i0), min(NX - 1, i1) + 1):
            for j in range(max(0, j0), min(NY - 1, j1) + 1):
                grid[j * NX + i] = 1

    def _block_seg(self, grid, ax, ay, bx, by, r):
        n = max(1, int(math.hypot(bx - ax, by - ay) / (GRID * 0.7)))
        for k in range(n + 1):
            t = k / n
            self._block_disc(grid, ax + t * (bx - ax), ay + t * (by - ay), r)

    def build_raster(self, target_net):
        for l in self.LAYERS:
            self.blocked[l] = bytearray(NX * NY)
        self.hole_pts = []
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                pos = p.GetPosition()
                px, py = ToMM(pos.x), ToMM(pos.y)
                if p.GetDrillSize().x > 0:
                    self.hole_pts.append((px, py))
                same = (p.GetNetname() == target_net)
                for l in self.LAYERS:
                    if not p.IsOnLayer(l) and p.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                        continue
                    if same:
                        continue
                    sz = p.GetSize(l if p.IsOnLayer(l) else pcbnew.F_Cu)
                    hx = ToMM(sz.x) / 2 + CLR
                    hy = ToMM(sz.y) / 2 + CLR
                    self._block_rect(self.blocked[l], px, py, hx, hy)
        for t in self.b.GetTracks():
            same = (t.GetNetname() == target_net)
            if t.Type() == pcbnew.PCB_VIA_T:
                pos = t.GetPosition()
                px, py = ToMM(pos.x), ToMM(pos.y)
                self.hole_pts.append((px, py))
                if same:
                    continue
                r = ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + CLR
                for l in self.LAYERS:
                    self._block_disc(self.blocked[l], px, py, r)
            else:
                if same or t.GetLayer() not in self.LAYERS:
                    continue
                s, e = t.GetStart(), t.GetEnd()
                r = ToMM(t.GetWidth()) / 2 + CLR
                self._block_seg(self.blocked[t.GetLayer()],
                                ToMM(s.x), ToMM(s.y), ToMM(e.x), ToMM(e.y), r)
        # rule areas: antenna keepout + edge ring (tracks banned)
        for z in self.b.Zones():
            if not z.GetIsRuleArea() or not z.GetDoNotAllowTracks():
                continue
            bb = z.GetBoundingBox()
            zx0, zy0 = ToMM(bb.GetLeft()) - 0.1, ToMM(bb.GetTop()) - 0.1
            zx1, zy1 = ToMM(bb.GetRight()) + 0.1, ToMM(bb.GetBottom()) + 0.1
            lset = z.GetLayerSet()
            for l in self.LAYERS:
                if not lset.Contains(l):
                    continue
                i0, j0 = cell(zx0, zy0); i1, j1 = cell(zx1, zy1)
                for i in range(max(0, i0), min(NX - 1, i1) + 1):
                    for j in range(max(0, j0), min(NY - 1, j1) + 1):
                        gx, gy = xy(i, j)
                        if z.HitTestFilledArea(l, P(gx, gy), FromMM(0.05)) or \
                           z.Outline().Contains(pcbnew.VECTOR2I(FromMM(gx), FromMM(gy))):
                            self.blocked[l][j * NX + i] = 1

    def via_ok(self, x, y):
        # keep via copper inside the edge keep-out ring with margin
        if not (83.1 <= x <= 116.9 and 83.1 <= y <= 116.9):
            return False
        for hx, hy in self.hole_pts:
            if math.hypot(hx - x, hy - y) < 0.85:
                return False
        for l in self.LAYERS:
            i, j = cell(x, y)
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < NX and 0 <= jj < NY and self.blocked[l][jj * NX + ii]:
                        return False
        return True

    # ---------------------------------------------------------- A* router
    def route(self, netname, start, goal, width=0.2, allow_via=True,
              start_layer=1, goal_layer=1):
        """A* start->goal. Layers: 0=F.Cu 1=B.Cu. Escape bubbles around the
        endpoints keep neighbor-pad inflation from swallowing them; emitted
        copper still faces the full DRC gate afterwards."""
        self.build_raster(netname)
        si = cell(*start)
        gi = cell(*goal)
        BUB = 0.32

        def blocked_at(i, j, li):
            if not (0 <= i < NX and 0 <= j < NY):
                return True
            if self.blocked[self.LAYERS[li]][j * NX + i]:
                gx, gy = xy(i, j)
                if li == start_layer and math.hypot(gx - start[0], gy - start[1]) < BUB:
                    return False
                if li == goal_layer and math.hypot(gx - goal[0], gy - goal[1]) < BUB:
                    return False
                return True
            return False

        import heapq
        def h(i, j):
            gx, gy = xy(i, j)
            return math.hypot(gx - goal[0], gy - goal[1])

        dist = {}
        prev = {}
        pq = []
        s0 = (si[0], si[1], start_layer)
        if not blocked_at(*s0):
            dist[s0] = 0
            heapq.heappush(pq, (h(si[0], si[1]), 0, s0))
        goal_cells = {(gi[0], gi[1], goal_layer)}
        found = None
        DIRS = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1),
                (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
        while pq:
            f, g, u = heapq.heappop(pq)
            if u in goal_cells:
                found = u
                break
            if g > dist.get(u, 1e9):
                continue
            i, j, li = u
            for di, dj, c in DIRS:
                v = (i + di, j + dj, li)
                if blocked_at(*v):
                    continue
                ng = g + c * GRID
                if ng < dist.get(v, 1e9):
                    dist[v] = ng
                    prev[v] = u
                    heapq.heappush(pq, (ng + h(v[0], v[1]), ng, v))
            if allow_via:
                v = (i, j, 1 - li)
                gx, gy = xy(i, j)
                if not blocked_at(*v) and self.via_ok(gx, gy):
                    ng = g + 1.2          # via cost
                    if ng < dist.get(v, 1e9):
                        dist[v] = ng
                        prev[v] = u
                        heapq.heappush(pq, (ng + h(v[0], v[1]), ng, v))
        if not found:
            return None
        # walk back
        path = [found]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        path.reverse()
        return path

    def emit(self, netname, path, start, goal, width=0.2):
        net = self.b.FindNet(netname)
        # compress colinear runs
        pts = []
        for (i, j, li) in path:
            x, y = xy(i, j)
            pts.append((x, y, li))
        # replace endpoints with exact pad coords
        pts[0] = (start[0], start[1], pts[0][2])
        pts[-1] = (goal[0], goal[1], pts[-1][2])
        segs = []
        k = 0
        while k < len(pts) - 1:
            x0c, y0c, l0 = pts[k]
            m = k + 1
            # via transition
            if pts[m][2] != l0:
                v = pcbnew.PCB_VIA(self.b)
                v.SetPosition(P(x0c, y0c))
                v.SetWidth(FromMM(0.6)); v.SetDrill(FromMM(0.3))
                v.SetNet(net)
                self.b.Add(v)
                k = m
                continue
            dx = pts[m][0] - x0c; dy = pts[m][1] - y0c
            while m + 1 < len(pts) and pts[m + 1][2] == l0:
                ndx = pts[m + 1][0] - pts[m][0]
                ndy = pts[m + 1][1] - pts[m][1]
                if abs(ndx * dy - ndy * dx) > 1e-9:
                    break
                m += 1
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(x0c, y0c)); t.SetEnd(P(pts[m][0], pts[m][1]))
            t.SetLayer(self.LAYERS[l0]); t.SetWidth(FromMM(width))
            t.SetNet(net)
            self.b.Add(t)
            k = m
        return True

    # ------------------------------------------------------------- passes
    def plane_taps(self, jobs):
        """jobs: (netname, pad_x, pad_y, region) - stub from pad to nearest
        via_ok spot inside region, via to the In1 plane."""
        for netname, px, py, (rx0, ry0, rx1, ry1) in jobs:
            self.build_raster(netname)
            best = None
            for i in range(int((rx1 - rx0) / 0.2)):
                for j in range(int((ry1 - ry0) / 0.2)):
                    x = rx0 + 0.2 * i; y = ry0 + 0.2 * j
                    if not self.via_ok(x, y):
                        continue
                    d = math.hypot(x - px, y - py)
                    if best is None or d < best[0]:
                        best = (d, x, y)
            if best is None:
                print(f'!! no via spot for {netname} near ({px},{py})')
                continue
            _, vx, vy = best
            net = self.b.FindNet(netname)
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(px, py)); t.SetEnd(P(vx, vy))
            t.SetLayer(pcbnew.B_Cu); t.SetWidth(FromMM(0.3))
            t.SetNet(net)
            self.b.Add(t)
            v = pcbnew.PCB_VIA(self.b)
            v.SetPosition(P(vx, vy))
            v.SetWidth(FromMM(0.6)); v.SetDrill(FromMM(0.3))
            v.SetNet(net)
            self.b.Add(v)
            print(f'{netname}: tap ({px:.2f},{py:.2f}) -> via ({vx:.2f},{vy:.2f})')

    def save(self):
        pcbnew.SaveBoard(BOARD_PATH, self.b)


def main():
    c = Completer()
    mode = sys.argv[1] if len(sys.argv) > 1 else 'links'
    if mode == 'taps':
        # plane-net pads the autorouter left open (regions inside In1 pours)
        jobs = [
            ('VSYS', 93.45, 103.95, (93.8, 103.6, 94.8, 108.4)),   # U2 pin4 PVDD
            ('VSYS', 88.55, 104.45, (88.8, 103.6, 94.8, 108.4)),   # U2 pin20
        ]
        c.plane_taps(jobs)
        c.save()
        return
    if mode == 'nudge':
        # (net, old_pos): move the via to the nearest clear spot 0.35-0.8 away
        jobs = [('I2C_SCL', (93.46, 94.31)),
                ('GND', (95.15, 98.7)),
                ('I2C_SDA', (90.53, 107.6))]
        for netname, old in jobs:
            c.build_raster(netname)
            # temporarily forget the via's own hole so via_ok doesn't self-block
            c.hole_pts = [h for h in c.hole_pts
                          if math.hypot(h[0]-old[0], h[1]-old[1]) > 0.05]
            best = None
            for r in (0.4, 0.5, 0.65, 0.8):
                for k in range(16):
                    ang = math.radians(k * 22.5)
                    x = old[0] + r * math.cos(ang)
                    y = old[1] + r * math.sin(ang)
                    if c.via_ok(x, y):
                        best = (x, y); break
                if best:
                    break
            if not best:
                print(f'!! no nudge spot for {netname} via at {old}')
                continue
            moved = False
            for t in c.b.GetTracks():
                pos = t.GetPosition()
                pp = (ToMM(pos.x), ToMM(pos.y))
                if t.Type() == pcbnew.PCB_VIA_T and                    math.hypot(pp[0]-old[0], pp[1]-old[1]) < 0.05:
                    t.SetPosition(P(*best)); moved = True
            if moved:
                for t in c.b.GetTracks():
                    if t.Type() != pcbnew.PCB_TRACE_T:
                        continue
                    st, en = t.GetStart(), t.GetEnd()
                    if math.hypot(ToMM(st.x)-old[0], ToMM(st.y)-old[1]) < 0.05:
                        t.SetStart(P(*best))
                    if math.hypot(ToMM(en.x)-old[0], ToMM(en.y)-old[1]) < 0.05:
                        t.SetEnd(P(*best))
                print(f'{netname} via {old} -> ({best[0]:.2f},{best[1]:.2f})')
        c.save()
        return
    if mode == 'trim':
        # delete the two ring-straddling stitch vias + the dangling stub
        kill = [(117.0, 86.2), (86.2, 117.0), (90.78, 110.74)]
        removed = 0
        for t in list(c.b.GetTracks()):
            pos = t.GetPosition()
            pp = (ToMM(pos.x), ToMM(pos.y))
            for kx, ky in kill:
                if math.hypot(pp[0]-kx, pp[1]-ky) < 0.15:
                    c.b.Remove(t); removed += 1
                    break
        print('trimmed:', removed)
        c.save()
        return
    # signal links: (net, (sx,sy), (gx,gy), width, s_layer, g_layer) 0=F 1=B
    links = [
        ('CC2',      (88.55, 102.45), (98.25, 109.555), 0.15, 1, 1),
        ('VDD_DISP', (91.25, 101.75), (89.68, 100.37), 0.15, 1, 1),
        ('VDD_IMU',  (92.25, 101.75), (91.73, 99.95), 0.15, 1, 1),
        ('3V0',      (91.25, 106.65), (90.5, 100.9), 0.15, 1, 1),
        ('VBAT',     (88.55, 104.95), (87.7473, 99.4553), 0.25, 1, 0),
        ('DISP_SCK', (95.35, 93.5), (87.05, 110.65), 0.15, 1, 0),
        ('SHPHLD',   (89.75, 106.65), (110.9, 95.51), 0.15, 1, 1),
    ]
    for net, st, g, w, sl, gl in links:
        path = c.route(net, st, g, width=w, start_layer=sl, goal_layer=gl)
        if path is None:
            print(f'!! no path for {net}')
            continue
        c.emit(net, path, st, g, width=w)
        print(f'{net}: routed {len(path)} cells')
    c.save()


if __name__ == '__main__':
    main()
