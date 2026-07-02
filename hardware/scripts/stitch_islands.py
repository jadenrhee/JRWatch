#!/usr/bin/env python3
"""Find GND fill islands that lack any through connection to the In2 plane
and stitch them with vias where clearance allows. Usage:
  stitch_islands.py scan    - report islands and whether they hold pads/vias
  stitch_islands.py fix     - add stitch vias (clearance-checked), refill, save
"""
import sys
import pcbnew

BOARD = "/Users/jadenrhee/JRWatch/hardware/jrwatch.kicad_pcb"
NM = pcbnew.FromMM
CLR = 0.13
VIA_PAD, VIA_DRILL = 0.45, 0.2
HOLE_TO_HOLE = 0.5

def mm(v):
    return v / 1e6

def island_info(b):
    """Return per-layer list of (polygon, gnd_pads, has_through)."""
    gnd = b.GetNetsByName()["GND"].GetNetCode()
    zones = {z.GetZoneName(): z for z in b.Zones()}
    out = []
    throughs = []   # (x, y) of GND vias and through pads
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetCode() == gnd:
            throughs.append(t.GetPosition())
    smd_pads = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() != gnd:
                continue
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                throughs.append(p.GetPosition())
            else:
                for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if p.IsOnLayer(L):
                        smd_pads[L].append(p)
    for zname, L in (("GND_FILL_F", pcbnew.F_Cu), ("GND_FILL_B", pcbnew.B_Cu)):
        z = zones[zname]
        polys = z.GetFilledPolysList(L)
        for i in range(polys.OutlineCount()):
            poly = polys.Polygon(i)
            single = pcbnew.SHAPE_POLY_SET(poly)
            pads_in = [p for p in smd_pads[L]
                       if single.Contains(pcbnew.VECTOR2I(p.GetPosition()))]
            thr_in = [t for t in throughs
                      if single.Contains(pcbnew.VECTOR2I(t))]
            bb = single.BBox()
            out.append((zname, i, mm(bb.GetWidth()) * mm(bb.GetHeight()),
                        [f"{p.GetParentFootprint().GetReference()}.{p.GetNumber()}"
                         for p in pads_in],
                        len(thr_in), single, pads_in, L))
    return out

def clear_at(b, x, y):
    """Conservative check: nothing but GND copper near the candidate via."""
    pos = pcbnew.VECTOR2I(NM(x), NM(y))
    gnd = b.GetNetsByName()["GND"].GetNetCode()
    r_pad = NM(VIA_PAD / 2 + CLR)
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            d = (t.GetPosition() - pos).EuclideanNorm()
            if d < NM(HOLE_TO_HOLE + VIA_DRILL / 2) + t.GetDrillValue() // 2:
                return False
            if t.GetNetCode() != gnd and d < r_pad + t.GetWidth(pcbnew.F_Cu) // 2:
                return False
        else:
            if t.GetNetCode() == gnd:
                continue
            seg = pcbnew.SEG(t.GetStart(), t.GetEnd())
            if seg.Distance(pos) < r_pad + t.GetWidth() // 2:
                return False
    for fp in b.GetFootprints():
        for p in fp.Pads():
            d = (p.GetPosition() - pos).EuclideanNorm()
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                if d < NM(HOLE_TO_HOLE + VIA_DRILL / 2) + \
                        max(p.GetDrillSize().x, p.GetDrillSize().y) // 2:
                    return False
            if p.GetNetCode() == gnd:
                continue
            sz = max(p.GetSize(pcbnew.F_Cu).x, p.GetSize(pcbnew.F_Cu).y)
            if d < r_pad + sz // 2 + NM(0.1):
                return False
    # keep-out areas and board interior margin
    for z in b.Zones():
        if z.GetIsRuleArea():
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if z.Outline().Contains(pos):
                    return False
    if not (83.2 < x < 116.8 and 83.2 < y < 116.8):
        return False
    return True

def main():
    b = pcbnew.LoadBoard(BOARD)
    infos = island_info(b)
    orphans = [x for x in infos if x[4] == 0]
    print(f"{len(infos)} islands total, {len(orphans)} without through connection")
    if sys.argv[1] == "scan":
        for zn, i, area, pads, nthr, _, _, _ in sorted(orphans, key=lambda r: -r[2]):
            print(f"  {zn}#{i} area~{area:.1f}mm2 pads={pads}")
        return
    gnd = b.GetNetsByName()["GND"]
    added = []
    for zn, i, area, padnames, nthr, poly, pads, L in orphans:
        placed = False
        anchors = [p.GetPosition() for p in pads]
        bb = poly.BBox()
        anchors.append(bb.Centre())
        for a in anchors:
            if placed:
                break
            import math
            cands = [(0.0, 0.0)]
            for r in (0.45, 0.6, 0.75, 0.9, 1.1, 1.3, 1.6, 2.0):
                for k in range(16):
                    th = k * math.pi / 8
                    cands.append((r * math.cos(th), r * math.sin(th)))
            for dx, dy in cands:
                x, y = mm(a.x) + dx, mm(a.y) + dy
                pt = pcbnew.VECTOR2I(NM(x), NM(y))
                if not poly.Contains(pt):
                    continue
                if any((pcbnew.VECTOR2I(NM(px), NM(py)) - pt).EuclideanNorm()
                       < NM(HOLE_TO_HOLE + VIA_DRILL) for px, py in added):
                    continue
                if clear_at(b, x, y):
                    v = pcbnew.PCB_VIA(b)
                    v.SetPosition(pt)
                    v.SetDrill(NM(VIA_DRILL))
                    v.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, NM(VIA_PAD))
                    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    v.SetNet(gnd)
                    b.Add(v)
                    added.append((x, y))
                    print(f"  stitched {zn}#{i} ({padnames}) at ({x:.2f},{y:.2f})")
                    placed = True
                    break
        if not placed:
            print(f"  NO SPOT for {zn}#{i} pads={padnames} area~{area:.1f}")
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(BOARD, b)
    print(f"added {len(added)} stitch vias, refilled, saved")

if __name__ == "__main__":
    main()
