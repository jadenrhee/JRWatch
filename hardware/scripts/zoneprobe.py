#!/usr/bin/env python3
"""List zones and test points against filled areas. Read-only.
Usage: zoneprobe.py [x y] — with a point, reports which filled zones cover it.
Without, lists all zones with layer/net/bbox/fill state.
"""
import sys
import pcbnew

BOARD = "/Users/jadenrhee/JRWatch/hardware/jrwatch.kicad_pcb"

def mm(nm):
    return nm / 1e6

b = pcbnew.LoadBoard(BOARD)
lname = b.GetLayerName

if len(sys.argv) >= 3:
    pt = pcbnew.VECTOR2I(pcbnew.FromMM(float(sys.argv[1])), pcbnew.FromMM(float(sys.argv[2])))
    for z in b.Zones():
        for L in z.GetLayerSet().CuStack():
            if z.HitTestFilledArea(L, pt, 0):
                bb = z.GetBoundingBox()
                print(f"HIT {lname(L):6s} net={z.GetNetname():10s} prio={z.GetAssignedPriority()} "
                      f"name='{z.GetZoneName()}'")
else:
    for z in b.Zones():
        bb = z.GetBoundingBox()
        layers = ",".join(lname(L) for L in z.GetLayerSet().CuStack())
        kind = "RULEAREA" if z.GetIsRuleArea() else "POUR"
        print(f"{kind:8s} [{layers}] net={z.GetNetname():10s} prio={z.GetAssignedPriority()} "
              f"bbox=({mm(bb.GetLeft()):.1f},{mm(bb.GetTop()):.1f})-({mm(bb.GetRight()):.1f},{mm(bb.GetBottom()):.1f}) "
              f"filled={z.IsFilled()} islands={z.GetIslandRemovalMode()} name='{z.GetZoneName()}'")
