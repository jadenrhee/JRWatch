#!/usr/bin/env python3
"""Dump every copper item (tracks, vias, pads) inside a window of the live
board, with nets and layers. Read-only. Usage:
  survey.py <x1> <y1> <x2> <y2> [netfilter]
"""
import sys
import pcbnew

BOARD = "/Users/jadenrhee/JRWatch/hardware/jrwatch.kicad_pcb"

def mm(nm):
    return nm / 1e6

def main():
    x1, y1, x2, y2 = (float(a) for a in sys.argv[1:5])
    netfilter = sys.argv[5] if len(sys.argv) > 5 else None
    b = pcbnew.LoadBoard(BOARD)
    lname = b.GetLayerName

    def inwin(p):
        return x1 <= mm(p.x) <= x2 and y1 <= mm(p.y) <= y2

    print("== TRACKS/VIAS ==")
    for t in b.GetTracks():
        net = t.GetNetname()
        if netfilter and netfilter not in net:
            pass  # still show blockers; tag matches
        if t.GetClass() == "PCB_VIA":
            if not inwin(t.GetPosition()):
                continue
            p = t.GetPosition()
            print(f"VIA  ({mm(p.x):.3f},{mm(p.y):.3f}) drill={mm(t.GetDrillValue()):.2f} "
                  f"pad={mm(t.GetWidth(pcbnew.F_Cu)):.2f} net={net}")
        else:
            s, e = t.GetStart(), t.GetEnd()
            if not (inwin(s) or inwin(e)):
                continue
            print(f"TRK {lname(t.GetLayer()):5s} ({mm(s.x):.3f},{mm(s.y):.3f})->({mm(e.x):.3f},{mm(e.y):.3f}) "
                  f"w={mm(t.GetWidth()):.2f} net={net}{' LOCKED' if t.IsLocked() else ''}")

    print("== PADS ==")
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if not inwin(pad.GetPosition()):
                continue
            p = pad.GetPosition()
            sz = pad.GetSize(pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
            layers = []
            for L in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(L):
                    layers.append(lname(L))
            print(f"PAD {fp.GetReference()}.{pad.GetNumber():>3s} ({mm(p.x):.3f},{mm(p.y):.3f}) "
                  f"{mm(sz.x):.2f}x{mm(sz.y):.2f} [{','.join(layers)}] net={pad.GetNetname()}")

if __name__ == "__main__":
    main()
