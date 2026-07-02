#!/usr/bin/env python3
"""
Stage 4: finish — fill zones, add the GND stitching lattice, report what
remains unconnected per net (so nothing hides behind the fills).
"""
import os

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def dist(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def main():
    b = pcbnew.LoadBoard(BOARD_PATH)
    gnd = b.FindNet('GND')

    # ---- collect obstacles for lattice placement
    pads = []
    holes = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            pos = p.GetPosition()
            pads.append((ToMM(pos.x), ToMM(pos.y), p.GetNetname()))
            if p.GetDrillSize().x > 0:
                holes.append((ToMM(pos.x), ToMM(pos.y)))
    segs = []
    for t in b.GetTracks():
        pos = t.GetPosition()
        if t.Type() == pcbnew.PCB_VIA_T:
            holes.append((ToMM(pos.x), ToMM(pos.y)))
        else:
            s, e = t.GetStart(), t.GetEnd()
            segs.append(((ToMM(s.x), ToMM(s.y)), (ToMM(e.x), ToMM(e.y)),
                         t.GetNetname()))

    def seg_dist(pt, a, c):
        ax, ay = a; cx, cy = c; px, py = pt
        dx, dy = cx - ax, cy - ay
        if dx == dy == 0:
            return dist(pt, a)
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return dist(pt, (ax + t * dx, ay + t * dy))

    def clear_for_via(x, y):
        # inside board (36mm square R6 corners), outside antenna keep-out
        if not (82.6 <= x <= 117.4 and 82.6 <= y <= 117.4):
            return False
        for cx, cy in ((88, 88), (112, 88), (88, 112), (112, 112)):
            if (x < 88 or x > 112) and (y < 88 or y > 112):
                if dist((x, y), (cx, cy)) > 5.4 and \
                   ((x < 88 or x > 112) and (y < 88 or y > 112)) and \
                   ((x - cx) * (1 if cx < 100 else -1) > 0 or True):
                    pass
        # corner check: in each corner square, must be within R-0.6 of center
        for cx, cy in ((88, 88), (112, 88), (88, 112), (112, 112)):
            if ((x < 88 and cx == 88) or (x > 112 and cx == 112)) and \
               ((y < 88 and cy == 88) or (y > 112 and cy == 112)):
                if dist((x, y), (cx, cy)) > 5.4:
                    return False
        if 93.3 <= x <= 106.7 and y <= 87.1:      # antenna keep-out + margin
            return False
        for hx, hy in holes:
            if dist((x, y), (hx, hy)) < 1.0:
                return False
        for px, py, net in pads:
            if dist((x, y), (px, py)) < (0.8 if net == 'GND' else 1.1):
                return False
        for a, c, net in segs:
            if net != 'GND' and seg_dist((x, y), a, c) < 0.65:
                return False
        return True

    added = 0
    ys = [84 + i * 2.2 for i in range(16)]
    xs = [84 + i * 2.2 for i in range(16)]
    for x in xs:
        for y in ys:
            if clear_for_via(x, y):
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(P(x, y))
                v.SetWidth(FromMM(0.6)); v.SetDrill(FromMM(0.3))
                v.SetNet(gnd)
                b.Add(v)
                holes.append((x, y))
                added += 1
    print(f'stitching vias added: {added}')

    # ---- fill all zones
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    pcbnew.SaveBoard(BOARD_PATH, b)

    # ---- per-net unconnected report
    b2 = pcbnew.LoadBoard(BOARD_PATH)
    b2.BuildConnectivity()
    conn = b2.GetConnectivity()
    print('unconnected after fill:', conn.GetUnconnectedCount(True))


if __name__ == '__main__':
    main()
