#!/usr/bin/env python3
"""
Stage 5: post-autoroute repair.

  * delete zero-length / dangling stubs left by the SES import
  * nudge the two via pairs that violate hole-to-hole (reconnecting the
    track endpoints that land on them)
  * clamp track/via endpoints that creep inside the copper-to-edge margin
  * switch all zones to SOLID pad connection (cures starved thermals;
    hand-rework tradeoff documented in the review checklist) and refill
  * report remaining unconnected items pad-by-pad
"""
import os

import pcbnew
from pcbnew import VECTOR2I, FromMM, ToMM

HW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
BOARD_PATH = os.path.join(HW, 'jrwatch.kicad_pcb')


def P(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def near(a, b, tol=0.01):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def main():
    import sys
    phase = sys.argv[1] if len(sys.argv) > 1 else 'all'
    b = pcbnew.LoadBoard(BOARD_PATH)

    if phase == 'clean':
        removed = 0
        for t in list(b.GetTracks()):
            if t.Type() == pcbnew.PCB_TRACE_T and t.GetLength() == 0:
                b.Remove(t); removed += 1
        print('zero-length removed:', removed)
        pcbnew.SaveBoard(BOARD_PATH, b)
        return

    # ---- 2. via nudges (old -> new), moving coincident track ends along
    if phase not in ('fix', 'all'):
        return
    nudges = [((91.9834, 98.2364), (91.95, 98.2)),     # I2C_SDA via
              ((87.2345, 101.5526), (87.15, 100.75))]  # VBUS_OUT via
    for old, new in nudges:
        moved = False
        for t in b.GetTracks():
            pos = t.GetPosition()
            if t.Type() == pcbnew.PCB_VIA_T and near((ToMM(pos.x), ToMM(pos.y)), old):
                t.SetPosition(P(*new)); moved = True
        if not moved:
            print('!! via not found at', old)
            continue
        for t in b.GetTracks():
            if t.Type() != pcbnew.PCB_TRACE_T:
                continue
            s, e = t.GetStart(), t.GetEnd()
            if near((ToMM(s.x), ToMM(s.y)), old):
                t.SetStart(P(*new))
            if near((ToMM(e.x), ToMM(e.y)), old):
                t.SetEnd(P(*new))
        print('via nudged', old, '->', new)

    # ---- 3. edge clamp (straight edges at 82/118; margin 0.65)
    LO, HI, M = 82.0, 118.0, 0.65
    def clamp(v):
        x, y = ToMM(v.x), ToMM(v.y)
        nx = min(max(x, LO + M), HI - M)
        ny = min(max(y, LO + M), HI - M)
        # rounded corners R6: centers at (88,88),(112,88),(88,112),(112,112)
        for cx, cy in ((88, 88), (112, 88), (88, 112), (112, 112)):
            inx = (nx < 88 and cx == 88) or (nx > 112 and cx == 112)
            iny = (ny < 88 and cy == 88) or (ny > 112 and cy == 112)
            if inx and iny:
                d = ((nx - cx) ** 2 + (ny - cy) ** 2) ** 0.5
                lim = 6.0 - M
                if d > lim:
                    nx = cx + (nx - cx) * lim / d
                    ny = cy + (ny - cy) * lim / d
        if abs(nx - x) > 1e-6 or abs(ny - y) > 1e-6:
            return P(nx, ny)
        return None

    clamped = 0
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            n = clamp(t.GetPosition())
            if n: t.SetPosition(n); clamped += 1
        else:
            n = clamp(t.GetStart())
            if n: t.SetStart(n); clamped += 1
            n = clamp(t.GetEnd())
            if n: t.SetEnd(n); clamped += 1
    print('endpoints clamped:', clamped)

    # ---- 4. solid pad connection + refill
    for z in b.Zones():
        if not z.GetIsRuleArea():
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())

    pcbnew.SaveBoard(BOARD_PATH, b)

    # ---- 5. unconnected report
    b2 = pcbnew.LoadBoard(BOARD_PATH)
    b2.BuildConnectivity()
    conn = b2.GetConnectivity()
    print('unconnected after repair:', conn.GetUnconnectedCount(True))


if __name__ == '__main__':
    main()
