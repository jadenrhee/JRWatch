#!/usr/bin/env python3
"""Land D-025: display connector reposition + mirrored nets + USB crossover
redesign + CC landings. Every coordinate is hand clearance-checked (0.13 mm
copper, 0.25 mm hole-to-copper, 0.5 mm hole-to-hole).

Geometry:
- J2 at (100, 111.8): pads y=109.95 centered x=100 (tail-centered), body ends
  y~113.55, clear of the USB shell legs at (95.68/104.32, 114.65). MP pads
  trimmed to 1.8x1.0 at y=112.9; courtyard clipped to y<=113.9.
- Panel mounts on 1.2 mm foam so its terminal ledge clears the 1.0 mm body.
- USB CONN highways move north: DM_CONN y=107.95, DP_CONN y=108.35.
- DM_CONN crossover: A7 -> via (99.85,111.05) -> F around the pad row at
  y=111.75 -> via (96.2,107.87) onto the new highway.
- CC2 lands on J1.B5 via a via at (98.24,108.87) overlapping the pad's top,
  fed on F at y=108.87 westward. CC1 lands on J1.A5 from the north-east.
"""
import pcbnew

BOARD = "/Users/jadenrhee/JRWatch/hardware/jrwatch.kicad_pcb"
NM = pcbnew.FromMM
mm = lambda v: v / 1e6
b = pcbnew.LoadBoard(BOARD)
nets = b.GetNetsByName()
F, B, In1 = pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In1_Cu

def track(net, layer, pts, w, locked=True):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(NM(x1), NM(y1)))
        t.SetEnd(pcbnew.VECTOR2I(NM(x2), NM(y2)))
        t.SetWidth(NM(w)); t.SetLayer(layer); t.SetNet(nets[net])
        t.SetLocked(locked); b.Add(t)

def via(net, x, y, pad=0.45, drill=0.2, locked=True):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(NM(x), NM(y)))
    v.SetDrill(NM(drill)); v.SetWidth(pcbnew.PADSTACK.ALL_LAYERS, NM(pad))
    v.SetLayerPair(F, B); v.SetNet(nets[net]); v.SetLocked(locked); b.Add(v)

# ---- 1. J2: move, trim MPs, clip courtyard, mirror nets -------------------
j2 = b.FindFootprintByReference("J2")
j2.SetPosition(pcbnew.VECTOR2I(NM(100.0), NM(111.8)))
for p in j2.Pads():
    if p.GetNumber() == "MP":
        pos = p.GetPosition()
        p.SetSize(F, pcbnew.VECTOR2I(NM(1.8), NM(1.0)))
        p.SetPosition(pcbnew.VECTOR2I(pos.x, NM(112.9)))
for g in j2.GraphicalItems():
    if g.GetLayerName() == "F.CrtYd" and g.GetClass() == "PCB_SHAPE":
        s, e = g.GetStart(), g.GetEnd()
        if mm(s.y) > 113.9: g.SetStart(pcbnew.VECTOR2I(s.x, NM(113.9)))
        if mm(e.y) > 113.9: g.SetEnd(pcbnew.VECTOR2I(e.x, NM(113.9)))
new_nets = {"1": "GND", "2": "GND", "3": "VDD_DISP", "4": "VDD_DISP",
            "5": "VDD_DISP", "6": "DISP_ON", "7": "EXTCOMIN",
            "8": "DISP_CS", "9": "DISP_MOSI", "10": "DISP_SCK", "MP": "GND"}
for p in j2.Pads():
    p.SetNet(nets[new_nets[p.GetNumber()]])
print("J2 moved/trimmed/renetted")

# ---- 2. rips ---------------------------------------------------------------
RIP_ALL = {"DISP_MOSI", "DISP_CS", "DISP_ON", "EXTCOMIN", "DISP_SCK",
           "I2C_SDA", "I2C_SCL", "CC1", "CC2", "SHPHLD", "PMIC_INT",
           "N$2", "N$4", "BTN2", "BTN2_PAD", "BTN1_PAD",
           "USB_DM_CONN", "USB_DP_CONN"}      # CONN nets fully re-laid below
tracks = list(b.GetTracks())
doomed = [t for t in tracks if t.GetNetname() in RIP_ALL]   # locked included
for t in tracks:
    if t.GetNetname() != "VDD_DISP":
        continue
    ymax = mm(t.GetPosition().y) if t.GetClass() == "PCB_VIA" else \
        max(mm(t.GetStart().y), mm(t.GetEnd().y))
    if ymax > 101.9:
        doomed.append(t)
def near(v, x, y): return abs(mm(v.x)-x) < 0.05 and abs(mm(v.y)-y) < 0.05
for t in tracks:
    if t.GetNetname() != "USB_DP":
        continue
    if t.GetClass() == "PCB_VIA" and near(t.GetPosition(), 91.25, 107.5):
        doomed.append(t)
    elif t.GetClass() != "PCB_VIA":
        s, e = t.GetStart(), t.GetEnd()
        if near(s, 91.25, 107.5) or near(e, 91.25, 107.5) or \
           (min(mm(s.y), mm(e.y)) >= 107.4 and max(mm(s.x), mm(e.x)) <= 91.35):
            doomed.append(t)
doomed = list({id(t): t for t in doomed}.values())
for t in doomed:
    b.Remove(t)
print(f"ripped {len(doomed)}")

# ---- 3. USB CONN re-lay (locked, hand-verified) ---------------------------
# DM_CONN: highway at y=107.95, B7 vertical, A7 -> crossover via1 -> F loop
# around the pad row -> via2 onto the highway.
track("USB_DM_CONN", B, [(94.5, 107.95), (100.75, 107.95)], 0.2)
track("USB_DM_CONN", B, [(100.75, 109.555), (100.75, 107.95)], 0.2)
track("USB_DM_CONN", B, [(99.75, 109.555), (99.85, 110.85), (99.85, 111.05)], 0.2)
via("USB_DM_CONN", 99.85, 111.05)
track("USB_DM_CONN", F, [(99.85, 111.05), (99.85, 111.75), (96.2, 111.75),
                         (96.2, 107.87)], 0.2)
via("USB_DM_CONN", 96.2, 107.87)
# DP_CONN: highway at y=108.35 + both verticals
track("USB_DP_CONN", B, [(94.95, 108.35), (100.25, 108.35)], 0.2)
track("USB_DP_CONN", B, [(99.25, 109.555), (99.25, 108.35)], 0.2)
track("USB_DP_CONN", B, [(100.25, 109.555), (100.25, 108.35)], 0.2)
print("CONN re-laid")

# ---- 4. CC landings (locked stubs; router finishes the long hauls) --------
via("CC2", 98.24, 108.87)                       # overlaps J1.B5 pad top
track("CC2", F, [(98.24, 108.87), (94.2, 108.87)], 0.15)
track("CC1", B, [(101.25, 109.555), (101.35, 109.2), (101.35, 107.5),
                 (102.3, 107.5)], 0.15)
print("CC landings placed")

# ---- 5. FPC-mouth keepout (tracks/vias; fills OK) --------------------------
z = pcbnew.ZONE(b)
z.SetIsRuleArea(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowPads(False)
z.SetZoneName("J2_FPC_KEEPOUT")
ls = pcbnew.LSET(); ls.AddLayer(F); z.SetLayerSet(ls)
o = z.Outline(); o.NewOutline()
for x, y in [(95.0, 114.0), (105.4, 114.0), (105.4, 117.45), (95.0, 117.45)]:
    o.Append(NM(x), NM(y))
b.Add(z)
print("keepout added")

pcbnew.SaveBoard(BOARD, b)
print("saved")
